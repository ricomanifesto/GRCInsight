#!/usr/bin/env python3
"""Exercise the real report-plan service with one fixed fictional mock answer."""

import argparse
import asyncio
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
CASE = ROOT / "agent/tests/fixtures/selected_model_case.json"
CASE_SHA256 = "f21bbf7ad30e72e485ecfb6ae6ce078fcd98959d4f0d3c5a28eab0f2b3955b08"
MAX_OUTPUT_TOKENS = 8000
SYNTHETIC_INPUT_RESERVE = 22000


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 11, 4, 12, tzinfo=timezone.utc)
        return value if tz is not None else value.replace(tzinfo=None)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def require(condition):
    if not condition:
        raise ValueError("Offline rehearsal invariant failed")


def load_case():
    raw = CASE.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CASE_SHA256)
    return json.loads(raw)


def validate_case():
    """Positive fixture oracle, independent of the service dependency check."""
    from core.report_plan import parse_report_plan, render_report_plan

    case = load_case()
    sources = case["analysis_data"]["source_evidence"]
    plan = parse_report_plan(json.dumps(case["calibration_plan"]), sources)
    require(plan["regulatory_changes"] == [])
    require(len(plan["control_implications"]) == 1)
    require(plan["control_implications"][0]["source_ids"] == [2])
    require(plan["control_implications"][0]["control_id"] == "third_party_risk")
    require(bool(render_report_plan(plan, sources)))
    return case


def deny_network(*_args, **_kwargs):
    raise RuntimeError("Offline rehearsal forbids network access")


async def rehearse():
    import httpx

    # Read only the fixed synthetic case. No feed, enrichment or relevance call.
    case = validate_case()
    requests = []

    def handler(request):
        require(not requests)
        require(str(request.url) == "https://openrouter.ai/api/v1/chat/completions")
        payload = json.loads(request.content)
        require(
            set(payload)
            == {
                "model",
                "messages",
                "provider",
                "max_tokens",
                "stream",
                "reasoning",
                "service_tier",
                "response_format",
            }
        )
        require(payload["max_tokens"] == MAX_OUTPUT_TOKENS)
        require([row["role"] for row in payload["messages"]] == ["system", "user"])
        require(all(type(row["content"]) is str for row in payload["messages"]))
        require(json.dumps(case["calibration_plan"]) not in payload["messages"][1]["content"])
        complete = {
            "messages": payload["messages"],
            "response_format": payload["response_format"],
        }
        message_bytes = len(json.dumps(payload["messages"], ensure_ascii=True).encode())
        schema_bytes = len(json.dumps(payload["response_format"], ensure_ascii=True).encode())
        complete_bytes = len(json.dumps(complete, ensure_ascii=True).encode())
        wrapper_bytes = complete_bytes - message_bytes - schema_bytes
        input_bound = message_bytes + schema_bytes + wrapper_bytes + 4096
        require(input_bound <= SYNTHETIC_INPUT_RESERVE)
        requests.append(
            {
                "sha256": digest(payload),
                "keys": sorted(payload),
                "input_bound": input_bound,
                "input_message_bytes": message_bytes,
                "input_schema_bytes": schema_bytes,
                "input_wrapper_bytes": wrapper_bytes,
                "wire_sha256": hashlib.sha256(request.content).hexdigest(),
                "wire_bytes": len(request.content),
            }
        )
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "service_tier": "default",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(case["calibration_plan"]),
                        },
                    }
                ],
            },
        )

    with (
        tempfile.TemporaryDirectory(prefix="grc-offline-") as directory,
        ExitStack() as stack,
    ):
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": directory,
            "AWS_CONFIG_FILE": "/dev/null",
            "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
            "AWS_EC2_METADATA_DISABLED": "true",
            "AWS_ACCESS_KEY_ID": "synthetic",
            "AWS_SECRET_ACCESS_KEY": "synthetic",
            "OTEL_SDK_DISABLED": "true",
            "LOGFIRE_SEND_TO_LOGFIRE": "false",
            "LANGSMITH_TRACING": "false",
            "LANGCHAIN_TRACING_V2": "false",
        }
        stack.enter_context(patch.dict(os.environ, environment, clear=True))
        stack.enter_context(patch.object(socket, "create_connection", deny_network))
        stack.enter_context(patch.object(socket, "getaddrinfo", deny_network))
        for name in ("connect", "connect_ex", "sendto"):
            stack.enter_context(patch.object(socket.socket, name, deny_network))
        stack.enter_context(
            patch.object(httpx.AsyncHTTPTransport, "handle_async_request", deny_network)
        )
        stack.enter_context(patch.object(httpx.HTTPTransport, "handle_request", deny_network))
        previous = Path.cwd()
        os.chdir(directory)  # Settings' relative .env path resolves to empty scratch.
        stack.callback(os.chdir, previous)
        from loguru import logger

        logger.disable("")
        from services.model_service import GRCModelService
        from services import model_service
        from services.model_route import ARGON_ROUTE, RouteActivation
        from core.report_plan import validate_rendered_report

        stack.enter_context(patch.object(model_service, "datetime", FixedDatetime))

        service = GRCModelService(
            model_name="openrouter/" + ARGON_ROUTE.model_id,
            max_tokens=MAX_OUTPUT_TOKENS,
            activation=RouteActivation.OFFLINE,
            transport=httpx.MockTransport(handler),
        )
        generation = await service.generate_grc_report(case["analysis_data"], case["feed_info"])
        require(len(requests) == 1 and generation.report_plan == case["calibration_plan"])
        validate_rendered_report(
            generation.content,
            generation.report_plan,
            case["analysis_data"]["source_evidence"],
        )
        return {
            "outcome": "offline_rehearsal_passed",
            "fixture_sha256": CASE_SHA256,
            "request_sha256": requests[0]["sha256"],
            "wire_request_sha256": requests[0]["wire_sha256"],
            "wire_request_bytes": requests[0]["wire_bytes"],
            "prompt_date": "2026-11-04",
            "keys": requests[0]["keys"],
            "requested_model": ARGON_ROUTE.model_id,
            "provider": ARGON_ROUTE.provider_payload(),
            "service_tier": "default",
            "reasoning": {"effort": "low", "exclude": True},
            "max_tokens": MAX_OUTPUT_TOKENS,
            "synthetic_input_reserve": SYNTHETIC_INPUT_RESERVE,
            "conservative_input_bound": requests[0]["input_bound"],
            "input_message_bytes": requests[0]["input_message_bytes"],
            "input_schema_bytes": requests[0]["input_schema_bytes"],
            "input_serialization_wrapper_bytes": requests[0]["input_wrapper_bytes"],
            "input_framing_reserve": 4096,
            "source_count": 2,
            "grounded_control_findings": 1,
            "regulatory_changes": 0,
            "rendered_sha256": hashlib.sha256(generation.content.encode()).hexdigest(),
            "mock_requests": 1,
            "live_requests": 0,
            "published": False,
            "production_ready": False,
            "provider_eligibility_verified": False,
            "excluded": ["mock_calibration_answer"],
            "usage": None,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-only", required=True, action="store_true")
    parser.parse_args()
    try:
        print(json.dumps(asyncio.run(rehearse()), sort_keys=True))
        return 0
    except (Exception, KeyboardInterrupt):
        print(
            '{"outcome":"offline_rehearsal_unavailable","live_requests":0,"published":false}',
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
