#!/usr/bin/env bash
set +x
set -euo pipefail

# Minimal end-to-end integration script.
# Prereqs: Go API running (API_URL), Python agent optionally running (PYTHON_URL),
# jq installed and the shared API_KEY set for both services.

API_URL=${API_URL:-http://localhost:8080}
FEED_URL=${FEED_URL:-}
PYTHON_URL=${PYTHON_URL:-}
TIMEOUT_SECS=${TIMEOUT_SECS:-300}
POLL_INTERVAL=${POLL_INTERVAL:-5}

if ! command -v jq >/dev/null 2>&1; then
  echo "[ERROR] jq is required for this script" >&2
  exit 1
fi

if [[ -z "$FEED_URL" ]]; then
  echo "[ERROR] FEED_URL env var must be set to a valid RSS URL" >&2
  exit 1
fi

if [[ -z "${API_KEY:-}" ]]; then
  echo "[ERROR] API_KEY env var must be set before running sensitive checks" >&2
  exit 1
fi
if [[ "$API_KEY" == *$'\n'* || "$API_KEY" == *$'\r'* ]]; then
  echo "[ERROR] API_KEY must not contain line breaks" >&2
  exit 1
fi

# Header bytes enter curl over stdin and redirects are never followed. Ignore
# user curl configuration so it cannot enable redirection or verbose tracing.
authenticated_curl() {
  printf '%s' "$API_KEY" | jq -Rrs '"header = " + (("X-API-Key: " + .) | @json)' | \
    curl -q --config - -fsS --proto '=http,https' "$@"
}

echo "[INFO] API_URL=$API_URL"
echo "[INFO] FEED_URL=$FEED_URL"
if [[ -n "$PYTHON_URL" ]]; then
  echo "[INFO] PYTHON_URL=$PYTHON_URL"
fi

echo "[STEP] Deep health check (optional)"
if [[ -n "$PYTHON_URL" ]]; then
  set +e
  authenticated_curl --url "$PYTHON_URL/api/v1/health?deep=true" | jq . || true
  set -e
else
  echo "[SKIP] PYTHON_URL not set; skipping Python deep health check"
fi

echo "[STEP] Generate report"
GEN_PAYLOAD=$(printf '%s' "$FEED_URL" | jq -Rs '{
  feed_url: ., config: {max_tokens: 4000, focus_areas: ["governance", "compliance", "risk"]}
}')

GEN_RESP=$(authenticated_curl -X POST --url "$API_URL/api/v1/reports/generate" \
  -H 'content-type: application/json' \
  --data "$GEN_PAYLOAD")

echo "$GEN_RESP" | jq .

RID=$(echo "$GEN_RESP" | jq -r '.report_id // .ReportID // empty')
STATUS=$(echo "$GEN_RESP" | jq -r '.status // .Status // empty')
if [[ -z "$RID" ]]; then
  echo "[ERROR] Could not parse report_id from response" >&2
  exit 1
fi
echo "[INFO] Report ID: $RID (initial status: $STATUS)"

RID_PATH=$(printf '%s' "$RID" | jq -sRr @uri)

echo "[STEP] Poll report status"
START=$(date +%s)
while true; do
  RESP=$(authenticated_curl --url "$API_URL/api/v1/reports/$RID_PATH/status")
  echo "$RESP" | jq .
  CUR_STATUS=$(echo "$RESP" | jq -r '.status // empty')
  if [[ "$CUR_STATUS" == "completed" || "$CUR_STATUS" == "failed" ]]; then
    echo "[INFO] Final status: $CUR_STATUS"
    break
  fi
  NOW=$(date +%s)
  ELAPSED=$((NOW-START))
  if (( ELAPSED > TIMEOUT_SECS )); then
    echo "[ERROR] Timed out waiting for report completion" >&2
    exit 1
  fi
  sleep "$POLL_INTERVAL"
done

echo "[STEP] List report articles"
ART_RESP=$(authenticated_curl --url "$API_URL/api/v1/reports/$RID_PATH/articles?page=1&per_page=20")
echo "$ART_RESP" | jq .
COUNT=$(echo "$ART_RESP" | jq -r '.articles | length')
echo "[SUCCESS] Retrieved $COUNT articles for report $RID"
