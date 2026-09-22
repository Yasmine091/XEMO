#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
fi
# Keep local identity and credentials outside version control when present.
if [[ -f "$ROOT/.env" ]]; then
    set -a
    source "$ROOT/.env"
    set +a
fi
export XEMO_INSTANCE_ID="${XEMO_INSTANCE_ID:-default}"
SHIM_PORT="${XEMO_JSON_SHIM_PORT:-1235}"
if ! curl -fsS --max-time 1 "http://127.0.0.1:${SHIM_PORT}/v1/models" >/dev/null 2>&1; then
    nohup "$PYTHON" "$ROOT/bot/llm_compat_proxy.py" \
        --listen-port "$SHIM_PORT" \
        --upstream "${XEMO_JSON_SHIM_UPSTREAM:-http://127.0.0.1:1234}" \
        >"${XEMO_JSON_SHIM_LOG:-/tmp/xemo-json-shim.log}" 2>&1 &
    echo "Started JSON compatibility shim on port ${SHIM_PORT}"
fi
exec "$PYTHON" "$ROOT/bot/bridge.py" --host "${XEMO_HOST:-0.0.0.0}" --port "${XEMO_PORT:-8765}" --brain "${XEMO_BRAIN_URL:-http://127.0.0.1:1234/v1}"
