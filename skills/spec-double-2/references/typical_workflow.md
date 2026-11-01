# Typical Workflow

Use one accepted whole-program model as the durable baseline. Use
`current` and `desired_program_model` only during active ticketed behavior
changes.

## 1. Onboard A New Repository

When a repository has no accepted program model yet, create only the baseline:

```bash
tla-spec-dev --repo-root path/to/repo --spec-root specs scaffold project --name ProjectName
```

This creates:

- `specs/program_model`: accepted whole-program semantic baseline.

Do not create `specs/current`, `specs/desired_program_model`, or
`ticket_plan.yaml` during first onboarding.

If the repository keeps specs outside `specs`, pass the same spec root to later
onboarding and ticket workflow commands:

```bash
tla-spec-dev --repo-root path/to/repo --spec-root project_specs scaffold project --name ProjectName
tla-spec-dev --repo-root path/to/repo --spec-root project_specs scaffold workflow TICKET-123 "Ticket title"
```

## 2. Start A Feature Or Behavior Change

After `program_model` exists, start the ticket workflow:

```bash
tla-spec-dev --repo-root path/to/repo --spec-root specs scaffold workflow TICKET-123 "Ticket title"
```

This resolves directories under `--spec-root`, defaulting to `specs`, and
creates:

- `specs/current`: executable whole-program model of what has landed so far.
- `specs/desired_program_model`: target whole-program model plus ticket plan.
- `specs/desired_program_model/ticket_plan.yaml`: phases, tickets,
  dependencies, acceptance criteria, validation commands, and evidence slots.

The scaffold copies useful baseline files from `program_model` into both
workflow directories before adding ticket metadata. `current` should start as
the whole accepted model, not as a feature-only projection.

## 3. Work Ticket By Ticket

For each ticket or implementation slice:

1. Scaffold a ticket-local workspace from the plan:

```bash
tla-spec-dev --repo-root path/to/repo --spec-root specs open ticket TICKET-123
```

This creates `specs/tickets/TICKET-123/desired` (a copy of project `current`),
`results`, any copied Test Graph configuration, a `ticket.yaml` recording
lifecycle metadata plus the seed manifest of project-`current` paths copied
into the workspace, and a `results/complexity_ledger.yaml` ledger input.
The ledger input is advisory; an unfilled one is recorded and the close
proceeds. Ticket `desired` is the whole-program state at the end of this
ticket, not the whole project destination. Pass `--with-current` to also seed
a ticket-local `current/` for the older two-directory loop.

2. Update `specs/tickets/TICKET-123/desired` so it represents the expected
   post-ticket whole-program state: TLA+ and configs, plus spec-unit
   adapters/tests and Test Graph bindings when the project has that layer.
   Run TLC on it once.
3. Update production code.
4. Keep `desired_program_model/ticket_plan.yaml` synchronized with changes in
   scope, order, dependencies, and acceptance criteria.
5. Run TLC and, when the project has them, generated adapter tests and Test
   Graph validation. Use the shipped CLI for spec-unit validation:

```bash
tla-spec-dev --repo-root path/to/repo --spec-root specs run spec-unit-tests --ticket TICKET-123
```

6. Record validation evidence in the ticket `results/` directory, manifests, or
   ticket status.
7. Mark the ticket `done` in `ticket_plan.yaml`, then close the ticket:

```bash
tla-spec-dev --repo-root path/to/repo --spec-root specs close ticket TICKET-123 --result path/to/repo/specs/results/tlc.txt
```

Closing promotes ticket `desired/` (with `--with-current`, a divergent
`current/` is accepted as `desired/` under `--force` and recorded), records a
complexity-ledger entry from the ticket's filled-in
`results/complexity_ledger.yaml` (advisory: a missing input skips the
measurement, and an input with TODO sentinels, no refinement record or
narrative, an unjustified increase, or an unevidenced decrease is recorded as
rejected with one warning line — the close still proceeds), promotes ticket
`desired/` onto project-level `specs/current` (removing only seeded paths the
ticket dropped and preserving current-only files the ticket was never seeded
with), merges ticket-local Test Graph artifacts into project specs, and moves
`specs/tickets/TICKET-123` into history. A file both the ticket and project
`current` changed since open is merged three ways first, and spec-unit re-runs
on the result (`spec_evolution.md`, "When project current moved under the
ticket").

Do not model tests, CI jobs, test graph nodes, integration harnesses, or
validation workflow mechanics as TLA+ program state/actions. Record them as
evidence for semantic program actions.

Repeat until project `current` semantically equals `desired_program_model`.

## 4. Close The Ticket Workflow

When the desired model has landed:

1. Promote the converged model into `program_model`.
2. Regenerate accepted artifacts from `program_model`.
3. Run accepted program-model validation.
4. Close the temporary workflow directories and record `closed-snapshot` under
   `specs/.history/<workflow-name>/`:

```bash
python scripts/close_tickets.py --repo-root path/to/repo
```

Use the same `--spec-root` used to scaffold the workflow when it is not
`specs`.

`close_tickets.py` validates that:

- semantic model files in `current` and `desired_program_model` match;
- semantic model files in `desired_program_model` and `program_model` match,
  proving promotion happened;
- every ticket in `desired_program_model/ticket_plan.yaml` has a closed status.

It ignores planning/status-only fields for manifest comparison, but it does not
ignore open tickets.

The snapshot step also records a workflow-scope complexity-ledger entry from
`specs/results/complexity_ledger_input.yaml`. That input must exist and pass
the ledger gates. Its `coverage_audit` status is recorded and printed at every
close and refuses none of them (changed 2026-08-04); `pass` still means "the
surface was walked and no in-scope gap was found", so run
`prompts/coverage_audit.md` if you want that read.
