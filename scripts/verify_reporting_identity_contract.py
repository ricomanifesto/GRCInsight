#!/usr/bin/env python3
"""Fail closed when the local reporting identity contract is unavailable or drifts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONTRACT = REPO_ROOT / "contracts" / "reporting-identity-v1.json"
CANONICAL_CONTRACT_URL = (
    "https://raw.githubusercontent.com/ricomanifesto/SentryDigest/"
    "main/contracts/reporting-identity-v1.json"
)
MAX_CONTRACT_BYTES = 1_000_000
UNAVAILABLE_EXIT_CODE = 2
DRIFT_EXIT_CODE = 3


class CanonicalContractUnavailable(RuntimeError):
    """The canonical contract could not be read safely."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_canonical_contract(url: str, timeout_seconds: float) -> bytes:
    request = Request(url, headers={"User-Agent": "GRCInsight-contract-verifier/1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            content = response.read(MAX_CONTRACT_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        raise CanonicalContractUnavailable from error

    if len(content) > MAX_CONTRACT_BYTES:
        raise CanonicalContractUnavailable
    return content


def verify_contract(local_contract: Path, canonical_url: str, timeout_seconds: float) -> int:
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
        canonical_bytes = fetch_canonical_contract(canonical_url, timeout_seconds)
    except CanonicalContractUnavailable:
        print(
            "::error title=Canonical reporting identity unavailable::"
            "The canonical contract could not be retrieved; release remains blocked.",
            file=sys.stderr,
        )
        return UNAVAILABLE_EXIT_CODE

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
    parser.add_argument("--local-contract", type=Path, default=LOCAL_CONTRACT)
    parser.add_argument("--canonical-url", default=CANONICAL_CONTRACT_URL)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    args = parser.parse_args()
    return verify_contract(args.local_contract, args.canonical_url, args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
