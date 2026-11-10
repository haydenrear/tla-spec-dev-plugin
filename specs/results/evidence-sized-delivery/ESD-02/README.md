# ESD-02: TLA+ architecture anchors and attribution of validation defects

Ticket #236 (epic #234, `evidence-sized-delivery`), wave 2. The base was `515f0af4`, which
contains the merged ESD-01. This ticket changes instructions and evidence only. It adds no
script, parser, validator, schema enforcement or gate.

## What changed

| File | +/- lines | What |
|---|---|---|
| `skills/spec-double-2/references/bug_attribution.md` | +177 / -6 | §2: note that the fifth direction is resolved. **§4.3** (new): origin, channel and effect are three separate axes. §6a: instrument defects anchor to a validation bin, and **"Resolved from audited records"** gives the false-red shape from BS-07-DF-05. §7b: the migration map for rename, split, merge and absorb. **§7d** (new): the model as anchor (the map a finding lands on, the validation-infrastructure area, model update vs no-op, and what TLC can and cannot establish). **§7e** (new): five worked examples, each an ESD-01 row. |
| `skills/discovery/SKILL.md` | +33 / -2 | A skill-import of `bug_attribution.md` (frontmatter `description` unchanged). The ticket output names the findings at the touched anchors, or a no-op model result. A new section, "The model is the architecture anchor, not a test transcript". One reference-map row. |
| `skills/discovery/references/` | 0 | unchanged |

Existing section numbers (§3, §4, §6, §6a, §7b, §7c) were kept, because `workflows.md`,
`consumption.md`, `plugin_evals.md` and the tests cite them. §4.1's token table and its "Ten
tokens" sentence are untouched (`tests/test_bs02_…::test_164_*`). The new content cites row
IDs and file paths, not line numbers, because ESD-01 family F4 found line citations to be a
standing source of false reds.

## Decisions

- **§6a false red: no new kind and no new field.** The audited records already keep both halves:
  - the original red stays in each ticket's evidence, unedited;
  - the correction is one CATCH against the instrument, which lists the charged runs, with the
    effect written in existing prose (`observed` / `consequence`);
  - a product CATCH filed earlier is superseded, not deleted (the `BS-10-DF-01` →
    `BS-11-DF-03` precedent);
  - exoneration requires a named control (red on the untouched base; the touched path passed).

  A new shape would be justified only by a red whose correction has no single instrument to
  file against. None of the audited examples is such a red.
- **Origin vs effect.** Effect (faithful, false red, false green/blind, skipped) is a third axis,
  written as words in existing free text (`consequence:`, ESD-01's precedent). It is not a new
  token set and not a field.
- **Origin is relative to the repository.** The same defect can be validation-origin in a
  consumer and product-origin in this plugin (`DEF-124`).

## Model result

**No-op.** `specs/current`, `specs/desired_program_model` and `specs/program_model` are
unchanged. The ticket edits prose and evidence and changes no action, variable or invariant.
§7d's own rule classifies this as a no-op.

## Validation

| Entry | Result | Output |
|---|---|---|
| `validation.repository_unit` | 407 passed, 1 skipped (base: the same) | `repository-unit.txt` |
| `validation.spec_unit` | 2 failed, 54 passed. These are the same 2 known base failures (`test_every_model_action_is_bound`, `test_unfilled_ledger_template_refuses_the_close`), with no new failures | `spec-unit.txt` |
| `skill-manager unit validate` (discovery skill, plugin) | no skill-import violations | (console) |

Local signal: `local-signal.md`.
