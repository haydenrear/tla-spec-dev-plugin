# Epic ticket assignment and execution

This block turns an ordinary `git-issue` work order into one ticket of a shared
epic. Keep it marker-delimited so an epic resume can update the assignment
without rewriting the issue's discovery.

## Assignment block

````markdown
<!-- git-epic-workflow:assignment:start -->
## Epic execution — REQUIRED

```yaml
version: 1
epic:
  id: "<epic-id>"
  workflow: "<unique-workflow-name>"
  branch: "epic/<slug>"
  base_sha: "<commit-reachable-from-origin-epic>"
  plan_commit: "<commit-containing-canonical-plan>"
  schedule_revision: 1
  default_branch: "<default-branch>"
ticket:
  spec_id: "<stable-ticket-id>"
  feature_branch: "feature/<issue-number>-<slug>"
  worktree: "../wt-<issue-number>-<slug>"
  pr_base: "epic/<slug>"
  depends_on: []
  blocks: []
  wave: 1
  promotion_order: 10
  promotion_predecessor: null
  role: implementation      # implementation | evaluation
  conflict_keys:
    production: []
    tla: []
    adapters: []
    test_graph: []
    workflow: []
goals:
  - goal: "<goal-id>"
    kind: "perf"            # perf | eval | integration | quality
    statement: "<what should be measurably better after the epic>"
    metric: "<measured quantity>"
    baseline: "<value + commit it was measured on, or 'unmeasured'>"
    target: "<threshold that counts as success>"
    decided_by:
      ticket: "<evaluation-ticket-id>"
      harness: "<command the evaluation ticket runs on the integrated epic>"
    contribution: "direct"  # direct | enabling | guard
    expected_effect: "<direction and magnitude this ticket should produce>"
    local_signal: "<cheap in-worktree command, or 'N/A: reason'>"
validation:
  tlc: "<exact command or N/A: reason>"
  # Name the target. `--ticket <id>` resolves two and runs one (SIS-KICKOFF-F-04).
  spec_unit: "<exact command, --target per target>"
  repository_unit: "<exact command or N/A: reason>"
  graphs: ["<affected-repository-graph>"]
  spec_graph: "<repository spec-conformance graph or N/A: reason>"
  toolchain_spec_workflow: "N/A unless this repository is tla-spec-dev"
  evidence_root: "<ticket-results-path>"
review:
  mode: "external"          # external TO THIS AGENT — do not change this value
  ticket_agent_stops_after: "pr_open"
  merged_by: "epic-owner"   # never this agent; never the default branch
  cadence: "wave"           # when the human review happens, epic-side
  artifact_root: "results/epic-<slug>/review"
deferment:
  mode: "batch"          # batch | ask | inline
  blocking: "escalate"   # escalate | ask
  budget: 5
  backlog: "specs/desired_program_model/deferred_findings.yaml"
```

This issue belongs to an existing shared spec workflow. The epic assignment
overrides ordinary instructions to branch from or target the default branch.

`review.mode` stays `external` because that is what the field means to the
ticket agent — the review is not this agent's, and `git-issue-workflow`'s
`references/epic-ticket.md` §1 refuses an assignment whose mode is anything
else. `merged_by` and `cadence` are additive: they say who performs the merge
the ticket agent is already forbidden to perform, and when the human sees the
result. Do not encode the cadence in `mode`.

- Read `goals` before implementing. The `expected_effect` is the result this
  change is aiming at; the named evaluation ticket decides the goal on the
  integrated epic. Run `local_signal` before close, record the number under the
  evidence root, and report it against `expected_effect` — including "no
  measurable movement".
- Start the worktree from the latest `origin/epic/<slug>` after all
  `depends_on` PRs are merged.
- Run `tla-spec-dev --spec-root specs open ticket <stable-ticket-id>`; never
  scaffold another workflow.
- Before close, wait for `promotion_predecessor`, reconcile the latest epic tip,
  and rerun the validation matrix.
- Mark and close only this spec ticket with every evidence path. Never run the
  whole-workflow close script and never use `--accept-new`.
- A local signal is a signal, not a gate. A missed one is reported, never
  hidden, and never justifies weakening the REQUIRED matrix or chasing the
  metric outside this ticket's conflict keys.
- Defects found outside this ticket's conflict keys and semantic delta are
  **deferred, not fixed**: record them in the backlog under the epic's
  deferment policy and keep working the assigned slice. Escalate blocking
  out-of-scope findings instead of widening scope.
- Your worktree has its own Skill Manager home
  (`<worktree>/.skill-manager`, gitignored, a real copy of the project home), and
  **nothing you change inside it is in this PR**. Before stopping, run
  `skill-manager home close-out --home <worktree>/.skill-manager --into <main-working-tree>/.skill-manager`
  (the **main working tree's** home, not `$PWD`'s nearest git toplevel, which
  from inside your worktree names your own home)
  and state the verdict in the PR body, then list every unit you changed and why
  under `## Review input` → *Machinery friction*. You may
  `skill-manager unit publish <unit> --ticket <ticket>` your own edits — that
  reaches the unit's own repository and contends with nothing. Do **not** run
  `home sync` into the project home: that is one shared destination, you cannot
  see the other tickets writing it, and the epic agent reconciles every
  worktree's home there in serial at wave close.
- Commit and push everything you want kept — evidence, backlog entries, close
  history. Leave the worktree standing; the epic agent removes every worktree in
  one sweep at the end of the epic, after checking that nothing uncommitted,
  stashed, unpushed, or unmerged is left in yours.
- Your PR body is **review input**, not only a delivery record. The epic owner
  merges it and then builds one review over the whole wave for a human, so write
  the `## Review input` section described below: the hot spots you created, the
  decisions you made that nobody asked for, any guardrail you had to override,
  where you would look for bugs in your own change, and what about the tooling
  or skills slowed you down. You are the only one who still knows the last two.
- Push the sealed ticket branch and open its PR with base `epic/<slug>` and
  `Refs #<issue-number>`. Stop there. The epic owner merges this PR into the
  epic branch; you do not merge it, do not merge to the default branch, and do
  not close the GitHub issue.
<!-- git-epic-workflow:assignment:end -->
````

## This block has one owning schema and one mechanical check

Three skills touch this block: it is **specified here**, rendered into an issue
body by `git-issue` (`references/epic-assignment.md`), and parsed by
`git-issue-workflow` (`references/epic-ticket.md` §1). Three prose copies of one
schema drift silently and have — a field added here and not to the renderer
produces issues that parse cleanly and just omit a policy, which the ticket
agent discovers by not having it.

So this file is the schema's owner, and `scripts/validate_assignment.py` is the
check. Run it on the rendered issue body, not on the plan and not on this
template:

```bash
gh issue view <issue-number> --json body -q .body \
  | uv run --script "<skill base directory>/scripts/validate_assignment.py" \
      --expect-ticket <stable-ticket-id> --expect-epic-branch epic/<slug>
# or, from a saved body (a flag, never a positional path):
uv run --script "<skill base directory>/scripts/validate_assignment.py" \
  --assignment issue-body.md --expect-ticket <stable-ticket-id> --expect-epic-branch epic/<slug>
```

The skill base directory is the `Base directory for this skill:` line printed
when the skill loads. Run the script with `uv run --script`, never `python3`,
which lacks PyYAML.

It fails only on what would send the agent to the wrong place: no parseable
block, a missing `epic`/`ticket` block, branch, feature branch, worktree or
`pr_base`, a `pr_base` that is not the epic branch, an epic branch that is the
default branch, or a ticket/branch the dispatch did not expect. Everything else
(placeholders, `N/A` without a reason, missing policy blocks, enum spellings,
`conflict_keys` lanes, which may be any names) is a short `WARNING:` summary
with exit 0; `--strict` restores them as errors and `--force` (or
`SKILL_GATES=off`) passes past blocking ones. Adding a field to the block above
still means adding it to the renderer in the same change.

## Evaluation-ticket variant

A ticket that decides one or more goals sets `role: evaluation`, lists
`owns_goals`, and replaces the per-goal `contribution` block with the harness it
must run:

```yaml
ticket:
  role: evaluation
  owns_goals: ["<goal-id>"]
goals:
  - goal: "<goal-id>"
    baseline: "<value + commit>"
    target: "<threshold>"
    harness: "<exact command run on the integrated epic tip>"
    evidence_root: "<results/epic-<slug>/goals/<goal-id>>"
    contribution: "guard"
    expected_effect: "decides the goal; adds no behavioral delta"
    local_signal: "N/A: this ticket is the measurement"
```

**`contribution: "guard"` is the spelling, and this file is where that is
settled.** It drifted three ways and cost a correctly rendered evaluation
assignment one spurious warning per owned goal — seven for a seven-goal
ticket (`SIS-KICKOFF-F-01`). This file and `git-issue`'s
`references/epic-assignment.md` both showed `guard`; the canonical plan schema
requires a contribution on *every* goal relation, evaluation tickets included;
only `scripts/validate_assignment.py` warned against it. The validator was the
outlier and the validator moved. It now accepts `guard` silently, and warns
only when the field is absent or says `direct`/`enabling` — an evaluation
ticket decides its goals rather than contributing to them, and that is what
`guard` records.

Its issue body states, in addition to the shared assignment rules:

- run each owned harness from a fresh start on the reconciled epic tip, after
  every contributing ticket has merged, and write results to `evidence_root`;
- report baseline → measured → target and a verdict (`met` / `missed` /
  `unmeasured` with a reason) per goal in the PR body — and one verdict **per
  clause** where the target has more than one, since a multi-clause goal that
  settles differently on each cannot be carried by a single token;
- never edit a target to match a result and never re-run selectively until a
  number passes; report the run that happened;
- file regressions and shortfalls as deferred findings for the epic owner
  instead of fixing them in this ticket.

## Ticket-agent flow

The presence of the start marker selects epic mode before ordinary
`git-issue-workflow` provisioning.

### 1. Verify readiness

Fetch remote state and confirm:

- every `depends_on` ticket PR is merged into the declared epic branch;
- `base_sha` is an ancestor of `origin/epic/<slug>`;
- `plan_commit` is reachable from the epic branch;
- the workflow name and ticket ID still exist in `ticket_plan.yaml`;
- the canonical ticket status is not `retired`; if it is, stop before creating
  or resuming a worktree and report the canonical retirement receipt — a stale
  assignment cannot resurrect retired scope;
- the assignment's schedule revision, dependencies, blocks, wave, promotion
  order/predecessor, conflict keys, goal relations, validation matrix, and
  evidence root exactly match that canonical ticket entry;
- the feature branch is not already merged or owned by another worktree.

Do not treat a locally closed spec ticket, a green branch, or an open PR as a
satisfied dependency.

Likewise, do not implement a ticket whose canonical plan entry is retired even
if its GitHub issue remains open. `retired` is an owner-approved schedule
amendment, and its receipt records that no semantic promotion or validation was
claimed. The epic owner must create a new ticket/revision to reintroduce scope.

### 2. Create the worktree from the epic branch

Apply the index-base pinning conventions (see "Worktree provisioning
conventions" in `plan-and-schedule.md`): clean tree, resolve the epic branch
to `commit_oid`/`tree_oid` **once**, create-only
`refs/index-bases/<repo-id>/<tree_oid>` retention ref, branch from the pinned
commit. Never re-resolve `origin/epic/<slug>` after creation — a ref is a
symbolic name, not an identity.

`skt` is a plugin, so **`skills/` is the wrong place to look for it** — a home
that has it reports it absent when you list that directory. One test answers the
question:

```bash
SMH="${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"
test -x "$SMH/bin/cli/skt"        # -> use the one command below
```

Where it resolves, the whole block below is one command — declared path, pinned
base, retention ref, and the worktree's own home, rolled back together on
bootstrap failure:

```bash
git fetch origin
commit_oid=$(git rev-parse origin/epic/<slug>)
skt ticket new <issue-number>-<slug> --base "$commit_oid" --path ../wt-<issue-number>-<slug>
cd ../wt-<issue-number>-<slug>
```

Without skt, the same conventions by hand.

**If you are reading this because the front door was not *found*, that is a
defect worth reporting.** The block below is for a repository that genuinely has
no `skt` — not for one where it was present and you looked in `skills/`, or ran
it and it failed. It works either way, which is exactly why its use is silent
unless you say so: run the `-x` test first, and if it resolved, name the reason
on the PR (`SKILL.md` rule 10, *Reaching that by-hand pair is itself a
finding*).

```bash
git fetch origin
test -z "$(git status --porcelain)" || { echo "dirty tree — reconcile first"; exit 1; }
commit_oid=$(git rev-parse origin/epic/<slug>)
tree_oid=$(git rev-parse "origin/epic/<slug>^{tree}")
git update-ref "refs/index-bases/$(basename "$(git rev-parse --show-toplevel)")/${tree_oid}" "$commit_oid" ""
# ONE chained command, deliberately. `git worktree add` alone leaves a checkout
# with NO Skill Manager home — an agent launched there reads and writes the
# operator's global ~/.skill-manager, and an epic runs several ticket agents at
# once. The W2 eval measured an agent running the add and stopping, so the two
# halves are not separable here:
git worktree add ../wt-<issue-number>-<slug> \
  -b feature/<issue-number>-<slug> "$commit_oid" \
  && "$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/git-issue-workflow "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/git-issue-workflow; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts/bootstrap-home.sh" \
       --root ../wt-<issue-number>-<slug>

cd ../wt-<issue-number>-<slug>
```

**Those first three lines are load-bearing, not tidiness.** `git fetch origin`
then `commit_oid=$(git rev-parse origin/epic/<slug>)` is what makes the branch
point the PUBLISHED tip. Branching a bare `epic/<slug>` instead resolves the
**local** ref — and in an epic whose ticket PRs are merged server-side with `gh
pr merge`, `origin/epic/<slug>` advances while your local `epic/<slug>` never
does, and neither does your local *copy* of the remote ref, because only a fetch
moves that. Measured once: a ticket branched **21 commits behind** and caught it
only because its work order carried a `base_sha` it thought to compare `HEAD`
against. It would otherwise have edited a superseded file and reported a true
sentence about the wrong tree.

`wt new` refuses that case now (exit 7, git-issue-workflow-skill#10) — but
**epic mode does not go through `wt new`**, it calls `git worktree add` directly,
which has no such gate. So in epic mode the fetch-and-resolve above *is* the
protection. Do not skip it, and do not substitute a bare branch name for
`"$commit_oid"`.

An ordinary (non-epic) ticket does both of those in one command, `wt new <ticket>
"$commit_oid"` — which is also a resolved SHA, and for the same reason. Epic mode
branches by hand because `wt` chooses the worktree path
(`<parent>/<repo>-<ticket>`) and an epic assignment **declares** it — the
assignment wins. The home the two routes produce is identical, and teardown is
the same single command either way:
`"$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/skt "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/skt; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts/wt" close <issue-number>-<slug>`,
which finds a hand-made `../wt-<issue-number>-<slug>` by search.

Resume the declared branch/worktree instead of creating another when it already
exists. Never use `origin/<default-branch>` in epic mode.

### 3. Check who owns the model before running anything against `specs/`

**The epic agent owns the TLA+ work** (SKILL.md rule 5), recorded as
`planning_rules.model_ownership_rule` in the canonical plan and restated as a
*Model ownership* note in the assignment. Read that rule first: it decides
whether this section applies to you at all.

**When the epic owns the model** — the normal case, and what rule 5 says — the
epic agent scaffolded this ticket's `desired` and `current` before dispatch and
closes and promotes the spec ticket at wave merge. The ticket agent's half is:

- **Do not run** `open ticket`, `close ticket`, `close_tickets.py`, or
  `--accept-new`. §6 below is not yours either; skip it and say so in the PR.
- **Do** move ticket-local `current/` toward `desired/` for your slice, run the
  spec tests the assignment names, and record evidence under the evidence root.
- `desired/` is the structure you validate against. A **small** correction to
  it is yours to make — a path substitution that makes the workspace runnable
  is the worked example, and without it one scaffolded workspace produced 94
  "could not locate repository root" errors and could not run at all. A
  **structural** change comes back to the epic agent in the PR body instead.
- **Say in the PR that you corrected it, and what you changed.** That is a debt
  the epic agent owes the project model after your ticket merges, and it is a
  named block of the wave artifact (`human-review.md` §3.4). Between your merge
  and that correction the model and the tree disagree; the only thing that
  closes the window is your having said so.
- Spec tests may be handed to you explicitly. If the assignment does not name
  them, they are not your slice.

**Where the plan's rule says otherwise**, the older shape holds and the ticket
opens exactly its own workspace, never a second workflow:

```bash
tla-spec-dev --spec-root specs open ticket <stable-ticket-id>
```

Update ticket-local `desired/` first. It is the whole-program state after this
ticket. Then implement production code and advance ticket-local `current/` to
the behavior that actually landed. Include all assigned surfaces:

- Internal/External TLA+ actions, state, invariants, and configs;
- spec-unit adapters, generated cases, and conformance tests;
- Test Graph adapters, bindings, nodes, composition, and context contracts;
- repository code/tests and structured validation evidence.

Do not reorder tickets, edit another ticket's status, or change workflow-wide
dependencies from the ticket branch.

### 4. Run the ticket validation loop

Run every matrix entry marked REQUIRED. Discover each affected graph before
running it and use Test Graph's saved-context loop for isolated failures. At a
minimum, record:

```bash
# Name the target explicitly, once per target. See the warning below.
tla-spec-dev --spec-root specs run spec-unit-tests --target specs/current
tla-spec-dev --spec-root specs run spec-unit-tests \
  --target specs/tickets/<stable-ticket-id>/desired
<test-graph-skill>/scripts/discover.py <graph>
<test-graph-skill>/scripts/run.py <graph>
```

**Do not use `--ticket <id>` as the measurement.** Confirmed at source
(`SIS-KICKOFF-F-04`): it resolves both targets, **executes only the first**,
and prints both — so it reports a target it never ran, and a green line covers
a suite that did not execute. It is the same silent-vacuity shape as a stale
pathspec that matches nothing: the negative result is indistinguishable from
not having looked. `--target` runs exactly what it names, so run it twice and
say in the PR which targets you ran.

A second reason to name the target: `--ticket <id>` addresses a ticket-local
workspace that only the epic agent creates. Where it has not been scaffolded
the command has nothing to resolve — ten assignments shipped in that state
before `validate_assignment.py` learned to warn about it.

Also run TLC, repository unit tests, the repository's assigned spec-conformance
graph, and any adapter commands from the issue. `specWorkflow` is the
spec-double-compiler repository's own CLI-lifecycle graph; run it only when the
plan explicitly targets that repository. Store reports under the evidence root.

### 4a. Defer failure cases found outside the assigned slice

Validation and review will surface real defects this ticket did not cause. Do
not chase them. Read `deferment.md` and apply the policy from the **canonical
plan** (`deferment_policy` in `ticket_plan.yaml`); the assignment block mirrors
it, but the plan wins if they differ.

For each failure case:

1. Classify it. In scope — every touched surface is inside this ticket's
   `conflict_keys` and its desired model already implies the fix — then it is
   ordinary ticket work; fix it.
2. Out of scope and blocking this ticket's REQUIRED matrix: stop, file the
   backlog entry with `severity: blocking`, push without closing the spec ticket
   or opening a promotion PR, and return the ticket to the epic owner with the
   surfaces a fix would touch and the sibling tickets sharing those keys.
3. Out of scope and non-blocking: append a backlog entry, then follow
   `mode` — `batch` continue, `ask` ask the owner now-or-batch, `inline` fix
   only within this ticket's conflict keys and record it.

Stop implementing and report when deferred findings exceed `budget`: that many
out-of-scope defects means the ticket's premise is wrong, and the next fix will
not be the last one.

Backlog entries are planning data. Commit them with the ticket's normal commits;
never place them in ticket-local `desired/` or `current/`, and never offer them
as close evidence. A deferred finding never justifies weakening a REQUIRED
validation entry, loosening an invariant, skipping a test, or closing a ticket
whose equality gate fails.

### 4b. Record the goal signal

Run each declared `local_signal` in the ticket worktree and store its output
under the ticket evidence root. Compare it with `expected_effect` and record one
of: moved as expected, moved less than expected, no measurable movement, or
moved the wrong way. An evaluation ticket instead runs its owned `harness` on
the reconciled epic tip and records baseline → measured → target per goal.

The local signal never changes the ticket's pass/fail: the REQUIRED validation
matrix decides that, and the evaluation ticket decides the goal. Do not tune,
re-run selectively, or widen scope to make the number look better. If the signal
shows the goal is unreachable from this slice, finish the assigned semantic
delta, file a deferred finding describing what the goal would actually require,
and report it — that is plan feedback, not ticket work.

### 5. Enter the serialized promotion lane

Parallel implementation ends here. Wait until the `promotion_predecessor` PR is
merged into the epic branch. Fetch and rebase or merge the latest epic tip into
the ticket branch before closing.

Re-read the canonical plan after fetching and repeat the complete assignment
equality check. A changed schedule revision or field mismatch returns the issue
to the epic owner; do not promote from stale assignment metadata.

Reconcile deliberately:

- preserve predecessor close-history entries and closed plan statuses;
- use the latest epic `specs/current` as the whole-program base;
- reapply this ticket's semantic delta to ticket-local desired/current;
- retain all sibling Test Graph artifacts and bindings;
- rerun the complete ticket validation matrix.

If reconciliation changes scope or reveals a semantic conflict, stop and ask
for an amendment/reconciliation ticket. Do not patch workflow-wide state
silently.

### 6. Close only this spec ticket — unless the epic owns the model

**Skip this whole section when `planning_rules.model_ownership_rule` reserves
the TLA+ work to the epic agent**, which is what SKILL.md rule 5 says by
default. In that case the epic agent sets the plan status, closes the ticket,
and promotes at wave merge; a ticket agent that runs `close ticket` here has
promoted a model into the shared workflow that the epic did not schedule, and
it cannot be un-promoted without rewriting append-only history. Push your
evidence, open the PR, say in the body that §6 was not yours, and stop.

The rest of this section is for an epic whose plan rule says ticket agents
close their own spec tickets.

**First** set this ticket's `status` to closed/done in the canonical plan,
`specs/desired_program_model/ticket_plan.yaml` — and only this ticket's. This is
a precondition, not bookkeeping: `close ticket` reads the plan, not the ticket
workspace, and refuses outright while the entry still says `status: planned`:

```
ERROR: ticket <id> is not closed in ticket_plan.yaml: status=planned
```

`--allow-open` exists to bypass that precondition and is recorded in the history
as a guard weakening. Never reach for it here; edit the plan entry instead.

Then run:

```bash
tla-spec-dev --spec-root specs close ticket <stable-ticket-id> \
  --summary "<what landed>" \
  --result <evidence-path> \
  --result <another-evidence-path>
```

The default equality gate must pass. Do not use `--accept-new`,
`--no-promote-current`, or the whole-workflow close script. Inspect and commit
the append-only history entry, promoted project current, graph artifacts, and
evidence together.

### 7. Open the ticket PR and stop

Push the feature branch and create a PR explicitly targeting the epic branch:

```bash
git push -u origin feature/<issue-number>-<slug>
gh pr create --base epic/<slug> --head feature/<issue-number>-<slug> \
  --title "<ticket-id>: <title>" --body-file <pr-body.md>
```

The PR body contains:

- `Refs #<issue-number>`;
- epic branch, workflow, and spec ticket ID;
- dependency and promotion-predecessor checks;
- exact commands run and report/evidence paths;
- the close-history path and resulting commit SHA;
- a `## Goal contribution` section with one row per declared goal — goal ID,
  contribution kind, expected effect, measured local signal (or `N/A: reason`),
  and the evaluation ticket that decides it;
- a `## Deferred findings` section listing each backlog ID filed by this ticket
  with its severity and one-line summary, or `None`;
- the `home close-out` verdict for this ticket's worktree, naming every blocking
  unit and any you published with `unit publish`. The epic agent reconciles this
  home into the project home and later deletes the worktree without being able
  to see inside it; this line and the *Machinery friction* list below are the
  only places that fact survives;
- a `## Review input` section, written for a human who has ten minutes and did
  not read the ticket. Four short lists, evidence-cited, no padding — the epic
  owner composes the wave review from these rather than re-deriving them from
  the diff (`human-review.md` §3):
  - **Hot spots** — what you changed that carries the most risk or the most
    meaning, with paths. Say when you wrote a file another ticket in your wave
    also touches;
  - **Decisions and overrides** — choices you made that the assignment did not
    specify and that another ticket would be needed to reverse, plus every
    guardrail you weakened (`--allow-open`, a skipped test, a matrix entry that
    became `N/A`, an inline out-of-scope fix). Report them even where they were
    obviously right;
  - **Where I'd look for bugs** — your own change, ranked, with the cheapest
    experiment that would settle each. Reproducible defects are backlog entries
    instead; this list is allowed to be suspicion, labelled as such;
  - **Machinery friction** — what about the skills, scripts, validators, or
    instruments cost you time, and what you changed in your own Skill Manager
    home to get around it. That home is gitignored and dies with this worktree,
    so a fix you do not name here reaches nobody.

Stop there. The epic owner merges this PR into the epic branch and reviews the
wave with the user. Do not self-merge, target the default branch, run
whole-workflow promotion, sync the primary checkout to the default branch, or
close the GitHub issue. The closed PR head is sealed; semantic review changes
require an explicit amendment ticket so append-only evidence stays truthful.


## The long form of the card's load-bearing rule 5

Moved out of `SKILL.md` by SI-29 (#391): the card keeps the rule, this page
keeps the reasons.

5. **The epic agent owns the model; ticket agents move `current` toward it.**
   Before dispatch it scaffolds each ticket's `desired` and `current`, validates
   them, and runs TLC. At wave merge it closes and promotes the spec ticket,
   applies the model delta, and places every attribution anchor.

   A ticket agent **does not run** `open ticket`, `close ticket`,
   `close_tickets.py`, or `--accept-new`. It moves ticket-local `current` toward
   `desired`, runs the spec tests its assignment names, and records evidence. A
   **small** correction to `desired` is the ticket's; a **structural** change
   comes back in the PR body. A small correction is a debt the epic agent then
   owes `specs/current`, `program_model` and `desired_program_model`
   (`references/epic-ticket.md` §3). Record the reversal in the plan as
   `planning_rules.model_ownership_rule` and restate it in every assignment.

