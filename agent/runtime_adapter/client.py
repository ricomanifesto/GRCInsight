"""Minimal synchronous client for a leased workflow HTTP API.

One client per role per process, explicitly closed. Each request has its own
timeout. Nothing here is bound to an event loop, so the worker can run each
attempt under its own ``asyncio.run`` and the heartbeat thread can own a second
client (``clone()``) whose close never affects the worker's.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from typing import Any, Callable
from urllib.parse import urlsplit
import uuid

import httpx

DEFAULT_TIMEOUT_SECONDS = 5.0
# Proxy and certificate variables from the environment are never consulted.
CLIENT_TRUSTS_ENVIRONMENT = False


class RuntimeClientError(Exception):
    """A Runtime response or transport failure, classified by HTTP contract."""

    def __init__(self, code: str, status: int | None = None, *, existing_run_id: str | None = None):
        super().__init__(f"{code} ({status})" if status is not None else code)
        self.code = code
        self.status = status
        self.existing_run_id = existing_run_id


class LeaseFenced(RuntimeClientError):
    """409 lease_fenced: the caller no longer owns the run lease (terminal for it)."""


class IdempotencyConflict(RuntimeClientError):
    """409 idempotency_conflict: the key belongs to a run with a different request."""


class RunNotFound(RuntimeClientError):
    """404 run_not_found."""


class InvalidRuntimeRequest(RuntimeClientError):
    """400 invalid_request: the adapter sent something outside the contract."""


class RuntimeDraining(RuntimeClientError):
    """503 runtime_draining: the Runtime is shutting down and admits no new work."""


class RuntimeUnavailable(RuntimeClientError):
    """Connection failure, timeout, 5xx or a response outside the contract."""


class ClientClosed(RuntimeClientError):
    """The client was already closed: a programming error, never retried."""


@dataclass(frozen=True)
class SubmitOutcome:
    created: bool
    run: dict[str, Any]


def validate_loopback_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
        port = parsed.port
    except ValueError as error:
        raise ValueError("runtime URL must use a numeric loopback address and port") from error
    if (
        parsed.scheme != "http"
        or not address.is_loopback
        or port is None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("runtime URL must be http://<numeric loopback>:<port> in local mode")
    return base_url.rstrip("/")


def _run_path(run_id: str, suffix: str = "") -> str:
    try:
        canonical = str(uuid.UUID(run_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("run_id must be a UUID") from error
    return f"/v1/runs/{canonical}{suffix}"


class _BorrowedTransport(httpx.BaseTransport):
    """Delegates to a caller-owned transport; closing the client never closes it."""

    def __init__(self, transport: httpx.BaseTransport):
        self._transport = transport

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._transport.handle_request(request)

    def close(self) -> None:
        """The caller that supplied the transport closes it."""


def _default_transport() -> httpx.BaseTransport:
    # httpx transports read TLS settings (SSL_CERT_FILE, SSL_CERT_DIR, SSLKEYLOGFILE)
    # from the environment unless told otherwise; Client(trust_env=False) does not
    # reach a separately constructed transport.
    return httpx.HTTPTransport(trust_env=CLIENT_TRUSTS_ENVIRONMENT)


class RuntimeClient:
    """Runtime HTTP client with an explicit transport ownership contract.

    - Owned (default, or ``transport_factory``): the client creates its transport
      and closes it exactly once, on its first ``close()``. ``clone()`` creates a
      new owned transport, so closing one client never affects a sibling. The
      default transport, like the client, never reads proxy or TLS settings
      from the environment; a caller-supplied factory is responsible for its own.
    - Borrowed (``transport``): the caller keeps ownership. No client, clone or
      close order ever closes it; the caller closes it after its last client.

    A closed client refuses further use with ``ClientClosed``.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
        transport_factory: Callable[[], httpx.BaseTransport] | None = None,
    ):
        if transport is not None and transport_factory is not None:
            raise ValueError("pass either a borrowed transport or an owned transport factory")
        self.base_url = validate_loopback_url(base_url)
        self.timeout = timeout
        self._borrowed = transport
        self._factory = transport_factory
        owned_or_borrowed = (
            _BorrowedTransport(transport)
            if transport is not None
            else (transport_factory or _default_transport)()
        )
        self._closed = False
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=owned_or_borrowed,
            trust_env=CLIENT_TRUSTS_ENVIRONMENT,
            follow_redirects=False,
        )

    def clone(self) -> "RuntimeClient":
        """A sibling client for another thread, with the same ownership rule."""
        if self._closed:
            raise ClientClosed("client_closed")
        return RuntimeClient(
            self.base_url,
            timeout=self.timeout,
            transport=self._borrowed,
            transport_factory=self._factory,
        )

    def close(self) -> None:
        """Idempotent. Closes an owned transport once; never a borrowed one."""
        if self._closed:
            return
        self._closed = True
        self._http.close()

    def __enter__(self) -> "RuntimeClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> httpx.Response:
        if self._closed:
            raise ClientClosed("client_closed")
        try:
            response = self._http.request(method, path, json=body)
        except httpx.HTTPError as error:
            raise RuntimeUnavailable(type(error).__name__) from error
        if response.status_code in (200, 201, 204):
            return response
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        code = payload.get("code") if isinstance(payload, dict) else None
        status = response.status_code
        if status == 409 and code == "lease_fenced":
            raise LeaseFenced(code, status)
        if status == 409 and code == "idempotency_conflict":
            raise IdempotencyConflict(code, status, existing_run_id=payload.get("existing_run_id"))
        if status == 404:
            raise RunNotFound(code or "run_not_found", status)
        if status == 400:
            raise InvalidRuntimeRequest(code or "invalid_request", status)
        if status == 503 and code == "runtime_draining":
            raise RuntimeDraining(code, status)
        raise RuntimeUnavailable(code or f"http_{status}", status)

    def _json(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as error:
            raise RuntimeUnavailable("malformed_response", response.status_code) from error

    def _run(self, response: httpx.Response) -> dict[str, Any]:
        payload = self._json(response)
        if not isinstance(payload, dict):
            raise RuntimeUnavailable("malformed_response", response.status_code)
        return payload

    def ready(self) -> bool:
        if self._closed:
            return False
        try:
            return self._http.get("/readyz").status_code == 200
        except httpx.HTTPError:
            return False

    def submit(
        self,
        *,
        product: str,
        workflow_name: str,
        workflow_version: str,
        idempotency_key: str,
        input_ref: dict[str, Any],
        max_attempts: int,
    ) -> SubmitOutcome:
        response = self._request(
            "POST",
            "/v1/runs",
            {
                "product": product,
                "workflow_name": workflow_name,
                "workflow_version": workflow_version,
                "idempotency_key": idempotency_key,
                "input_ref": input_ref,
                "max_attempts": max_attempts,
            },
        )
        return SubmitOutcome(created=response.status_code == 201, run=self._run(response))

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._run(self._request("GET", _run_path(run_id)))

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        payload = self._json(self._request("GET", _run_path(run_id, "/events")))
        if not isinstance(payload, list):
            raise RuntimeUnavailable("malformed_response")
        return payload

    def claim(
        self,
        *,
        product: str,
        workflow_name: str,
        workflow_version: str,
        lease_owner: str,
        lease_seconds: int,
    ) -> dict[str, Any] | None:
        response = self._request(
            "POST",
            "/v1/worker/claims",
            {
                "product": product,
                "workflow_name": workflow_name,
                "workflow_version": workflow_version,
                "lease_owner": lease_owner,
                "lease_duration_seconds": lease_seconds,
            },
        )
        if response.status_code == 204:
            return None
        return self._run(response)

    def heartbeat(
        self, run_id: str, *, lease_owner: str, lease_version: int, lease_seconds: int
    ) -> dict[str, Any]:
        return self._run(
            self._request(
                "POST",
                _run_path(run_id, "/heartbeat"),
                {
                    "lease_owner": lease_owner,
                    "lease_version": lease_version,
                    "lease_duration_seconds": lease_seconds,
                },
            )
        )

    def complete(
        self, run_id: str, *, lease_owner: str, lease_version: int, output_ref: dict[str, Any]
    ) -> dict[str, Any]:
        return self._run(
            self._request(
                "POST",
                _run_path(run_id, "/complete"),
                {
                    "lease_owner": lease_owner,
                    "lease_version": lease_version,
                    "output_ref": output_ref,
                },
            )
        )

    def fail(
        self,
        run_id: str,
        *,
        lease_owner: str,
        lease_version: int,
        error_code: str,
        error_summary: str,
    ) -> dict[str, Any]:
        return self._run(
            self._request(
                "POST",
                _run_path(run_id, "/fail"),
                {
                    "lease_owner": lease_owner,
                    "lease_version": lease_version,
                    "error_code": error_code,
                    "error_summary": error_summary,
                },
            )
        )
