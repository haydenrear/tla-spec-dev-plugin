---
skill-imports:
  - unit: tla-spec-dev
    path: skills/spec-double-2/references/agent_roles.md
    reason: "ROLE review — you are the review agent. This is your reading path and where a substrate finding goes when you open no PR: specs/results/deferred/REVIEW-AGENT.yaml. §3.4 below is where you write back OTHER roles' dispositions."
    section: review
---

# Wave integration and human review

An epic's only human checkpoints used to be one external review per ticket PR
and the semantic-review gate at finalization. That shape has two problems. It
serializes the whole schedule on a person at every ticket, and it hands that
person a PR-shaped view — one ticket's diff, one ticket's evidence — at the
exact moment nobody can yet see what the wave did as a whole.

So the checkpoint moves. The epic agent **merges the wave into the epic branch
itself**, and then stops and hands the user one review over the whole wave
diff: where the change concentrated, what it decided on their behalf, where it
is probably wrong, what the machinery running the epic should become, and what
to do next — with a rendered diff and a short spoken walkthrough.

This reference covers who merges what (§1), when the review happens and how the
user changes that (§2), the five things the artifact must carry (§3), the
visualization (§4), the walkthrough (§5), what a review may change (§6), and how
wave artifacts feed finalization (§7).

## 1. Who merges what

| Actor | May merge | Never |
| --- | --- | --- |
| Ticket agent | nothing | its own PR, the default branch, the GitHub issue |
| Epic agent (this skill) | ticket PRs into `epic/<slug>` | the epic PR into the default branch |
| User | anything | — |

Rule 7 is unchanged for the ticket agent: it pushes a sealed branch, opens a PR
based on `epic/<slug>`, states its evidence, and stops. It does not merge,
because it cannot see the wave — only the epic agent knows whether the
promotion lane held, whether a sibling landed on the same file, and whether the
plan still says what the assignment said.

The epic agent merges that PR. The epic branch is an *integration* branch: a
merge into it is reversible, is reviewed at the wave boundary before anything
downstream depends on it, and is gated again by finalize.md §3 before it can
reach the default branch. That is why this merge does not need a human and the
epic PR still does.

### Merging a wave

Merge in `promotion_order`, one at a time, never concurrently. For each ticket:

```bash
gh pr view <pr> --json baseRefName,mergeable,mergeStateStatus,statusCheckRollup
gh pr checks <pr>
gh pr merge <pr> --merge          # a merge commit, never squash
git fetch origin && git log --oneline -1 origin/epic/<slug>
```

- **`--merge`, not `--squash`.** The ticket's append-only close-history entry,
  its promoted `specs/current`, and its evidence were committed as separate
  facts. A squash collapses them into one blob whose message claims all three,
  and the finalizer's audit (finalize.md §1) reads those commits.
- **Verify before each merge, not once at the start.** Base is `epic/<slug>`;
  required checks are green; the assignment's scheduling fields still equal the
  canonical plan entry; the plan entry is not `retired`; the declared
  `promotion_predecessor` is already merged.
- **A merge conflict is a stop, not a task.** The promotion lane exists so that
  every ticket reconciles onto the current tip *before* it closes its spec
  ticket (epic-ticket.md §5). A conflict means that did not happen, so the
  ticket's close evidence describes a tree that no longer exists. Return it to
  its agent to reconcile and re-close. Do not resolve it on the epic branch:
  the resolution would be a semantic change with no ticket, no evidence, and no
  history entry.

  **A *mechanical* conflict is still that agent's.** The distinction is about
  cost, not authority. A conflict is mechanical when both sides are pure
  tail-appends to one append-only file and neither side deleted or changed a
  line against the merge base — the shape a shared findings backlog produces
  when several tickets in a wave each file their own rows. Everything else is
  semantic, and the rule above is unchanged for those.

  Naming the mechanical case buys two things, and neither is a waiver:

  1. **The resolution is a procedure, not a judgement**, so the round-trip is
     one command chain rather than a re-read. Prove both sides are tail-appends
     (`head -n <base-lines>` byte-identical on each side), re-derive your own
     block from your pre-reconcile commit, produce literally `tip ++ my_block`,
     then verify `diff <(git show <parent>:<file>) <file> | grep -c '^<'`
     returns **0 against both parents** — a row count alone cannot catch a
     swap. Measured in one wave of this skill's own epic: four reconciles, one
     ticket twice, every one of them this.
  2. **It is the case that should not have happened**, so it is evidence about
     the plan rather than work for the agent. Record it in `merges.md` and fix
     it in the schedule with `deferment_policy.per_ticket_backlog`
     (`references/deferment.md`), which makes the merge a no-op instead of a
     resolution.

  **The epic agent still does not resolve it either way.** Proving a conflict
  is mechanical means knowing which rows are that ticket's own, and the
  authority for that is the ticket's pre-reconcile commit — which the ticket
  has and the epic branch does not. Resolving from `found_by` fields instead is
  a guess at the one moment a guess is invisible.
- **Do not delete a ticket branch whose worktree still stands.** The worktree
  holds a Skill Manager home nobody has closed out yet (finalize.md §1b), and
  its author may still need the branch to reconcile.

Record, per merged ticket, the PR number, the merge commit SHA, and the
planned versus actual promotion position. Those three go in the wave artifact;
they are the evidence that the lane held.

### Then reconcile the wave's homes, and leave the worktrees standing

Merging the PR moves the tracked files. It moves **nothing** from the ticket
worktree's `.skill-manager`, which is gitignored and in no PR. Before writing
the review, reconcile each of the wave's worktree homes into the project home —
serialized, one at a time, reading `held-back` and `conflicted` as decisions
rather than retries — and check every worktree for uncommitted, stashed,
unpushed, or epic-unmerged work. That reconciliation is the epic agent's job,
not the ticket agent's, and doing it now rather than at finalization is the
whole reason it stays cheap. `references/worktree-lifecycle.md` §3 is the
procedure; §4 is the ledger row it updates.

The worktrees themselves stay standing until the epic ends, when all of them are
swept at once (§5 there). Nothing in a wave review removes one.

### What still stops the epic agent cold

Do not merge a PR whose REQUIRED validation matrix has a failing or missing
entry; whose ticket filed a `severity: blocking` deferred finding that is still
`pending`; whose assignment disagrees with the canonical plan; or which targets
anything other than the epic branch. Do not force-push `epic/<slug>`, bypass
branch protection, or merge the epic PR into the default branch — that last one
needs the user's explicit authorization at finalization and nowhere else.

## 2. When the review happens

**Default: at every wave boundary, and it is a gate.** After the last PR of
wave *N* is merged and before any wave *N+1* issue URL is handed out, the epic
agent produces the artifact, walks the user through it, and waits. No issue
from the next wave is dispatched until the user answers.

The gate is placed there rather than per-ticket because a wave is the smallest
unit that has a shape: its tickets were scheduled to be independent, so how
they actually interacted is information the plan did not have, and the next
wave is the first thing that can act on it.

Review also happens, regardless of cadence, when:

- a ticket escalates a blocking out-of-scope finding (deferment.md, *Escalation*);
- the plan is amended — a retirement, a promoted finding, a re-waving;
- finalization runs. That keeps its own external semantic-review gate
  (finalize.md §3); wave reviews do not replace it.

### The user changes the cadence, and the change is on the record

Agree `review_policy` at kickoff, alongside the goals and the deferment policy,
and store it at the root of `specs/desired_program_model/ticket_plan.yaml`:

```yaml
review_policy:
  cadence: wave                 # wave | ticket | milestone | finalization-only
  gate: true                    # false: produce the artifact and keep dispatching
  merges: owner                 # owner | human — who merges ticket PRs into the epic branch
  milestones: []                # waves to review after, when cadence is milestone
  artifact_root: "results/epic-<slug>/review"
  walkthrough: required         # required | on-request
```

Ask once, concretely:

> Between waves I'll merge the wave's ticket PRs into the epic branch, then
> stop and hand you a review — hot spots, the decisions I made without asking,
> where I think bugs are, what the epic's own machinery should become, and what
> I recommend next — with a rendered diff and a short walkthrough. Should I stop
> for you at every wave boundary (recommended), only after named waves, or only
> at finalization? And do you want to do the merges yourself instead?

`cadence: finalization-only` and `gate: false` are legitimate answers for a
small or exploratory epic. They are *decisions*, recorded in the plan, and the
epic PR says which one was in force. A skipped review that nobody chose is
indistinguishable at finalization from one that never happened — which is why
the field exists and why the validator warns when the block is absent.

## 3. What the artifact carries

Five sections, in this order, because that is the order a reviewer needs them.
Every row cites something a reader can open: a path, a line, a commit, an
evidence file, a backlog ID. A row that cannot cite is either labelled a
suspicion (§3.3 permits that, and only there) or it is not written.

Establish the range first — every command below reads it:

```bash
base=<epic tip before the wave's first merge>
tip=$(git rev-parse origin/epic/<slug>)
```

### 3.1 Hot spots

Where the wave's change concentrated or was contended. This section exists
because reviewer attention is finite and diffs are not self-ranking.

```bash
git diff --numstat "$base..$tip"                    # churn per file
git diff --name-status --diff-filter=A "$base..$tip"  # net-new files
for pr in <this wave's PRs>; do
  gh pr view "$pr" --json files -q '.files[].path'
done | sort | uniq -d                                # files two tickets wrote
```

Rank, highest first:

1. **Files more than one ticket in this wave wrote.** The conflict keys were
   supposed to make that impossible, so it is a planning miss as well as a
   review target — say which keys should have covered it.
2. **Net-new files that no Test Graph node or spec-unit case names.** New
   surface, no instrument.
3. **Highest churn**, by changed lines, with the ticket that produced it.
4. **Files an adapter mapping reaches from a changed TLA action or invariant.**
   A small production diff behind a semantic change is a hot spot even when the
   line count says otherwise.
5. **Anything a deferred finding already points at.**

Keep it to about seven rows. Each row: the location, why it is hot, and the one
question the reviewer should ask about it.

### 3.2 Decisions made implicitly, and guardrails overridden

Two lists. They are different, and the second one is not optional.

**Implicit decisions** are choices nobody approved because nobody was asked:
a data shape, a name that has become an interface, an error-handling policy, a
default value, a new dependency, an ordering, a fallback, a retry. The test for
inclusion: *if reversing this later needs another ticket, it belongs here.*

| Decision | Where | Alternative not taken | Cost to reverse later |
| --- | --- | --- | --- |

**Guardrail overrides** are specific and greppable. Never summarize them as
"a few test skips" — name each one:

| Override | How to find it |
| --- | --- |
| `--allow-open` on `close ticket` | the close-history entry records the guard weakening — `grep -rn 'allow.open' specs/.history/<workflow>` |
| `--accept-new`, `--no-promote-current` | same history entries. SKILL.md forbids both; an occurrence is a defect to report, not a footnote |
| skipped, xfailed, or quarantined tests | `git diff "$base..$tip" -- '*test*' \| grep -nE '^\+.*(skip\|xfail\|Disabled\|\.only)'` |
| a REQUIRED matrix entry downgraded to `N/A` | diff each assignment's `validation` block against its canonical plan entry |
| a weakened invariant or a dropped TLC property | `git diff "$base..$tip" -- '*.tla' '*.cfg'` |
| `wt close --force`, or a `home close-out` blocker cleared with the wrong remedy | the close-out verdict line in each ticket PR body |
| out-of-scope fixes made inline | backlog entries with `disposition: fixed-inline` |
| a ticket over its deferral budget | count backlog entries per `found_by` against `deferment_policy.budget` |
| a goal target edited after dispatch | `git log -p "$base..$tip" -- specs/desired_program_model/ticket_plan.yaml` over the `epic_goals` block |

That last row is the one to run every time. Editing a target so a measurement
passes is forbidden (SKILL.md *Boundaries*), and a wave review is the only
place a human sees the plan's own history rather than its current state.

Report an override even when it was clearly right. The reviewer decides whether
it was; the agent's obligation is that nobody had to go looking.

### 3.3 Where the bugs probably are

Not a bug list. Real, reproducible defects are deferred findings with entries in
the backlog (deferment.md) — they appear in §3.5, already filed. This section is
the agent saying where it would look first and why, which is worth more than a
confident "no issues found".

Draw from:

- code the wave changed with no new or changed test, graph node, or spec-unit
  case covering it;
- hunks written during a promotion-lane reconcile (epic-ticket.md §5) — those
  were authored against a moving tip under the most pressure of any moment in
  the ticket;
- error and failure paths added but never exercised by the matrix;
- surfaces where the ticket's local signal moved less than `expected_effect`,
  not at all, or the wrong way — the code did something other than what the
  ticket predicted, and the prediction was the design;
- pending backlog entries at `severity: major`;
- order- or concurrency-sensitive code that two tickets in one wave introduced
  independently.

Each row: the location, why it is suspicious, and the cheapest experiment that
would settle it. Label a row with no reproduction as a suspicion in the row
itself. A hunch is allowed here and is never filed to the backlog —
deferment.md's rule stands: an entry with no reproduction is not a finding.

### 3.4 What the epic agent applied, and what it still owes

This section used to be a recommendation list that "re-entered as a ticket".
For the machinery half that was a way of writing improvements down and never
making them: the skills lived in a gitignored Skill Manager home, so the
recommendation was the only thing that could survive a wave, and it routinely
was the only thing that did.

Two targets still ship through different doors, but the doors have changed:

- **The repository's architecture** — the program the epic is changing. It
  still ships as a new ticket in this epic (a plan amendment) or an issue on
  the default branch. Nothing here is implemented during a review, and that
  rule is unchanged.
- **The machinery that ran the epic** — the skills, scripts, validators, plan
  schema, harnesses, and instruments. **Where those files are tracked in the
  repository the epic is running in, the epic agent applies the change here,
  in the epic worktree, and says so below.** Where they are not — a unit
  outside the bundle, `skt`, another repository — the route is
  `skill-manager unit publish`, or `home sync --merge` to reach one
  tier up, and it dies with the worktree otherwise (SKILL.md rule 10,
  finalize.md §1b).

  **`unit publish` needs the unit to be a git checkout, and a projected unit is
  not one.** This is the step the paragraph above used to omit, and the omission
  has a measured cost: an epic agent read "reaches nothing by being merged",
  concluded no PR could fix a CLI defect it had just diagnosed, and filed a
  recommendation instead of a fix. The unit was in the project home the whole
  time. From the repository the epic runs in:

  ```bash
  # 1. Declare the unit in the checkout's own manifest. Git coords only; the
  #    coord names the REPOSITORY, not the installed unit.
  #      [plugins.tla-spec-dev]
  #      source = "github:haydenrear/tla-spec-dev-plugin"
  # 2. Point at the project home FIRST -- resolve writes whatever
  #    SKILL_MANAGER_HOME names, and before a local home exists that is the
  #    operator's global one.
  export SKILL_MANAGER_HOME=<repo>/.skill-manager
  skill-manager project register --project-dir <repo>
  skill-manager project resolve  --project-dir <repo>
  # 3. Materialize it as its OWN git checkout, which is what makes step 5 work.
  skill-manager project sync --project-dir <repo> --checkout <unit>
  # 4. Edit under <repo>/.skill-manager/plugins/<unit>/ (or skills/<unit>/) and
  #    prove the fix against this repository, before/after.
  # 5. Ship it to every project on every machine.
  skill-manager unit publish <unit> --child-home <repo>/.skill-manager --ticket <T>
  ```

  So the epic agent has three doors, not two: a tracked repository file, a
  gitignored home it can only sync one tier, and **a unit it can develop in
  place and publish upstream**. Reach for the third whenever the finding is in a
  skill, a reference page, a validator or a CLI the bundle ships — that is the
  self-improvement loop, and declining to use it turns every recurrence into
  another deferred row. `skill-manager project sync` without `--checkout` will
  not do: it reconciles the projection and leaves you unable to publish. The
  mechanism, the tier model and what `unit publish` refuses when the unit is not
  a checkout are specified in the `skill-manager` skill's
  `references/projects.md`.

That split is why this section belongs at a wave boundary rather than at
finalization: the ticket worktrees are still standing and their authors are
still reachable.

#### The five blocks

**The epic agent is the one writer of the loop.** Ticket agents report
upward — in the PR body, the close-out, and `## Skill changes proposed` — and
the epic agent places what they reported. That is what keeps naming stable
without a taxonomy, a merge step, or a reconciliation pass: there is only ever
one party naming things.

So this section carries five named blocks. Write every one of them, including
when the answer is `none` — `none` is a claim, and an absent block is not one.
`scripts/validate_epic_plan.py` warns, once per wave, when a committed artifact
does not show one of them, and **exits 0**: the block schema is a report, not a
gate, so there is nothing to force past.

| Block | What it records | Absent means |
| --- | --- | --- |
| **Model delta applied** | every edit the epic agent made this wave to `specs/desired_program_model`, `specs/current` and `specs/program_model`, and each `UNMODELED/<bin>` that reached `MODELABLE` and the ticket scheduled for it | nobody can tell a wave with no model delta from a wave whose delta was never applied |
| **Anchors placed** | the `<Module>.<Action>` or `UNMODELED/<bin>` anchor placed for each finding this wave produced, and the count they moved | findings were filed and never anchored, which the matrix reads as a model that is thin everywhere |
| **Improvement-card row** | this wave's row on the improvement card — the card scores the loop, not the artifact | the epic's own delta is invisible across epics, which is the thing the card exists to make visible |
| **Skill changes applied or declined** | one row per `## Skill changes proposed` row in this wave's ticket PRs: unit, what was hit, and `applied(<commit>)` or `declined(<reason>)` | a proposal with no disposition is a finding that was routed rather than consumed |
| **Model corrections owed by merged tickets** | every ticket that corrected the epic-owned `specs/tickets/<id>/desired` so its ticket could run, and the matching change to `specs/current`, `program_model` and `desired_program_model` the epic agent now owes | see below |

**On the fifth block.** It exists because the debt is real and nothing tracked
it. Twice in one epic a ticket agent corrected the epic-owned workspace so its
ticket could run — which `model_ownership_rule` explicitly permits as a *small*
correction — obliging the epic agent to make the matching change to the project
model. That change can only be committed *after* the ticket merges, so between
the two there is a window where the model and the tree disagree, and it is
observable: `BuildSkillCli` reported `accepted: false` for exactly that
interval. The rule works. What was missing was a ledger, and this is it.

A row is owed until the correction is committed. Carry an unpaid row forward
into the next wave's artifact rather than dropping it, and do not close the
epic with one outstanding — finalize.md §2 will not agree that `specs/current`
equals the target while one is.

**Applying is not reviewing.** The prohibition in §6 stands: the epic agent
does not hand-fix on the epic branch what the review surfaced in the
*repository's* code. What it applies here is the substrate — the skill files,
the validators, the plan schema — which has no ticket to re-enter through and
is the half this whole section exists to stop losing.

#### Then the recommendations that remain

Look for evidence the wave produced, not for wishes:

- a *class* of deferred findings that one schema, validator, or template change
  would have prevented — the class is the signal, not any one finding;
- a conflict key that mispredicted reality: two tickets collided under disjoint
  keys, or a declared key was never touched;
- a check every ticket agent ran by hand that belongs in the validation matrix,
  a graph, or CI;
- a goal whose instrument could not actually decide it — then the instrument is
  the architectural problem, and goals-and-evaluation.md is the authority on
  what a replacement must satisfy;
- friction each ticket agent solved locally in its own home. §1's reconciliation
  has already lifted those into the project home; report what moved, what came
  back `held-back` and how you resolved it, and — the decision that outlives
  this epic — which of them should reach other repositories through
  `unit publish` rather than stopping at this one project home.

Each row: what was observed → what shape it suggests → which door it ships
through (`unit publish`, plan amendment, new issue) → rough cost. Recommend;
do not implement. A review that starts changing things is no longer a review,
and the wave it was reviewing has moved underneath it.

### 3.5 Suggested next steps

One place where the schedule and the defect ledger are read together:

- **Ready issues for the next wave** — dependencies merged into the epic branch,
  with the goals each serves, exactly as the dispatch table in
  plan-and-schedule.md §7.
- **The deferred-findings table** — every pending entry with the three outcomes
  offered per row (promote to a ticket now, keep batched, `wontfix` with a
  reason). This *is* the between-waves triage deferment.md calls for, not a
  second one.

  | ID | Found by | Severity | Summary | Blast radius | Disposition |
  | --- | --- | --- | --- | --- | --- |

- **Goal trajectory** — per goal, the baseline, each delivered contributor's
  measured local signal against its `expected_effect`, and what that implies for
  the evaluation ticket. Say plainly when the trend suggests the target will be
  missed; that is a decision the user can still act on cheaply now and cannot
  act on at finalization.
- **What gets more expensive if deferred** — a hot spot two more tickets are
  scheduled to write, a goal whose baseline is still `unmeasured`, a unit edit
  reconciled into the project home that nobody has decided to publish.
- **Standing worktrees and headroom** — how many worktrees the epic has open,
  what they cost on disk, and how much free space is left. Every one of them
  stays until the sweep at the end, so this number only grows during the epic;
  say so before it is urgent (`worktree-lifecycle.md` §4, §6).
- **A recommendation with a default**, so that "go ahead" is a complete answer.

## 4. The diff visualization

The visualization is for orientation: the reviewer should see the wave's shape
before reading any of it. Write everything into
`<artifact_root>/wave-<n>/` and commit it to the epic branch:

```
results/epic-<slug>/review/wave-2/
  review.md      the five sections; the durable record, always present
  diff.stat      git diff --numstat "$base..$tip"
  diff.patch     git diff "$base..$tip"
  merges.md      PR, merge SHA, planned vs actual promotion position
```

plus the epic-wide worktree ledger one level up at
`<artifact_root>/worktrees.md`, updated by this wave's reconciliation
(`worktree-lifecycle.md` §4). It is epic-wide rather than per-wave because the
sweep at the end reads one file, not *n* of them.

`review.md` is committed evidence, so every claim in it stays checkable against
`diff.patch` in the same directory rather than against a command the reader has
to re-run against a tip that has since moved.

Where the agent's harness can publish a rendered page, render `review.md` and
the visuals as one self-contained page and give the user the link; the
committed markdown remains the record either way. Mermaid inside `review.md` is
the fallback and is enough.

Charts worth their space — each one answers a question, and a chart with no
question does not go in:

- **Churn by surface.** Changed lines grouped into production / TLA / adapters /
  test_graph / workflow, classified with the wave's own conflict keys. *Did this
  wave go where the plan said it would?*
- **The wave in the DAG.** The ticket graph with this wave highlighted, retired
  tickets greyed, the evaluation ticket at the terminus. *What is now unblocked?*
- **The promotion lane as merged.** Merge order and SHAs against planned
  `promotion_order`. *Did the lane hold?*
- **Goal trajectory.** Baseline, each delivered ticket's local signal, target.
  *Are we going to make it?* Label the axis as local signals — they predict the
  metric, they are not the metric, and drawing them as one is how a wave review
  starts reporting a goal the evaluation ticket has not decided.
- **Hot-spot map.** Files ranked by churn, marked for multi-ticket ownership and
  for missing coverage.

Never plot a number the epic did not measure. An `unmeasured` baseline is a gap
in the chart with a label, not a zero. Where a `dataviz` skill is installed, it
is the authority on palette, chart form, and accessibility; this file does not
restate it.

## 5. The walkthrough

"Quickly" is the specification, not a nicety — a walkthrough long enough to be
skipped has failed. Target a couple of minutes, in this order:

1. **What the wave was for** — one sentence, in goal terms, not ticket terms.
2. **The design decisions** — three to five. What was chosen, what was not, why.
   This is the only part of the review that cannot be derived from the diff: the
   diff carries the what, and the why exists nowhere else once the ticket agents
   are gone.
3. **The intuition** — what the shape says. "Almost all of it landed in the
   adapters, which is what we planned; the surprise is that the graph nodes
   barely moved." Name what surprised you. A walkthrough with no surprise in it
   usually means nobody looked at the shape.
4. **Where the bugs probably are** — the top three from §3.3, each with its
   cheapest settling experiment.
5. **What was decided for the user** — §3.2, shortest possible form, with the
   reversal cost. Overrides first.
6. **The ask** — the recommendation, the alternatives, the default.

Open the diff only where it carries the argument: the two or three hunks that
*are* the decisions, not a tour of the file list. Offer depth rather than
spending it — the artifact is written down and linked, so reading it aloud
wastes the one thing the walkthrough uniquely provides.

## 6. What a review may and may not change

**May:** amend the plan (add, retire, or re-wave tickets, re-key conflicts, bump
`schedule_revision`, re-render affected assignments); promote a deferred finding
to a ticket; change the deferment or review policy; change a goal's target as an
explicit, recorded scope decision; stop the epic.

**May not:** hand-fix on the epic branch what the review surfaced — it re-enters
through the normal ticket path (finalize.md §1a); rewrite sealed close history
or evidence; delete or reword backlog entries; resolve a merge conflict by hand;
edit a target so a measurement passes; carry a decision the user never answered
forward as though they had.

**Record the outcome.** Append the user's decision to the wave artifact and
commit it — "reviewed, proceed", "amended: <what changed>", "waived, see
review_policy". An unrecorded review is indistinguishable at finalization from a
skipped one, and the epic PR has to state which happened.

## 7. What finalization does with the wave artifacts

Wave artifacts are inputs to the epic PR body and to finalize.md §3's external
semantic-review gate — never substitutes for it. Each one reviewed an increment
against the plan at that moment; the gate reviews the whole against the default
branch.

At finalization:

- link every wave artifact from the epic PR, in order;
- carry forward every guardrail override and implicit decision the user never
  explicitly answered, into a single list in the PR body. An epic must not close
  with an override that appeared only in a wave artifact nobody responded to,
  for the same reason it must not close with a pending finding (§1a) or an
  unexplained home blocker (§1b);
- state which `review_policy` was in force, and name any wave whose review was
  waived or skipped.


## The long form of the card's load-bearing rule(s)

Moved out of `SKILL.md` by SI-29 (#391): the card keeps the rule, this page
keeps the reasons. The card's numbering is unchanged.

13. **Every wave boundary produces a review, and by default it is a gate.** After
    merging a wave and before handing out any issue URL from the next, commit a
    review artifact and walk the user through it, then stop and wait. Its fourth
    section carries **five named blocks** — model delta applied, anchors placed,
    the improvement-card row, every proposed skill change applied or declined,
    and the model corrections merged tickets still owe. Write each even when the
    answer is `none`; `none` is a claim and an absent block is not one. The user
    may change the cadence or drop the gate; record that as `review_policy`.

