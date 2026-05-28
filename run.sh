#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT/apps/python-api"
UI_DIR="$ROOT/apps/electron-ui"

API_PID=""
UI_PID=""

# ── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[hand2notes]${NC} $*"; }
success() { echo -e "${GREEN}[hand2notes]${NC} $*"; }
warn()    { echo -e "${YELLOW}[hand2notes]${NC} $*"; }
error()   { echo -e "${RED}[hand2notes]${NC} $*" >&2; }

# ── cleanup ───────────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  info "Shutting down..."
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$UI_PID"  ]] && kill "$UI_PID"  2>/dev/null || true
  wait 2>/dev/null || true
  success "Done."
}
trap cleanup EXIT INT TERM

# ── prerequisites ─────────────────────────────────────────────────────────────
check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    error "Required tool not found: $1. $2"
    exit 1
  fi
}
check_cmd uv   "Install from https://docs.astral.sh/uv/"
check_cmd node "Install Node 20+ from https://nodejs.org/"
check_cmd npm  "Install Node 20+ from https://nodejs.org/"

# ── Python dependencies ───────────────────────────────────────────────────────
info "Installing Python dependencies..."
uv sync --quiet
success "Python dependencies ready."

# ── Node dependencies ─────────────────────────────────────────────────────────
info "Installing Node dependencies..."
(cd "$UI_DIR" && npm install --silent)
success "Node dependencies ready."

# ── Database migrations ───────────────────────────────────────────────────────
info "Applying database migrations..."
(cd "$API_DIR" && uv run alembic upgrade head 2>&1) || warn "Migration skipped or already up to date."
success "Database ready."

# ── Start API ─────────────────────────────────────────────────────────────────
info "Starting API server..."
uv run --package hand2notes-api uvicorn hand2notes.api.main:app --reload &
API_PID=$!

# Wait for the API to become healthy (up to 30 s)
API_PORT="${HAND2NOTES_API_PORT:-8000}"
API_URL="http://127.0.0.1:${API_PORT}/health"
for i in $(seq 1 30); do
  if curl -sf "$API_URL" &>/dev/null; then
    success "API is up at http://127.0.0.1:${API_PORT}"
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    error "API process exited unexpectedly."
    exit 1
  fi
  sleep 1
done

if ! curl -sf "$API_URL" &>/dev/null; then
  warn "API health check timed out — UI will still launch."
fi

# ── Start UI ──────────────────────────────────────────────────────────────────
info "Starting Electron UI..."
(cd "$UI_DIR" && HAND2NOTES_API_PORT="$API_PORT" npm run dev) &
UI_PID=$!

# ── Wait ──────────────────────────────────────────────────────────────────────
success "hand2notes is running. Press Ctrl+C to stop."
wait "$UI_PID" "$API_PID"
