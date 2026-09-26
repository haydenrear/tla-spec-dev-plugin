# Plan and schedule an epic

Use this reference when creating a new epic or reconciling a partially planned
one. Discovery and issue content still follow `git-issue`; this reference adds
the shared branch, spec workflow, and schedule.

## 1. Preflight

Confirm all of these before writing:

```bash
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef
git status --short --branch
git fetch origin
ls specs/program_model specs/.history test_graph
```

Inspect `specs/program_model/spec_manifest.yaml`, both TLA+ views, action and
adapter mappings, active spec directories, the existing graph plans, and the
latest relevant history. Stop if the baseline is incomplete or an unrelated
`specs/current` / `specs/desired_program_model` workflow is active on the branch
lineage.

For a resumed epic, first read its remote branch, ticket plan, assignment blocks,
and ticket PRs. Reconcile those artifacts instead of scaffolding again.

## 2. Create the epic integration branch

### Worktree provisioning conventions (index-base pinning)

Every worktree this skill creates — the epic worktree here and every ticket
worktree in `epic-ticket.md` — follows these conventions so its base is
immutable and reproducible (index platforms such as commit-diff-context
snapshot branching consume these OIDs as base-snapshot identity):

1. **Clean slate** — `git status --porcelain` empty before provisioning;
   stop and reconcile otherwise.
2. **Resolve the base rev to object IDs once** — capture
   `commit_oid=$(git rev-parse <base-ref>)` and
   `tree_oid=$(git rev-parse "<base-ref>^{tree}")`; record them; never
   re-resolve the branch name afterwards.
3. **Retention ref** — create-only
   `git update-ref refs/index-bases/<repo-id>/<tree_oid> <commit_oid> ""`;
   an existing ref pointing at a different commit is a hard error. Reserved
   namespace, never public tags.
4. **Branch from the pinned commit**, not from the moving ref name.

Choose a short stable slug and create a dedicated epic worktree from the fetched
default-branch tip:

`skt` is a plugin, so it is never under a home's `skills/`; test it by path:

```bash
SMH="${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"
test -x "$SMH/bin/cli/skt"        # -> use the one command below
```

Where it resolves, one command applies every convention below — clean-slate
check, OIDs resolved once, create-only retention ref, branch from the pinned
commit — and gives the worktree its own home in the same breath, rolling both
back if the bootstrap fails:

```bash
git fetch origin
skt ticket new epic-<slug> --base origin/<default-branch> --path ../wt-epic-<slug>
cd ../wt-epic-<slug>
```

(The branch it creates is `feature/epic-<slug>`; rename with `git branch -m
epic/<slug>` if the plan declares the bare epic name, or pass the resolved
`commit_oid` as `--base`.) Without skt, the same conventions by hand — and if
you are here because the front door was not *found* rather than not *present*,
that is a front-door defect: report it under `SKILL.md` rule 10, *Reaching that
by-hand pair is itself a finding*.

```bash
git fetch origin
test -z "$(git status --porcelain)" || { echo "dirty tree — reconcile first"; exit 1; }
commit_oid=$(git rev-parse origin/<default-branch>)
tree_oid=$(git rev-parse "origin/<default-branch>^{tree}")
git update-ref "refs/index-bases/$(basename "$(git rev-parse --show-toplevel)")/${tree_oid}" "$commit_oid" ""
git worktree add ../wt-epic-<slug> -b epic/<slug> "$commit_oid"
cd ../wt-epic-<slug>
# NOT DONE YET: this worktree has NO home until the bootstrap under
# "Skill Manager homes" below runs — that block is part of THIS step,
# not optional reading (the W2 eval measured an agent stopping here).
```

Record the starting SHA (`commit_oid`). Never create ticket branches from the
primary checkout or from the default branch once the epic exists. Never
force-push `epic/<slug>`.

### Skill Manager homes: what an epic is actually fanning out

An epic is the first place the three-tier home model becomes a *scheduling*
concern, so decide it here rather than discovering it at finalization.

```
root       ~/.skill-manager              where the operator installs
   |  copy
project    <repo>/.skill-manager         ONE per repository — the shared destination
   |  copy                               for every worktree below
worktree   <worktree>/.skill-manager     one per ticket, and one for the epic worktree
```

Each tier is a **real copy, not a symlink**, and that is the load-bearing part for
you: an epic runs several ticket agents at once, and a symlink farm would make
their homes one shared object, so two agents editing "their" copy of a skill would
be editing each other's, last writer winning silently. Copies buy you the
parallelism the whole scheduling model assumes.

Give the epic worktree its own home before running anything that installs, syncs,
binds, or resolves — those all write into whatever `SKILL_MANAGER_HOME` names, and
before the local home exists that is the operator's global home:

```bash
# the skt path above already did this; by hand it is:
"$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/git-issue-workflow "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/git-issue-workflow; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts/bootstrap-home.sh" \
  --root ../wt-epic-<slug>
```

That path is the resolution, not a placeholder: an installed unit's files live at
`$SKILL_MANAGER_HOME/skills/<unit>/`, and the `:-` fallback makes the same line
work from a bare shell. If this repository has never been given a home of its own,
this is also the command that gives it one — run it with `--root <repo-root>`
first, once, then again for the worktree.

Then note two things about the schedule you are about to write:

- **`conflict_keys` do not cover units in a home.** They partition *tracked files*
  under lane names the plan chooses — `production`, `tla`, `adapters`,
  `test_graph` and `workflow` are common examples, not a required set, and the
  validators accept any lane name. A skill unit lives in a home,
  which is gitignored, so two tickets in the same wave can have perfectly disjoint
  conflict keys and still both improve `test-graph` in their own homes. Neither
  edit is in either PR. **You** reconcile both into the one project home at that
  wave's close (`references/worktree-lifecycle.md` §3), in serial, and the second
  one comes back **held back** rather than overwritten — a conflict you resolve,
  not a silent loss. That is the designed outcome, but it is work you scheduled
  without meaning to. If you expect a wave to touch the same unit, say so in the
  assignment and have one ticket own it.
- **Publishing beats chaining.** `home sync` only moves an edit up one tier. An
  improvement that should reach other repositories has to go to the unit's own
  git repo via `skill-manager unit publish`; a chain-only route would need the same
  merge performed twice and would still never reach a sibling project.
- **The schedule has a disk cost, but not the one `du` reports.** Homes are
  cloned copy-on-write, so a wave of six worktrees does not cost six project
  homes — measured here, cloning a home `du` calls 1.1 GB moved free space by
  33.7 MB. The space goes instead to per-home venvs and tools and to divergence
  as each worktree is worked in, so the cost grows with *activity*, not with
  wave width, and it accrues until the epic's final sweep. Check headroom with
  free space before writing the waves, and never size a schedule off `du`:

  ```bash
  df -h <repo-root>
  ```

  If the headroom is thin, the answer is a narrower wave or an earlier sweep of
  delivered tickets, decided with the user
  (`references/worktree-lifecycle.md` §1, §6).

## 3. Discover the whole change

Use the `git-issue` discovery sequence once for the epic and then refine it per
ticket. Identify:

- target program state, Internal/External actions, variables, and invariants;
- production paths and symbols;
- spec-unit adapters and conformance tests;
- Test Graph bindings, node IDs, composition, and context keys;
- acceptance commands and evidence paths;
- true ordering dependencies and potential write conflicts.

The desired model describes the final whole-program state. A ticket desired
model later describes the whole-program state after that ticket, not a feature
fragment.

While discovering, inventory what already measures this program: benchmark
scripts, eval datasets and scorers, perf-marked test suites, end-to-end Test
Graph graphs, and any dashboards or saved baselines. That inventory is the raw
material for the goals agreed in step 3a — goals are cheapest when an existing
harness already decides them.

## 3a. Agree the epic goals

Before scaffolding the workflow, ask the user what should be measurably better
when the epic is done. This is a required decision, like the deferment policy;
do not infer goals from the codebase and do not default them.

Ask for each outcome: the metric, the command that measures it, today's value,
and the threshold that counts as success. Then:

- write each answer as a goal in the schema from `goals-and-evaluation.md`;
- measure the baseline now, on the fresh epic branch, whenever the harness
  already exists, and commit it under the epic evidence root;
- schedule a wave-1 harness+baseline ticket when it does not;
- schedule the terminal evaluation ticket(s) that run the harnesses on the
  integrated epic and decide each goal;
- give every other ticket a goal relation — contribution kind, expected effect,
  and a local signal it can run in its own worktree.

If the user has no measurable outcome, record `epic_goals: []` with a
`goals_waived` reason rather than inventing a metric. Read
`references/goals-and-evaluation.md` for goal kinds, baselines, contribution
kinds, the evaluation-ticket contract, and reporting.

## 4. Scaffold the shared workflow once

Choose stable ticket IDs before scaffolding. Use the first ticket only as the
CLI seed:

```bash
tla-spec-dev --spec-root specs scaffold workflow <first-ticket-id> "<epic title>"
```

Then replace the placeholder planning data with the complete epic:

- set a unique workflow `name` / `status.workflow` derived from the epic slug;
- make `specs/current` the complete accepted starting model;
- author `specs/desired_program_model` as the complete target model;
- expand `ticket_plan.yaml` to every stable ticket;
- add an integer `schedule_revision` that changes whenever IDs, dependency
  edges, waves, promotion order, conflict ownership, or validation scope changes;
- add the `epic_goals` block agreed in step 3a;
- add the `deferment_policy` block agreed in step 4a;
- add the `review_policy` block agreed in step 4b;
- remove placeholder actions, scopes, commands, and assertions.

Do not run `open ticket` on the epic branch. Each ticket agent opens exactly its
own workspace on its ticket branch.

Keep the generated ticket schema and add these scheduling fields to each ticket:

```yaml
github_issue: "https://github.com/<owner>/<repo>/issues/<number>"
schedule_revision: 1
depends_on: []
blocks: []
wave: 1
promotion_order: 10
promotion_predecessor: null
role: implementation          # implementation | evaluation
conflict_keys:
  production: []
  tla: []
  adapters: []
  test_graph: []
  workflow: []
goals:
  - goal: "<goal-id>"
    contribution: direct      # direct | enabling | guard
    expected_effect: "<direction and magnitude, or 'none — enabling only'>"
    local_signal: "<cheap in-worktree command, or 'N/A: reason'>"
```

Evaluation tickets add `role: evaluation` and `owns_goals: ["<goal-id>"]`, and
depend on every ticket contributing to the goals they own.

## 4a. Agree the deferment policy

Before any issue is dispatched, ask the user how ticket agents must handle
failure cases they find outside their assigned slice. This is a required
decision, not a default to assume silently — unbounded in-ticket bug fixing is
the main way epic tickets lose their semantic boundary.

Ask one question with the concrete tradeoff:

> Ticket agents will find real defects outside their assigned slice. How should
> they handle them?
>
> - **batch** (recommended) — record to the backlog, keep working the assigned
>   slice, triage between waves and at finalization;
> - **ask** — record, then stop and ask you per finding whether to open a ticket
>   now or batch it;
> - **inline** — allowed to fix within their own conflict keys, still recorded.
>
> Blocking findings (the ticket's REQUIRED validation cannot pass without
> touching another surface) **escalate** to you by default; say so if you would
> rather be asked to authorize an inline fix instead.

Record the answer, a per-ticket deferral `budget`, and the backlog path in
`ticket_plan.yaml` using the schema in `deferment.md`.

**Create the backlog file only if that path does not already exist.** In a
repository that has run epics before, the configured backlog path is very often
a **cumulative** ledger carrying every prior epic's findings, and writing the
empty template over it is a silent, pushable data loss that no validator, test
or gate in this workflow detects:

```bash
test -e <backlog-path> || printf 'findings: []\n' > <backlog-path>
```

**When the file already exists, do not truncate, re-template, prune, reorder or
"reset it for this epic".** Leave every existing row in place and append this
epic's findings to it — the `filed_as` references in sealed close-history
records point into that file by ID, and rewriting it breaks them. Confirm before
dispatching any issue that the row count did not fall:

```bash
grep -c '^  - id:' <backlog-path>   # before the kickoff commit, and after it
```

If the epic genuinely needs a backlog scoped to itself, give it a **new path**
and record that path in `ticket_plan.yaml`; do not repoint an existing
cumulative ledger at a fresh file.

**Partition the backlog when a wave runs more than one ticket.** A single
append-only file that every agent in a wave appends to makes collision certain,
not careless — four tickets in one wave of this skill's own epic cost four
reconciles, one of them twice, and `conflict_keys` cannot express it because
each ticket owns only its own rows. Set `per_ticket_backlog` alongside
`backlog`; the validator warns when a multi-ticket wave has no partition.
Prefer it to a union merge driver, which silently produces a valid-looking file
when it is wrong (`references/deferment.md`).

Read `references/deferment.md` for scope classification, entry format, agent
behavior, and triage.

## 4b. Agree the review cadence

The third required decision, asked in the same conversation as the goals and the
deferment policy. It settles who merges ticket PRs into the epic branch and when
the user is handed a review — which is also when they get their only look at the
epic while it can still be steered cheaply.

Ask once, concretely:

> Between waves I'll merge the wave's ticket PRs into the epic branch, then stop
> and hand you a review — hot spots in what landed, the decisions I made without
> asking and any guardrail that got overridden, where I think the bugs are, what
> the epic's own machinery should become, and what I recommend next — with a
> rendered diff and a short walkthrough. Should I stop for you at every wave
> boundary (recommended), only after named waves, or only at finalization? And
> do you want to do the merges yourself instead?

Record the answer next to `deferment_policy`:

```yaml
review_policy:
  cadence: wave                 # wave | ticket | milestone | finalization-only
  gate: true                    # false: produce the artifact and keep dispatching
  merges: owner                 # owner | human
  milestones: []                # waves to review after, when cadence is milestone
  artifact_root: "results/epic-<slug>/review"
  walkthrough: required         # required | on-request
```

`cadence: finalization-only` and `gate: false` are legitimate for a small or
exploratory epic, and both are decisions on the record rather than silence — the
epic PR states which policy was in force. The validator warns when the block is
missing and errors on a malformed one.

Read `references/human-review.md` for what the artifact carries, how the diff is
rendered, and what a review may and may not change.

## 5. Validate the schedule

Treat `depends_on` as a directed graph and reject the plan unless:

- every referenced ticket exists and no ticket depends on itself;
- a topological ordering includes every ticket;
- `blocks` is the reverse of `depends_on`;
- tickets in the same wave have no dependency path between them;
- every dependency is in an earlier wave;
- tickets in the same wave have disjoint conflict keys;
- every ticket has an exact validation matrix or an explicit `N/A` reason;
- `promotion_order` is unique and total;
- promotion order is a topological extension of `depends_on`;
- each `promotion_predecessor` names the preceding ticket in that total order;
- every ticket relates to at least one declared goal, every goal has a
  contributing ticket, and each goal's evaluation ticket both depends on and
  promotes after every contributor.

Run the bundled validator before dispatch and whenever the schedule changes.
The skill base directory is printed as `Base directory for this skill:` when the
skill loads — use it, don't search for the scripts. The scripts declare their
own dependencies: run them with `uv run --script`, never `python3` (which lacks
PyYAML). `validate_assignment.py` reads `--assignment <file>` or stdin, never a
positional path.

```bash
uv run --script "<skill base directory>/scripts/validate_epic_plan.py" \
  specs/desired_program_model/ticket_plan.yaml
```

Only a plan that cannot be scheduled at all fails (exit 1): no tickets, an
unusable or duplicate ticket ID, a `depends_on` naming a ticket that does not
exist, or a dependency cycle. Every other rule above is advisory: it prints a
`WARNING:` summary (at most three lines; `--verbose` lists all) and exits 0.
Read the warnings and fix what matters; do not let them stop the epic. `--strict`
turns every rule back into an error. `--force` (or `SKILL_GATES=off`) exits 0
even past a blocking error, for when you have decided it does not apply.
Report what the validator printed; its warnings explain themselves — do not read
the validator's source to interpret them.

A valid plan is not a valid dispatch. The plan is this skill's; the assignment
block that reaches a ticket agent is rendered by `git-issue` into a GitHub issue
body, and a field this plan carries can simply fail to arrive. Validate what
GitHub actually holds, per issue, before handing out its URL:

```bash
gh issue view <issue-number> --json body -q .body \
  | uv run --script "<skill base directory>/scripts/validate_assignment.py" \
      --expect-ticket <stable-ticket-id> --expect-epic-branch epic/<slug>
# or, from a saved body:
uv run --script "<skill base directory>/scripts/validate_assignment.py" \
  --assignment issue-body.md --expect-ticket <stable-ticket-id> --expect-epic-branch epic/<slug>
```

Exit 2 means there is no parseable assignment block at all; exit 1 lists what is
wrong with the one there is. It catches the failures that are invisible in
review of the plan: a placeholder nobody rendered, a `pr_base` that is not the
epic branch, a `review.mode` other than `external`, a `deferment` block the
renderer never learned to emit. Re-run it after any resume that rewrites
assignments, because a resume edits issues rather than the plan.

The total promotion order is an integration lane, not an implementation
dependency. Agents in one wave may implement and validate concurrently, but
only the next ticket in that lane may reconcile, close/promote, and enter the
epic branch.

## 5a. Retire dispatched scope without claiming delivery

Retirement is a reviewed schedule amendment for work the owner has explicitly
removed from this epic. It is not ticket completion and it does not rewrite the
published plan. Use it only after the user chooses the disposition; do not
infer abandonment from an idle branch or absent PR.

Apply one retirement transaction as follows:

1. Reconcile a clean epic worktree at the canonical plan tip. Determine the
   complete affected set: the unwanted ticket, every still-active dependent,
   its active promotion successor, its evaluation ticket, and every goal it
   contributes to or owns. An undelivered non-retired ticket may not depend on,
   block, or name a retired ticket as `promotion_predecessor`.
2. Preserve every dispatched ticket entry at its original zero-based list
   ordinal. Never delete, reorder, rename, or reuse its ID. Increment the root
   `schedule_revision` once for the amendment and update every changed active
   assignment to that revision.
3. Add `status: retired` and the `retirement` block below. Retain the retired
   entry's original scheduling fields as history. Do not rewrite a delivered
   ticket's sealed historical dependency, reverse-block, or promotion edges,
   even when they name a ticket this later amendment retires. Rebuild only the
   still-undelivered dependency/reverse-block and promotion-predecessor chains
   so new work skips all retired entries; retire or fully deliver every
   remaining ticket associated with an affected goal.
4. Update GitHub blocking relationships and the marker-delimited assignments
   for non-retired tickets to mirror the amended plan. Close or annotate a
   retired issue as not planned and link its successor when carried. Never
   describe it as merged or implemented.
5. Validate the amended plan, then generate each receipt with
   `tla-spec-dev --spec-root specs retire ticket <ticket-id>`. Do not hand-write
   the receipt manifest. Validate again and review the amendment before commit.

The plan entry has this exact shape:

```yaml
- id: EPIC-4                    # original ID at original ordinal; never moved
  status: retired
  # ...original scheduling and goal-relation fields remain...
  retirement:
    schedule_revision: 2       # positive decision revision; <= current root
    resolution: carried        # carried | superseded | abandoned
    reason: "Owner moved remote hardening out of the local MVP."
    decided_by: "@epic-owner"
    decided_at: "2026-08-12T03:00:00Z"
    successor_issue: "https://github.com/org/repo/issues/99"   # carried only
    successor_workflow: "agent-trace-indexing"                 # carried only
    receipt: "specs/.history/<workflow>/retired-ticket-003-EPIC-4/manifest.json"
    affected_goals:
      - goal: GOAL-remote-hardening
        disposition: carried   # accepted_missed | accepted_unmeasured | carried
        reason: "The local MVP intentionally does not decide this goal."
        successor_issue: "https://github.com/org/repo/issues/99" # carried only
        successor_workflow: "agent-trace-indexing"               # carried only
```

`resolution` records what happened to the ticket scope: `carried` moves it to a
named issue and workflow, `superseded` says another decision made this ticket's
slice unnecessary, and `abandoned` says the owner deliberately drops it. A
carried ticket requires both top-level successor fields, every affected goal
must also be `carried`, and every goal must name that exact same successor issue
and workflow. A superseded or abandoned ticket has no successor fields, none of
its affected goals may be carried, and non-carried goal entries have no
successor fields. Ticket and goals move together or do not carry at all. None
of the resolution values is a direct ticket `status`; the only schedule state
for this transaction is `retired`.

`retirement.schedule_revision` seals the revision at which the owner made this
decision. It equals the root revision when the receipt is created, but a later
unrelated plan amendment may advance the root beyond it. Never rewrite the
retirement block merely to catch up: validation requires a positive decision
revision no newer than the current root, and the receipt must continue to match
the complete decision-time `retirement` mapping exactly.

`affected_goals` must exactly copy every goal the ticket relates to or owns,
including a goal for which it was the evaluator. `accepted_missed` records that
the owner accepts a known miss; `accepted_unmeasured` records that the owner
accepts closing without a measurement; `carried` requires its own named
successor issue and workflow. When several retired tickets affect one goal,
their dispositions and carried target must agree, in addition to matching each
ticket-level decision. Do not delete the goal or edit its baseline/target to
conceal the disposition.

The canonical receipt path encodes the immutable zero-based ordinal and ID:

```text
specs/.history/<workflow>/retired-ticket-<ordinal:03d>-<safe-id>/manifest.json
```

For a git-epic workflow, `specs/.history` is canonical and the plan receipt must
use that exact repository-relative prefix. The lower-level `tla-spec-dev` CLI
may support a custom history root for non-epic workflows; that flexibility does
not change the epic contract.

The generated manifest identifies both `kind` and `entry_kind` as
`ticket-retirement`, and asserts `semantic_promotion.performed: false` and
`validation.claimed: false`. It is a durable receipt that work was *not*
accepted or measured, not a close-history entry. A delivered PR/history cannot
substitute for this receipt, and this receipt cannot substitute for delivery
evidence. If an abandoned ticket workspace existed, the retire command may
archive it as explicitly unaccepted; that archive is not a promoted model.
The plan and receipt declaration are closed schemas: do not add extension keys
to `retirement` or its `affected_goals` entries, and do not reorder or edit the
declaration after the receipt exists.

Prefer an amendment/reconciliation ticket over assigning shared workflow-wide
metadata to a parallel ticket. Ticket agents own their plan entry and declared
semantic slice; the epic owner owns ticket order, dependency edges, and
workflow-wide status.

## 6. Create or schedule GitHub issues

Every scheduled issue maps to one spec ticket and retains the standard
`git-issue` sections: Summary, References, Discovery notes, Worktree & branch,
Spec workflow, and Regression & close-out.

### New issues

Use `git-issue` to create the work order, then add the assignment from
`epic-ticket.md`. Set the spec workflow to REQUIRED because the agent must open
and close its planned spec ticket. If a slice has no semantic delta, document
the no-op model result and its evidence; do not silently skip ticket closeout.

After issue creation, write its URL back to `ticket_plan.yaml` and update the
assignment with the final issue number, feature branch, and worktree path.
Commit and push the canonical plan, then record that commit plus the current
`schedule_revision` in every assignment.

### Existing issues

Read the existing body and preserve it. Add or replace only this bounded region:

```text
<!-- git-epic-workflow:assignment:start -->
...rendered assignment from epic-ticket.md...
<!-- git-epic-workflow:assignment:end -->
```

Use `gh issue edit --body-file`; do not append duplicate assignments on resume.
The assignment explicitly overrides any older instruction to branch from or
target the default branch.

### Mirror the dependency DAG in GitHub

After every issue number exists, mirror each `depends_on` edge with GitHub's
blocking relationship and verify both directions:

```bash
gh issue edit <ticket-issue> --add-blocked-by <dependency-issue>
gh issue view <ticket-issue> --json blockedBy,blocking
```

On resume, compare the GitHub relationships with `ticket_plan.yaml`; add missing
edges and remove stale edges with the corresponding `--remove-blocked-by` /
`--remove-blocking` flags. The plan remains canonical, but the tracker must show
the same readiness graph agents see in their assignments.

Before dispatch, render every assignment from its canonical plan entry and
compare the following fields exactly: ticket ID, schedule revision,
dependencies, blocks, wave, promotion order/predecessor, conflict keys, goal
relations, validation matrix, and evidence root. An older ancestor `plan_commit` alone is
not freshness proof; the copied scheduling fields must still match.

## 7. Commit, push, and dispatch

Review the desired model and plan, then commit and push `epic/<slug>` before
dispatch. Each assignment records an epic base SHA that is already reachable
from the remote epic branch.

Return the goals the epic is aiming at:

| Goal | Kind | Metric | Baseline | Target | Decided by |
| --- | --- | --- | --- | --- | --- |

and a schedule such as:

| Issue | Spec ticket | Start dependencies | Wave | Promote after | Goals | State |
| --- | --- | --- | --- | --- | --- | --- |

An issue is ready to hand off only when every dependency PR is merged into the
remote epic branch. An open or green PR is not a satisfied dependency.

Whenever you recommend the next ticket — at dispatch and on every resume — read
the deferred-findings backlog and present pending entries in the same report.
From the first wave boundary onward that report is a section of the wave review
artifact rather than a separate message (`references/human-review.md` §3.5); the
table and the three outcomes are the same either way:

| ID | Found by | Severity | Summary | Blast radius | Disposition |
| --- | --- | --- | --- | --- | --- |

Ask the user, per pending finding, to promote it to a ticket now, keep it
batched, or close it `wontfix`. Recommend batching unless it blocks a planned
ticket. Promoting a finding is a plan change: new stable ID, dependency edges,
wave, promotion order, conflict keys, revalidated schedule, bumped
`schedule_revision`, new issue. Never retrofit it into a dispatched ticket.

This version does not start agents or poll them. The user passes ready issue
URLs to ticket agents, then invokes the epic workflow again to integrate and
review the finished wave, refresh readiness, or finalize. Merging those tickets'
PRs into the epic branch is this skill's work, not the user's, unless
`review_policy.merges` says `human` (`references/human-review.md` §1).


## The long form of the card's load-bearing rule(s)

Moved out of `SKILL.md` by SI-29 (#391): the card keeps the rule, this page
keeps the reasons. The card's numbering is unchanged.

3. **Dispatched identities are immutable, including retired work.** Never delete,
   reorder, rename or reuse a ticket ID after publishing assignments — delivery
   histories and retirement-receipt paths depend on the original zero-based
   ordinal and ID. Adding scope creates a new ticket; removing scope keeps the
   entry with `status: retired`, bumps `schedule_revision`, and records a
   retirement receipt and goal disposition.

12. **Every epic states measurable goals; every ticket relates to one.** Ask the
    user what should be measurably better before scaffolding. Record each goal
    with metric, harness, baseline and target; schedule the terminal evaluation
    tickets that decide them; give every other ticket a contribution, expected
    effect and local signal (`references/goals-and-evaluation.md`).

