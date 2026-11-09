#!/usr/bin/env bash
# release.sh <patch|minor|major|X.Y.Z>
# Write ONE new version into BOTH plugin manifests. That is the whole job, and
# it is a script because the two files must agree: skill-manager warns on drift
# and the harness silently prefers one, so a hand-edit of either alone surfaces
# later as an inexplicable version on a consumer's machine.
#
# It does not commit, tag, or push. A version bump belongs to the change that
# earned it — usually the same commit — and pushing is outward-facing.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; . "$SCRIPT_DIR/plugin-repo-lib.sh"

usage() {
  cat >&2 <<'EOF'
usage: release.sh <patch|minor|major|X.Y.Z>

  patch   a skill's wording, a fix inside a skill
  minor   a skill JOINS the bundle, new hooks/commands, a routine upstream pull
  major   a skill LEAVES the bundle, or a contained skill's name changes (both
          change what every consumer can invoke), or a convention lands that
          consumers must act on
  X.Y.Z   an explicit version
  -h, --help  This message.

Writes the new version into .claude-plugin/plugin.json and
skill-manager-plugin.toml. Does not commit, tag, or push.
EOF
}
help_guard "$@"

BUMP="${1:-}"; [ -n "$BUMP" ] || { usage; die "a bump kind or an explicit version is required"; }
[ $# -eq 1 ] || { usage; die "release.sh takes exactly one argument, got: $*"; }

ROOT="$(repo_root)"; cd "$ROOT"
require_plugin_repo "$ROOT"

CUR="$(plugin_json_get "$ROOT" version)"
[ -n "$CUR" ] || die "$PLUGIN_JSON declares no version to bump"

case "$BUMP" in
  patch|minor|major)
    MAJOR="${CUR%%.*}"; _rest="${CUR#*.}"; MINOR="${_rest%%.*}"; PATCH="${_rest#*.}"
    case "$CUR.$MAJOR.$MINOR.$PATCH" in
      *[!0-9.]*) die "current version '$CUR' is not a numeric X.Y.Z, so '$BUMP' has no meaning — pass an explicit version" ;;
    esac
    case "$CUR" in *.*.*) : ;; *) die "current version '$CUR' is not X.Y.Z — pass an explicit version" ;; esac
    case "$BUMP" in
      major) NEW="$((MAJOR + 1)).0.0" ;;
      minor) NEW="$MAJOR.$((MINOR + 1)).0" ;;
      patch) NEW="$MAJOR.$MINOR.$((PATCH + 1))" ;;
    esac
    ;;
  *)
    # Exactly three numeric fields. The old glob accepted 1.2.3.4, which then
    # reached `$(( 3.4 + 1 ))` on the NEXT bump and aborted in bash arithmetic
    # instead of refusing here.
    _n="$BUMP"
    case "$_n" in
      *.*.*.*|*[!0-9.]*|.*|*.) usage; die "'$BUMP' is neither a bump kind (patch|minor|major) nor an X.Y.Z version" ;;
      *.*.*) NEW="$BUMP" ;;
      *) usage; die "'$BUMP' is neither a bump kind (patch|minor|major) nor an X.Y.Z version" ;;
    esac
    ;;
esac

step "Version"
info "$CUR -> $NEW"

# In-place edits through $PY: sed -i is not portable between GNU and BSD, and
# this file is edited on both.
"$PY" - "$ROOT" "$PLUGIN_JSON" "$PLUGIN_TOML" "$CUR" "$NEW" <<'PY'
import json, re, sys
from pathlib import Path

root, pjson, ptoml, cur, new = sys.argv[1:6]
root = Path(root)

p = root / pjson
data = json.loads(p.read_text(encoding="utf-8"))
data["version"] = new
# ensure_ascii=False: every description in this ecosystem carries an em dash,
# and the default would ship it to the marketplace UI as \u2014.
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"  wrote {pjson}")

t = root / ptoml
if t.exists():
    text = t.read_text(encoding="utf-8")
    # Only the [plugin] table's `version`, only the first one, and only when it
    # is the value we were told is current — a blind s/version/ would rewrite a
    # pinned dependency spec further down the file.
    out, done, in_plugin = [], False, False
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("["):
            in_plugin = s.strip("[]").strip() == "plugin"
        elif in_plugin and not done and re.match(r'\s*version\s*=', line):
            out.append(re.sub(r'("|\')%s\1' % re.escape(cur), f'"{new}"', line, count=1)
                       if cur in line else f'version = "{new}"\n')
            done = True
            continue
        out.append(line)
    t.write_text("".join(out), encoding="utf-8")
    print(f"  wrote {ptoml}" if done else f"  WARNING: no [plugin] version in {ptoml} — left unchanged")
else:
    print(f"  no {ptoml} — only {pjson} carries the version")
PY

cat >&2 <<EOF

Version is $NEW in both manifests. Nothing was committed.

Next:
  git add -A && git commit -m "release $NEW"
  git tag "v$NEW"     # optional: a pinnable ref (github:owner/repo#v$NEW). A
                      # plain git-coord install/sync does not use tags.
  # push, then consumers: skill-manager sync $(plugin_json_get "$ROOT" name) --git-latest
  #   (a green sync is NOT evidence the bytes moved — compare gitHash in
  #    \$SKILL_MANAGER_HOME/installed/<plugin>.json against the pushed HEAD)
EOF
