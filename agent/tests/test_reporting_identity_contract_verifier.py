import importlib.util
from pathlib import Path
import subprocess
import sys
from urllib.error import URLError

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFIER = REPO_ROOT / "scripts" / "verify_reporting_identity_contract.py"


def run_verifier(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_verifier_accepts_byte_identical_contract(tmp_path: Path):
    local_contract = tmp_path / "local.json"
    canonical_contract = tmp_path / "canonical.json"
    contract = b'{"contract_version":1}\n'
    local_contract.write_bytes(contract)
    canonical_contract.write_bytes(contract)

    result = run_verifier(
        "compare",
        "--local-contract",
        str(local_contract),
        "--canonical-contract",
        str(canonical_contract),
    )

    assert result.returncode == 0
    assert "contract verified" in result.stdout
    assert result.stderr == ""


def test_verifier_classifies_canonical_source_unavailability(tmp_path: Path):
    result = run_verifier(
        "fetch",
        "--canonical-url",
        (tmp_path / "missing.json").as_uri(),
        "--canonical-output",
        str(tmp_path / "fetched.json"),
        "--attempts",
        "1",
    )

    assert result.returncode == 2
    assert "Canonical reporting identity unavailable" in result.stderr
    assert "contract drift" not in result.stderr


def test_verifier_classifies_byte_drift(tmp_path: Path):
    local_contract = tmp_path / "local.json"
    canonical_contract = tmp_path / "canonical.json"
    local_contract.write_text('{"contract_version":1}\n')
    canonical_contract.write_text('{"contract_version":2}\n')

    result = run_verifier(
        "compare",
        "--local-contract",
        str(local_contract),
        "--canonical-contract",
        str(canonical_contract),
    )

    assert result.returncode == 3
    assert "Reporting identity contract drift" in result.stderr
    assert "Local SHA-256" in result.stderr
    assert "canonical SHA-256" in result.stderr


def test_verifier_treats_missing_local_copy_as_drift(tmp_path: Path):
    canonical_contract = tmp_path / "canonical.json"
    canonical_contract.write_text("{}\n")

    result = run_verifier(
        "compare",
        "--local-contract",
        str(tmp_path / "missing.json"),
        "--canonical-contract",
        str(canonical_contract),
    )

    assert result.returncode == 3
    assert "repository-local contract is missing or unreadable" in result.stderr


def test_canonical_fetch_retries_bounded_transient_failures(monkeypatch):
    spec = importlib.util.spec_from_file_location("contract_verifier", VERIFIER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = b'{"contract_version":1}\n'
    calls = []
    sleeps = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            assert limit == module.MAX_CONTRACT_BYTES + 1
            return payload

    def transient_urlopen(_request, timeout):
        calls.append(timeout)
        if len(calls) < 4:
            raise URLError("transient")
        return Response()

    monkeypatch.setattr(module, "urlopen", transient_urlopen)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)

    result = module.fetch_canonical_contract(
        "https://example.invalid/contract.json", timeout_seconds=3.0, attempts=4
    )

    assert result == payload
    assert calls == [3.0, 3.0, 3.0, 3.0]
    assert sleeps == [1, 2, 4]


def test_fetch_and_compare_are_separate_fail_closed_stages(tmp_path: Path):
    canonical_contract = tmp_path / "canonical.json"
    fetched_contract = tmp_path / "fetched.json"
    local_contract = tmp_path / "local.json"
    contract = b'{"contract_version":1}\n'
    canonical_contract.write_bytes(contract)
    local_contract.write_bytes(contract)

    fetch_result = run_verifier(
        "fetch",
        "--canonical-url",
        canonical_contract.as_uri(),
        "--canonical-output",
        str(fetched_contract),
    )
    compare_result = run_verifier(
        "compare",
        "--local-contract",
        str(local_contract),
        "--canonical-contract",
        str(fetched_contract),
    )

    assert fetch_result.returncode == 0
    assert fetched_contract.read_bytes() == contract
    assert "contract fetched" in fetch_result.stdout
    assert compare_result.returncode == 0
    assert "contract verified" in compare_result.stdout
