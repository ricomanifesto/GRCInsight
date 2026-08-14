#!/usr/bin/env python3
"""Fetch and compare the canonical reporting identity contract in distinct stages."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONTRACT = REPO_ROOT / "contracts" / "reporting-identity-v1.json"
CANONICAL_CONTRACT_URL = (
    "https://raw.githubusercontent.com/ricomanifesto/SentryDigest/"
    "main/contracts/reporting-identity-v1.json"
)
MAX_CONTRACT_BYTES = 1_000_000
DEFAULT_ATTEMPTS = 4
UNAVAILABLE_EXIT_CODE = 2
DRIFT_EXIT_CODE = 3


class CanonicalContractUnavailable(RuntimeError):
    """The canonical contract could not be read safely."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_canonical_contract(
    url: str, timeout_seconds: float, attempts: int = DEFAULT_ATTEMPTS
) -> bytes:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    request = Request(url, headers={"User-Agent": "GRCInsight-contract-verifier/1"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                content = response.read(MAX_CONTRACT_BYTES + 1)
            break
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            if attempt + 1 == attempts:
                raise CanonicalContractUnavailable from error
            time.sleep(2**attempt)

    if len(content) > MAX_CONTRACT_BYTES:
        raise CanonicalContractUnavailable
    return content


def report_unavailable() -> int:
    print(
        "::error title=Canonical reporting identity unavailable::"
        "The canonical contract could not be retrieved; release remains blocked.",
        file=sys.stderr,
    )
    return UNAVAILABLE_EXIT_CODE


def fetch_contract(
    canonical_url: str,
    canonical_output: Path,
    timeout_seconds: float,
    attempts: int = DEFAULT_ATTEMPTS,
) -> int:
    try:
        canonical_bytes = fetch_canonical_contract(
            canonical_url, timeout_seconds, attempts=attempts
        )
        canonical_output.write_bytes(canonical_bytes)
    except (CanonicalContractUnavailable, OSError):
        return report_unavailable()

    print(f"Reporting identity contract fetched: SHA-256 {sha256(canonical_bytes)}")
    return 0


def compare_contract(local_contract: Path, canonical_contract: Path) -> int:
    try:
        local_bytes = local_contract.read_bytes()
    except OSError:
        print(
            "::error title=Reporting identity contract drift::"
            "The repository-local contract is missing or unreadable.",
            file=sys.stderr,
        )
        return DRIFT_EXIT_CODE

    try:
        canonical_bytes = canonical_contract.read_bytes()
    except OSError:
        return report_unavailable()

    local_hash = sha256(local_bytes)
    canonical_hash = sha256(canonical_bytes)
    if local_bytes != canonical_bytes:
        print(
            "::error title=Reporting identity contract drift::"
            f"Local SHA-256 {local_hash} does not match canonical SHA-256 "
            f"{canonical_hash}; release remains blocked.",
            file=sys.stderr,
        )
        return DRIFT_EXIT_CODE

    print(f"Reporting identity contract verified: SHA-256 {local_hash}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    fetch_parser = commands.add_parser("fetch")
    fetch_parser.add_argument("--canonical-url", default=CANONICAL_CONTRACT_URL)
    fetch_parser.add_argument("--canonical-output", type=Path, required=True)
    fetch_parser.add_argument("--timeout-seconds", type=float, default=15.0)
    fetch_parser.add_argument(
        "--attempts", type=int, choices=range(1, 6), default=DEFAULT_ATTEMPTS
    )

    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("--local-contract", type=Path, default=LOCAL_CONTRACT)
    compare_parser.add_argument("--canonical-contract", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "fetch":
        return fetch_contract(
            args.canonical_url,
            args.canonical_output,
            args.timeout_seconds,
            args.attempts,
        )
    return compare_contract(args.local_contract, args.canonical_contract)


if __name__ == "__main__":
    raise SystemExit(main())
