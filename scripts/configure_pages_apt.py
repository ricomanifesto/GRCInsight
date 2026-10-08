"""Configure bounded, authenticated Ubuntu downloads on a disposable Pages runner."""

import argparse
from pathlib import Path
import re

SETTINGS = """Acquire::Retries "2";
Acquire::http::Timeout "30";
Acquire::https::Timeout "30";
APT::Update::Error-Mode "any";
"""
AZURE = re.compile(r"(?m)^(https?://azure\.archive\.ubuntu\.com/ubuntu)(/?)(?=\s|$)")
OFFICIAL = re.compile(r"(?m)^https://archive\.ubuntu\.com/ubuntu/?(?=\s|$)")
# APT merges snippets in C-locale order; hosted runner defaults use zz-retries.
DEFAULT_CONFIG = Path("/etc/apt/apt.conf.d/zzz-grcinsight-acquire")


def configure(mirror_list: Path, config: Path) -> None:
    original = mirror_list.read_text(encoding="utf-8")
    updated, count = AZURE.subn(r"https://archive.ubuntu.com/ubuntu\2", original)
    if not count and not OFFICIAL.search(original):
        raise ValueError(
            "Unsupported Ubuntu runner mirror list; no configuration written"
        )
    # Change only the known mirror URL, never suites, components or trust settings.
    config.write_text(SETTINGS, encoding="utf-8")
    if updated != original:
        mirror_list.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mirror-list", type=Path, default=Path("/etc/apt/apt-mirrors.txt")
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    configure(args.mirror_list, args.config)
    print("Ubuntu HTTPS mirror and bounded APT acquisition configured")


if __name__ == "__main__":
    main()
