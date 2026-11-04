#!/usr/bin/env python3
"""Classify fixed Go concurrency metadata without changing maintenance settings."""

import json
import sys


def mode(value):
    if value == {}:
        return "available"  # AWS omits ReservedConcurrentExecutions when unreserved.
    if type(value) is not dict or set(value) != {"ReservedConcurrentExecutions"}:
        raise ValueError("Unknown Go maintenance state")
    count = value["ReservedConcurrentExecutions"]
    if type(count) is not int or count < 0:
        raise ValueError("Unknown Go maintenance state")
    return "paused" if count == 0 else "available"


def main():
    try:
        raw = sys.stdin.buffer.read(4097)
        if len(raw) > 4096:
            raise ValueError()
        print(mode(json.loads(raw)))
        return 0
    except Exception:
        print("Unknown Go maintenance state; health verification stopped", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
