#!/usr/bin/env bash
# BS-20 (#202): the finite local fixture, against the REAL skill-manager CLI.
#
# One unit (`fixa`) with one skill-script CLI dep (`fixtool`), installed from a
# local git repo into a throwaway home. Every agent root, HOME and
# user.home point inside the scratch dir, so nothing outside it is written and
# no unrelated installed CLI is reachable — the producer set is exactly one.
#
# Then the store is moved under its install record (a commit in
# skills/fixa that does not touch skill-scripts/), which is what reconciling a
# reviewed pin into a home does: unit-store:fixa goes positively stale while
# fixtool's own install fingerprint still matches its bytes.
#
# usage: real_fixture.sh <scratch-dir> <skt-src-dir> <out-dir>
set -uo pipefail
S=${1:?scratch dir}; SKT_SRC=${2:?skt src dir}; OUT=${3:?out dir}
SM=${SM:-/opt/homebrew/Cellar/skill-manager/0.28.2/libexec/bin/skill-manager}
rm -rf "$S"; mkdir -p "$S/ws/.skill-manager/bin/cli" "$S/units/fixa/skill-scripts" "$S/agent/.claude" "$OUT"
cat > "$S/ws/.skill-manager/policy.toml" <<'EOF'
require_confirmation = false
[install]
require_confirmation_for_hooks = false
require_confirmation_for_mcp = false
require_confirmation_for_cli_deps = false
require_confirmation_for_executable_commands = false
EOF
U=$S/units/fixa
printf -- '---\nname: fixa\ndescription: BS-20 fixture declaring the skill-script CLI dep fixtool.\n---\n# fixa\n' > "$U/SKILL.md"
cat > "$U/skill-manager.toml" <<'EOF'
[skill]
name = "fixa"
version = "0.1.0"
description = "BS-20 fixture declaring the skill-script CLI dep fixtool."

[[cli_dependencies]]
spec = "skill-script:fixtool"
on_path = "fixtool"

[cli_dependencies.install.any]
script = "install-fixtool.sh"
binary = "fixtool"
EOF
cat > "$U/skill-scripts/install-fixtool.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tree="$SKILL_MANAGER_HOME/cache/skill-script-fixa-fixtool"
mkdir -p "$tree/bin" "$SKILL_MANAGER_HOME/bin/cli"
{ echo '#!/usr/bin/env bash'; echo 'echo "fixtool v1"'; } > "$tree/bin/fixtool"
chmod +x "$tree/bin/fixtool"
{ echo '#!/usr/bin/env bash'; echo "exec \"$tree/bin/fixtool\" \"\$@\""; } > "$SKILL_MANAGER_HOME/bin/cli/fixtool"
chmod +x "$SKILL_MANAGER_HOME/bin/cli/fixtool"
EOF
chmod +x "$U/skill-scripts/install-fixtool.sh"
g() { git -c user.email=f@x -c user.name=f "$@"; }
(cd "$U" && git init -q && git add -A && g commit -qm init)

export SKILL_MANAGER_HOME=$S/ws/.skill-manager
export CLAUDE_HOME=$S/agent CLAUDE_CONFIG_DIR=$S/agent/.claude CODEX_HOME=$S/agent/.codex GEMINI_HOME=$S/agent/.gemini
export HOME=$S/agent JAVA_TOOL_OPTIONS=-Duser.home=$S/agent SKILL_MANAGER_CONFINE_ROOT=$S
unset SKILL_MANAGER_CLI
ln -sf "$SM" "$SKILL_MANAGER_HOME/bin/cli/skill-manager"   # the home's own pin, for skt
cd "$S/ws"
stale_summary() { "$SM" artifacts stale --json 2>/dev/null | python3 -c '
import json,sys; d=json.load(sys.stdin); print("stale", d["summary"]["stale"], "current", d["summary"]["current"])
for r in d.get("stale", []): print("  ", r["id"], r["materialization"], r["because"], "|", r["reason"][:120])'; }
PY=${PY:-/Users/hayde/.local/bin/python3.12}
skt() { PYTHONPATH="$SKT_SRC" "$PY" -m skt.cli "$@"; }

{
echo "== skill-manager: $("$SM" --version 2>/dev/null | head -1)"
echo "== install fixa"; "$SM" install "$U" --yes >/dev/null 2>&1; echo "exit $?"
stale_summary
echo "== move the store under its record (reviewed pin reconciled; skill-scripts/ untouched)"
(cd "$SKILL_MANAGER_HOME/skills/fixa" && echo reviewed >> SKILL.md && g commit -qam reviewed && git log --oneline -2)
stale_summary
echo "== independent byte proof: installed skill-scripts/ vs unit source, and the tool runs"
diff -r "$U/skill-scripts" "$SKILL_MANAGER_HOME/skills/fixa/skill-scripts" && echo "skill-scripts/: identical"
shasum -a 256 "$U/skill-scripts/install-fixtool.sh" "$SKILL_MANAGER_HOME/skills/fixa/skill-scripts/install-fixtool.sh"
"$SKILL_MANAGER_HOME/bin/cli/fixtool"; echo "fixtool exit $?"
for i in 1 2; do
  echo "== skt build fixtool, run $i"
  skt build fixtool; echo "skt exit $?"
  skt build fixtool --json > "$OUT/skt-build-$i.json" 2>/dev/null; echo "skt --json exit $?"
done
echo "== repair the ancestor with its printed remedy (isolated: one unit, one CLI)"
"$SM" sync fixa --yes >/dev/null 2>&1; echo "sync exit $?"
stale_summary
echo "== skt build fixtool, after repair"
skt build fixtool; echo "skt exit $?"
} 2>&1
