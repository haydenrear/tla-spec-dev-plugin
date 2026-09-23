#!/bin/sh
# WHAT THE AGENT WAKES UP TO. The staged plugin's `SessionStart` hook, run with
# the workspace as its working directory, before the first turn.
#
# Why a hook and not `scaffold_script:`
# ------------------------------------
# A case may declare `scaffold_script:` and `--scaffold` promises to run it.
# **It is never executed.** Measured in 2.1.261 at every placement -- top
# level, `execution:`, `setup:`, `workspace:`, `sandbox:`, `scaffold.script` --
# and in both forms, a file name and inline bash. The decisive probe was an
# inline body of `echo ... >&2; exit 3`: the case still scored 1.00, so the
# script was not failing quietly, it was never invoked.
#
# Why this file is not loaded from the repository root
# ---------------------------------------------------
# Hooks belong to the PLUGIN, and this plugin is the repository, so a
# `hooks/hooks.json` committed at the root would run in every session of every
# user who installs tla-spec-dev. `evals/run.sh` stages it into the throwaway
# view instead. See evals/hooks/hooks.json.
#
# How one hook serves many cases
# ------------------------------
# Hooks belong to the plugin, not to a case, so this file has to know which
# case is running. `execution.env` in case.yaml is the channel, and it is
# deliberately narrow: setting any non-`EVAL_*` key is refused with *"only
# EVAL_* keys can be set from case.yaml. Anything else must come from the
# operator's shell."* So each case sets `EVAL_CASE`, and this dispatches on it.
set -u

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
plugin=$(CDPATH= cd -- "$here/../.." && pwd)
# The view IS a copy of the checkout, so the fixtures the cases draw on -- the
# examples/ trees -- are inside the plugin root. There is no `../../..` walk any
# more, and that is the difference the nesting bought: the plugin is the
# repository rather than a thin directory beside it.
repo="$plugin"
case_name="${EVAL_CASE:-}"

# EXIT 2, NOT 1. Claude Code treats exit 2 as blocking and every other non-zero
# code as advisory, so `exit 1` printed a complaint and let the session start
# anyway -- on a workspace it had just failed to set up. Where a case seeds a
# deliberate fault, that is the difference between refusing and handing the
# agent a program with nothing wrong with it, which scores well for doing
# nothing.
#
# THIS IS NOT A NEW GATE. It can only fire inside an eval run, because this
# file is only ever loaded from a staged view; nothing a user of the plugin
# does reaches it.
fail() { echo "place: $*" >&2; exit 2; }

git_init() {
    git init -q -b main . 2>/dev/null || return 0
    git config user.email harness@tla-spec-dev.invalid
    git config user.name "eval harness"
    git add -A
    git commit -q -m "$1"
}

# The shortlink fixture: a small program with no spec. Used by more than one
# case, so it is a function rather than three copies that drift apart.
place_shortlink() {
    fixture="$repo/examples/agent_integration/fixture"
    test -f "$fixture/shortlink.py" || fail "no fixture at $fixture -- refusing to hand the agent an empty repository, which would score 0 for the wrong reason"
    cp "$fixture/shortlink.py" ./shortlink.py
    cp "$fixture/test_shortlink.py" ./test_shortlink.py
}

# The ecommerce backend and the model that describes it, unfaulted.
place_ecommerce() {
    src="$repo/examples/distributed_history"
    test -d "$src/ecommerce_backend" || fail "no distributed_history example at $src"
    mkdir -p specs
    cp -R "$src/ecommerce_backend" ./ecommerce_backend
    cp -R "$src/specs/program_model" ./specs/program_model
    cp "$src/specs/__init__.py" ./specs/__init__.py 2>/dev/null || true
    rm -rf ./specs/program_model/__pycache__ ./ecommerce_backend/__pycache__
}

# ------------------------------------------------------- the moved cases
# SI-15 moved 54 cases here from skill-manager's own harness. On that side each
# one was placed by a `fixture` PLUGIN whose SessionStart hook copied a prebuilt
# `fixture-workspace` in. That plugin cannot come with them: it was delivered
# through a case's `plugins:` key, and a case declaring `plugins:` silently
# loses THIS plugin's hooks -- the ones that place every fixture here
# (SI-14-DF-01: four runs, hook fired 2/2 without the key and 0/2 with it,
# both arms scoring 1.00, so the score is blind to it).
#
# So placement moves into this hook. The convention is the one the moved
# prompts already use: 35 of them name `cases/<case>/`, and not one names
# another case's directory, so a case's own `fixture/` lands at `cases/<name>/`
# and nothing is shared between cases.
place_moved_fixture() {
    src="$here/../$1/$case_name/fixture"
    mkdir -p "cases/$case_name"
    if [ -d "$src" ]; then
        cp -R "$src/." "cases/$case_name/"
        echo "place: the fixture for $case_name is at cases/$case_name/"
    else
        # NOT A FAILURE, AND SAYING SO IS THE POINT. 20 of the moved cases ship
        # no fixture: they ask which command the agent reaches for, which is
        # decided from the transcript. This keeps "no fixture by design" apart
        # from "the fixture was lost in the move" -- the second is exactly the
        # silent failure this ticket is designed against.
        echo "place: $case_name ships no fixture/ -- by design; it is graded from the transcript"
    fi
    git_init "$case_name: the case fixture"
}

# A case whose fixture is a REAL branched Skill Manager home. That home is
# ~41,000 entries and `claude plugin eval` refuses a plugin directory over
# 20,000, so it cannot be staged into this view and these six cases cannot run
# here yet.
#
# THEY ARE DECLARED UNDECIDED, NOT SILENTLY BROKEN. An empty workspace would
# score 0 and read as "the agent could not provision a home" -- an instrument
# failing in the one direction this project says it may not. verify.sh writes a
# matching UNDECIDED verdict so the reason travels with the score.
undecided_needs_home() {
    echo "place: $case_name NEEDS A BRANCHED SKILL MANAGER HOME, which this"
    echo "place:   plugin view cannot carry: a home is ~41,000 entries and the"
    echo "place:   view's ceiling is 20,000. This case is UNDECIDED, not failed,"
    echo "place:   and its graders below are red for that reason and no other."
    echo "place:   See evals/README.md, 'The six that need a home'."
    git_init "$case_name: no Skill Manager home -- UNDECIDED"
}

case "$case_name" in

  scaffold-a-program-model)
    place_shortlink
    git_init "shortlink: the program, and the tests that hold it up"
    echo "place: the fixture is a link shortener with no spec"
    ;;

  catch-the-drift)
    # The break is not invented here. It is mutant `store-account_store` from
    # examples/distributed_history/specs/program_model/kill_mutants.toml, which
    # that example already declares as a real reviewable behavioural fault:
    # creating an account returns 201 and writes nothing to the account store.
    # Using the project's own seeded fault rather than a fresh one keeps this
    # case honest about what it measures -- MF-020, do not fit a recogniser to
    # an answer you invented for it.
    place_ecommerce
    git_init "ecommerce backend, and the model that describes it"

    # The seed. `find` must match EXACTLY ONCE: a formatter that reflows the
    # line -- double quotes to single, say -- makes this refuse rather than
    # hand the agent a program with nothing wrong with it.
    python3 - <<'SEED' || fail "could not seed the mutant; the case would run on an UNFAULTED program and pass for free"
import pathlib
p = pathlib.Path("ecommerce_backend/domain.py")
find = '            self._conn.execute("insert or ignore into accounts(account_id) values (?)", (account_id,))'
replace = "            pass  # a change from an earlier commit"
text = p.read_text(encoding="utf-8")
n = text.count(find)
if n != 1:
    raise SystemExit(f"the anchor line appears {n} times in domain.py, expected exactly 1")
p.write_text(text.replace(find, replace, 1), encoding="utf-8")
SEED
    git add -A && git commit -q -m "accounts: simplify creation"

    # AND THE SEED IS CONFIRMED BY BEHAVIOUR, not by the edit returning 0.
    # A successful string replacement is not a broken program.
    python3 - <<'CHECK' || fail "the seeded fault did not change the program's behaviour; refusing to run a case that would pass for free"
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from ecommerce_backend.domain import EcommerceStore
b = EcommerceStore()
b.create_account("acct-seed-check")
if "acct-seed-check" in repr(b.snapshot()):
    raise SystemExit("create_account still persists: the fault was not seeded")
CHECK
    echo "place: an ecommerce backend, its TLA+ model, and two commits"
    ;;

  start-from-the-spec-not-the-source)
    # discovery's question. The same repository as catch-the-drift and
    # deliberately NOT faulted: nothing here is broken, and the only thing
    # being measured is whether the account of the program comes from the
    # model that is sitting there or from a re-derivation of it by grep.
    place_ecommerce
    git_init "ecommerce backend, its TLA+ model, and its test graph"
    echo "place: an ecommerce backend with a program model already in specs/program_model"
    ;;

  a-work-order-not-a-wish)
    place_shortlink
    cat > README.md <<'EOF'
# shortlink

A link shortener. `reserve(slug, owner)` claims a slug for an owner,
`release(slug, owner)` gives it up, and `resolve(slug)` returns the target.

Known problem, reported twice this month: a slug released by one owner can be
re-reserved by a different owner while the first owner still believes it holds
it. Nobody has written down what the correct behaviour is.
EOF
    git_init "shortlink, and a problem report nobody has turned into work yet"
    echo "place: a small program and an unwritten problem"
    ;;

  use-the-front-door)
    place_shortlink
    # An ordinary work order: no epic marker anywhere in it. What the case
    # measures is the FIRST move, which this skill is emphatic about and which
    # four measured eval runs got wrong in four different ways.
    cat > ISSUE.md <<'EOF'
# SL-14: resolve() should not answer for a released slug

## Summary
`resolve()` returns the old target for a slug whose owner has released it,
until something else re-reserves it. It should report the slug as unclaimed.

## References
- `shortlink.py` -- `reserve`, `release`, `resolve`
- `test_shortlink.py` -- the existing behavioural tests

## Regression checklist
- [ ] `pytest test_shortlink.py` stays green
- [ ] a new test covers release-then-resolve
EOF
    git_init "shortlink, and an issue somebody has to pick up"
    echo "place: a repository and one ordinary (non-epic) work order in ISSUE.md"
    ;;

  epic-mode-is-not-main)
    place_shortlink
    # The same shape as the assignment blocks this repository's own epics use,
    # trimmed to what the decision needs. The marker is the whole point: it
    # selects epic mode BEFORE ordinary provisioning, and an agent that misses
    # it branches from and targets the default branch.
    cat > ISSUE.md <<'EOF'
# SL-21: reserve() should refuse a slug that is already claimed

Epic: #77 (`shortlink-hardening`). Stable ticket ID `SL-21`.

## Summary
`reserve()` overwrites an existing claim. It should refuse one.

<!-- git-epic-workflow:assignment:start -->
## Epic execution — REQUIRED

```yaml
version: 1
epic:
  id: shortlink-hardening
  workflow: shortlink-hardening
  branch: epic/shortlink-hardening
  base_sha: 0000000000000000000000000000000000000000
  default_branch: main
ticket:
  spec_id: SL-21
  feature_branch: feature/77-refuse-claimed-slug
  worktree: ../wt-77-refuse-claimed-slug
  pr_base: epic/shortlink-hardening
  wave: 1
  role: implementation
review:
  mode: external
  ticket_agent_stops_after: pr_open
  merged_by: epic-owner
```
<!-- git-epic-workflow:assignment:end -->

## References
- `shortlink.py` -- `reserve`
EOF
    git_init "shortlink, and an epic-assigned ticket in ISSUE.md"
    echo "place: a repository and an EPIC-ASSIGNED work order in ISSUE.md"
    ;;

  compose-a-behavioural-graph)
    place_shortlink
    git_init "shortlink: the program, and the unit tests that hold it up"
    echo "place: a link shortener with unit tests and no behavioural validation"
    ;;

  bootstraps-a-home-for-a-repo)
    undecided_needs_home
    ;;

  epic-provisions-a-ticket-worktree)
    undecided_needs_home
    ;;

  reconciles-a-worktree-into-the-project-home)
    undecided_needs_home
    ;;

  syncs-a-stale-home-from-root)
    undecided_needs_home
    ;;

  ticket-agent-closes-a-ticket)
    undecided_needs_home
    ;;

  ticket-agent-opens-a-ticket)
    undecided_needs_home
    ;;

  w-epic-assignment-no-force-on-blocking)
    place_moved_fixture git-epic-workflow
    ;;

  w-epic-force-when-owner-decided)
    place_moved_fixture git-epic-workflow
    ;;

  w-epic-merged-by-is-epic-owner)
    place_moved_fixture git-epic-workflow
    ;;

  w-epic-plan-free-form-lane)
    place_moved_fixture git-epic-workflow
    ;;

  w-epic-retire-part-of-goal-warns-only)
    place_moved_fixture git-epic-workflow
    ;;

  w-giw-bootstrap-cross-home-is-not-old-cli)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-epic-ticket-plan-values-win)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-epic-ticket-stops-on-wrong-pr-base)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-exit6-is-unreadable-frontmatter)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-wt-close-no-force-on-unpublished)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-wt-new-dirty-ok)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-wt-refusal-quotes-subject)
    place_moved_fixture git-issue-workflow
    ;;

  w-giw-wt-stale-branch-point)
    place_moved_fixture git-issue-workflow
    ;;

  w-harness-smoke)
    place_moved_fixture harness
    ;;

  w-misc-debug-bounded-wait)
    place_moved_fixture unnested
    ;;

  w-misc-issue-body-names-home-closeout)
    place_moved_fixture git-issue
    ;;

  w-misc-issue-names-rubric-not-copies)
    place_moved_fixture git-issue
    ;;

  w-misc-otlp-endpoint-native-runner)
    place_moved_fixture unnested
    ;;

  w-misc-plugin-repo-finalize-sh)
    place_moved_fixture plugin-repository
    ;;

  w-misc-plugin-repo-home-does-not-sandbox-install)
    place_moved_fixture plugin-repository
    ;;

  w-sdc-attribution-before-close)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-close-ticket-delivered-status)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-close-workflow-is-close-tickets)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-complexity-ledger-is-advisory)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-eval-run-has-case-glob)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-forced-close-names-guard-weakening)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-no-deferred-findings-at-root)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-open-closed-ticket-adds-new-entry)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-out-path-is-absolute)
    place_moved_fixture spec-double-2
    ;;

  w-sdc-ticket-binding-bare-adapter-module)
    place_moved_fixture spec-double-2
    ;;

  w-skt-check-pinned-is-not-stale)
    place_moved_fixture skt
    ;;

  w-skt-check-record-disagrees-with-checkout)
    place_moved_fixture skt
    ;;

  w-skt-check-unknown-is-not-current)
    place_moved_fixture skt
    ;;

  w-skt-is-a-plugin-not-a-skill)
    place_moved_fixture skt
    ;;

  w-skt-migration-delete-project-block)
    place_moved_fixture skt
    ;;

  w-skt-migration-no-import-edits)
    place_moved_fixture skt
    ;;

  w-skt-not-installed-is-not-not-synced)
    place_moved_fixture skt
    ;;

  w-skt-remedy-without-origin)
    place_moved_fixture skt
    ;;

  w-skt-stale-artifacts-are-not-stale-home)
    place_moved_fixture skt
    ;;

  w-skt-sweep-requires-epic)
    place_moved_fixture skt
    ;;

  w-skt-ticket-path-must-be-sibling)
    place_moved_fixture skt
    ;;

  w-skt-ticket-verb-help-is-scoped)
    place_moved_fixture skt
    ;;

  w-sm-closeout-ahead-is-publish-not-sync)
    place_moved_fixture skill-manager
    ;;

  w-sm-cold-shim-means-build)
    place_moved_fixture skill-manager
    ;;

  w-sm-drift-ack-once)
    place_moved_fixture skill-manager
    ;;

  w-sm-sync-retired-name-redirects)
    place_moved_fixture skill-manager
    ;;

  w-sm-sync-skt-when-absent)
    place_moved_fixture skill-manager
    ;;

  w-sm-verify-is-not-currency)
    place_moved_fixture skill-manager
    ;;

  w-tg-run-a-graph-not-bare-gradle)
    place_moved_fixture test-graph
    ;;
  "")
    fail "EVAL_CASE is unset. Every case must set it under execution.env, or this hook cannot tell which fixture to place"
    ;;

  *)
    fail "unknown EVAL_CASE '$case_name'"
    ;;
esac

# ------------------------------------------------------------ the toolchain
#
# NAMED, NOT HUNTED. The first scored run of the first case spent 39 of its 40
# turns on `find / -maxdepth 8 -iname "tla2tools*.jar"`, a scan of
# /Library/Java/JavaVirtualMachines and an `unzip` of the jar, hit the turn
# ceiling, and left behind a scratch module about a counter mod 3. The
# trace-property grader then voted FAIL, which reads as *the model is wrong*
# and meant *no model was ever attempted*.
#
# Nothing below is hardcoded. Another machine gets its own paths, or gets told
# the tool is missing -- a truthful input rather than a silent 0.
#
# A CASE THAT GRANTS NO BASH CANNOT USE ANY OF IT, and that is fine: the lines
# still land in the trace, where they answer "was the environment able to do
# this at all" for whoever reads the score.
echo "place: the toolchain, so the session does not have to go looking:"

cli=$(command -v tla-spec-dev 2>/dev/null || true)
if [ -n "$cli" ] && [ "$cli" = "$repo/evals/bin/tla-spec-dev" ]; then
    echo "  tla-spec-dev: $cli  (THE VIEW's shim)"
elif [ -n "$cli" ] && [ -n "${SI10_CHECKOUT:-}" ] && [ "$cli" = "$SI10_CHECKOUT/evals/bin/tla-spec-dev" ]; then
    echo "  tla-spec-dev: $cli  (THE CHECKOUT under review)"
elif [ -n "$cli" ] && [ "${cli##*/evals/bin/}" != "$cli" ]; then
    echo "  tla-spec-dev: $cli  (a checkout's evals/bin shim)"
elif [ -n "$cli" ]; then
    echo "  tla-spec-dev: $cli"
    echo "    WARNING: this is not a checkout's shim. The run will grade"
    echo "    whichever copy is installed, not the branch. Re-run through"
    echo "    evals/run.sh, which prepends the checkout's evals/bin."
else
    echo "  tla-spec-dev: NOT ON PATH"
fi

java=$(command -v java 2>/dev/null || true)
if [ -z "$java" ]; then
    for j in /Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java \
             /usr/lib/jvm/*/bin/java; do
        [ -x "$j" ] && { java="$j"; break; }
    done
fi
echo "  java:         ${java:-NOT FOUND} ${java:+(export PATH=\"$(dirname "$java" 2>/dev/null):\$PATH\")}"

jar=""
for c in "${TLA2TOOLS_JAR:-}" \
         "$repo/.skill-manager/bin/cli/.spec-double-compiler/tla2tools.jar" \
         "$HOME/.skill-manager/bin/cli/.spec-double-compiler/tla2tools.jar"; do
    [ -n "$c" ] && [ -f "$c" ] && { jar="$c"; break; }
done
echo "  tla2tools:    ${jar:-NOT FOUND}"

# The rest of what skill-manager.toml declares. A dependency that is missing is
# said out loud here rather than discovered as a confusing failure on turn 30.
#
# `skill-manager` joined this list in SI-14, for the same reason `tla-spec-dev`
# is checked above: the run is supposed to reach THIS epic's CLI through
# `evals/bin/skill-manager`, not the operator's brew install at
# /opt/homebrew/Cellar/skill-manager/0.28.1.
for tool in python3 pytest jinja2 tlc2 git gradle skill-manager; do
    p=$(command -v "$tool" 2>/dev/null || true)
    echo "  ${tool}: ${p:-NOT ON PATH}"
done

# ------------------------------------------------------- the PINNED toolchain
#
# WHAT MAKES A SCORE QUOTABLE. Before SI-14, no eval run recorded the toolchain
# it ran against: `skt` resolved from the operator's live home at whatever
# `main` pointed to that day (gitRef main, gitHash 286a3694, installed
# 2026-09-14) -- and `main` had ALREADY moved to 0f380781 by 2026-09-19.
# Two runs a week apart were not known to be comparable, so a score that moved
# could not be attributed to the change that was supposed to move it.
#
# `evals/run.sh` materialises the commits pinned in
# `evals/lib/toolchain.lock.toml` and stages the record beside the view.
# Printing it HERE is what puts those commits in the run's own trace, next to
# the score, instead of only in a file on the operator's disk.
record="$plugin/toolchain/RECORD.json"
if [ -f "$record" ]; then
    echo "place: the pinned toolchain (evals/lib/toolchain.lock.toml):"
    python3 - "$record" <<'PY' || echo "  (the record is present but could not be read)"
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    rec = json.load(fh)
units = rec.get("units") or []
if not units:
    # AN EMPTY RECORD IS NOT A PINNED RECORD. Say so, rather than print nothing
    # and let the silence read as "there was nothing to report".
    print("  THE RECORD NAMES NO UNITS -- this run cannot say what it ran against")
for u in units:
    print(f"  {u['unit']}: {u['pinned_commit']} ({u.get('ref_source', 'source unrecorded')})")
    if u.get("self_report"):
        print(f"      the CLI itself says: {u['self_report'].splitlines()[0]}")
for note in rec.get("drift") or []:
    print(f"  drift: {note}")
PY
else
    # NOT A REFUSAL. A run without the record is still a run; what it is not is a
    # run whose score can be quoted against a toolchain. Say which one this is.
    echo "place: NO TOOLCHAIN RECORD at $record."
    echo "  This run cannot name the toolchain it used. If it was not started"
    echo "  by evals/run.sh, that is why."
fi
exit 0
