# Deferment policy

Epic tickets fail in a characteristic way: validation surfaces a real defect that
sits outside the ticket's declared slice, the agent fixes it, the fix breaks a
sibling surface, and the ticket expands until its evidence no longer describes
the semantic delta it was assigned. Deferment makes the alternative explicit —
the agent **reports** the finding and the epic owner decides when it becomes
work.

The policy is agreed once, at epic creation, and applies to every ticket agent
and to finalization.

## Scope classification

Before any finding can be deferred it must be classified. A finding is
**in scope** for the current ticket only when *all* of these hold:

- every file/surface the fix touches is covered by this ticket's
  `conflict_keys`;
- the fix changes no TLA+ action, invariant, or adapter mapping outside this
  ticket's declared semantic delta;
- the ticket's own desired model already implies the corrected behavior.

Anything else is **out of scope**, including: defects in already-promoted
sibling tickets, latent bugs the ticket merely exposed, missing coverage on
untouched surfaces, flaky infrastructure, and refactors the fix would be
"cleaner" with. Out-of-scope findings are candidates for deferment. In-scope
findings are simply the ticket's work — fix them and say nothing about
deferment.

A finding is **blocking** when the ticket's REQUIRED validation matrix cannot
pass without touching an out-of-scope surface. Blocking out-of-scope findings
are never silently deferred and never silently fixed: the agent stops and
returns the ticket to the epic owner (see *Escalation*).

## Policy record

Set once during planning, stored in `specs/desired_program_model/ticket_plan.yaml`
next to `schedule_revision`:

```yaml
deferment_policy:
  mode: batch            # batch | ask | inline
  blocking: escalate     # escalate | ask   (blocking findings only)
  budget: 5              # max deferred findings per ticket before the agent stops
  backlog: "specs/desired_program_model/deferred_findings.yaml"
  per_ticket_backlog: "specs/results/deferred/{ticket}.yaml"   # see below
```

### `per_ticket_backlog`: partition the file, or schedule the collisions

`backlog` alone is one mutable file that every ticket in a wave appends to, and
that is **a shared mutable namespace with no per-agent partition, where
collision is certain rather than careless.** Measured: four tickets in one wave
appending rows to the end of one 45-row cumulative ledger from the same base
produced four reconciles, one ticket twice. Every branch showed zero deleted
lines — the instruction to re-fetch worked — and not one of them could avoid
the conflict.

`conflict_keys` cannot express this, which is why it keeps happening past a
validated schedule: each ticket legitimately owns only *its own rows*, and no
lane name partitions the inside of a file.

Set `per_ticket_backlog` to a path template containing `{ticket}`. Each agent
appends **only** to its own rendered path, the cumulative `backlog` stays the
canonical thing readers and sealed `filed_as` references point into, and the
epic agent concatenates the wave's per-ticket files onto it at wave close —
which is an append nobody contends, not a resolution.

**Not a union merge driver**, and the reason is the one that matters: a union
driver silently produces a valid-looking file when it is wrong. That is the
same shape as the defect it would be papering over — a check whose negative
result is indistinguishable from not having looked — so it trades four visible
reconciles for one invisible corruption. A per-ticket file makes the merge a
no-op instead; the judgement is recorded here because it was argued from a
wave that paid for both halves.

`validate_epic_plan.py` warns when any wave carries more than one ticket and no
`per_ticket_backlog` is set, and exits 0. A single-ticket-per-wave epic does
not need one.

Modes:

- **`batch`** (default, recommended) — the agent records every out-of-scope
  finding to the backlog and continues its assigned slice. No interruption, no
  inline fixes. The owner triages the backlog between waves and at finalization.
- **`ask`** — the agent records the finding, then asks the owner whether to open
  a ticket now or batch it. Use when the epic touches load-bearing surfaces and
  a latent defect changes the plan.
- **`inline`** — the agent may fix out-of-scope findings within its own conflict
  keys' blast radius, and must still record what it fixed and why. Use only for
  small epics with a single active ticket; it reintroduces the spiral in
  parallel waves.

`budget` is the anti-spiral guard and applies in every mode. When a ticket
accumulates more than `budget` out-of-scope findings, the agent stops
implementing, files the backlog entries, and reports that the ticket's premise
looks wrong. Repeated deferrals are a signal that the plan is off, not a queue
to drain.

The canonical plan is authoritative for the policy. Assignments mirror it for
readability, but a ticket agent re-reads the plan entry before acting on it, so
the owner may change the policy mid-epic without bumping `schedule_revision` or
invalidating dispatched assignments.

## Backlog format

`specs/desired_program_model/deferred_findings.yaml` is append-only. Agents add
entries; only the epic owner edits `disposition`, except the ticket-agent flip
in step 6 below.

```yaml
findings:
  - id: DEF-003                      # sequential, never reused
    found_by: "<ticket-id>"
    found_at_commit: "<sha>"
    schedule_revision: 3
    severity: blocking | major | minor
    surface:
      production: ["<path>"]
      tla: []
      adapters: []
      test_graph: []
    summary: "<one line: what is wrong>"
    reproduction: "<exact command + observed vs expected>"
    evidence: ["<path under the ticket evidence root>"]
    why_out_of_scope: "<which conflict key or semantic boundary it crosses>"
    suggested_fix: "<one line, or 'unknown'>"
    blast_radius: "<other tickets/surfaces a fix would touch>"
    disposition: pending             # pending | ticketed | wontfix | fixed-inline | fixed
    fixed_at: null                   # commit that fixed it, when disposition is fixed
    disposition_ticket: null         # spec ticket ID once promoted
```

An entry with no reproduction is not a finding, it is a hunch — do not file it.

## The epic ledger and the closure census

Per-ticket files drift: in one measured reconciliation 10 rows still read open
after their fix had merged, 20 were closed by a later ticket than the one that
recorded them, and one finding was filed again under a new id. The ledger is the
one place the epic's findings and their closures meet, and the tooling writes it.
Script: `scripts/census.py` (`--epic <name>` when no live plan names one).

- **Kickoff.** `census.py init` creates `specs/results/<epic>/deferred-ledger.yaml`
  (or the plan's `deferment_policy.ledger`).
- **Recording.** `census.py record --ticket <id> --summary ... --reproduction ...`
  gives the finding its id at once, `<ticket>-DF-NN`. With `per_ticket_backlog`
  the row goes to the ticket's own file, so parallel tickets never contend for
  the ledger; without it the row goes straight into the ledger. A finding seen
  before is recorded with `--duplicate-of <original id>`.
- **Wave close.** `census.py absorb` copies per-ticket rows the ledger lacks into
  it, ids unchanged.
- **Closing.** A ticket that fixes findings lists them in
  `specs/tickets/<id>/closure.yaml` (or `close ticket --closure <path>`):

  ```yaml
  closed: [BS-02-DF-01]        # this ticket's fix closes it
  review_closed: [BS-03-DF-02] # closed by the review of this ticket
  also: [BS-07-DF-04]          # fixed in passing
  ```

  `tla-spec-dev close ticket` marks those ledger rows (`disposition: fixed`,
  `closed_by`, `closed_as`, `closed_on`), keeps the closure at
  `<ledger dir>/closures/<ticket>.yaml`, and records both in the receipt as
  `deferred_ledger`. An id the ledger lacks, or no ledger at all, is a warning
  in the receipt: close never blocks on the ledger.
- **Census.** `census.py` (or `census.py check`) counts `closed`,
  `review_closed`, `also` and closed-by-a-later-ticket over every kept closure,
  and fails (exit 1) on: `unabsorbed` (a per-ticket row the ledger lacks),
  `drift` (a per-ticket file and the ledger disagree on open/closed, or a
  disposition it cannot read), `fixed_but_open` (an open row a merged closure
  already closes), `dangling_duplicate`, and `closure_unknown_id`. No ledger is
  exit 2; an empty ledger with no closures and no per-ticket rows is exit 3, the
  vacuum, because a census that reconciled nothing is not green. `--force` or
  `SKILL_GATES=off` prints everything and exits 0.
- **After workflow close** the live plan is gone; the census then reads
  `specs/.history/<epic>/closed-snapshot/.../ticket_plan.yaml` and says so.

Open dispositions: `pending`, `open`, `ticketed`, `routed`. Closed: `fixed`,
`fixed-inline`, `wontfix`, `duplicate`, `consumed`, `closed`. Free text in
`disposition` is drift: put the prose in a note field.

## Ticket-agent behavior

1. Classify the finding. In scope → fix it as ordinary ticket work.
2. Out of scope and blocking → apply `deferment_policy.blocking`.
3. Out of scope and non-blocking → append a backlog entry, then follow
   `deferment_policy.mode`. In `batch`, continue. In `ask`, ask now-or-batch. In
   `inline`, fix only within the ticket's conflict keys and set
   `disposition: fixed-inline`.
4. Commit backlog entries with the ticket's normal commits. The backlog is
   planning data, not spec state: it never enters ticket-local `desired/` or
   `current/`, and it is never evidence for a ticket close.
5. Report deferred findings in the ticket PR body under a
   `## Deferred findings` heading, one line per ID.
6. If your change fixes a finding filed by ANOTHER ticket, flip its row in the
   same commit: `disposition: fixed`, `fixed_at`, and the test that now pins it.
   Where `per_ticket_backlog` keeps you out of the cumulative file, put
   `DEF-<n> fixed at <sha>, pinned by <test>` under `## Deferred findings` so the
   epic agent flips it at wave close. A commit message naming the finding does
   not update the backlog, and the planner reads the backlog, not the log.

A deferred finding never justifies weakening a REQUIRED validation entry,
loosening an invariant, marking a test skipped, or closing a ticket whose
equality gate fails.

## Escalation

When a blocking out-of-scope finding appears and `blocking: escalate`, the agent:

- stops implementation at the current commit;
- files the backlog entry with `severity: blocking`;
- pushes the branch without closing the spec ticket or opening a promotion PR;
- reports: the finding, the ticket it blocks, the surfaces a fix would touch,
  and which sibling tickets share those conflict keys.

The epic owner then either inserts a repair ticket ahead of it in the promotion
lane, rescopes the blocked ticket's conflict keys, or drops the ticket. The
agent does not make that call, and does not "unblock itself" by widening scope.

## Owner triage

Triage the backlog at two points.

**Between waves, when recommending the next issue.** Present pending findings
alongside the ready issue list so the owner sees defects and schedule together.
That presentation is a section of the wave review artifact, not a separate
message — `references/human-review.md` §3.5, where it sits next to the hot
spots, the overrides, and the goal trajectory that give each finding its weight:

| ID | Found by | Severity | Summary | Blast radius | Disposition |
| --- | --- | --- | --- | --- | --- |

For each pending finding, offer exactly three outcomes: promote it to a new
spec ticket now (new stable ID, dependency edges, wave, promotion order,
conflict keys, revalidated schedule, `schedule_revision` bump, new issue), keep
it batched for finalization, or close it `wontfix` with a recorded reason.
Recommend batching unless the finding blocks a planned ticket or grows more
expensive the longer it sits.

Before scheduling a finding as a fix, re-run its `reproduction` on the
dispatch base and record the result in the assignment. A row is a claim about
the code, and the code moves without it. A finding that no longer reproduces is
not scheduled: find the commit that fixed it, flip the row to `fixed` with that
`fixed_at`, and schedule only the residual, if any.

Promoting a finding is an ordinary plan change: add the ticket, rerun
`scripts/validate_epic_plan.py`, bump `schedule_revision`, re-render affected
assignments. Never retrofit a deferred fix into a dispatched ticket's scope.

**At finalization.** No pending findings may remain. Every entry ends as
`ticketed` (and merged), `wontfix` (with a reason), `fixed-inline`, or `fixed` (with `fixed_at`). Findings
carried past the epic become issues on the default branch, referenced from the
epic PR body — deferring is a scheduling decision, not a way to lose defects.
