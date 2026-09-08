#!/bin/bash
set -u

echo "[*] profile-analyzer installer (uv preferred)"

if command -v uv >/dev/null 2>&1; then
  uv venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  uv pip install -r requirements.txt
else
  echo "[!] uv not found; falling back to python3 -m venv"
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -U pip
  pip install -r requirements.txt
fi

read -r -p "[?] Install full stack (pytest, playwright, social-analyzer)? [y/N]: " full
if [[ "${full:-}" =~ ^[Yy]$ ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv pip install -r requirements-full.txt
  else
    pip install -r requirements-full.txt
  fi
  python -m playwright install chromium || true
fi

mkdir -p results
echo "[+] Done. Activate with: source .venv/bin/activate"
echo "[+] Run: python profile_analyzer.py --help"
