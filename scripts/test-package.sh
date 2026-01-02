#!/usr/bin/env bash
set -euo pipefail

# test-package.sh - Build wheel, install into a clean virtualenv, and smoke test import and version
# This script is intended to be invoked via `just test-package`.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
project_root="${script_dir%/scripts}"
cd "${project_root}"

if ! command -v poetry >/dev/null 2>&1; then
	echo "poetry not found on PATH. Run 'just install-poetry' first." >&2
	exit 127
fi

# Deactivate any foreign venv to avoid interference
if [ -n "${VIRTUAL_ENV-}" ]; then
	deactivate || true
fi

# Clean build artifacts and build wheel
rm -rf dist build
poetry check
poetry build -f wheel

wheel="$(ls -t dist/*.whl 2>/dev/null | head -n1)"
if [ -z "${wheel}" ] || [ ! -f "${wheel}" ]; then
	echo "Wheel not found in dist/ after build." >&2
	exit 2
fi

venv_dir=".testpkg-venv"
rm -rf "${venv_dir}"
python3 -m venv "${venv_dir}"
# shellcheck disable=SC1091
source "${venv_dir}/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install "${wheel}"

# Read expected version from pyproject.toml using stdlib tomllib (Python 3.11+)
expected_version="$(python - <<'PY'
import tomllib
with open("pyproject.toml","rb") as f:
    data = tomllib.load(f)
print(data.get("project",{}).get("version",""))
PY
)"
if [ -z "${expected_version}" ]; then
	echo "Failed to extract version from pyproject.toml" >&2
	deactivate || true
	exit 3
fi

dist_name="MCP_remove_background"
module_name="MCP_remove_background"

# Smoke tests: import module, call add(2,3)==5 if present, and verify distribution version
python - <<PY
import importlib, importlib.metadata
name = "${dist_name}"
mod = importlib.import_module("${module_name}")
#if hasattr(mod, "add"): # A smoke test function, to optionally put here
#    assert mod.add(2, 3) == 5, "add(2,3) did not return 5"
ver = importlib.metadata.version(name)
print(f"Installed {name}=={ver}")
assert ver == "${expected_version}", f"Version mismatch: {ver} != ${expected_version}"
PY

deactivate
rm -rf "${venv_dir}"
echo "test-package: success"
