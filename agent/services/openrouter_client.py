"""OpenRouter chat completions client for Lambda model calls."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import json
import re
import time
from typing import Any

import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class OpenRouterModel:
    """Validated OpenRouter provider and model identifiers."""

    model_id: str
    provider_id: str = "openrouter"


@dataclass(frozen=True)
class OpenRouterGeneration:
    """Provider-attested text and the upstream model that generated it."""

    text: str
    resolved_model: str


def parse_openrouter_model(model_name: str) -> OpenRouterModel:
    """Parse the required openrouter/provider-model configuration."""
    provider, separator, model_id = model_name.partition("/")
    if provider != "openrouter" or not separator or not model_id:
        raise ValueError("Model must use openrouter/provider-model format")
    return OpenRouterModel(model_id=model_id)


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter cannot return usable model output."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class OpenRouterClient:
    """Small async client for OpenRouter chat completions."""

    def __init__(
        self,
        *,
        api_key: str,
        max_tokens: int,
        base_url: str = OPENROUTER_BASE_URL,
        timeout: float = 120.0,
        total_timeout: float | None = None,
        deadline: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 2,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if total_timeout is not None and total_timeout <= 0:
            raise ValueError("total_timeout must be greater than zero")
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.total_timeout = total_timeout
        self.transport = transport
        self.max_attempts = max_attempts
        self.clock = clock
        self._deadline = deadline
        self._total_timeout_applied = False

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: OpenRouterModel,
        title: str,
    ) -> OpenRouterGeneration:
        """Generate text and retain OpenRouter's resolved upstream model."""
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self.transport,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Title": title,
            },
        ) as client:
            for attempt in range(self.max_attempts):
                try:
                    async with asyncio.timeout(self._remaining_timeout()):
                        response = await client.post(
                            "/chat/completions",
                            json={
                                "model": model.model_id,
                                "max_tokens": self.max_tokens,
                                "stream": False,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                            },
                        )
                    self._raise_for_status(response)
                    return self._extract_generation(self._decode_payload(response))
                except TimeoutError as exc:
                    error = OpenRouterError(
                        "OpenRouter request deadline exceeded",
                        retryable=True,
                    )
                    if attempt + 1 >= self.max_attempts:
                        raise error from exc
                except httpx.RequestError as exc:
                    error = OpenRouterError("OpenRouter request failed", retryable=True)
                    if attempt + 1 >= self.max_attempts:
                        raise error from exc
                except OpenRouterError as error:
                    if not error.retryable or attempt + 1 >= self.max_attempts:
                        raise

        raise OpenRouterError("OpenRouter request failed")

    def _remaining_timeout(self) -> float:
        """Return this attempt's limit within all workflow runtime budgets."""
        now = self.clock()
        if self.total_timeout is not None and not self._total_timeout_applied:
            total_deadline = now + self.total_timeout
            self._deadline = (
                total_deadline if self._deadline is None else min(self._deadline, total_deadline)
            )
            self._total_timeout_applied = True

        if self._deadline is None:
            return self.timeout

        remaining = self._deadline - now
        if remaining <= 0:
            raise OpenRouterError("OpenRouter total request budget exceeded")
        return min(self.timeout, remaining)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        raise OpenRouterError(
            f"OpenRouter chat completion failed: HTTP {response.status_code}",
            retryable=response.status_code in {408, 429, 502, 503, 504},
        )

    def _decode_payload(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise OpenRouterError("OpenRouter returned invalid JSON", retryable=True) from exc
        if not isinstance(payload, dict):
            raise OpenRouterError("OpenRouter returned invalid JSON", retryable=True)
        return payload

    def _extract_generation(self, payload: dict[str, Any]) -> OpenRouterGeneration:
        error = payload.get("error")
        if isinstance(error, dict):
            raise self._provider_error(error)

        resolved_model = payload.get("model")
        if not isinstance(resolved_model, str):
            raise OpenRouterError(
                "OpenRouter response did not include resolved model identity",
                retryable=True,
            )
        resolved_model = resolved_model.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{1,255}", resolved_model):
            raise OpenRouterError(
                "OpenRouter response included invalid resolved model identity",
                retryable=True,
            )

        choices = payload.get("choices")
        if not isinstance(choices, list):
            raise OpenRouterError(
                "OpenRouter response did not include choices",
                retryable=True,
            )

        text_parts = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            choice_error = choice.get("error")
            if isinstance(choice_error, dict) or choice.get("finish_reason") == "error":
                raise self._provider_error(choice_error or {})
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    text_parts.append(content)

        if text_parts:
            return OpenRouterGeneration(
                text="\n".join(text_parts),
                resolved_model=resolved_model,
            )

        raise OpenRouterError(
            "OpenRouter response did not include text output",
            retryable=True,
        )

    def _provider_error(self, error: dict[str, Any]) -> OpenRouterError:
        code = error.get("code", "unknown")
        metadata = error.get("metadata")
        error_type = metadata.get("error_type") if isinstance(metadata, dict) else None
        retryable_codes = {408, 429, 502, 503, 504}
        retryable_types = {
            "provider_overloaded",
            "provider_unavailable",
            "rate_limit_exceeded",
            "timeout",
        }
        return OpenRouterError(
            f"OpenRouter generation failed: {code}",
            retryable=code in retryable_codes or error_type in retryable_types,
        )
