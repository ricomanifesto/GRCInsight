"""Defensive build, CI and deployment boundary contracts; no live providers."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap

import pytest
from scripts import update_lambda_environment as deploy

ROOT = Path(__file__).resolve().parents[2]


def step_block(source, name):
    return source.split(f"- name: {name}\n", 1)[1].split("- name:", 1)[0]


def test_every_container_base_is_immutable_and_server_images_are_non_root():
    for name in (
        "Dockerfile",
        "Dockerfile.lambda",
        "agent/Dockerfile",
        "agent/Dockerfile.lambda",
    ):
        source = (ROOT / name).read_text()
        for image in re.findall(r"^FROM (\S+)", source, re.M):
            assert re.search(r"@sha256:[a-f0-9]{64}$", image), (name, image)
        if not name.endswith(".lambda"):
            assert re.search(r"^USER (?!root\b|0\b)\S+", source, re.M), name


def test_build_contexts_exclude_operator_secrets_and_repository_metadata():
    for name in (".dockerignore", "agent/.dockerignore"):
        rules = (ROOT / name).read_text().splitlines()
        assert {".env", ".env.*", ".git", ".venv", "data"} <= set(rules)


def test_compose_services_bind_loopback_and_receive_the_auth_key():
    source = (ROOT / "docker-compose.yml").read_text()
    assert '"127.0.0.1:8080:8080"' in source
    assert '"127.0.0.1:8081:8081"' in source
    assert source.count("API_KEY=${API_KEY:?API_KEY is required}") == 2


def test_actions_are_sha_pinned_and_pr_ci_explicitly_read_only():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        for action in re.findall(r"uses:\s*(\S+)", path.read_text()):
            assert action.startswith("./") or re.fullmatch(
                r"[^@]+@[a-f0-9]{40}", action
            ), (path, action)
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "\npermissions:\n  contents: read\n" in ci


def test_dynamic_workflow_values_only_enter_scripts_via_environment():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        # A run block ends at its next peer key/step. Workflow expressions in
        # that block become shell source; env/with/if expressions remain data.
        for match in re.finditer(
            r"^( +)run: [|>]\n((?:\1 +.*\n|\n)*)", path.read_text(), re.M
        ):
            assert "${{" not in match[2], path


def test_aws_deploy_and_report_jobs_use_distinct_short_lived_identities():
    for filename, role in (
        ("deploy-lambda.yml", "AWS_DEPLOY_ROLE_ARN"),
        ("lambda-report-generation.yml", "AWS_REPORT_ROLE_ARN"),
    ):
        workflow = (ROOT / ".github/workflows" / filename).read_text()
        credential = step_block(workflow, "Configure AWS credentials")
        assert "role-to-assume: ${{ vars." + role + " }}" in credential
        assert "aws-access-key-id" not in credential
        assert "id-token: write" in workflow
        environment = (
            "aws-lambda-deploy"
            if filename == "deploy-lambda.yml"
            else "aws-report-generation"
        )
        assert "environment: " + environment in workflow
        trust_name = (
            "github-deploy-trust-policy.json"
            if filename == "deploy-lambda.yml"
            else "github-report-trust-policy.json"
        )
        trust = json.loads((ROOT / "deployments" / trust_name).read_text())
        assert (
            trust["Statement"][0]["Condition"]["StringEquals"][
                "token.actions.githubusercontent.com:sub"
            ]
            == "repo:ricomanifesto/GRCInsight:environment:" + environment
        )


def test_runtime_and_release_policies_cannot_delete_or_mix_deploy_with_data_writes():
    for path in (ROOT / "deployments").glob("*policy.json"):
        statements = json.loads(path.read_text())["Statement"]
        actions = {action for statement in statements for action in statement["Action"]}
        assert "dynamodb:DeleteItem" not in actions, path
        assert (
            "dynamodb:BatchWriteItem" not in actions
        ), path  # permits DeleteRequest too
        if "lambda:UpdateFunctionCode" in actions:
            assert not any(action.startswith("dynamodb:") for action in actions), path
            assert not {"ecr:CreateRepository", "ecr:SetRepositoryPolicy"} & actions
            for statement in statements:
                if "ecr:PutImage" in statement["Action"]:
                    assert statement["Resource"] != "*"


def test_manual_bootstrap_verifies_existing_runtime_policy_before_image_publication():
    source = (ROOT / "scripts/deploy-lambda.sh").read_text()
    assert "get-policy-version" in source
    assert "--slurpfile expected deployments/lambda-permissions-policy.json" in source
    assert source.index("get-policy-version") < source.index("docker build")
    assert "requires owner reconciliation" in source


def test_auth_configuration_is_required_before_environment_updates():
    values = {
        "LLM_MODEL": "openrouter/test/model",
        "OPENROUTER_API_KEY": "synthetic-provider",
    }
    for kind in ("go", "python"):
        with pytest.raises(deploy.EnvironmentUpdateError):
            deploy.owned_environment(kind, values)
        assert (
            deploy.owned_environment(kind, {**values, "API_KEY": "synthetic-api-key"})[
                "API_KEY"
            ]
            == "synthetic-api-key"
        )


def test_nondefault_model_is_shared_by_both_services():
    values = {
        "LLM_MODEL": "openrouter/test/nondefault",
        "OPENROUTER_API_KEY": "synthetic-provider",
        "API_KEY": "synthetic-api-key",
    }
    for kind in ("go", "python"):
        assert (
            deploy.owned_environment(kind, values)["LLM_MODEL"] == values["LLM_MODEL"]
        )
    compose = (ROOT / "docker-compose.yml").read_text()
    assert (
        compose.count(
            "LLM_MODEL=${LLM_MODEL:-openrouter/nvidia/nemotron-3-ultra-550b-a55b:free}"
        )
        == 2
    )


@pytest.mark.parametrize("kind", ["go", "python"])
def test_missing_api_key_stops_preflight_before_any_aws_client(monkeypatch, kind):
    monkeypatch.setattr(
        sys, "argv", ["environment", "--function-kind", kind, "--preflight-only"]
    )
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setattr(
        deploy,
        "AwsCli",
        lambda *_a, **_k: pytest.fail("AWS client must not be constructed"),
    )
    assert deploy.main() == 1


def test_authenticated_invocation_keeps_header_out_of_argv_logs_and_response(tmp_path):
    source = (ROOT / ".github/workflows/lambda-report-generation.yml").read_text()
    block = step_block(source, "Invoke Lambda report generation")
    shell = textwrap.dedent(block.split("      run: |\n", 1)[1])
    binary = tmp_path / "aws"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json,os,pathlib,sys\n"
        "assert sys.argv[sys.argv.index('--payload')+1] == 'fileb:///dev/stdin'\n"
        "assert os.environ['AWS_CLI_HISTORY_FILE'] == '/dev'\n"
        "payload=json.load(sys.stdin)\n"
        "assert payload['headers']['X-API-Key'] == os.environ['API_KEY']\n"
        "assert payload['path'] == '/api/v1/reports/generate'\n"
        "pathlib.Path('argv.json').write_text(json.dumps(sys.argv))\n"
        "pathlib.Path(sys.argv[-1]).write_text(json.dumps({'statusCode':200,'body':json.dumps({'report_id':'report-test'})}))\n"
    )
    binary.chmod(0o755)
    key = "synthetic-api-key-only-for-test"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-x", "-c", shell],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "API_KEY": key,
            "LLM_MODEL": "openrouter/test/model",
            "FEED_URL": "https://example.test/feed.xml",
            "GO_FUNCTION_NAME": "synthetic-function",
            "AWS_REGION": "us-east-1",
            "AWS_CLI_HISTORY_FILE": "/dev",
            "GITHUB_OUTPUT": str(tmp_path / "output"),
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert key not in result.stdout + result.stderr
    assert key not in (tmp_path / "argv.json").read_text()
    assert key not in (tmp_path / "lambda-response.json").read_text()


def test_generation_sends_auth_over_stdin_without_tracing_or_cli_history():
    workflow = (ROOT / ".github/workflows/lambda-report-generation.yml").read_text()
    assert "AWS_CLI_HISTORY_FILE: /dev" in workflow
    for name in ("Invoke Lambda report generation", "Retrieve generated report"):
        step = step_block(workflow, name)
        assert "API_KEY: ${{ secrets.API_KEY }}" in step
        shell = step.split("run: |", 1)[1]
        assert "set +x" in shell
        assert "env.API_KEY" in shell
        assert "--payload fileb:///dev/stdin" in shell
        assert '--payload "$' not in shell
