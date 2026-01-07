#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$repo_root/.venv" ]]; then
  python3 -m venv "$repo_root/.venv"
fi

source "$repo_root/.venv/bin/activate"
pip install -r "$repo_root/requirements.txt"

cleanup() {
  if [[ -n "${backend_pid:-}" ]]; then
    kill "$backend_pid" 2>/dev/null || true
  fi
  if [[ -n "${frontend_pid:-}" ]]; then
    kill "$frontend_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT

uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000 &
backend_pid=$!

(
  cd "$repo_root/frontend"
  if [[ ! -d node_modules ]]; then
    npm install
  fi
  npm run dev -- --host 0.0.0.0 --port 5173
) &
frontend_pid=$!

wait "$backend_pid" "$frontend_pid"
