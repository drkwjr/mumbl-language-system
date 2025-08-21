#!/usr/bin/env bash
set -e
/usr/bin/python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r packages/data-contracts/python/requirements.txt
pip install -e packages/data-contracts/python/
echo "Bootstrap complete."
