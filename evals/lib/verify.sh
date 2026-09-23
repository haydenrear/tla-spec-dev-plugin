#!/bin/sh
# THE GRADER THAT CAN LOOK. The staged plugin's `Stop` and `SessionEnd` hooks,
# run after the agent finishes and before the case is scored.
#
# Why this file exists
# --------------------
# A `claude plugin eval` case can observe exactly three things: paths in the
# workspace (`file_exists`), tool NAMES and their order (`tool_used`,
# `tool_order`), and the agent's final response text (`regex`, `llm`,
# `baseline`). It cannot observe file CONTENTS, tool inputs, tool outputs, or
# exit codes.
#
# That set cannot grade a toolchain. The first passing run of the first case
# scored 1.00 while `tla-spec-dev scaffold project` failed with exit 1 on all
# three attempts, and the `spec_manifest.yaml` its artefact grader accepted as
# proof the pipeline had run was typed by the agent's own `Write` tool.
#
# A hook is the way out: the sandbox that stops the agent does not apply here.
# The Bash TOOL runs under a profile denying filesystem writes to every
# subprocess it spawns; hooks are outside it, so SANY and TLC can run.
#
# WHY IT IS REGISTERED ON BOTH Stop AND SessionEnd
# ------------------------------------------------
# Measured in the skill-manager wide lane (2026-09-14, 2.1.270): a run that
# ends `error_max_turns` fires `SessionEnd` and NOT `Stop`. A round registered
# only on `Stop` lost every verdict on 12 capped runs and scored them red -- on
# work that may have been finished. Both events derive the same verdicts from
# the same workspace, so the second write is harmless.
#
# THE ORDERING RULE, AND WHY IT IS NOT WHERE YOU WOULD FIRST PUT IT
# -----------------------------------------------------------------
# The first version cleared `.eval/` at the top and wrote verdicts as it went.
# A blind review broke it in one move: the `catch-the-drift` check IMPORTS
# `ecommerce_backend/domain.py`, which is the file the agent was told to edit.
# Importing it executes agent-authored module-level code -- here, outside the
# sandbox, with `.eval/` already created and writable. Five appended lines
# wrote all four verdicts at import time, and a workspace where nothing was
# repaired and the model had been illegally edited scored 4 of 5, while this
# file's own log recorded both failures.
#
# So verdicts are collected OUTSIDE the workspace, and `.eval/` is created and
# filled only after every line of agent-authored code has already run:
#
#   1. collect into $WORK, a temp dir the workspace cannot name;
#   2. run everything, including the imports;
#   3. THEN `rm -rf .eval`, recreate it, and copy the collected verdicts in.
#
# Step 3's clear is what defeats a forgery the agent wrote during its session
# or its own code wrote during step 2. It did NOT defend against a process
# spawned to write a verdict after this script exits -- see `run_confined`,
# which does, by denying agent-authored code every filesystem write.
#
# Two rules survive from the first version:
#   * NOTHING TRUSTS THE RESPONSE. A verdict is written only after a real
#     program -- SANY, TLC, a behavioural check, a structural check, a diff --
#     succeeds.
#   * `exit 0`, ALWAYS. A Stop hook that fails non-zero can push the session
#     onward, and a verifier that changes the run it measures is not a verifier.
set -u

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
plugin=$(CDPATH= cd -- "$here/../.." && pwd)
repo="$plugin"
case_name="${EVAL_CASE:-}"

# WHERE THE VERDICTS GO, AND WHY IT IS NOT JUST ".eval".
#
# Every `file_exists` grader spells its path `.eval/<verdict>`, and `plugin
# eval` resolves that against the WORKSPACE ROOT -- the directory the session
# started in. This hook does NOT run there. A Stop hook inherits the cwd the
# agent left behind, so any case whose prompt sends the agent into a
# subdirectory (`cases/<case>/` is the house style) publishes its verdicts one
# or more levels down, where no grader looks.
#
# That failure is SILENT AND MAXIMALLY MISLEADING: the verdicts are all
# derived correctly and written correctly, the log says `ok`, and the case
# still scores 0.00 -- which reads as "the agent did the wrong thing" when the
# agent did the right thing. Measured on w-misc-plugin-repo-finalize-sh
# (2026-09-22): `forbid-no-finalize-constituents:ok
# require-runs-finalize-sh:ok`, published to
# `home/cwd/cases/w-misc-plugin-repo-finalize-sh/.eval/`, scored 0.00 twice.
#
# So the root is resolved rather than assumed. `CLAUDE_PROJECT_DIR` is the
# direct answer and needs nothing read; `verify_from_expect` re-anchors from
# the transcript's first `cwd` if it is not set (the transcript records the
# session cwd per entry, and the FIRST one predates any agent `cd`). The bare
# relative path stays as the last resort so a hand-run `sh verify.sh` in a
# workspace still publishes where it always did.
VD=".eval"
if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}" ]; then
    VD="$CLAUDE_PROJECT_DIR/.eval"
fi
WORK=$(mktemp -d 2>/dev/null) || exit 0
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/v" 2>/dev/null || exit 0
log="$WORK/verify.log"
: > "$log"
say() { echo "$@" >> "$log" 2>/dev/null; }
verdict() { echo "$2" > "$WORK/v/$1" 2>/dev/null; }

# ------------------------------------------- the moved cases' verdicts (SI-15)
# 45 of the cases SI-15 moved here ask "which command did the agent reach for",
# and `plugin eval` has no grader that can answer it: `tool_used` matches a tool
# NAME, never a command. The other side answered it with `expect.py`, which
# reads the transcript's tool_use INPUTS after the run and writes one verdict
# file per rule; graders are then plain `file_exists` checks on those files.
# That module is vendored at `checks/expect.py`. The wide lane that carried it
# is retired -- it was the second harness this ticket exists to remove.
#
# NOTHING FROM THE TRANSCRIPT IS EXECUTED. expect.py only matches text. This
# hook runs unsandboxed AS THE OPERATOR, so replaying an eval subject's command
# here would hand it a shell on the real machine.
#
# VERDICTS GO TO "$WORK/v", NEVER STRAIGHT TO .eval: the publish step at the
# bottom clears .eval and copies them in only after every line of
# agent-authored code has already run. Writing here directly would restore the
# forgery window that ordering exists to close.
verify_from_expect() {
    # STDIN IS READ LAZILY, AND DELIBERATELY SO. A Stop hook receives its
    # context as JSON on stdin, and `transcript_path` is the only route to what
    # the agent actually ran -- but reading stdin at the top of this script
    # would block any invocation whose stdin is an open pipe, and the
    # repository's own forged-workspace control runs `sh verify.sh` directly.
    # Only this path needs the transcript, so only this path reads it.
    if [ -t 0 ]; then
        say "stdin is a terminal, so there is no hook context to read"
        verdict UNDECIDED-notranscript "verify.sh was run without a Stop-hook stdin, so no command verdict could be derived"
        return 0
    fi
    stdin_json=$(cat 2>/dev/null || true)
    transcript=$(printf '%s' "$stdin_json" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("transcript_path") or "")
except Exception: print("")' 2>/dev/null)
    if [ -z "$transcript" ]; then
        # AN ABSENT TRANSCRIPT IS UNDECIDED, NOT FAILED. Every expect-based
        # grader below would otherwise go red on work that may have been
        # perfect, and read as a finding about the skill.
        say "no transcript_path on stdin; no command verdicts for $case_name"
        verdict UNDECIDED-notranscript "the Stop hook received no transcript_path, so no command verdict could be derived"
        return 0
    fi
    # Re-anchor the publish directory if CLAUDE_PROJECT_DIR did not answer.
    # Each transcript entry carries the session cwd; the first one is the
    # workspace root, before any `cd` the agent made.
    if [ "$VD" = ".eval" ]; then
        root=$(python3 -c 'import json,sys
for line in open(sys.argv[1], errors="replace"):
    try: d = json.loads(line)
    except Exception: continue
    c = d.get("cwd")
    if c:
        print(c); break' "$transcript" 2>/dev/null)
        if [ -n "$root" ] && [ -d "$root" ]; then
            VD="$root/.eval"
            say "publish dir anchored from the transcript: $VD"
        fi
    fi
    say "expect.py over $transcript"
    python3 "$here/checks/expect.py" "$transcript" "$here/.." "$WORK/v" >>"$log" 2>&1 \
        || say "expect.py failed for $case_name (see above)"
}

# The six cases whose fixture is a real branched Skill Manager home. place.sh
# says why they cannot run in a plugin view; this writes the matching verdict so
# the REASON travels next to the score instead of living in a report.
undecided_needs_home_verify() {
    say "$case_name needs a branched Skill Manager home, which the view cannot carry"
    verdict UNDECIDED-needs-home "this case needs a real branched Skill Manager home (~41,000 entries) in its workspace; the plugin view's ceiling is 20,000, so the case is UNDECIDED rather than failed"
}

# Three moved cases ship no expect.json: they are graded entirely from the final
# response by `llm` and `regex` graders. Saying so keeps "nothing to verify by
# design" apart from "the verifier silently did nothing", which look identical
# in a score.
verify_response_only() {
    say "$case_name is graded from the final response only; this hook writes no verdict"
}

# RUN AGENT-AUTHORED CODE WITH NO WRITE ANYWHERE, AND WRITE ITS VERDICT HERE.
#
# A Stop hook is outside the sandbox that constrains the agent's Bash tool, so
# anything the hook executes runs with the hook's privileges. That was a real
# hole, not a theoretical one: five lines appended to `domain.py` spawning
# `Popen([...], start_new_session=True)` with a four-second sleep produced a
# `.eval/behaviour` AFTER this script exited and before the graders read it --
# on a workspace where the program was never repaired. The hook had refused
# correctly and the refusal was overwritten by the thing it refused.
#
# A process-group kill does not close that; the payload starts a new session to
# escape exactly that. Denying writes does, and it holds for descendants, which
# inherit the profile. The check therefore CANNOT record its own verdict and
# signals through its exit status instead, which is the separation that matters:
# untrusted code decides nothing about what gets written.
run_confined() {
    name=$1; script=$2; shift 2
    if [ -n "$SANDBOX" ]; then
        PYTHONDONTWRITEBYTECODE=1 "$SANDBOX" -f "$here/checks/nowrite.sb" \
            python3 "$script" "$@" >>"$log" 2>&1
    else
        PYTHONDONTWRITEBYTECODE=1 python3 "$script" "$@" >>"$log" 2>&1
    fi
}

# EVERYTHING the hook executes, under a profile that forbids the one directory
# the graders read. SANY and TLC parse and explore agent-authored `.tla` and
# legitimately need to write -- TLC creates a metadir before exploring anything
# -- so they cannot run under `nowrite.sb`; they run under this.
#
# THE PATH MUST BE THE RESOLVED ONE. macOS resolves before matching, so a
# profile naming `/tmp/ws/.eval` does not deny a write to
# `/private/tmp/ws/.eval` -- and the failed deny looks exactly like a
# successful one, because a write that is allowed prints nothing.
confine() {
    if [ -n "$SANDBOX" ]; then
        "$SANDBOX" -D "VERDICTS=$WS_REAL/$VD" -f "$here/checks/noverdict.sb" "$@"
    else
        "$@"
    fi
}

SANDBOX=$(command -v sandbox-exec 2>/dev/null || true)
WS_REAL=$(pwd -P)
if [ -z "$SANDBOX" ]; then
    say "sandbox-exec not available: agent-authored code runs unconfined"
fi

say "verify.sh case=$case_name at $(date)"
say "cwd=$(pwd)"

# ---------------------------------------------------------------- toolchain
java=$(command -v java 2>/dev/null || true)
if [ -z "$java" ]; then
    for j in /Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java \
             /usr/lib/jvm/*/bin/java; do
        [ -x "$j" ] && { java="$j"; break; }
    done
fi

# The jar, resolved the way the project's own wrapper resolves it. A search
# rooted at `$HOME/.skill-manager` finds nothing here: inside the hook `$HOME`
# is the sandbox's own sealed home, which has neither `.claude` nor
# `.skill-manager`. That cost two cases their artefact verdicts once already.
jar="${TLA2TOOLS_JAR:-}"
if [ -z "$jar" ]; then
    tlc=$(command -v tlc2 2>/dev/null || true)
    if [ -n "$tlc" ]; then
        tlcdir=$(CDPATH= cd -- "$(dirname -- "$tlc")" && pwd)
        [ -f "$tlcdir/.spec-double-compiler/tla2tools.jar" ] &&
            jar="$tlcdir/.spec-double-compiler/tla2tools.jar"
    fi
fi
if [ -z "$jar" ]; then
    for c in "$repo/.skill-manager/bin/cli/.spec-double-compiler/tla2tools.jar" \
             "${SI10_CHECKOUT:-/nonexistent}/.skill-manager/bin/cli/.spec-double-compiler/tla2tools.jar" \
             "$HOME/.skill-manager/bin/cli/.spec-double-compiler/tla2tools.jar"; do
        [ -f "$c" ] && { jar="$c"; break; }
    done
fi
say "java=${java:-MISSING} jar=${jar:-MISSING}"

# WHAT THIS MARKER DOES AND DOES NOT DO.
#
# It records that the tools resolved, so a human reading `.eval/` can tell "the
# model does not parse" from "SANY never ran". IT DOES NOT CHANGE THE SCORE,
# and no grader may read it -- a forged workspace earns it too.
#
# `file_exists` has only pass and fail. There is no UNDECIDED. So when the
# toolchain is missing, `parses` and `checks` are absent and score FAIL on a
# model that may be perfect. That is SS-02 and this script cannot fix it from
# the inside; what it can do is leave the reason where the person reading a 0
# will find it.
if [ -n "$java" ] && [ -n "$jar" ]; then
    verdict toolchain "java=$java jar=$jar"
else
    verdict UNDECIDED-toolchain "SANY and TLC could not run; parses/checks below are UNDECIDED, not failed"
    say "TOOLCHAIN INCOMPLETE -- every SANY/TLC verdict is UNDECIDED, not failed"
fi

if [ -z "$SANDBOX" ]; then
    verdict UNDECIDED-unconfined "sandbox-exec was unavailable, so agent-authored code ran unconfined and could have written any verdict below"
fi

MODEL="specs/program_model"

# ------------------------------------------------- V1: every module parses
sany() {
    [ -n "$java" ] && [ -n "$jar" ] || { say "V1 skipped: no java or jar"; return 1; }
    [ -d "$MODEL" ] || { say "V1: no $MODEL"; return 1; }
    any=0
    ok=1
    # Globbed rather than word-split from `ls`: the previous `for m in $mods`
    # split `My Mod.tla` into two names, failed both, and withheld the verdict
    # from a model that parses.
    for m in "$MODEL"/*.tla; do
        [ -f "$m" ] || continue
        any=1
        base=$(basename "$m")
        # Run FROM the model directory on a bare filename: SANY resolves
        # `EXTENDS Internal` against the working directory, and invoking it
        # from the workspace root reported `Cannot find source file for module
        # Internal` on a module that parses perfectly.
        if (cd "$MODEL" && confine "$java" -cp "$jar" tla2sany.SANY "$base") >>"$log" 2>&1; then
            say "SANY ok: $base"
        else
            say "SANY FAILED: $base"
            ok=0
        fi
    done
    [ "$any" = 1 ] || { say "V1: no .tla modules"; return 1; }
    [ "$ok" = 1 ]
}

# ------------------------------------------- V2: TLC explores a finite model
#
# A CONFIG THAT ASSERTS NOTHING IS NOT A CHECK. The first version accepted any
# config whose run printed "Model checking completed. No error has been found",
# and a six-line stub with a `.cfg` naming only `SPECIFICATION Spec` prints
# exactly that. So the config has to declare an INVARIANT or a PROPERTY first.
tlc() {
    [ -n "$java" ] && [ -n "$jar" ] || { say "V2 skipped: no java or jar"; return 1; }
    found=0
    for cfg in "$MODEL"/*.cfg; do
        [ -f "$cfg" ] || continue
        base=$(basename "$cfg" .cfg)
        [ -f "$MODEL/$base.tla" ] || { say "TLC: $base.cfg has no $base.tla"; continue; }
        if ! grep -qiE '^[[:space:]]*(INVARIANT|INVARIANTS|PROPERTY|PROPERTIES)\b' "$cfg"; then
            say "TLC: $base.cfg declares no INVARIANT and no PROPERTY -- a run over it asserts nothing"
            continue
        fi
        say "TLC on $base"
        out=$(cd "$MODEL" && confine "$java" -XX:+UseParallelGC -cp "$jar" tlc2.TLC \
                 -config "$base.cfg" -workers 1 -cleanup "$base.tla" 2>&1)
        echo "$out" >> "$log" 2>/dev/null
        if echo "$out" | grep -q "Model checking completed. No error has been found"; then
            states=$(echo "$out" | grep -oE '[0-9]+ distinct states found' | head -1)
            say "TLC clean: $base (${states:-state count not reported})"
            echo "$base ${states:-}" >> "$WORK/v/checks"
            found=1
        else
            say "TLC did not complete cleanly: $base"
        fi
    done
    [ "$found" = 1 ]
}

case "$case_name" in

  scaffold-a-program-model)
    sany && verdict parses "every module parses"
    tlc || rm -f "$WORK/v/checks"

    if run_confined manifest "$here/checks/manifest.py" "$MODEL/spec_manifest.yaml"; then
        verdict manifest "a manifest, not a token"
    fi
    ;;

  catch-the-drift)
    sany && verdict parses "every module parses"

    # V2': the program does what its model says again.
    #
    # THIS EXECUTES AGENT-AUTHORED CODE -- `domain.py` is the file the agent was
    # told to edit -- so it runs confined and writes nothing. The verdict below
    # is written by this script, from the exit status.
    if run_confined behaviour "$here/checks/behaviour.py"; then
        verdict behaviour "create_account persists"
    fi

    # V3': the repair is in the PROGRAM, not in the model. The cheapest way to
    # make a program agree with its model is to change the model.
    shipped="$repo/examples/distributed_history/specs/program_model"
    if [ ! -d "$MODEL" ]; then
        say "model-intact: no $MODEL in the workspace"
    elif [ ! -d "$shipped" ]; then
        say "model-intact UNDECIDED: no reference tree at $shipped to compare against"
        verdict UNDECIDED-reference "the shipped model tree is missing; model-intact could not be decided"
    elif diff -r -x '__pycache__' -x '*.pyc' "$shipped" "$MODEL" >>"$log" 2>&1; then
        verdict model-intact "model untouched"
        say "model matches the shipped tree"
    else
        say "the model tree was modified -- the fix belongs in the program"
    fi
    ;;

  start-from-the-spec-not-the-source)
    # The account has to be ANCHORED IN THE MODEL THAT IS SITTING THERE. The
    # check reads the workspace's own Internal.tla, extracts the action names
    # the module actually defines, and requires the write-up to name several of
    # them. A plausible essay about an ecommerce backend does not pass: the
    # names are this model's, not the domain's.
    if run_confined grounded "$here/checks/discovery_map.py"; then
        verdict grounded "the account names actions this model actually defines"
    fi
    ;;

  a-work-order-not-a-wish)
    if run_confined work-order "$here/checks/work_order.py"; then
        verdict work-order "the issue carries the parts an implementer needs"
    fi
    ;;

  use-the-front-door)
    if run_confined front-door "$here/checks/front_door.py"; then
        verdict front-door "the plan starts at the worktree front door"
    fi
    ;;

  epic-mode-is-not-main)
    if run_confined epic-mode "$here/checks/epic_plan.py"; then
        verdict epic-mode "the plan targets the epic branch and stops at PR open"
    fi
    ;;

  compose-a-behavioural-graph)
    if run_confined graph "$here/checks/testgraph_scaffold.py"; then
        verdict graph "a test_graph project with a registered graph and a real node"
    fi
    ;;

  bootstraps-a-home-for-a-repo)
    undecided_needs_home_verify
    ;;

  epic-provisions-a-ticket-worktree)
    undecided_needs_home_verify
    ;;

  reconciles-a-worktree-into-the-project-home)
    undecided_needs_home_verify
    ;;

  syncs-a-stale-home-from-root)
    undecided_needs_home_verify
    ;;

  ticket-agent-closes-a-ticket)
    undecided_needs_home_verify
    ;;

  ticket-agent-opens-a-ticket)
    undecided_needs_home_verify
    ;;

  w-epic-assignment-no-force-on-blocking)
    verify_from_expect
    ;;

  w-epic-force-when-owner-decided)
    verify_from_expect
    ;;

  w-epic-merged-by-is-epic-owner)
    verify_from_expect
    ;;

  w-epic-plan-free-form-lane)
    verify_from_expect
    ;;

  w-epic-retire-part-of-goal-warns-only)
    verify_from_expect
    ;;

  w-giw-bootstrap-cross-home-is-not-old-cli)
    verify_from_expect
    ;;

  w-giw-epic-ticket-plan-values-win)
    verify_from_expect
    ;;

  w-giw-epic-ticket-stops-on-wrong-pr-base)
    verify_from_expect
    ;;

  w-giw-exit6-is-unreadable-frontmatter)
    verify_from_expect
    ;;

  w-giw-wt-close-no-force-on-unpublished)
    verify_from_expect
    ;;

  w-giw-wt-new-dirty-ok)
    verify_from_expect
    ;;

  w-giw-wt-refusal-quotes-subject)
    verify_from_expect
    ;;

  w-giw-wt-stale-branch-point)
    verify_from_expect
    ;;

  w-harness-smoke)
    verify_from_expect
    ;;

  w-misc-debug-bounded-wait)
    verify_response_only
    ;;

  w-misc-issue-body-names-home-closeout)
    verify_from_expect
    ;;

  w-misc-issue-names-rubric-not-copies)
    verify_response_only
    ;;

  w-misc-otlp-endpoint-native-runner)
    verify_response_only
    ;;

  w-misc-plugin-repo-finalize-sh)
    verify_from_expect
    ;;

  w-misc-plugin-repo-home-does-not-sandbox-install)
    verify_from_expect
    ;;

  w-sdc-attribution-before-close)
    verify_from_expect
    ;;

  w-sdc-close-ticket-delivered-status)
    verify_from_expect
    ;;

  w-sdc-close-workflow-is-close-tickets)
    verify_from_expect
    ;;

  w-sdc-complexity-ledger-is-advisory)
    verify_from_expect
    ;;

  w-sdc-eval-run-has-case-glob)
    verify_from_expect
    ;;

  w-sdc-forced-close-names-guard-weakening)
    verify_from_expect
    ;;

  w-sdc-no-deferred-findings-at-root)
    verify_from_expect
    ;;

  w-sdc-open-closed-ticket-adds-new-entry)
    verify_from_expect
    ;;

  w-sdc-out-path-is-absolute)
    verify_from_expect
    ;;

  w-sdc-ticket-binding-bare-adapter-module)
    verify_from_expect
    ;;

  w-skt-check-pinned-is-not-stale)
    verify_from_expect
    ;;

  w-skt-check-record-disagrees-with-checkout)
    verify_from_expect
    ;;

  w-skt-check-unknown-is-not-current)
    verify_from_expect
    ;;

  w-skt-is-a-plugin-not-a-skill)
    verify_from_expect
    ;;

  w-skt-migration-delete-project-block)
    verify_from_expect
    ;;

  w-skt-migration-no-import-edits)
    verify_from_expect
    ;;

  w-skt-not-installed-is-not-not-synced)
    verify_from_expect
    ;;

  w-skt-remedy-without-origin)
    verify_from_expect
    ;;

  w-skt-stale-artifacts-are-not-stale-home)
    verify_from_expect
    ;;

  w-skt-sweep-requires-epic)
    verify_from_expect
    ;;

  w-skt-ticket-path-must-be-sibling)
    verify_from_expect
    ;;

  w-skt-ticket-verb-help-is-scoped)
    verify_from_expect
    ;;

  w-sm-closeout-ahead-is-publish-not-sync)
    verify_from_expect
    ;;

  w-sm-cold-shim-means-build)
    verify_from_expect
    ;;

  w-sm-drift-ack-once)
    verify_from_expect
    ;;

  w-sm-sync-retired-name-redirects)
    verify_from_expect
    ;;

  w-sm-sync-skt-when-absent)
    verify_from_expect
    ;;

  w-sm-verify-is-not-currency)
    verify_from_expect
    ;;

  w-tg-run-a-graph-not-bare-gradle)
    verify_from_expect
    ;;
  "")
    say "EVAL_CASE unset; nothing verified"
    verdict UNDECIDED-nocase "EVAL_CASE was not set, so no case arm ran and nothing was checked"
    ;;
  *)
    say "unknown EVAL_CASE '$case_name'; nothing verified"
    verdict UNDECIDED-nocase "unknown EVAL_CASE '$case_name'"
    ;;
esac

# ---------------------------------------------------------------- publish
# ONLY NOW. Every line of agent-authored code has already run; anything it
# wrote under `.eval/` dies here.
say "verdicts: $(ls "$WORK/v" 2>/dev/null | tr '\n' ' ')"
say "publish dir: $VD"
rm -rf "$VD"
mkdir -p "$VD" 2>/dev/null || exit 0
for v in "$WORK/v/"*; do
    [ -f "$v" ] && cp "$v" "$VD/$(basename "$v")" 2>/dev/null
done
cp "$log" "$VD/verify.log" 2>/dev/null
exit 0
