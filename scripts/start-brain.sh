#!/usr/bin/env bash
set -euo pipefail

MODEL="${XEMO_MODEL:-qwen/qwen3-vl-8b}"
LMS="${LM_STUDIO_BIN:-lms}"

MODELS_JSON="$(curl -fsS --max-time 3 "${XEMO_BRAIN_URL:-http://127.0.0.1:1234/v1}/models" 2>/dev/null || true)"
if [[ -z "$MODELS_JSON" ]]; then
  echo "LM Studio is not running."
  exit 1
fi

if ! printf '%s' "$MODELS_JSON" | grep -Fq '"id"'; then
  echo "LM Studio is reachable but no model is loaded."
  exit 1
fi

echo "XEMO brain: $MODEL"
exec "$LMS" server start
