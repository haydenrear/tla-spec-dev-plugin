# The eval suite

**61 cases, one place, one command**, run against **this checkout**.

```bash
evals/setup-eval-home.sh --smoke              # ONCE per machine, first
evals/run.sh                                  # all of them
evals/run.sh --case use-the-front-door        # one
evals/run.sh --case 'w-sdc-*'                 # a glob
evals/run.sh --case 'w-sm-*' --runs 6         # six samples, for an unstable case
```

## Run this first, once per machine

```bash
evals/setup-eval-home.sh            # build it (idempotent)
evals/setup-eval-home.sh --check    # check it, change nothing
evals/setup-eval-home.sh --smoke    # check it, then bill ONE case and prove the lane
```

It builds a scratch HOME at `.toolchain/evalhome` and `run.sh` picks that path
up on its own, so after the first run there is no incantation to remember. The
script carries the reasoning for every piece; the short version is below because
**two of these were rediscovered the expensive way, one of them twice in a
single day.**

| prerequisite | what happens without it |
| --- | --- |
| scratch `HOME` with a symlink-free `.docker` | **60 of 64 cases score 0.00.** The Bash sandbox refuses while the Docker credential store holds a symlink, and stock Docker Desktop puts 18 of its own CLI shims in `~/.docker`. None is a credential. |
| `Library/Keychains` linked into it | every run fails to authenticate — the login credential is in the keychain and the keychain path is HOME-relative |
| a JDK 21+ | `skill-manager` never starts, so its cases grade an agent that cannot run it — **silently, at 1.00 in five of six cases** |
| a python 3.11+ | skt's SessionStart hook injects nothing, and the session loses the line naming the next command |
| offline uv wheels | **no `uv run --script` skill script starts** — 81 files carry that header. The three cases requiring a validator then spend two of their 3–4 Bash calls on a tool that cannot run, so `within-budget` fails as a *consequence*. Fixing it moved them 0.75→1.00, 0.88→1.00, 0.43→0.86 |

### `HOME`, not `SKILL_MANAGER_HOME`, and not `DOCKER_CONFIG`

The obvious two levers do not work, and both were tried:

* **`DOCKER_CONFIG` pointed elsewhere does nothing.** The check reads `~/.docker`
  regardless and the refusal message is byte-identical. Measured.
* **`SKILL_MANAGER_HOME` is a different question.** It selects which skill-manager
  home a run uses; it has no bearing on the sandbox's credential-store scan. Set
  it when a case needs a particular home, not to fix this.

`HOME` is the only lever that moves the Docker check, which is why the scratch
home exists at all — and overriding `HOME` is also what breaks authentication,
which is why it must link the keychain. The two constraints are only satisfiable
together.

### If you are extending the harness: how things reach the agent

Learned across six failed attempts, and worth more than any single fix.

**The agent runs in a sandbox that shares almost nothing with the runner.**
Four ways of handing it something all failed silently — each looked correct,
printed nothing wrong, and changed no behaviour:

| what was tried | why it fails |
| --- | --- |
| `export VAR` from `run.sh` | hooks inherit the runner's environment; **the agent's Bash sandbox does not** |
| `$HOME/...` inside a hook | `$HOME` in a hook is the **operator's**, not the agent's |
| symlink over `<agent-home>/.cache/...` | the harness **pre-creates** parts of the agent's home; a link cannot be planted over a real directory |
| `$SI10_CHECKOUT/...` inside a hook | **not visible to hooks** — diagnosed from the guard printing neither its success line nor its warning |

**Two things do work, and nothing else has been shown to:**

1. **The view.** `run.sh` stages it and `place.sh` can always resolve it as
   `$plugin/...`, because that is the hook's own location.
2. **A file in the agent's home.** `place.sh` derives it as the parent of its
   own working directory (`<sandbox>/home/cwd` → `<sandbox>/home`) and writes
   there. This is how `uv.toml` reaches the agent.

**A corollary with teeth:** a sandboxed run inherits an empty `HOME`, so *every*
toolchain that caches under `HOME` is cold and reaches for a network that is not
there. jbang wanted a JDK, skt's hook wanted a python, uv wanted PyPI — three
separate "the tool could not start and the run scored anyway" defects in one
day. Anything else that caches under `HOME` will do the same, silently.

And note what does **not** work as a remedy: a **uv cache is not relocatable**.
Copying one into the agent's home succeeds mechanically (92K → 1.9M) and still
fails to resolve, because the environments it holds are keyed to the path they
were built at. Ship the **wheel**.

### Reading a score without fooling yourself

* **Every case is `runs: 1`.** One case was measured moving **±0.8 between
  identical invocations on an unchanged commit**. A single score is a sample,
  not a measurement. Use `--runs 6` before claiming any change.
* **Do not re-run only the failures and add them to the old passes.** Measured:
  3 of 11 returned 1.00 with nothing fixed for them, and one fell 0.86→0.43.
  Selecting on failure shows you one direction and regression to the mean
  supplies the rest. A corpus number comes from one full run at one commit.
* **Six cases are UNDECIDED, not red.** `run.sh` names them under the table.
  Their scores are not verdicts and must not be averaged with the rest.
* **A low score is more often the instrument than the substrate.** Of the low
  scores investigated to the end in this lane, every one was an instrument
  defect. Read the transcript before filing anything against the work.

### Proving the setup rather than assuming it

`--check` inspects the *shape* of the setup. `--smoke` bills one case
(`w-harness-smoke`, 3 turns, about $0.11) and **asserts a 1.00** — because a run
that fails to place its fixture, or whose tool grant is wrong, still exits 0
with a score of 0.00. "The script ran" proves nothing.

`w-harness-smoke` is built for exactly this and says so itself: *a red here means
no other `w-*` score means anything.* Run `--smoke` after any change to
`run.sh`, `lib/place.sh`, `lib/verify.sh` or the hooks.

## One place (SI-15)

The development loop's evals used to be split across two repositories and two
harnesses that shared no runner: 7 cases here, and 54 in `skill-manager` under
`specs/evals/harness/`, run by `eval_run_case()` in a 43,330-byte `lib.sh`
against a branched Skill Manager home built per case. Nothing ran them
together, so nothing could say whether a change to the substrate moved the
whole picture or only the half somebody happened to run.

`claude plugin eval` runs on a **plugin**. This repository is one;
`skill-manager` has no `.claude-plugin/` and is not. That asymmetry decided the
direction: **the cases moved here.**

| where | cases |
|---|---|
| `spec-double-2` | 12 |
| `git-issue-workflow` | 9 |
| `git-epic-workflow` | 7 |
| `skt` | 16 |
| `skill-manager` | 9 |
| `git-issue` | 3 |
| `plugin-repository` | 2 |
| `test-graph` | 2 |
| `discovery` | 1 |
| `harness`, `unnested` | 3 |

**No moved case declares `plugins:`, and that is not a style rule.** Measured
over four runs (SI-14-DF-01): a case declaring `plugins:` **silently loses the
target plugin's hooks**, and *both arms score 1.00* — the score is completely
blind to it. Every fixture here is placed by a `SessionStart` hook, so such a
case would be handed an empty workspace and scored 0 as a skill failure. The
unit a moved case is *about* is delivered instead by the view itself:
`run.sh` stages the **pinned** `skt`'s skills into it, so those cases load
their subject at the commit `lib/toolchain.lock.toml` names rather than
whatever the operator's home holds today.

### The six that need a home

Six moved cases — `bootstraps-a-home-for-a-repo`,
`reconciles-a-worktree-into-the-project-home`, `syncs-a-stale-home-from-root`,
`ticket-agent-opens-a-ticket`, `ticket-agent-closes-a-ticket` and
`epic-provisions-a-ticket-worktree` — have a **real branched Skill Manager
home** as their fixture. A home is ~41,000 entries and `claude plugin eval`
refuses a plugin directory over 20,000, so it cannot be staged into the view.

They move, and they are declared **UNDECIDED**: `lib/place.sh` says so in the
run's own trace and `lib/verify.sh` writes `.eval/UNDECIDED-needs-home`. They
are **not** handed an empty workspace and scored 0 — that would read as "the
agent could not provision a home", an instrument failing in the one direction
this project says it may not.

`sandbox-probe` did **not** move. It is a diagnostic of the *other* harness's
sandbox rather than a skill test, and its `the-workspace-is-writable` grader is
a deliberate standing red reading `path: probe-write` — a path the agent
writes, which `test_no_grader_reads_a_path_the_agent_can_simply_write` forbids
here. Filed as `SI-15-DF-02`.

## The seven this plugin started with

| skill | case | the question |
|---|---|---|
| `spec-double-2` | `scaffold-a-program-model` | given a program with no spec, does the model represent the one property that is only true over a trace? |
| `spec-double-2` | `catch-the-drift` | given a program and the model it already has, can you find where they stopped agreeing — and repair the program rather than the model? |
| `discovery` | `start-from-the-spec-not-the-source` | does the account of the program come from the map the repository carries, or from a re-derivation of it? |
| `git-issue` | `a-work-order-not-a-wish` | does the issue carry what an implementer needs, or restate the complaint? |
| `git-issue-workflow` | `use-the-front-door` | is the first move `wt new`, or a bare `git worktree add` that leaves the agent writing the operator's global home? |
| `git-epic-workflow` | `epic-mode-is-not-main` | does the assignment marker change the branch point, the PR base, and the stopping point? |
| `test-graph` | `compose-a-behavioural-graph` | does a registered graph with a node in it come out, or another unit test in a new directory? |

SI-19 added one more, and it is the first case in this suite written AFTER
the behaviour it grades was watched by hand rather than alongside it:

| skill | case | the question |
|---|---|---|
| `test-graph` | `w-tg-run-a-graph-not-bare-gradle` | asked to run a registered graph in a fresh checkout, is the command the skill's runner — or `cd test_graph && ./gradlew`, which fails at configuration time because the managed provider bindings are generated links no checkout carries? |

Its provenance is a committed transcript, not a memory: the control and the
treatment were both run in the SI-19 worktree at `f4b42169` on 2026-09-23,
and `specs/results/epic-self-improvement-substrate/tickets/SI-19/manual-verification.md`
is committed in an EARLIER commit than the case. That ordering is the whole
of `GOAL-evals-earned`, and it is checkable with `git log`.

SI-20 added two, the second rung of the same ladder, and both are about
telling *which code ran* from *what the command printed*:

| skill | case | the question |
|---|---|---|
| `skt` | `w-skt-worktree-leaves-the-integration-repo` | `skt ticket new` exits 0 and the worktree is not where the caller expected. Is that a defect in skt, or the `integration.toml` ancestor deciding the location — and what would have gone wrong at the expected path? |
| `skt` | `w-skt-which-copy-of-skt-ran` | an edit to `skills/skt/` has no effect through `<checkout>/.skill-manager/bin/cli/skt`. Does the agent find that the wrapper resolves from the home it lives in, or reach for caches and `PATH`? |

Same provenance rule, same check: the by-hand record
`specs/results/epic-self-improvement-substrate/tickets/SI-20/manual-verification.md`
is committed in an EARLIER commit than either case, and it names every `skt`
verb it drove. **Neither case is a report of the reds that motivated it.**
`sktSurface`'s `skt.ticket-roundtrip` node was red on 13 of 40 assertions when
this stage started; four of those are the first case's subject, nine are
obsolete assertions recorded as findings, and none of the nine became a case.

Full method — what a grader can see, what a case can observe, how to keep a
score attached to something that happened — is
`skills/spec-double-2/references/plugin_evals.md`. This page is how to run
*these*.

## Which toolchain the score belongs to

Every run resolves a toolchain, and until SI-14 **no run recorded which one**.
`skt` came from the operator's live home at whatever `main` pointed to that day:
the project home's record said `gitRef main, gitHash 286a3694, installed
2026-09-14`, and by 2026-09-19 `main` was `0f380781`. Five days, two different
toolchains, one name — so no two runs a week apart were known to be comparable,
and a score that moved could not be attributed to the change meant to move it.

**The pin is `evals/lib/toolchain.lock.toml`**, under change control, naming a
**commit** for each unit. It cannot be declared to the CLI — `claude plugin
eval` has no version pinning for plugin dependencies, and `plugins:` takes
relative filesystem paths only — so `evals/lib/toolchain.py` **materialises**
it: fetches each pinned commit, verifies the checkout *is* that commit, stages
it beside the view, and writes a run record that the `SessionStart` hook prints
into the run's own trace.

```bash
evals/run.sh                                   # asks which skt, at a terminal
evals/run.sh --toolchain-ref <commit>          # answer it up front
SI14_TOOLCHAIN_REF=<commit> evals/run.sh       # same, from the environment
python3 evals/lib/toolchain.py print-ref       # what is pinned, no network
python3 evals/lib/toolchain.py materialise --check-drift   # and has it moved?
```

* **A full-suite run ASKS**, because a silent default is the defect this closes.
  Pressing Enter takes the pin; asking is not refusing.
* **With no terminal** (CI) it takes the pin and *says so*. Refusing there would
  block a run on a question nobody can answer, which is a gate.
* **A single-case run defaults** to the pin and **says what it defaulted to**.
* Anything you answer other than the pin is recorded as an `OVERRIDE`.

Each run writes `evals/results/toolchain/<timestamp>.json` — origin, pinned
commit, the verified `HEAD`, whether the branch has drifted since, and what the
operator's ambient home *would* have used instead.

### The CLI under test is the epic branch's, not the brew install

`evals/bin/skill-manager` is a shim, the sibling of `evals/bin/tla-spec-dev` and
for the same measured reason. It execs `./skill-manager` — the 346-byte wrapper
in the materialised checkout — so reaching the epic branch's CLI is a PATH entry,
**not a rebuild and not an install**, and nothing is written over
`/opt/homebrew/Cellar/skill-manager`. Like its sibling it exits 127 rather than
falling through to the installed copy. The wrapper names its own commit, so the
record quotes the CLI's own account of what ran:

```
skill-manager 0.28.1+g6ffacb88ff96
build:  6ffacb88ff96 (detached)
```

The materialised checkouts live in `.toolchain/` at the repository root
(gitignored) — **not** under `evals/`, because case discovery is a recursive
glob over the eval dir and the skill-manager checkout ships 56 `case.yaml` files
of its own, which would otherwise be discovered, scored and billed as ours.

### What is not yet wired, and why

The pinned unit is materialised, verified, staged and recorded — but **no case
loads it through `plugins:`**, and that is deliberate. Measured over 4 runs on
2.1.276: a case declaring `plugins:` **silently loses the target plugin's
hooks**, scoring 1.00 either way.

```
si14-target-noplug     hook fired 2 of 2 runs    score 1.00
si14-target-withplug   hook fired 0 of 2 runs    score 1.00
```

Every fixture in this suite is placed by `lib/place.sh`, a `SessionStart` hook.
A `plugins:` entry added to any case here would hand the agent an **empty
workspace** and score it 0 — reported as a skill failure. `tests/test_eval_toolchain_pin.py`
holds that line until the defect is resolved upstream.

## Why there is a script and not a command to copy

The command underneath is this, and every part of it is load-bearing:

```bash
PATH="$PWD/evals/bin:$PATH" CLAUDE_CODE_WALNUT_SPIRE=1 \
  claude plugin eval <a staged view of this checkout> \
      --ablation none --runs 1 --allow-tools Bash Write Edit
```

Four of those five parts were learned from a run that scored 0 for a reason
that was not the agent's, and the fifth is a directory that has to be built.

* **the staged view** — `claude plugin eval` refuses a plugin directory over
  20,000 entries, and this repository **is** the plugin. See below.
* **`CLAUDE_CODE_WALNUT_SPIRE=1`** — the subcommand is gated behind it and does
  not exist without it.
* **`PATH="…/evals/bin:$PATH"`** — without it the run grades whichever
  `tla-spec-dev` the operator has installed, not this checkout. Measured: a
  run's `which -a tla-spec-dev` returned the installed wrapper three times and
  nothing else. A plugin `bin/` directory does not reach the eval's PATH, and
  `execution.env` refuses `PATH` — *"only EVAL_\* keys can be set from
  case.yaml. Anything else must come from the operator's shell."* The operator's
  shell is the only channel, which is what `run.sh` is.
* **`--allow-tools`** — a tool named in a case's `allowed_tools:` is still
  refused unless the operator ALSO grants it. `--allow-tools Bash` against a
  case declaring `[Bash, Write, Edit]` produced `not granted (missing
  --allow-tools grant, or a malformed entry): Write, Edit` and a score of 0 — an
  agent that could read the program and could not write one line of the spec,
  reported as a failure to model. `run.sh` **derives the grant from the cases it
  is about to run**, so a new case cannot fall out of step with a README.
* **`--ablation none`** — the second arm loads no plugin, so the fixture hook
  does not fire and the baseline gets an empty repository. Its 0 would read as
  "the skill is what scored" when it means "the fixture was never placed".

`run.sh` does those, stages the hooks, and harvests the report back out of the
view into `evals/results/`.

## The 20,000-entry limit, and what was done about it

```
a plugin directory holds more than 20000 entries to check for eval directories
  — point the case at a smaller plugin directory
```

Measured on Claude Code 2.1.275 at `994f650c`: this checkout is **70,741
entries** and the refusal fires — with or without an explicit `plugins:` entry
in the case. It is not marginal. `specs/.history`, the append-only record, is
19,154 of it; the gitignored per-checkout `.skill-manager` home is another
41,169.

**There is no exclusion mechanism to reach for.** No `.gitignore`, no
`.claudeignore`, no manifest key, no flag, no environment variable. The
traversal skips version-control metadata (`.git`, `.svn`, `.hg`) and nothing
else. `--eval-dir` moves where *cases* are found, not what gets counted.

So the ticket's question — *a plugin directory that excludes the append-only
record, or a documented exclusion* — has only one honest answer here, and
`run.sh` implements it: **stage a plugin directory that excludes the record.**
A copy of the working tree without `specs/.history`, without `.skill-manager`,
without the agent homes, made fresh on every run. **6,264 entries**, and the CLI
accepts it.

Three things worth knowing about that choice:

* **It is a copy, and copies drift — this one cannot.** It is built at the top
  of every run from the working tree it is testing, and deleted the next time.
  Nothing commits it, and nothing has to remember to update it.
* **It replaced a committed symlink shim that had already gone stale.**
  `examples/agent_integration/eval-plugin/` carried the skill surface by name —
  `skills/spec-double-2` — and after the skills were nested there were six.
  A directory that has to be hand-edited whenever a skill is added shows one
  skill and reports nothing about the other five.
* **The record is what is excluded, and that is not a loss.** `specs/.history`
  is a record of what was true when it was written. No case reads it.

If you run `claude plugin eval .` directly you will get the refusal above. That
is the CLI telling you to use `run.sh`.

## The hooks are staged, not committed at the root

A plugin's hooks live at `<plugin>/hooks/hooks.json`. This plugin is the
repository, so a `hooks/hooks.json` committed at the root would run a
`SessionStart` shell script in **every session of every user who installs
tla-spec-dev** — and a fixture hook's blocking `exit 2` would be able to refuse
somebody's ordinary session.

So `evals/hooks/hooks.json` is copied into the staged view by `run.sh` and
loaded from there.

> **CORRECTED 2026-09-23 (`SI-16-DF-02`).** This paragraph used to end "the
> shipped plugin gains no hooks and no new way to refuse." That stopped being
> true at SI-16, which absorbed skt and lifted its two hooks to the repository
> root: `hooks/hooks.json` is a COMMITTED FILE now, and the `cp` above
> OVERWRITES it inside the view rather than creating one.
>
> **So the shipped hooks are out of this suite's scope, deliberately.** An eval
> run loads the fixture-placing hooks and only those. Merging skt's
> `SessionStart` in would add a `skt status` spawn to every case and change what
> every score measures, so the overwrite is kept and the limit is stated here
> instead: **no score in this suite is evidence about `hooks/skt-session-start.sh`
> or `hooks/skt-post-tool.sh`.** Those are covered by the `sktHooks` test graph,
> which asserts the hook contract directly.

Two hooks do the work that no grader can:

* **`SessionStart` → `lib/place.sh`** places the fixture and names the
  toolchain. It is a hook and not `scaffold_script:` because that key is
  accepted by the loader and **never executed** — measured at every placement,
  in both forms, including a body that exits 3, which changed nothing.
* **`Stop` and `SessionEnd` → `lib/verify.sh`** runs the real checks and writes
  the verdict paths the graders read. Both events, because a run that ends
  `error_max_turns` fires `SessionEnd` and not `Stop`: a sibling suite
  registered only on `Stop` and lost every verdict on 12 capped runs, scoring
  them red.

## Five cases need no shell, and that is deliberate

Only `scaffold-a-program-model`, `catch-the-drift` and
`compose-a-behavioural-graph` grant `Bash`. The other four ask for a document —
a plan, an issue, an account — and grade it with a program.

That is not a compromise on rigour; it is what makes the suite runnable. A
Bash-granted run on a machine with Docker Desktop refuses:

> the Docker (`~/.docker`, `DOCKER_CONFIG`) credential store on this machine
> holds a symbolic link inside it, so the Bash sandbox cannot reliably exclude it

`~/.docker` holds 18 of Docker's own CLI shims, none of them credentials, and
`DOCKER_CONFIG` pointed elsewhere does not help — the message is byte-identical,
so the check reads `~/.docker` regardless. Overriding `HOME` fixes the sandbox
and breaks authentication, because the login credential is in the keychain and
the keychain path is HOME-relative. Both hold at once only if the scratch home
symlinks `Library/Keychains`:

```bash
EVAL_HOME=/path/to/scratch/evalhome
mkdir -p "$EVAL_HOME/.docker" "$EVAL_HOME/Library"
cp ~/.docker/config.json "$EVAL_HOME/.docker/config.json"   # the file only
for p in .claude .claude.json .config .cache .local; do ln -s "$HOME/$p" "$EVAL_HOME/$p"; done
ln -s "$HOME/Library/Keychains" "$EVAL_HOME/Library/Keychains"
export EVAL_HOME
```

`run.sh` honours `EVAL_HOME` and says so when a Bash-granted case is selected
without one. It does not build the home itself: that copies a credential file
and links a keychain, which is the operator's call to make once, not something
a run script should do behind them.

## Reading a score

* **A red is not always the work's.** `file_exists` has no UNDECIDED state, so a
  verifier whose `java` or `tla2tools.jar` did not resolve leaves the same
  absent path as a genuine failure. `.eval/UNDECIDED-toolchain` is written in
  that case, `.eval/UNDECIDED-unconfined` when `sandbox-exec` was unavailable,
  and `.eval/verify.log` records what was missing. Check them before reading a 0
  as the agent's.
* **A run that ended `error_max_turns` has no closing report**, so every
  response grader votes FAIL on work that may be finished. Read the `error:`
  column beside the score.
* **A majority is not a consensus.** The `llm` grader takes three votes, and a
  run whose artefact was plainly correct has passed FAIL PASS PASS. One run of
  one case is not evidence of much.
* **Four cases grade a document.** `use-the-front-door`,
  `epic-mode-is-not-main`, `a-work-order-not-a-wish` and
  `start-from-the-spec-not-the-source` check what an agent *wrote*, mechanically
  and against the workspace's own contents, not what it would do. Each grader
  body says so in its own words. That bound is smaller than it sounds — the
  three moves `epic-mode-is-not-main` checks are the ones that cannot be taken
  back — but it is a bound, and a score from this suite should be quoted with
  it.

## Debugging a run

`--keep-temp` preserves each run's sandbox and prints its path. The workspace is
sealed at mode 000; open it with

```bash
chmod 700 <kept>/ <kept>/sealed && chmod -R u+rX <kept>/sealed
```

then read the workspace at `<kept>/sealed/home/cwd` and the event stream at
`<kept>/out/trace.jsonl`. The trace is where the hook's `exit_code`, the
per-turn tool calls and the turn-ceiling error are visible; the summary line
shows none of them.
