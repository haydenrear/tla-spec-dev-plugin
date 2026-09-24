# Eval ladder — stages 0 and 1, the first billed runs of this epic

Recorded 2026-09-24, against commit `10e16817`. `evals/results/` is gitignored
(a rerun reproduces it), so the verdicts live here.

**THESE ARE THE FIRST `claude plugin eval` RUNS ON THIS BRANCH.** SI-19 and
SI-20 each wrote cases and ran none, correctly for their scope. There is no
prior score to compare against: the numbers below are simultaneously the first
measurement and the baseline, and SI-23 inherits that limit.

Toolchain: `skill-manager 0.28.1+g7941f4e1dd9e`, the pin in
`evals/lib/toolchain.lock.toml`. Every run reported drift and held the pin —
`epic/self-improvement-substrate HAS MOVED to 6536defb8d02 since the pin`. The
scores therefore describe the PINNED toolchain, not the branch tip.

## Stage 0 — the harness, before anything else was billed

    w-harness-smoke   1.00   5/5 graders   $0.11   7s

Its own description: *"a red here means no other `w-*` score means anything."*
It earned that on the first attempt by failing for a reason that was not a
case's:

> the Docker (`~/.docker`, `DOCKER_CONFIG`) credential store on this machine
> holds a symbolic link inside it, so the Bash sandbox cannot reliably exclude
> it — a Bash-granting evaluation cannot run here

**60 of 64 cases grant Bash.** Firing any later stage first would have produced
60 zeros with an identical error string, which reads as a substrate that does
not work. Cost of finding that out: **$0.00, 2 seconds.**

`~/.docker` holds 18 of Docker Desktop's own CLI shims and no credentials.
`DOCKER_CONFIG` pointed elsewhere does not help — `evals/README.md` says the
message is byte-identical and it is; that was measured here before the README
was read, which is a second-hand way of confirming the README. The remedy is
the documented scratch `EVAL_HOME` that copies `~/.docker/config.json` (checked
first: `credsStore: desktop`, three `auths` entries, **zero inline auth blobs**)
and symlinks `Library/Keychains`, because overriding HOME fixes the sandbox and
breaks authentication. `~/.docker` was not modified. The owner authorised
building it; `run.sh` deliberately refuses to build it itself.

## Stage 1 — skt, 16 cases

### 1a — the fourteen `w-skt-*` cases: $2.44, 300s

    1.00  w-skt-check-pinned-is-not-stale
    0.83  w-skt-check-record-disagrees-with-checkout
    1.00  w-skt-check-unknown-is-not-current
    0.67  w-skt-is-a-plugin-not-a-skill
    1.00  w-skt-migration-delete-project-block
    1.00  w-skt-migration-no-import-edits
    1.00  w-skt-not-installed-is-not-not-synced
    1.00  w-skt-remedy-without-origin
    1.00  w-skt-stale-artifacts-are-not-stale-home
    1.00  w-skt-sweep-requires-epic
    1.00  w-skt-ticket-path-must-be-sibling
    1.00  w-skt-ticket-verb-help-is-scoped
    1.00  w-skt-which-copy-of-skt-ran
    1.00  w-skt-worktree-leaves-the-integration-repo

**Twelve at 1.00.** Both non-1.00 results were read rather than recorded, and
neither is a substrate defect.

`w-skt-check-record-disagrees-with-checkout` **0.83 — a genuine efficiency
miss.** Both substantive graders passed: the agent synced the unit and did not
reconstruct state by hand (`no-reconstruction` forbids `rev-parse`,
`ls-remote`, `git log`, reading `units.lock`). It failed only `within-budget`,
which is `max_calls: {Bash: 3}` and whose prose is "Two reads and one command."
Right behaviour, over the shell budget. The case is working as designed.

`w-skt-is-a-plugin-not-a-skill` **0.67 — the grader is unearnable.** Filed as
EA-DF-09. Reproduced twice. The agent answered *"**No.** This checkout has no
`./.skill-manager` home"* with five cited read-only checks, and it was right:
the case ships no fixture and nothing creates that home. Its two transcript
graders passed. The third is a content grader demanding the literal word "Yes".

### 1b — the two `ticket-agent-*` cases: UNDECIDED, not red

    0.30  ticket-agent-closes-a-ticket
    0.27  ticket-agent-opens-a-ticket

**These two cannot run in the staged view and say so in writing.** Their
fixture is a real branched Skill Manager home, ~41,000 entries against `claude
plugin eval`'s hard 20,000 ceiling. Verified in a kept sandbox:

    /private/tmp/e-QUMkuv/sealed/home/cwd/.eval/UNDECIDED-needs-home
    verify.log: "ticket-agent-opens-a-ticket needs a branched Skill Manager
                 home, which the view cannot carry"

**The epic agent read them as substrate failures first**, reported them as "the
agent never issued the front door", and called them the highest-value cases in
the corpus. That is precisely the misreading `place.sh` was written to prevent —
"an empty workspace would score 0 and read as *the agent could not provision a
home*, an instrument failing in the one direction this project says it may not."
The marker was written and did not reach the summary table, which is the only
thing an operator reads. Filed as **EA-DF-08**, and the misreading is recorded
here because the finding is worth less without it.

Four more of the six sit in later stages — three in skill-manager, one in
git-epic-workflow — so the same misreading is available three more times.

## Cost, measured

| | |
| --- | --- |
| stage 0 | $0.11 |
| stage 1a (14 cases) | $2.44 |
| stage 1b (2 cases) | $0.34 |
| two diagnostic re-runs | $0.32 |
| **total, 19 case-runs** | **$3.21** |

About **$0.17 per case**, which puts the whole 64-case corpus near **$11**. An
earlier estimate of $55–150 in this session was extrapolated from the 3-turn
smoke case and was wrong by an order of magnitude; 14 real cases are the right
basis. The stagger is therefore NOT justified by cost. It is justified by what
stages 0 and 1 actually bought: one environment blocker caught for $0.00 that
would have voided 60 cases, and two instrument defects caught before they could
be averaged into a verdict about the substrate.

## What stage 1 says about skt

Stated narrowly, because the temptation is to say more. Twelve cases covering
`check`, `sync`, `status`, `migration`, `ticket new`, `ticket sweep`, worktree
placement and wrapper resolution scored 1.00 against the post-fix code — the
same surface that was ERRORED at 4/5 nodes in the morning's graph run and that
three fixes landed on today. One case scored 0.83 for using five shell calls
where the budget allows three.

It does not say the cases are good cases; nothing here validates the corpus
itself, and two of the sixteen were just shown to be mis-instrumented. It says
that where the corpus asks skt a question it can answer, skt answers correctly.
