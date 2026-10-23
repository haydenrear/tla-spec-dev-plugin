# Spec Workflow History

`specs/.history/<workflow-name>/` is append-only history for one
desired/current workflow. It exists so active context can stay small while old
decisions remain auditable.

## Mentality

The active workspace is mutable:

- `specs/program_model`: accepted whole-program baseline.
- `specs/desired_program_model`: target whole-program state and ticket plan.
- `specs/current`: executable whole-program state that has landed so far.
- `specs/tickets/<ticket-id>`: active ticket-local current/desired workspace
  for one parallelizable ticket.
- `specs/results`: current TLC, generated-case, adapter, and graph evidence,
  plus the append-only `complexity_ledger.json` and the `skill_feedback.md`
  retro document written at close time.

The history directory is append-only by convention:

- Never edit an existing history entry.
- Never overwrite a ticket or closed-workflow snapshot.
- Create a new explicit entry only when new evidence needs another checkpoint.
- Commit history entries with the related spec changes.
- Close commands leave filesystem permissions writable so normal git operations
  keep working.

The ticket source of truth is
`specs/desired_program_model/ticket_plan.yaml`. Do not invent or require
repository-level Markdown files per ticket.

## Layout

Per-ticket closes:

```text
specs/.history/
  <workflow-name>/
    ticket-000-<ticket-id>/
      manifest.json
      summary.md
      snapshots/
        program_model/
        desired_program_model/
        current/
      ticket/
        ticket.yaml
        current/
        desired/
        results/
        testgraph/
      results/
```

Owner-directed ticket retirements use a different entry kind and directory
prefix so no reader can mistake a scheduling decision for successful delivery:

```text
specs/.history/
  <workflow-name>/
    retired-ticket-000-<ticket-id>/
      manifest.json
      summary.md
      ticket/                         # only when an active workspace existed
```

The optional `ticket/` tree is preserved as explicitly unaccepted work. A
retirement entry has no model snapshots, accepted results, complexity-ledger
entry, semantic promotion, or validation claim.

Whole-workflow close:

```text
specs/.history/
  <workflow-name>/
    closed-snapshot/
      manifest.json
      summary.md
      deferred_findings.yaml
      snapshots/
        program_model/
        desired_program_model/
        current/
      results/
```

`manifest.json` is the machine-readable index. `summary.md` is the human
overview. The copied snapshots are evidence, not active state.

`deferred_findings.yaml` is the cumulative findings ledger, archived here
because the close removes the directory it lives in. It is cross-epic and
append-only, so this copy is the record of every finding filed up to the close,
not just this workflow's. The manifest names it under `findings_ledger`, and
`scripts/disposition.py` reads it once the live path is gone.

## Preparing For Promotion

A ticket close promotes the ticket `desired/` onto the project `current/`, so
before closing you must decide what the accepted state is. Promotion is not a
blind replace: a project-`current` path is removed only when it was seeded
into the ticket workspace (recorded in the ticket's `ticket.yaml` seed
manifest at `open ticket` time) and the ticket then dropped it. Current-only
paths the ticket was never seeded with are preserved, and every removal and
preservation is enumerated in the close output and manifest.

### When project current moved under the ticket

`open ticket` records the sha256 of every seeded file in `ticket.yaml`
(`seed_manifest.desired_sha256`). At close, per seeded file:

| Ticket | Project `current/` since open | Close |
|---|---|---|
| unchanged | changed | keeps project `current/` |
| changed | unchanged | takes the ticket |
| changed | changed | **three-way carry** |
| dropped | changed (or the reverse) | refuses by name: a deletion has no lines to merge |

The three-way carry runs `git merge-file --diff3` with base = the seed blob
(the committed `specs/current/<file>` whose sha256 is the recorded digest,
found in the repository's history or index), ours = project `current/` now,
theirs = the ticket's `desired/` (and `current/`, when the ticket keeps both).
A clean merge is written to the ticket, the digest is re-recorded and the
rebase is noted under `seed_manifest.rebased`, and `run spec-unit-tests` runs
on the merged ticket model before the close writes anything else. The history
manifest records it as `three_way_carry`.

It refuses, with nothing written, when:

- a file conflicts — every file and hunk is named, with what each side holds;
- no commit or index entry holds the seed bytes — the merge base is unknown;
- spec-unit fails on the merged model — every carried byte is restored.

Resolve the named hunks in the ticket model and re-run the close. Do not copy
project `current/` over the ticket's model or re-record digests by hand: in
commit-diff-context-parent #462 that copy dropped MS-015's TLA invariants while
its spec test was promoted, and across three epics 2 of 16 such hand carries
shipped a regression. The carry is the default because a flag the close needed
every time a predecessor promoted would be a flag everyone has to remember.
It does not run TLC; run `scripts/run_tlc.sh` on the merged model when the
merge touched a `.tla` file whose spec-unit tests do not.

- The default close requires ticket-local `current/` to *semantically match*
  `desired/`. Semantic comparison covers `.tla`, `.cfg`, `.yaml`/`.yml`, `.py`,
  `.toml`, and `.json` files; planning files (`README.md`, `ticket_plan.yaml`,
  `desired_state.yaml`, `ticket.yaml`) and `status`/`notes`/`promotion`
  metadata keys are ignored. They do **not** need to be byte-identical — only
  semantically equal.
- To prepare, edit `current/` (the TLA+ modules, model `.yml`, adapters, and
  tests) until it matches `desired/`, re-run `tla-spec-dev run spec-unit-tests`,
  then close.
- If the ticket `desired/` already *is* the intended accepted state and you do
  not want to hand-reconcile `current/`, pass `--accept-new`. That overwrites
  ticket `current/` from `desired/` before promotion, so no divergence check is
  needed. The whole-workflow close accepts `--accept-new` the same way to adopt
  `desired_program_model/` as the new `current/` and `program_model/`.

The same applies to the whole-workflow close, which requires `current/`,
`desired_program_model/`, and the promoted `program_model/` to converge
(the whole-workflow comparison covers `.tla`, `.cfg`, `.yaml`/`.yml` files
only).

Both closes also run the complexity ledger (MF-019): a ticket close reads the
ticket's `results/complexity_ledger.yaml` input (scaffolded by `open ticket`),
and the workflow close reads `specs/results/complexity_ledger_input.yaml`. It
is advisory. It appends an entry (recorded or rejected) to
`specs/results/complexity_ledger.json` and prints one warning line when it
rejects — unfilled input, no refinement record or narrative, an unjustified
increase, or an unevidenced decrease — and the close proceeds. A model or
input it cannot read skips the measurement with one warning line.

Every other close refusal (ticket status, receipts, current == desired) can
be skipped with `--force` or `SKILL_GATES=off` (alias `SPEC_GATES=off`). Each
skipped refusal prints one line, and the receipt's `guard_weakening.force`
records it. Path confinement, symlink workspaces, and overwriting an existing
history entry are never skipped.

The coverage audit was a sixth refusal — at workflow close, on anything but
`pass`, with no override — until 2026-08-04. Its verdict is still recorded and
printed at every close, `fail` and `incomplete` included; it stops nothing. See
`references/coverage_audit.md`, "Status".

## Per-Ticket Close

First create and work in a ticket-local directory:

```bash
tla-spec-dev --spec-root specs open ticket TICKET-123
```

When `specs/tickets/TICKET-123/current` semantically equals
`specs/tickets/TICKET-123/desired`, mark the ticket closed in
`specs/desired_program_model/ticket_plan.yaml`. Then run:

```bash
tla-spec-dev --spec-root specs close ticket TICKET-123 \
  --summary "Captured ticket-level desired/current history" \
  --result specs/results/tlc.txt \
  --result specs/results/adapter.txt
```

The command reads the matching ticket mapping from `ticket_plan.yaml`,
evaluates the complexity-ledger gate against the ticket's filled-in
`results/complexity_ledger.yaml`, writes the ticket mapping and ledger record
into the manifest, snapshots the project model directories, moves the active
ticket directory into the history entry, promotes ticket `desired/` onto
project `specs/current` (removing only seeded paths the ticket dropped,
preserving unseeded current-only paths), merges ticket-local Test Graph
artifacts into project specs, and recommends committing the created history
entry together with the ledger and skill-feedback files it wrote.

To accept the ticket `desired/` as the new `current/` without hand-reconciling
a divergent `current/`, add `--accept-new`:

```bash
tla-spec-dev --spec-root specs close ticket TICKET-123 --accept-new \
  --summary "Accepted ticket desired state as current"
```

`--accept-new` overwrites ticket `current/` from `desired/`, skips the
`current == desired` gate, and records `accept_new` in the entry manifest.

## Per-Ticket Retirement

Retirement is for an already-dispatched ticket the owner has decided not to
deliver in this workflow. It is not a weaker successful close and it does not
mean the proposed ticket state was accepted.

Keep the ticket mapping at its original ordinal, bump the plan schedule
revision under the epic workflow's amendment rules, and replace its working
status with this terminal shape:

```yaml
- id: TICKET-123
  # The rest of the dispatched ticket mapping remains in place.
  status: retired
  retirement:
    schedule_revision: 4
    resolution: carried              # carried | superseded | abandoned
    reason: "Owner-approved reason the dispatched work is not delivered here."
    decided_by: "owner identity"
    decided_at: "2026-08-12T12:00:00Z"
    receipt: specs/.history/<workflow>/retired-ticket-000-TICKET-123/manifest.json
    successor_issue: "https://github.com/owner/repo/issues/456"  # carried requires both
    successor_workflow: successor-workflow
    affected_goals:
      - goal: GOAL-1
        disposition: carried         # accepted_missed | accepted_unmeasured | carried
        reason: "This goal is decided by the successor workflow."
        successor_issue: "https://github.com/owner/repo/issues/456"
        successor_workflow: successor-workflow
```

`retirement.schedule_revision` must be a positive integer no newer than the
plan's current root schedule revision. It seals the revision at which the owner
made the decision, so later schedule amendments do not invalidate an older
append-only receipt. `reason`, `decided_by`, and `decided_at` are required. A
ticket-level `carried` resolution requires both
`successor_issue` and `successor_workflow`. `affected_goals` is required and
may be empty in a workflow with no epic goals; this tool preserves the list
exactly in the receipt, while the owning epic workflow validates each goal's
disposition and successor. The receipt path is canonical: it uses the ticket's
zero-based immutable plan ordinal, padded to three digits.

Git epic workflows use the repository's canonical `specs` root, so their
receipt always begins `specs/.history/`. The underlying CLI preserves its
existing custom `--spec-root` support for non-epic workflows and derives the
same repository-relative receipt under that explicit root.

Then run:

```bash
tla-spec-dev --spec-root specs retire ticket TICKET-123
```

The command validates the complete owner decision before writing anything,
refuses to overwrite an entry, refuses a ticket that already has a successful
close receipt, and moves any active ticket workspace beneath the retirement
entry without accepting it. Its manifest records, exactly:

```json
{
  "entry_kind": "ticket-retirement",
  "semantic_promotion": {"performed": false},
  "validation": {"claimed": false},
  "promotion": null,
  "complexity_ledger": null
}
```

`close ticket` refuses `status: retired`, even under `--allow-open`, unless
`--force` is passed.
Whole-workflow close recognizes a retirement only when the canonical receipt
exists and its ticket identity, complete retirement block, no-promotion field,
no-validation field, and empty accepted snapshot/result lists exactly match the
plan. Writing `status: carried`, `status: superseded`, or `status: abandoned`
directly does not make a ticket terminal.

A terminal receipt is irreversible. Its identity is the workflow history root
plus the ticket's immutable zero-based ordinal and id, not its directory name
or the plan's later mutable status. `close ticket` refuses an existing
retirement receipt even if the plan was edited back to `done`; retirement
refuses an existing successful-close receipt. Whole-workflow validation rejects
a delivered status after retirement, a retired status after successful close,
and any identity for which both receipt kinds coexist.

## Whole-Workflow Close

After `current`, `desired_program_model`, and promoted `program_model` converge,
run:

```bash
python scripts/close_tickets.py \
  --repo-root . \
  --summary "Promoted desired/current into program_model"
```

This writes `closed-snapshot` under the workflow history directory before
removing `current` and `desired_program_model`. Every delivered ticket must
have both a successful terminal status and exactly one matching successful-close
receipt (workflow, immutable ordinal, ticket identity, and terminal status);
every retired ticket must have the exact
canonical retirement receipt described above. It requires the
workflow-close ledger input at `specs/results/complexity_ledger_input.yaml`.
That input carries a `coverage_audit` block, which is recorded and printed but
(since 2026-08-04) refuses nothing — `pass` is still the only value meaning
"the surface was walked and no in-scope gap was found".

If `current`, `desired_program_model`, and `program_model` have not been
hand-reconciled but `desired_program_model` is the intended accepted state, pass
`--accept-new` to promote its semantic files into `current` and `program_model`
before the snapshot (tickets must still be marked closed):

```bash
python scripts/close_tickets.py --repo-root . --accept-new \
  --summary "Accepted desired_program_model as the new program_model"
```

When the plan contains any retired ticket, `--accept-new` is deliberately
narrower. The current `desired_program_model` must be byte-for-byte identical
to the archived desired snapshot in the one successful close receipt for the
terminal delivered ticket (the unique greatest `promotion_order`, or the final
delivered ordinal when no orders are declared). That receipt must match the
final plan's workflow, immutable ordinal, ticket identity, and a terminal
status. A forced or `accept_new` terminal close still qualifies; its receipt
records that in `guard_weakening`. This lets a final
evaluation ticket authorize promotion while preventing withdrawn ticket state
from becoming the program model merely because its schedule was retired.

## Searching History

Start with summaries and manifests:

```bash
rg -n "TICKET-123|CreateWorkspace|LimitInvariant|resource-name" specs/.history
find specs/.history -name manifest.json
```

Then open only the copied snapshot paths referenced by relevant manifests.
Avoid reading every historical snapshot by default; the point of the
append-only log is selective retrieval.

## Commit Rule

After each close, commit the specific history directory with the related spec
changes:

```bash
git add specs/.history/<workflow-name>/ticket-000-TICKET-123 specs
git commit -m "record spec history for TICKET-123"
```

For whole-workflow close-out, commit the final spec, closed ticket plan, and
`closed-snapshot` together. The scripts print a recommended command, but the
reviewer should still inspect the staged scope before committing in production
repositories.
