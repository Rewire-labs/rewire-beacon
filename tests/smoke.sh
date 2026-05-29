#!/usr/bin/env bash
# rewire-messaging smoke battery (MSG-V0 DoD #19)
#
# Runs against a deployed rewire-messaging control-plane (default:
# https://messaging.rewirelabs.dev). Override via MESSAGING_BASE_URL.
#
# Auth: MESSAGING_API_TOKEN env var (tenant API key bcn_live_... or OIDC JWT).
# Tenant: MESSAGING_TENANT_ID env var (uuid).
#
# Exit codes:
#   0 — all cases passed
#   N>0 — N failures (see stderr for details)

set -euo pipefail

BASE_URL="${MESSAGING_BASE_URL:-https://messaging.rewirelabs.dev}"
TOKEN="${MESSAGING_API_TOKEN:-}"
TENANT="${MESSAGING_TENANT_ID:-}"
RESULTS_OK=0
RESULTS_FAIL=0

color_red()   { printf "\033[31m%s\033[0m\n" "$1"; }
color_green() { printf "\033[32m%s\033[0m\n" "$1"; }
color_blue()  { printf "\033[34m%s\033[0m\n" "$1"; }

if [[ -z "$TOKEN" || -z "$TENANT" ]]; then
  echo "MESSAGING_API_TOKEN and MESSAGING_TENANT_ID required" >&2
  exit 2
fi

AUTH_HDR="Authorization: Bearer $TOKEN"
ORG_HDR="X-Organization-Id: $TENANT"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

ASSERT() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    color_green "  PASS — $desc (status=$actual)"
    RESULTS_OK=$((RESULTS_OK + 1))
  else
    color_red "  FAIL — $desc (expected=$expected actual=$actual)"
    RESULTS_FAIL=$((RESULTS_FAIL + 1))
  fi
}

# -----------------------------------------------------------------------------
# 1. Health probes
# -----------------------------------------------------------------------------

color_blue "== 1. Health probes =="

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" "$BASE_URL/healthz")
ASSERT "GET /healthz" 200 "$STATUS"

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" "$BASE_URL/ready")
ASSERT "GET /ready" 200 "$STATUS"

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" "$BASE_URL/metrics")
ASSERT "GET /metrics" 200 "$STATUS"

# -----------------------------------------------------------------------------
# 2. Email send (canonical)
# -----------------------------------------------------------------------------

color_blue "== 2. Email send =="

RESP=$(curl -sk -X POST "$BASE_URL/v1/emails" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"sender":"noreply@rewirelabs.dev","to":["smoke+test@rewirelabs.dev"],"subject":"smoke test","plain_body":"smoke","consent_basis":"contract"}' \
  -w "%{http_code}")
STATUS="${RESP: -3}"
ASSERT "POST /v1/emails -> 202" 202 "$STATUS"

# -----------------------------------------------------------------------------
# 3. SMS send (E.164 BR validation)
# -----------------------------------------------------------------------------

color_blue "== 3. SMS send =="

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/sms" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"to":"+5511999998888","text":"smoke","consent_basis":"contract"}')
ASSERT "POST /v1/sms (valid E.164) -> 202" 202 "$STATUS"

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/sms" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"to":"99999","text":"bad phone"}')
ASSERT "POST /v1/sms (invalid phone) -> 422" 422 "$STATUS"

# -----------------------------------------------------------------------------
# 4. Push send (ios + android + web stub)
# -----------------------------------------------------------------------------

color_blue "== 4. Push send =="

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/push" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"device_token":"abcd1234efgh5678","platform":"android","title":"hi","body":"smoke"}')
# expect 202 OR 503 (provider CB open in dev w/o credentials)
if [[ "$STATUS" == "202" || "$STATUS" == "503" || "$STATUS" == "502" ]]; then
  color_green "  PASS — POST /v1/push (android) -> $STATUS (acceptable)"
  RESULTS_OK=$((RESULTS_OK + 1))
else
  color_red "  FAIL — POST /v1/push (android) -> $STATUS"
  RESULTS_FAIL=$((RESULTS_FAIL + 1))
fi

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/push" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"device_token":"webabcd","platform":"web","title":"hi","body":"smoke"}')
ASSERT "POST /v1/push (web platform V0.3 pending) -> 501" 501 "$STATUS"

# Device-token register
STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/push/devices" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"device_token":"abcd1234efgh5678","platform":"ios","user_id":"u1"}')
ASSERT "POST /v1/push/devices -> 201" 201 "$STATUS"

# -----------------------------------------------------------------------------
# 5. Templates CRUD
# -----------------------------------------------------------------------------

color_blue "== 5. Templates =="

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/templates" \
  -H "$AUTH_HDR" -H "$ORG_HDR" -H "Content-Type: application/json" \
  -d '{"slug":"smoke","channel":"email","locale":"pt-BR","subject":"oi {{ name }}","body":"<p>oi</p>"}')
ASSERT "POST /v1/templates -> 201" 201 "$STATUS"

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" "$BASE_URL/v1/templates" \
  -H "$AUTH_HDR" -H "$ORG_HDR")
ASSERT "GET /v1/templates -> 200" 200 "$STATUS"

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" "$BASE_URL/v1/templates/tpl_smoke" \
  -H "$AUTH_HDR" -H "$ORG_HDR")
ASSERT "GET /v1/templates/tpl_smoke -> 200" 200 "$STATUS"

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/v1/templates/tpl_smoke" \
  -H "$AUTH_HDR" -H "$ORG_HDR")
ASSERT "DELETE /v1/templates/tpl_smoke -> 204" 204 "$STATUS"

# -----------------------------------------------------------------------------
# 6. Webhook ingest (404 for unknown provider)
# -----------------------------------------------------------------------------

color_blue "== 6. Webhooks =="

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/webhooks/unknown_provider" \
  -H "Content-Type: application/json" -d '{}')
ASSERT "POST /v1/webhooks/unknown -> 404" 404 "$STATUS"

# -----------------------------------------------------------------------------
# 7. Tenant-missing returns 400
# -----------------------------------------------------------------------------

color_blue "== 7. Tenant-required guard =="

STATUS=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/emails" \
  -H "$AUTH_HDR" -H "Content-Type: application/json" \
  -d '{"sender":"noreply@rewirelabs.dev","to":["x@example.com"],"subject":"x","plain_body":"x"}')
ASSERT "POST /v1/emails sem X-Organization-Id -> 400" 400 "$STATUS"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo
echo "============================="
echo "  Passed: $RESULTS_OK"
echo "  Failed: $RESULTS_FAIL"
echo "============================="

exit "$RESULTS_FAIL"
