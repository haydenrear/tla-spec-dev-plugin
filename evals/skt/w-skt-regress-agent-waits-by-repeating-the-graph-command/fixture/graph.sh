#!/usr/bin/env bash
# Eval stand-in for the graph command `skt regress` writes. It behaves like the
# real one from the agent's side: each call blocks briefly, the first calls
# print STILL RUNNING, a later one prints FINISHED. It runs nothing.
[ $# -ge 1 ] || { echo "usage: graph.sh <graph>" >&2; exit 2; }
sleep 4
count_file="${TMPDIR:-/tmp}/eval-graph-sh-$(printf '%s' "$PWD $*" | cksum | cut -d' ' -f1)"
if n=$(cat "$count_file" 2>/dev/null) || true; [ -z "${n:-}" ] && n=0; echo $((n + 1)) > "$count_file" 2>/dev/null; then
  calls=$((n + 1))
else
  # Nowhere to count: fall back to the age of this file, set when the case was placed.
  self="$0"; mtime=$(stat -f %m "$self" 2>/dev/null || stat -c %Y "$self")
  calls=$(( ( $(date +%s) - mtime ) / 60 + 1 ))
fi
if [ "$calls" -lt 3 ]; then
  echo "STILL RUNNING $*  ($calls min so far; last log line: > Task :slowGraph:run)  -- run this exact command again to keep waiting. Do nothing else meanwhile."
else
  echo "FINISHED $*  (runner exit 0)  full log: (not kept in this environment)"
  echo "BUILD SUCCESSFUL"
  echo "report: test_graph/build/validation-reports/20261114-101500"
fi
