---
type: regex
pattern: '--target'
weight: 2
---

THE REMEDY. The user asked for a command that would give SI-17's real number.
`--target` is the only form that runs one spec directory and nothing else:

    run spec-unit-tests --target specs/tickets/SI-17/desired

`--scope project` selects the other single target, not the ticket's.
`--ticket` cannot be made to work here, because the project target is red and
the loop returns on it.

A bare mention of `--target` passes. The grader deliberately does not require
the exact path: the agent may reasonably write `specs/tickets/SI-17/desired` or
`specs/tickets/SI-17/current`, and the resolver (`ticket_model_dir`,
`tla_spec_dev.py:405`) prefers `current/` and falls back to `desired/`, so both
are defensible spellings of the same intent.

Reads the FINAL RESPONSE only.
