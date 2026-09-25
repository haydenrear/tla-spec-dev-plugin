#!/usr/bin/env bash
# ONE COMMAND TO MAKE THIS MACHINE ABLE TO RUN THE EVALS. Run it once.
#
#   evals/setup-eval-home.sh            build it (idempotent; safe to re-run)
#   evals/setup-eval-home.sh --check    check it, change nothing
#   evals/setup-eval-home.sh --smoke    check it, then BILL ONE EVAL and prove
#                                       the whole lane end to end
#
# WHY THIS FILE EXISTS AT ALL
# ---------------------------
# Every prerequisite below was rediscovered from scratch, mid-session, by
# somebody who then had to read three files to find the fix. The Docker one was
# rediscovered twice in a single day. A prerequisite that is learned by hitting
# it is a prerequisite that will be hit again, so it is written down here as
# CODE rather than prose, and `--check` tells you which part is missing instead
# of making you infer it from a score of 0.00.
#
# WHAT IT BUILDS, AND WHY EACH PIECE
# ----------------------------------
# A scratch HOME at .toolchain/evalhome. Not a temp directory: it has to
# outlive the session that made it, or the next session rediscovers all of
# this. `.toolchain/` is already gitignored and already holds the pinned
# checkout and the jbang cache, so the whole eval toolchain sits in one place
# and `rm -rf .toolchain` is the reset button.
#
#   .docker/config.json     A COPY OF THE FILE, never a link to the directory.
#                           The Bash sandbox REFUSES to run while the Docker
#                           credential store holds a symlink anywhere inside it,
#                           and a stock Docker Desktop install puts 18 of its own
#                           CLI shims in ~/.docker (bin/docker, cli-plugins/*).
#                           None of them is a credential. Pointing DOCKER_CONFIG
#                           elsewhere does NOT help -- the check reads ~/.docker
#                           regardless, and the refusal is byte-identical. The
#                           only lever is HOME, which is why this directory
#                           exists. 60 of the 64 cases grant Bash, so without
#                           this, 60 cases score 0.00 with an error that reads
#                           like a broken substrate.
#
#   Library/Keychains ->    Overriding HOME fixes the sandbox and BREAKS
#                           authentication, because the login credential lives in
#                           the keychain and the keychain path is HOME-relative.
#                           Both hold at once only if the scratch home links it.
#
#   .claude .claude.json    Linked, not copied: settings, credentials and caches
#   .config .cache .local   that a run must see as its own.
#
# Nothing here writes ~/.docker, ~/.claude or any other real directory. The only
# thing created outside this repository is nothing at all.
#
# WHAT IT CHECKS BEYOND THE HOME
# ------------------------------
#   JDK 21+      skill-manager is `jbang SkillManager.java` with `//JAVA 21+`.
#                jbang looks for a JDK under the CURRENT home, and a sandboxed
#                run's home is empty, so it tries to download one from
#                api.foojay.io and the sandbox has no network. Result: the CLI
#                does not start and every skill-manager case grades an agent
#                that cannot run it -- silently, at 1.00 in five of six cases.
#                This machine already has a JDK; it only had to be found.
#
#   python 3.11+ skt's SessionStart hook resolves skt through a python of at
#                least 3.11 and macOS ships 3.9.6. Below the floor the hook
#                injects NOTHING, and the session loses the one line that names
#                the next command.
#
#   uv wheels    Every script in skills/*/scripts/ with a `# /// script` header
#                runs under `uv run --script`, which resolves its dependencies
#                at INVOCATION time from PyPI. A sandboxed run has no network,
#                so those scripts never start -- and the three git-epic-workflow
#                cases that require invoking a validator then burn two of their
#                three or four Bash calls on a tool that cannot run, failing
#                `within-budget` as a CONSEQUENCE rather than as a finding.
#                Measured: fixing this moved them 0.75->1.00, 0.88->1.00 and
#                0.43->0.86.
#
#                So the wheels are downloaded HERE, once, with the operator's
#                network, into .toolchain/uv-wheels. `run.sh` stages them into
#                the view and `place.sh` writes a uv.toml in the agent's home
#                naming them. A uv CACHE cannot be used for this -- it is not
#                relocatable, its environments being keyed to the path they were
#                built at, which cost five failed attempts to establish.
#
# NOTHING HERE REFUSES ANYTHING. `--check` exits non-zero so CI can read it, but
# `run.sh` never blocks on this file: a missing prerequisite warns and the run
# continues. An eval is an instrument, and an instrument that blocks the work is
# a gate wearing a lab coat.
set -euo pipefail

here=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(CDPATH= cd -- "$here/.." && pwd)

# OUTSIDE THE REPOSITORY, AND THAT IS NOT A PREFERENCE.
#
# This home contains SYMLINKS INTO THE OPERATOR'S HOME -- .claude, .config,
# .local, Library/Keychains -- because that is the only way to override HOME for
# the Docker sandbox and keep authentication working. Put that inside the
# checkout and anything which copies the checkout and dereferences links copies
# the operator's home with it.
#
# Measured, 2026-09-25, the day it was first placed at .toolchain/evalhome: the
# sktSurface graph provisions a fixture by copying the plugin checkout, followed
# the links, and wrote a 57 GB fixture directory. A 926 GB disk went to 532 MB
# free, both skt graphs errored with "[Errno 28] No space left on device", and
# every node after the first was skipped. The graphs had passed 318/318 and
# 167/167 hours earlier; nothing in them had changed.
#
# So it lives beside the operator's other caches instead. The cost is that
# `rm -rf .toolchain` no longer resets it -- `--reset` does, and the README says
# so.
EVAL_HOME_DEFAULT="${XDG_STATE_HOME:-$HOME/.local/state}/tla-spec-dev/evalhome"
EVAL_HOME="${EVAL_HOME:-$EVAL_HOME_DEFAULT}"

mode=build
case "${1:-}" in
    --check) mode=check ;;
    --reset) rm -rf "${EVAL_HOME:-$EVAL_HOME_DEFAULT}"
             echo "removed ${EVAL_HOME:-$EVAL_HOME_DEFAULT}"
             exit 0 ;;
    --smoke) mode=smoke ;;
    -h|--help)
        sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
        exit 0 ;;
    "") : ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 2 ;;
esac

fail=0
say()  { printf '%s\n' "$*"; }
ok()   { printf '  ok    %s\n' "$*"; }
bad()  { printf '  MISS  %s\n' "$*"; fail=$((fail + 1)); }
note() { printf '        %s\n' "$*"; }

# ------------------------------------------------------------------ build
if [ "$mode" = build ]; then
    say "building the eval home at $EVAL_HOME"
    mkdir -p "$EVAL_HOME/.docker" "$EVAL_HOME/Library"

    # THE FILE, NOT THE DIRECTORY. Copying ~/.docker wholesale would bring the
    # 18 symlinks that cause the refusal this exists to avoid.
    if [ -f "$HOME/.docker/config.json" ]; then
        cp "$HOME/.docker/config.json" "$EVAL_HOME/.docker/config.json"
        say "  copied ~/.docker/config.json (the file only)"
    else
        printf '{}\n' > "$EVAL_HOME/.docker/config.json"
        say "  wrote an empty .docker/config.json (you have none)"
    fi

    for p in .claude .claude.json .config .cache .local; do
        [ -e "$HOME/$p" ] || continue
        [ -e "$EVAL_HOME/$p" ] || ln -s "$HOME/$p" "$EVAL_HOME/$p"
    done
    say "  linked .claude .claude.json .config .cache .local"

    if [ -d "$HOME/Library/Keychains" ] && [ ! -e "$EVAL_HOME/Library/Keychains" ]; then
        ln -s "$HOME/Library/Keychains" "$EVAL_HOME/Library/Keychains"
    fi
    say "  linked Library/Keychains (auth survives the HOME override)"

    # THE WHEELS. Derived from the scripts rather than hardcoded, so a new
    # dependency in any skill script is picked up by re-running this.
    wheels="$repo/.toolchain/uv-wheels"
    # ALL of skills/, not just */scripts/*.py. Node files under
    # project_sdk_sources/ and test_graph/ carry the same header and run under
    # the same uv. They declare no pinned dependency TODAY -- checked -- so this
    # widening changes nothing now and stops the derivation going quietly stale
    # the first time one does.
    deps=$(grep -rh -A10 '^# /// script' "$repo/skills" 2>/dev/null \
           | grep -oE '"[A-Za-z][A-Za-z0-9_.-]*[><=!~]=[^"]*"' | tr -d '"' | sort -u)
    if [ -n "$deps" ]; then
        mkdir -p "$wheels"
        for d in $deps; do
            for v in 311 312 313 314; do
                python3 -m pip download "$d" --only-binary=:all: \
                    --python-version "$v" --implementation cp --abi "cp$v" \
                    --platform macosx_11_0_arm64 -d "$wheels" -q >/dev/null 2>&1 || true
            done
        done
        say "  downloaded $(ls "$wheels" 2>/dev/null | wc -l | tr -d ' ') wheel(s) for offline uv: $(printf '%s ' $deps)"
    else
        say '  no script-header dependencies found to download'
    fi
    say ""
fi

# ------------------------------------------------------------------ check
say "checking the eval home at $EVAL_HOME"

[ -d "$EVAL_HOME" ] && ok "the home exists" || bad "no home -- run this script with no arguments"

if [ -f "$EVAL_HOME/.docker/config.json" ]; then
    ok ".docker/config.json is present"
else
    bad ".docker/config.json missing -- the Bash sandbox needs a clean store"
fi

# THE CHECK THAT MATTERS: one symlink anywhere under .docker and every
# Bash-granting case scores 0.00.
# AN ABSENT DIRECTORY IS NOT A CLEAN ONE. `find` on a path that does not exist
# reports zero symlinks, so the naive form of this check PASSES when there is no
# home at all -- caught by running the check against a nonexistent home and
# watching it say "ok". An empty result is not a passing result, and this is the
# check whose vacuous pass would be most expensive: it is the one standing
# between a run and 60 cases scoring 0.00.
if [ ! -d "$EVAL_HOME/.docker" ]; then
    bad ".docker does not exist -- nothing to check, which is not the same as clean"
else
    dlinks=$(find "$EVAL_HOME/.docker" -type l 2>/dev/null | wc -l | tr -d ' ')
    if [ "${dlinks:-1}" = "0" ]; then
        ok ".docker exists and holds no symlinks (this is the whole point)"
    else
        bad ".docker holds $dlinks symlink(s) -- the sandbox will refuse every Bash case"
    fi
fi

if [ -e "$EVAL_HOME/Library/Keychains" ]; then
    ok "Library/Keychains is linked (auth works under the HOME override)"
else
    bad "Library/Keychains not linked -- runs will fail to authenticate"
fi

for p in .claude .claude.json; do
    [ -e "$EVAL_HOME/$p" ] && ok "$p is linked" || bad "$p not linked"
done

jdk="${JAVA_HOME:-}"
if [ -z "$jdk" ] || [ ! -x "$jdk/bin/java" ]; then
    [ -x /usr/libexec/java_home ] && jdk=$(/usr/libexec/java_home -v 21 2>/dev/null || /usr/libexec/java_home 2>/dev/null || true)
fi
if [ -n "$jdk" ] && [ -x "$jdk/bin/java" ]; then
    ok "JDK: $("$jdk/bin/java" -version 2>&1 | head -1)"
    note "JAVA_HOME=$jdk"
else
    bad "no JDK 21+ -- skill-manager cannot start and its cases grade an agent that cannot run it"
fi

# THE CHECK THAT PROVES IT, not that the files exist. A wheel for the wrong
# interpreter is a directory that looks right and resolves nothing, so this runs
# a real script with a real config and reads the exit code.
wheels="$repo/.toolchain/uv-wheels"
_v="$repo/skills/git-epic-workflow/scripts/validate_epic_plan.py"
if [ ! -d "$wheels" ] || [ -z "$(ls "$wheels" 2>/dev/null)" ]; then
    bad "no offline uv wheels -- every 'uv run --script' skill script fails in a sandboxed run"
elif [ ! -f "$_v" ]; then
    ok "uv wheels present ($(ls "$wheels" | wc -l | tr -d ' ')); no validator here to prove them against"
else
    _probe=$(mktemp -d)
    mkdir -p "$_probe/.config/uv"
    printf 'offline = true\nno-index = true\nfind-links = ["%s"]\n' "$wheels" \
        > "$_probe/.config/uv/uv.toml"
    if env -u XDG_CONFIG_HOME -u UV_CACHE_DIR HOME="$_probe" \
         uv run --script "$_v" --help >/dev/null 2>&1; then
        ok "uv resolves offline from $(ls "$wheels" | wc -l | tr -d ' ') wheel(s) (a validator really ran)"
    else
        bad "uv wheels present but a validator still will not resolve offline -- check the interpreter versions"
    fi
    rm -rf "$_probe"
fi

skt_py=""
for c in python3.14 python3.13 python3.12 python3.11; do
    p=$(command -v "$c" 2>/dev/null) || continue
    skt_py="$p"; break
done
if [ -n "$skt_py" ]; then
    ok "python for the orientation hook: $skt_py"
else
    bad "no python 3.11+ -- skt SessionStart injects nothing and the session gets no orientation"
fi

say ""
if [ "$fail" -gt 0 ]; then
    say "$fail check(s) failed. Re-run with no arguments to build, or fix the tool above."
    say "Nothing refuses on this: evals/run.sh warns and carries on."
else
    say "all checks passed."
fi

say ""
say "to use it:"
say "  EVAL_HOME=$EVAL_HOME evals/run.sh --case w-harness-smoke"
say "or nothing at all -- run.sh picks up $EVAL_HOME_DEFAULT when EVAL_HOME is unset."

# ------------------------------------------------------------------ smoke
#
# THE ONLY CHECK THAT CANNOT LIE. Everything above inspects the SHAPE of the
# setup; this bills one tiny case and reads the score. `w-harness-smoke` exists
# precisely for this -- its own description says "a red here means no other w-*
# score means anything" -- and it is 3 turns and about $0.11.
#
# It asserts a 1.00, not merely that the command ran. A run that fails to place
# its fixture, or whose grant is wrong, or that cannot reach the sandbox, exits
# 0 with a score of 0.00, so "the script ran" proves nothing at all.
if [ "$mode" = smoke ]; then
    say ""
    say "smoke: billing one case (w-harness-smoke) to prove the lane end to end"
    out=$(EVAL_HOME="$EVAL_HOME" "$here/run.sh" --case w-harness-smoke 2>&1) || true
    printf '%s\n' "$out" | grep -E "^eval: (java|SKT_PYTHON)|the CLI starts|score" || true
    if printf '%s\n' "$out" | grep -qE '^w-harness-smoke +1\.00'; then
        say "smoke: PASSED -- w-harness-smoke scored 1.00, so the lane is real"
        exit 0
    fi
    say "smoke: FAILED -- w-harness-smoke did not score 1.00."
    say "       That is the harness, not a skill. The run output is above;"
    say "       a 0.00 with a Docker message means this home is not being used."
    exit 1
fi

[ "$fail" -gt 0 ] && [ "$mode" = check ] && exit 1
exit 0
