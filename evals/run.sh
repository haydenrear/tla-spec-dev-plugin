#!/usr/bin/env bash
# THE ONE COMMAND.
#
#   evals/run.sh                       every case
#   evals/run.sh --case catch-the-drift        one of them
#   evals/run.sh --case 'git-*' --runs 2       any claude-plugin-eval flag
#
# What it does, and why each part is here rather than in a README somebody has
# to follow by hand. Every one of the five was learned from a run that scored 0
# for a reason that was not the agent's.
#
# 1. STAGES A VIEW OF THIS CHECKOUT THAT EXCLUDES THE APPEND-ONLY RECORD.
#    `claude plugin eval` refuses a plugin directory over 20,000 entries:
#
#      a plugin directory holds more than 20000 entries to check for eval
#      directories -- point the case at a smaller plugin directory
#
#    Measured on 2.1.275 at 994f650c: this checkout is 70,741 entries, and the
#    refusal fires. It is not close. There is no ignore file, no flag and no
#    manifest key that excludes anything from that count (the traversal skips
#    `.git`, `.svn`, `.hg` and nothing else), so the only way to hand the CLI a
#    small plugin directory is to hand it a different directory. This stages
#    one, made fresh on every run so it cannot drift from what it was built
#    from.
#
#    UPDATED 2026-09-23: it is built from a COMMIT, not from the working tree.
#    Copying the tree with an exclude list staged everything `.gitignore` hides,
#    because `tar` does not read it -- 360,230 entries by then, of which
#    294,611 were `test_graph/build` and ~56,500 `examples/*/evidence`. Built
#    from `git archive HEAD`, the same checkout is 30,849, and 8,640 once
#    `specs/.history` is dropped. See "the view" below.
#
#    The previous answer was a committed symlink shim carrying one skill's
#    surface. It could not grow to the nested skills -- it named
#    `skills/spec-double-2` explicitly, and there are six -- and a committed
#    directory that has to be edited whenever a skill is added goes stale
#    silently. A staged copy carries whatever the checkout carries.
#
# 2. STAGES THE HOOKS. `evals/hooks/hooks.json` is copied to
#    `<view>/hooks/hooks.json`.
#
#    SI-16 CHANGED WHAT THAT COPY DOES, and the old wording here is retired.
#    This used to say "staging keeps the shipped plugin hookless", which was
#    true while the repository shipped no hooks. It now DOES: absorbing skt
#    lifted its two hooks to the repository root, so `hooks/hooks.json` is a
#    COMMITTED FILE and this `cp` OVERWRITES it inside the view.
#
#    That is deliberate and is left as an overwrite, not a merge. An eval run
#    must load the fixture-placing hooks and only those; merging skt's
#    SessionStart in would add a `skt status` spawn to every case and move
#    scores in a ticket that is not about evals. The consequence to know is
#    that AN EVAL RUN DOES NOT EXERCISE THE SHIPPED HOOKS -- so this suite is
#    not evidence about them. Their evidence is <home>/logs/skt/hook.log and
#    the sktHooks graph (SI-16-DF-02).
#
#    The original reason the fixture hooks stay uncommitted still stands: a
#    fixture hook's blocking exit 2 would be able to refuse somebody's ordinary
#    session. skt's two shipped hooks never exit non-zero by contract.
#
# 3. PUTS THE CHECKOUT'S CLI FIRST ON PATH. Without `evals/bin` first, the run
#    grades whichever `tla-spec-dev` the operator has installed. Measured: a
#    run's `which -a tla-spec-dev` returned the installed wrapper three times
#    and nothing else. A plugin `bin/` directory does not reach the eval's
#    PATH, and `execution.env` refuses `PATH` ("only EVAL_* keys can be set
#    from case.yaml"), so the operator's shell is the only channel -- which is
#    what this script is.
#
# 4. DERIVES `--allow-tools` FROM THE CASES IT IS ABOUT TO RUN. A tool named in
#    a case's `allowed_tools:` is still refused unless the operator ALSO grants
#    it. `--allow-tools Bash` against a case declaring `[Bash, Write, Edit]`
#    produced `not granted (missing --allow-tools grant, or a malformed
#    entry): Write, Edit` and a score of 0 -- an agent that could read the
#    program and could not write one line of the spec, reported as a failure to
#    model. A README cannot keep that in step; this reads the cases.
#
# 5. HARVESTS THE RESULTS BACK. The CLI writes its report next to the plugin,
#    which is the throwaway view, so the report would vanish with it.
#
# 6. MATERIALISES THE PINNED TOOLCHAIN, ASKS ABOUT IT, AND RECORDS IT. (SI-14.)
#    Before this, every run resolved its toolchain from the OPERATOR'S LIVE
#    HOME: the project home's `skt` said `gitRef main, gitHash 286a3694,
#    installed 2026-09-14`, and by 2026-09-19 `main` was `0f380781`. Zero runs
#    recorded what they ran against, so no two runs a week apart were known to
#    be comparable and a score that moved could not be attributed to the change
#    that was supposed to move it.
#
#    `claude plugin eval` cannot help: its `plugins:` field takes relative
#    filesystem PATHS only -- no git ref, no marketplace constraint, no
#    lockfile, no manifest-level plugin-depends-on-plugin. So the pin cannot be
#    DECLARED to the CLI, only MATERIALISED: `lib/toolchain.py` fetches each
#    commit named in `lib/toolchain.lock.toml`, verifies the checkout IS that
#    commit, stages it beside the view and writes a run record that
#    `lib/place.sh` prints into the run's own trace.
#
#    "Which version?" is therefore a RUNNER obligation, not a schema one: there
#    is no field for the CLI to prompt about, and `execution.env` refuses
#    everything but `EVAL_*`, so the operator's shell is the only channel.
#
# NOTHING HERE REFUSES -- with one bounded exception added in SI-14, below.
# Every check warns on one line and carries on: an eval is an instrument, and an
# instrument that blocks the work is a gate wearing a lab coat. The exception is
# not a gate either: on a FULL-SUITE run at a terminal the script ASKS which
# toolchain to use, because a silent default is the defect SI-14 exists to
# close. Asking is not refusing -- pressing Enter takes the pin -- and with no
# terminal to ask at, it takes the pin and SAYS SO rather than blocking a CI
# run. A single-case run defaults to the pin and says what it defaulted to.
set -euo pipefail

here=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(CDPATH= cd -- "$here/.." && pwd)

# A path the eval sandbox can reach. The operator's home is not one: the same
# command succeeded in an ordinary shell and failed inside a run, and
# /private/tmp is where the CLI keeps its own temporaries.
view="${SI10_VIEW:-/private/tmp/tla-spec-dev-eval-view}"

# ---------------------------------------------------------------- the view
#
# THE VIEW IS A COMMIT, NOT THE WORKING TREE.
#
# This used to `tar` the working tree with an exclude list, and the exclude list
# was the defect. `tar` does not read `.gitignore`, so every ignored byte on
# disk was staged and counted: measured 2026-09-23, the working-tree view held
# 360,230 entries against the CLI's hard 20,000 ceiling. 294,611 of those were
# `test_graph/build` and ~56,500 were `examples/*/evidence` -- run output, not
# repository content. `git status` reported ZERO untracked files in the latter,
# because every one of them is ignored. An exclude list can only ever name the
# residue somebody already tripped over; three were added that way before this.
#
# `git archive <commit>` enumerates TRACKED CONTENT AT THAT COMMIT and nothing
# else, so ignored residue cannot enter the view however much of it is on disk.
# Measured on the same checkout: 30,849 entries, and 8,640 once `specs/.history`
# is dropped -- 11,360 under the ceiling, against 360,230 before.
#
# WHY IT REFUSES A DIRTY OR UNPUSHED CHECKOUT. A score is a claim about a
# COMMIT. If the view is built from work that is uncommitted, or committed and
# unpushed, then nobody else can reconstruct what was graded and the run record
# names a sha that does not contain what ran. The refusal is overridable with
# SI10_ALLOW_DIRTY=1, which says so loudly in the output and in the record,
# because iterating on a case locally is a real thing to want -- but it is never
# the default and never silent.
echo "eval: staging a plugin view of $repo"

# "Unpushed" asks whether ANYBODY ELSE CAN FETCH THIS COMMIT, which is not the
# same as whether it is on this branch's configured upstream. Measured
# 2026-09-23: this branch's `@{u}` is `origin/epic/self-improvement-substrate`
# in the ARCHIVED tla-spec-dev repository, while delivery happens on
# `tla-spec-dev-plugin/main`. Checking `@{u}..` therefore reported 13 unpushed
# commits for a tip that was published and fetchable -- refusing a run that
# should have been allowed, for a reason that was about remote bookkeeping
# rather than reproducibility.
#
# `git branch -r --contains HEAD` answers the question directly: it lists every
# remote-tracking ref that already contains this commit. Empty means no remote
# has it and the sha in the record names something only this disk holds.
dirty=$(git -C "$repo" status --porcelain 2>/dev/null)
on_remote=$(git -C "$repo" branch -r --contains HEAD 2>/dev/null | sed 's/^[ *]*//' | grep -v '^$' || true)
if [ -n "$on_remote" ]; then
    unpushed=""
else
    unpushed=$(git -C "$repo" log --oneline -10 "$(git -C "$repo" rev-parse HEAD)" --not --remotes 2>/dev/null || true)
fi
if [ -n "$dirty" ] || [ -n "$unpushed" ]; then
    if [ "${SI10_ALLOW_DIRTY:-0}" = "1" ]; then
        echo "eval: WARNING -- SI10_ALLOW_DIRTY=1. The view is built from HEAD, so"
        echo "eval:            uncommitted work is NOT in it and unpushed commits are"
        echo "eval:            not reachable by anyone else. This score is not"
        echo "eval:            reproducible from the recorded sha."
        [ -n "$dirty" ]    && echo "eval:            uncommitted: $(printf '%s' "$dirty" | wc -l | tr -d ' ') path(s)"
        [ -n "$unpushed" ] && echo "eval:            on no remote: $(printf '%s' "$unpushed" | wc -l | tr -d ' ') commit(s) only this disk holds"
    else
        echo "eval: REFUSING -- a score is a claim about a commit, and this checkout" >&2
        echo "eval:   does not match one that anybody else can fetch." >&2
        [ -n "$dirty" ] && {
            echo "eval:   uncommitted changes:" >&2
            printf '%s\n' "$dirty" | sed 's/^/eval:     /' >&2
        }
        [ -n "$unpushed" ] && {
            echo "eval:   this commit is on NO remote -- nobody else can fetch it:" >&2
            printf '%s\n' "$unpushed" | sed 's/^/eval:     /' >&2
        }
        echo "eval:   fix: commit and push, or re-run with SI10_ALLOW_DIRTY=1 to grade" >&2
        echo "eval:        HEAD anyway and have the record say the score is not" >&2
        echo "eval:        reproducible." >&2
        exit 1
    fi
fi

view_commit=$(git -C "$repo" rev-parse HEAD)
echo "eval: the view is commit $view_commit"
rm -rf "$view"
mkdir -p "$view"
git -C "$repo" archive "$view_commit" | tar -xf - -C "$view"

# specs/.history is 22,209 entries of append-only closed-epic record. It is
# TRACKED, so `git archive` carries it and the exclude has to happen here rather
# than in the enumeration. No case reads it.
rm -rf "$view/specs/.history"

entries=$(find "$view" | wc -l | tr -d ' ')
echo "eval: the view holds $entries entries (the limit is 20000; tracked at this commit is $(git -C "$repo" ls-tree -r --name-only "$view_commit" | wc -l | tr -d ' '), and the working tree on disk is $(find "$repo" -path "$repo/.git" -prune -o -print | wc -l | tr -d ' '))"
if [ "$entries" -ge 20000 ]; then
    # WARN, NEVER REFUSE. The run that follows will fail with the CLI's own
    # message, which is more informative than anything this script could say;
    # what this line adds is where the entries went.
    echo "eval: WARNING -- the view is over the 20000-entry limit and the run below will be refused."
    echo "eval:            the biggest directories in it are:"
    (cd "$view" && for d in */ .[!.]*/; do [ -d "$d" ] && echo "  $(find "$d" | wc -l | tr -d ' ') $d"; done | sort -rn | head -5) || true
fi

mkdir -p "$view/hooks"
cp "$here/hooks/hooks.json" "$view/hooks/hooks.json"

# ------------------------------------------------------------- the grant
# Read the cases this invocation will actually run, and grant exactly the gated
# tools they declare. `--case` is a glob, so the filter here is the same glob.
#
# SI-21: `--case` is REPEATABLE, and this used to keep only the last one. Every
# `--case` was still appended to `args` and passed to the CLI, so a three-case
# invocation ran three cases and derived its grant from ONE of them -- and a
# short grant is scored 0.00 and reported as a skill failure, which is the exact
# defect lib/grant.py was written to prevent. Measured: `--case A --case B
# --case C` printed `cases selected: C`. Now every glob is collected and a case
# matching ANY of them is selected.
case_globs=()
toolchain_ref=''
args=()
while [ $# -gt 0 ]; do
    case "$1" in
        --case) case_globs+=("${2:-*}"); args+=("$1" "$2"); shift 2 ;;
        --case=*) case_globs+=("${1#--case=}"); args+=("$1"); shift ;;
        # CONSUMED HERE, NOT PASSED ON: `claude plugin eval` has no such flag,
        # and passing it through would fail the run with an unknown-option error
        # that says nothing about toolchains.
        --toolchain-ref) toolchain_ref="${2:-}"; shift 2 ;;
        --toolchain-ref=*) toolchain_ref="${1#--toolchain-ref=}"; shift ;;
        *) args+=("$1"); shift ;;
    esac
done

[ ${#case_globs[@]} -eq 0 ] && case_globs=('*')
# `case_glob` is kept for the messages below, which speak about a single
# selection. `all_cases` is the honest test for "the whole suite": exactly one
# glob, and it is `*`. Three explicit --case flags are not a full-suite run.
case_glob="${case_globs[0]}"
if [ ${#case_globs[@]} -eq 1 ] && [ "${case_globs[0]}" = '*' ]; then
    all_cases=1
else
    all_cases=0
fi
[ ${#case_globs[@]} -gt 1 ] && case_glob="${case_globs[*]}"

grant=$(python3 "$here/lib/grant.py" "$here" "${case_globs[@]}") || grant=""

# SI-21: a `type: regex` grader is compiled by the harness's JavaScript engine.
# Three of mine used Python inline flags `(?is)`, every grader in the case threw
# at scoring time, and the case came back 0.00 -- a red row with a score, not an
# error, and billed. This says so BEFORE the money is spent. It never refuses
# (GOAL-no-new-gates) and `|| true` keeps its own failure off the run.
python3 "$here/lib/check_graders.py" "$here" || true

if [ -n "$grant" ]; then
    echo "eval: granting $grant (derived from the cases' allowed_tools)"
    # shellcheck disable=SC2206
    grant_args=(--allow-tools $grant)
else
    grant_args=()
fi

# A Bash-granted run needs a scratch HOME on a machine with Docker Desktop: the
# sandbox refuses while `~/.docker` holds a symlink, and `~/.docker` here holds
# 18 of Docker's own CLI shims. Overriding HOME fixes the sandbox and breaks
# authentication, because the login credential is in the keychain and the
# keychain path is HOME-relative -- so the home has to symlink
# `Library/Keychains`. evals/README.md builds one in six lines. It is not built
# here: it copies a credential file and links a keychain, which is the
# operator's call to make, once, rather than something a run script does behind
# them.
if [[ " $grant " == *" Bash "* ]] && [ -z "${EVAL_HOME:-}" ]; then
    echo "eval: NOTE -- a Bash-granted case may need EVAL_HOME (see evals/README.md, 'The home')."
fi

# --------------------------------------------------------- the toolchain pin
# WHICH skt, AND SAID OUT LOUD. See header item 6. The rule this implements:
# a full-suite run ASKS and never guesses silently; a single-case run may
# default, but it must say what it defaulted to. A silent default is the defect;
# a loud one is a convenience.
pinned=$(python3 "$here/lib/toolchain.py" print-ref --unit skt 2>/dev/null || echo "")
ref_args=()
if [ -n "$toolchain_ref" ]; then
    ref_args=(--ref "$toolchain_ref")
    echo "eval: toolchain -- using the ref you named: $toolchain_ref (recorded as an OVERRIDE)"
elif [ -n "${SI14_TOOLCHAIN_REF:-}" ]; then
    ref_args=(--ref "$SI14_TOOLCHAIN_REF")
    echo "eval: toolchain -- using SI14_TOOLCHAIN_REF=$SI14_TOOLCHAIN_REF (recorded as an OVERRIDE)"
elif [ "$all_cases" = 1 ] && [ -t 0 ]; then
    # THE ASK. Only for a full suite, and only where there is somebody to answer.
    echo "eval: ------------------------------------------------------------"
    echo "eval: this is a FULL-SUITE run. Which skt is it graded against?"
    echo "eval:   pinned:  ${pinned:-UNREADABLE} "
    echo "eval:            (evals/lib/toolchain.lock.toml, under change control)"
    echo "eval:   the operator's home would instead have used whatever its"
    echo "eval:   install record says today -- that is what the pin replaces."
    printf 'eval: press Enter to use the pin, or type a commit/branch: '
    read -r answer || answer=''
    if [ -n "$answer" ]; then
        ref_args=(--ref "$answer")
        echo "eval: toolchain -- you answered $answer (recorded as an OVERRIDE)"
    else
        echo "eval: toolchain -- using the pin ${pinned:-?}"
    fi
    echo "eval: ------------------------------------------------------------"
elif [ "$all_cases" = 1 ]; then
    # NO TERMINAL. Refusing here would block CI on a question nobody can answer,
    # which is a gate. Taking the PIN is not a guess -- it is the declared value,
    # read from a file under change control -- so it is taken, and announced.
    echo "eval: toolchain -- FULL SUITE with no terminal to ask at."
    echo "eval:   using the PINNED ${pinned:-?} from evals/lib/toolchain.lock.toml."
    echo "eval:   Nothing was guessed. To choose: --toolchain-ref <commit> or SI14_TOOLCHAIN_REF."
else
    echo "eval: toolchain -- ${#case_globs[@]} case selector(s) ('$case_glob'); DEFAULTING to the pinned ${pinned:-?}"
    echo "eval:   (override with --toolchain-ref <commit>)"
fi

record_dir="$repo/evals/results/toolchain"
mkdir -p "$record_dir" "$view/toolchain"
record="$record_dir/$(date -u +%Y%m%dT%H%M%SZ).json"
echo "eval: materialising the toolchain (this fetches pinned commits)"
# `${arr[@]+"${arr[@]}"}` AND NOT `"${arr[@]}"`: macOS ships bash 3.2.57, where
# an EMPTY array expanded under `set -u` is an "unbound variable" error. Measured
# here -- the first version of this line died with
# `run.sh: line 217: ref_args[@]: unbound variable` on the ordinary path where
# the operator took the pin and named no override, i.e. on almost every run.
if python3 "$here/lib/toolchain.py" materialise \
        ${ref_args[@]+"${ref_args[@]}"} --check-drift --stage-into "$view" --record "$record"; then
    cp "$record" "$view/toolchain/RECORD.json"
    echo "eval: the run record is $record (and staged for the hook to print)"

    # ---------------------------------------------------- the unit under test
    # THE MOVED CASES' UNIT, DELIVERED WITHOUT `plugins:`. (SI-15.)
    #
    # 54 cases moved here from skill-manager, and 18 of them ask about `skt` or
    # the `skill-manager` CLI -- units this plugin does not nest. On the other
    # side each case reached its unit through a `plugins:` entry. That route is
    # closed here, and the reason is measured rather than stylistic: a case
    # declaring `plugins:` SILENTLY LOSES the target plugin's hooks, and both
    # arms still score 1.00 (SI-14-DF-01, four runs, hook fired 2/2 without and
    # 0/2 with). Every fixture in this suite is placed by a SessionStart hook,
    # so such a case would be handed an empty workspace and scored 0 as a skill
    # failure.
    #
    # The view IS the plugin, so its `skills/` is what loads. Staging the
    # pinned skt's skills into it delivers the unit through the plugin itself
    # -- no `plugins:` entry -- and AT THE PINNED COMMIT rather than whatever
    # the operator's home holds today, which is what SI-14 bought.
    #
    # STAGED, NEVER COMMITTED, exactly like hooks.json above: the shipped
    # plugin gains no skills it does not own. And it is cheap -- the pinned skt
    # is 183 entries and ships NO case.yaml of its own, so it cannot contribute
    # cases to this suite's discovery the way the 11,481-entry skill-manager
    # checkout would (which is why that one is reached by a PATH shim instead).
    # THE STAGING IS GONE, AND SO IS THE PIN IT STAGED.
    #
    # This block copied the pinned skt's skills into the view, refusing to put
    # one OVER a skill the plugin owns. SI-16 nested skt here, so the pinned
    # unit's three skills -- skill-manager, skt, unit-authoring -- ALL collide
    # now. Every candidate was skipped, `staged_units` stayed empty, and the
    # success line never printed: a silent no-op that read as provisioning.
    #
    # The view IS the plugin and its skills/ is what loads, so the w-skt and
    # w-sm cases reach their units from the branch under test. That is the
    # outcome the skip rule wanted all along -- grade the branch, not the pin.
    #
    # What replaces it is the CHECK, not the copy. A case about a unit the view
    # does not carry scores as a skill failure and reads as a model problem, so
    # the absence is named here, loudly, before anything runs.
    missing_units=""
    for unit_name in skt skill-manager unit-authoring; do
        [ -d "$view/skills/$unit_name" ] || missing_units="$missing_units $unit_name"
    done
    if [ -n "$missing_units" ]; then
        echo "eval: WARNING -- the view carries no:$missing_units"
        echo "eval:            the w-skt and w-sm cases are ABOUT those units and will"
        echo "eval:            run without them, scoring as skill failures."
        echo "eval:            Do not quote their scores. This plugin is supposed to"
        echo "eval:            nest them (SI-16); check skills/ in the view."
    else
        echo "eval: the view carries skt, skill-manager and unit-authoring from this branch"
    fi

else
    # WARN, NEVER REFUSE -- but be explicit about what the run now cannot say.
    echo "eval: WARNING -- the toolchain could not be materialised."
    echo "eval:            The run below will proceed, and it will NOT be able to"
    echo "eval:            name the toolchain it used. Do not quote its score"
    echo "eval:            against a toolchain version."
fi

# The entry count above was taken BEFORE the toolchain was staged, so re-check:
# a view that crosses 20,000 is refused by the CLI with a message about plugin
# directory size, which reads as a repository problem rather than as this.
# STAGE THE uv CACHE INTO THE VIEW, so the hook needs no environment at all.
# Four attempts failed because the cache kept being addressed through something
# the SessionStart hook cannot see: run.sh's exported UV_CACHE_DIR (the agent's
# sandbox does not inherit it), $HOME in a hook (that is the operator's), and
# SI10_CHECKOUT (not visible either -- the guard fell through printing neither
# success nor its own warning, which is how two runs looked identical).
#
# The view is the one thing place.sh can always resolve, from its own location.
# 126 entries against a 20,000 ceiling and ~8,700 already used, so it costs
# nothing to carry.

entries_after=$(find "$view" | wc -l | tr -d ' ')
echo "eval: the view holds $entries_after entries after staging the toolchain"
if [ "$entries_after" -ge 20000 ]; then
    echo "eval: WARNING -- staging the toolchain pushed the view over the 20000-entry limit."
fi

export SI10_CHECKOUT="$repo"
export PATH="$repo/evals/bin:$PATH"
export CLAUDE_CODE_WALNUT_SPIRE=1

# --------------------------------------------- the skill scripts' dependencies
#
# EA-DF-15, resolved. Every script under `skills/` with a `# /// script` header
# runs via `uv run --script`, which resolves dependencies at INVOCATION time.
# A sandboxed run has no network, so uv reaches for pypi.org, is denied, and the
# script never starts -- the run scores anyway, and a plausible number comes out.
#
# THE ANSWER IS WHEELS, NOT A CACHE, and that cost five wrong attempts to learn:
# a uv cache is not relocatable (its environments are keyed to the path they were
# built at), and four different ways of naming a cache to the agent all failed
# because the agent's sandbox inherits neither the runner's environment nor its
# HOME. What works is a FILE in the agent's own home, written by place.sh, and
# wheels it can point at.
#
# `setup-eval-home.sh` downloads them. This stages them where place.sh can find
# them -- the view, which is the one path a hook can always resolve.
if [ -d "$repo/.toolchain/uv-wheels" ]; then
    rm -rf "$view/.uv-wheels"
    cp -R "$repo/.toolchain/uv-wheels" "$view/.uv-wheels" 2>/dev/null \
        && echo "eval: staged $(ls "$view/.uv-wheels" | wc -l | tr -d ' ') wheel(s) into the view for offline uv"
else
    echo 'eval: WARNING -- no offline uv wheels; any `uv run --script` skill script' >&2
    echo 'eval:   will fail in the sandbox. Build them: evals/setup-eval-home.sh' >&2
fi

# ------------------------------------------- the orientation hook's interpreter
#
# EA-DF-14. skt's SessionStart hook is what tells a session `next  skt check`,
# and it resolves skt through a python of at least 3.11. macOS ships 3.9.6 at
# /usr/bin/python3, which the gate REJECTS, and the hook then exits 0 with no
# output -- deliberately, because "a broken orientation hook must not break the
# session it orients". The cost is that a session on a stock macOS PATH gets NO
# orientation and no sign that any was attempted.
#
# Measured here: both SessionStart hooks fired, place.sh returned 1098 bytes and
# skt's returned ZERO, and the agent then spent nine Bash calls rediscovering
# what the hook would have handed it in one line.
#
# `pick_python` honours SKT_PYTHON before it scans PATH, so this names an
# interpreter rather than reordering PATH for the whole run.
if [ -z "${SKT_PYTHON:-}" ]; then
    for _c in python3.14 python3.13 python3.12 python3.11; do
        _p=$(command -v "$_c" 2>/dev/null) || continue
        SKT_PYTHON="$_p"; break
    done
fi
if [ -n "${SKT_PYTHON:-}" ]; then
    export SKT_PYTHON
    echo "eval: SKT_PYTHON=$SKT_PYTHON (the orientation hook needs >= 3.11; the system python3 is 3.9)"
else
    echo 'eval: WARNING -- no python >= 3.11 found, so skt SessionStart will inject nothing' >&2
    echo 'eval:   and every case grades an agent with no orientation. Not refusing.' >&2
fi
# THE SCRATCH HOME, FOUND RATHER THAN DEMANDED. `evals/setup-eval-home.sh`
# builds one at .toolchain/evalhome and everything about why it is needed is
# documented there. Using it when it exists means a future run needs no
# incantation and nobody rediscovers the Docker refusal at the cost of a
# confusing 0.00 -- which has now happened twice.
#
# IT LIVES OUTSIDE THE CHECKOUT. It holds symlinks into the operator's home, so
# inside the repository anything that copies the checkout and dereferences links
# copies the operator's home too -- measured on 2026-09-25 as a 57 GB fixture
# directory that filled a 926 GB disk and errored both skt graphs. See
# setup-eval-home.sh.
: "${EVAL_HOME:=${XDG_STATE_HOME:-$HOME/.local/state}/tla-spec-dev/evalhome}"
if [ -d "$EVAL_HOME" ]; then
    export HOME="$EVAL_HOME"
    echo "eval: HOME -> $EVAL_HOME (scratch home; see evals/setup-eval-home.sh)"
else
    echo 'eval: NOTE -- no scratch eval home. On a machine with Docker Desktop the' >&2
    echo 'eval:   Bash sandbox refuses every Bash-granting case (60 of 64) with a' >&2
    echo 'eval:   credential-store message that reads like a broken substrate.' >&2
    echo 'eval:   Build one once:  evals/setup-eval-home.sh' >&2
fi

# --------------------------------------------- the CLI's interpreter and cache
#
# WHY A skill-manager CASE COULD NOT REACH skill-manager. The CLI is
# `jbang SkillManager.java`, and SkillManager.java declares `//JAVA 21+`. jbang
# looks for a JDK under the CURRENT HOME, and a sandboxed run's HOME is a fresh
# ephemeral directory, so it found none, decided it had to fetch one, and asked
# api.foojay.io for JDK 17. The sandbox has no network. The agent reported it
# exactly: "it doesn't start here. It tries to download JDK 17, and the sandbox
# blocks that request."
#
# Every skill-manager case in this lane was therefore grading an agent that
# could not run skill-manager. That is an instrument failing in the direction
# this project says it may not: the run still scores.
#
# THE FIX IS NOT TO OPEN THE NETWORK. This machine already carries twelve JDKs;
# nothing needed downloading, only finding. Pointing jbang at one removes the
# request instead of permitting it, which is both the smaller change and the
# stronger isolation -- the sandbox keeps no network at all.
#
# JBANG_DIR is the other half, and it is what keeps this isolated. Left unset,
# jbang reads and WRITES the operator's ~/.jbang: an eval run would mutate a
# directory outside the repository, and its contents would differ between
# machines and between runs. Pinned here to `.toolchain/jbang`, beside the
# pinned checkout it serves, gitignored, and reproducible by deleting it.
#
# The cache is primed HERE, operator-side, before the sandbox starts -- the
# dependency fetch is a real download and it happens once, outside the run,
# under the operator's own network. A sandboxed run then needs nothing.
#
# NOTHING HERE REFUSES. No JDK, or a priming failure, warns on one line and
# carries on: the non-skill-manager cases do not need any of it, and an eval
# that blocks is a gate wearing a lab coat.
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME:-}/bin/java" ]; then
    if [ -x /usr/libexec/java_home ]; then
        JAVA_HOME=$(/usr/libexec/java_home -v 21 2>/dev/null || /usr/libexec/java_home 2>/dev/null || true)
    fi
fi
if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/java" ]; then
    export JAVA_HOME
    export JBANG_DIR="${JBANG_DIR:-$repo/.toolchain/jbang}"
    mkdir -p "$JBANG_DIR"
    echo "eval: java -- $("$JAVA_HOME/bin/java" -version 2>&1 | head -1)"
    echo "eval:   JAVA_HOME=$JAVA_HOME"
    echo "eval:   JBANG_DIR=$JBANG_DIR (isolated; the operator's ~/.jbang is untouched)"
    # Prime it. `--version` is the cheapest call that resolves every dependency
    # and builds the jar, and it prints the CLI's own account of which commit it
    # is, which is the line a run record wants anyway.
    if sm_version=$("$repo/evals/bin/skill-manager" --version 2>/dev/null | head -1); then
        echo "eval:   the CLI starts: $sm_version"
    else
        echo "eval:   WARNING -- skill-manager did not start even with a JDK; skill-manager" >&2
        echo "eval:   cases will grade an agent that cannot run it. Not refusing." >&2
    fi
else
    echo 'eval: WARNING -- no JDK 21+ found, so skill-manager cannot start and any' >&2
    echo "eval:   skill-manager case grades an agent that cannot run it. Not refusing." >&2
fi

echo "eval: running"
set +e
# `${arr[@]+"${arr[@]}"}` FOR BOTH ARRAYS. macOS ships bash 3.2.57, where an
# EMPTY array expanded under `set -u` is an "unbound variable" error. This was a
# latent defect here before SI-14 and it fired the moment a run selected no
# cases -- `--case` with a typo in it, say:
#
#   evals/run.sh: line 250: grant_args[@]: unbound variable
#
# which reads as a broken runner rather than as "that glob matched nothing".
claude plugin eval "$view" \
    --ablation none \
    --runs 1 \
    --trust-plugin \
    ${grant_args[@]+"${grant_args[@]}"} \
    ${args[@]+"${args[@]}"}
status=$?
set -e

# ----------------------------------------------------------- undecided
# SAY WHICH SCORES ABOVE ARE NOT VERDICTS, WHILE THE TABLE IS STILL ON SCREEN.
# Six cases cannot be decided in this view -- their fixture is a real branched
# Skill Manager home, ~41,000 entries against the CLI's 20,000 ceiling.
# `place.sh` already says so in the run's trace and `verify.sh` already writes
# `.eval/UNDECIDED-needs-home` beside the verdicts, but the trace scrolls past
# and the sandbox holding that file is deleted unless `--keep-temp` was passed.
# What is left on screen is `â ... score 0.27` and a grader message.
#
# EA-DF-08, measured on this epic's first billed rung: the epic agent read two
# such scores as substrate failures and wrote them up as "the agent never
# issued the front door", calling them the highest-value cases in the corpus.
# Every safeguard the design put in place had fired correctly, and not one of
# them was where the number was. This prints after the table, which is the one
# place that gets read.
#
# It never refuses, and its own failure is never the run's (`|| true`): a case
# being undecidable is a fact about the view, not a fault in the work, and
# GOAL-no-new-gates means no line in this script may block on one.
python3 "$here/lib/undecided.py" "$here" "${case_globs[@]}" || true

# -------------------------------------------------------------- harvest
if [ -d "$view/evals/results" ]; then
    mkdir -p "$repo/evals/results"
    cp -R "$view/evals/results/." "$repo/evals/results/" 2>/dev/null || true
    echo "eval: results harvested into $repo/evals/results"
fi
exit "$status"
