#!/usr/bin/env bash
# unit-tests.sh [--test-graph-root DIR] [--with PKG]... [--] <pytest arguments>
#
# Run a test graph project's Python unit tests (test_graph/tests and the like)
# with the node SDK importable.
#
# `testgraphsdk` is not an installed package: it is source under
# <test graph root>/sdk/python/src. The graph runner puts it on the path for a
# node; a hand-written `uv run ... pytest` line does not, and every test that
# imports a node source then fails with "No module named 'testgraphsdk'". That
# reads like a red and is not one. This is the one command that gets it right.
set -euo pipefail

root="test_graph"
with=(pytest pyyaml)
while [ $# -gt 0 ]; do
  case "$1" in
    --test-graph-root) root="$2"; shift 2 ;;
    --with) with+=("$2"); shift 2 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --) shift; break ;;
    *) break ;;
  esac
done
if [ $# -eq 0 ]; then
  echo "error: name the test files or directories to run" >&2
  echo "fix:   $0 [--with PKG]... ${root}/tests/<file>.py" >&2
  exit 2
fi
sdk="$root/sdk/python/src"
if [ ! -d "$sdk/testgraphsdk" ]; then
  echo "error: no node SDK at $sdk/testgraphsdk" >&2
  echo "fix:   run from the repository root, or pass --test-graph-root <dir>; a checkout with no" >&2
  echo "       skill home has no SDK link -- run in the development checkout" >&2
  exit 2
fi
command -v uv >/dev/null 2>&1 || { echo "error: uv is not on PATH" >&2; exit 2; }
args=()
for package in "${with[@]}"; do args+=(--with "$package"); done
export PYTHONPATH="$sdk:$root/support${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
exec uv run -q "${args[@]}" python -B -m pytest -p no:cacheprovider "$@"
