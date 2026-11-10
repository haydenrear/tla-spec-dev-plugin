# ESD-05 (#239): route evidence and graph-risk review into the role paths

Instruction-only. No script, validator, schema field, role, approval round or
artifact was added. The assignment schema the validator enforces is unchanged;
the additions to `epic-ticket.md` are prose bullets of the rendered assignment.

## What changed, by role

| role | entry point it already reads | added | canonical source it now links to |
| --- | --- | --- | --- |
| all | spec-double-2 `references/agent_roles.md` | § *Evidence routing*: one role → trigger → minimum evidence → decision → output → next consumer table; one line in each role's *You read* | — (the table only routes) |
| epic: planning | git-epic-workflow `SKILL.md`, `plan-and-schedule.md` §3, §7 | reference-map rows for `step-sizing.md` and `validation-review.md`; §3 *bounded evidence slice*; §7 states both estimates, batch, cadences, confidence, cold-start gaps, eval cost | `bug_attribution.md` §6a, §7d; `graph-architecture-review.md`; `step-sizing.md` §1–§5, §7 |
| ticket (epic) | the rendered assignment in the issue body (`epic-ticket.md`) | **Evidence slice** bullet; delivery line in the review-input bullet and §7 | `graph-architecture-review.md` *A graph change is a product change*; `bug_attribution.md` §4.3; `step-sizing.md` §8 |
| ticket (ordinary) | `complete.md` §5 PR template; issue template *Discovery notes* | `started_at` delivery line; *Risk evidence* line | `bug_attribution.md` §4.3; `step-sizing.md` §1 |
| review | `human-review.md` §3 | §3.1 rank 6 (graph/oracle/recovery contracts; evidence provenance); §3.3 validation-specific bugs | `graph-architecture-review.md` A–H; `bug_attribution.md` §6, §6a |
| epic: wave owner | `human-review.md` §3.4, §3.5 | owner + disposition per recommendation; *Delivery velocity and step size* block (the section `validation-review.md` *Deeper review* already required) | `step-sizing.md` §6 |
| epic: finalizer | `finalize.md` §2c, §5 | *Next epic's starting estimate*, keyed to repo/component/model, with unresolved uncertainty; listed in the epic PR body. Integrated graph and manual acceptance sequence unchanged | `validation-review.md` *Across epics*; `step-sizing.md` |

## Routed deferred rows closed here

| id | what | where fixed |
| --- | --- | --- |
| `ESD-01-DF-01` | no record timestamps the start of ticket work | `started_at` in the delivery line: `epic-ticket.md` (assignment bullet and §7), `complete.md` §5 |
| `ESD-04-DF-01` | no record names reviewer/verifier model and version | `agent:` in the delivery line; reviewer/verifier model in `human-review.md` §3.5 |
| `ESD-04-DF-02` | `step-sizing.md` not in `git-epic-workflow/SKILL.md`'s reference map | reference-map row (plus one for `validation-review.md`, which was also missing) |
| `ESD-04-DF-03` | no record states a batch's scope-item count | `scope items:` in the delivery line; batch scope items in `human-review.md` §3.5 |

Each is `disposition: fixed`, `disposition_ticket: ESD-05` in both
`../deferred-ledger.yaml` and its per-ticket inbox.

## Reconciliation: main, installed copy, bug-sweep

| copy | revision | role-path files vs main `a1ff56cf` |
| --- | --- | --- |
| `~/.skill-manager/plugins/tla-spec-dev/skills` | HEAD `a1ff56cf` | identical (only build caches under `test-graph/project_sdk_sources/build-logic` differ) |
| `~/.skill-manager/plugin-marketplace/plugins/tla-spec-dev/skills` (the copy this session loaded) | — | identical, same caveat |
| this worktree's `.skill-manager` home | — | identical, same caveat |
| `origin/epic/bug-sweep` (`67e8aa6a`) | merged to main as #250 | none of the files under ESD-05's keys differ; main is ahead in `test-graph` (`workflows.md` +19 project-lock lines, `_common.py`/`run.py`/`discover.py`) and `skill-manager/references/projects.md` (2 lines) |

**Material divergence:** none between main and the installed copies. The
divergence that matters is the epic's own: `step-sizing.md`,
`graph-architecture-review.md`, the ESD-02 sections and all of ESD-05's routing
exist only on `epic/evidence-sized-delivery` and reach installed homes when the
epic merges and the plugin is synced. An eval home built from the installed
plugin measures main for both arms (`ESD-05-DF-02`, for ESD-06).

Commands:

```bash
git archive a1ff56cf skills | tar -x -C <scratch>
diff -rq <scratch>/skills ~/.skill-manager/plugins/tla-spec-dev/skills -x __pycache__ -x test_graph
diff -rq <scratch>/skills ~/.skill-manager/plugin-marketplace/plugins/tla-spec-dev/skills -x __pycache__ -x test_graph
git diff --stat a1ff56cf origin/epic/bug-sweep -- skills
```

## Reading burden

Per-role table and the walk-through: `local-signal.md`. Counts are `wc -l` over
`git show <rev>:skills/<path>` for the files each role's *You read* list names
(`agent_roles.md`), plus that role's own section and the routing section of
`agent_roles.md` (awk from the `## <role>` heading to the next `## `), plus, for
the epic ticket, the rendered assignment block (`epic-ticket.md` between the
`assignment:start`/`end` markers). Revisions: `a1ff56cf` (main), `54241b36`
(epic base), working tree (tip).

## No-op model result

`specs/current`, `specs/desired_program_model` and `specs/program_model` are
unchanged. The change is instruction prose and evidence; it alters no state,
guard, effect, invariant, interleaving, resource ownership or External surface
(`bug_attribution.md` §7d: prose is a no-op model result). The epic agent closes
the spec ticket.

## Validation

| entry | result | output |
| --- | --- | --- |
| `validation.repository_unit` | 407 passed, 1 skipped | `repository-unit.txt` |
| `validation.spec_unit` | 54 passed, 2 failed: the 2 known base failures (`baseline/spec-unit.txt`), no new failure | `spec-unit.txt` |
| `skill-manager unit validate` on `git-epic-workflow`, `spec-double-2`, `git-issue-workflow`, `git-issue` | all clean | `unit-validate.txt` |
| `validation.tlc`, `graphs` | N/A per assignment (no model delta; prose has no graph proof) | — |
