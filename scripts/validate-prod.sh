#!/usr/bin/env bash
set -euo pipefail

# GRCInsight - Production Validation Script
# Verifies end-to-end flow: API Gateway → Go Lambda → Python Lambda → DynamoDB

# Requirements: aws cli, jq, curl

# Config (override via env vars)
AWS_REGION=${AWS_REGION:-us-east-1}
GO_FUNCTION_NAME=${GO_FUNCTION_NAME:-grcinsight-go-function}
PYTHON_FUNCTION_NAME=${PYTHON_FUNCTION_NAME:-grcinsight-python-function}
ROLE_NAME=${ROLE_NAME:-grcinsight-lambda-role}
FEED_URL=${FEED_URL:-https://ricomanifesto.github.io/SentryDigest/feed.xml}

# API URL: provide API_URL env var to override. Otherwise uses the known ID from notes.
API_URL=${API_URL:-https://nwerrmsza0.execute-api.${AWS_REGION}.amazonaws.com/dev}

echo "Validating production stack in region: $AWS_REGION"
echo "API URL: $API_URL"
echo

function check_aws() {
  if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "[ERROR] AWS CLI not configured. Run 'aws configure'." >&2
    exit 1
  fi
}

function check_tools() {
  for t in jq curl; do
    if ! command -v "$t" >/dev/null 2>&1; then
      echo "[ERROR] Missing tool: $t" >&2
      exit 1
    fi
  done
}

function check_lambda_env() {
  echo "[1/6] Checking Go Lambda env for PYTHON_LAMBDA_FUNCTION_NAME..."
  local name
  name=$(aws lambda get-function-configuration \
    --function-name "$GO_FUNCTION_NAME" \
    --query 'Environment.Variables.PYTHON_LAMBDA_FUNCTION_NAME' \
    --output text)
  echo "    PYTHON_LAMBDA_FUNCTION_NAME=$name"
  if [[ "$name" == "None" || -z "$name" ]]; then
    echo "[ERROR] PYTHON_LAMBDA_FUNCTION_NAME is not set on $GO_FUNCTION_NAME" >&2
    exit 1
  fi
}

function check_policy_attachment() {
  echo "[2/6] Checking IAM policy attachment on role $ROLE_NAME..."
  local attached
  attached=$(aws iam list-attached-role-policies \
    --role-name "$ROLE_NAME" \
    --query 'AttachedPolicies[?contains(PolicyName, `grcinsight-lambda-permissions`)] | length(@)' \
    --output text)
  echo "    Attached grcinsight-lambda-permissions: $attached"
  if [[ "$attached" == "0" || -z "$attached" ]]; then
    echo "[WARN] Policy not attached. Cross-Lambda/DynamoDB access may fail." >&2
  fi
}

function generate_report() {
  echo "[3/6] Generating report via API Gateway..."
  local payload http_code report_id body_file
  payload=$(jq -n --arg url "$FEED_URL" '{feed_url: $url, config: {model: "gpt-4", max_tokens: 4000, focus_areas: ["governance","compliance","risk"]}}')
  body_file=$(mktemp)
  http_code=$(curl -sS -o "$body_file" -w '%{http_code}' -X POST "$API_URL/api/v1/reports/generate" \
    -H 'Content-Type: application/json' -d "$payload")
  echo "    HTTP $http_code"
  cat "$body_file" | jq . >/dev/null 2>&1 || true
  if [[ "$http_code" != "201" && "$http_code" != "200" && "$http_code" != "202" ]]; then
    echo "[ERROR] Report generation failed: $(cat "$body_file")" >&2
    exit 1
  fi
  report_id=$(jq -r '.report_id // empty' "$body_file")
  if [[ -z "$report_id" || "$report_id" == "null" ]]; then
    echo "[ERROR] Missing report_id in response: $(cat "$body_file")" >&2
    exit 1
  fi
  echo "$report_id"
}

function fetch_report() {
  local report_id="$1"
  echo "[4/6] Fetching report via API Gateway: $report_id ..."
  local http_code body_file
  body_file=$(mktemp)
  http_code=$(curl -sS -o "$body_file" -w '%{http_code}' -X GET "$API_URL/api/v1/reports/$report_id")
  echo "    HTTP $http_code"
  if [[ "$http_code" != "200" ]]; then
    echo "[ERROR] Failed to fetch report: $(cat "$body_file")" >&2
    exit 1
  fi
  cat "$body_file" | jq . >/dev/null 2>&1 || true
}

function check_dynamodb() {
  local report_id="$1"
  echo "[5/6] Verifying DynamoDB record exists for: $report_id ..."
  local item
  item=$(aws dynamodb get-item \
    --table-name grcinsight-reports \
    --key "{\"report_id\": {\"S\": \"$report_id\"}}" \
    --query 'Item' --output json)
  if [[ "$item" == "null" || -z "$item" ]]; then
    echo "[ERROR] DynamoDB record not found for $report_id" >&2
    exit 1
  fi
  echo "    DynamoDB item found"
}

function tail_logs_hint() {
  echo "[6/6] You can inspect CloudWatch logs with:"
  echo "    aws logs tail /aws/lambda/$GO_FUNCTION_NAME --follow --since 15m"
  echo "    aws logs tail /aws/lambda/$PYTHON_FUNCTION_NAME --follow --since 15m"
}

check_tools
check_aws
check_lambda_env
check_policy_attachment
RID=$(generate_report)
fetch_report "$RID"
check_dynamodb "$RID"
tail_logs_hint

echo
echo "[SUCCESS] End-to-end validation passed. Report ID: $RID"
