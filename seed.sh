#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "$repo_root/.venv/bin/python" ]]; then
  echo "Virtualenv not found. Run ./dev.sh once to create it." >&2
  exit 1
fi

"$repo_root/.venv/bin/python" -m backend.seed
