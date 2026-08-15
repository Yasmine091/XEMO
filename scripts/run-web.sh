#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/bot/bridge.py" --host "${XEMO_HOST:-0.0.0.0}" --port "${XEMO_PORT:-8765}" --brain "${XEMO_BRAIN_URL:-http://127.0.0.1:1234/v1}"
