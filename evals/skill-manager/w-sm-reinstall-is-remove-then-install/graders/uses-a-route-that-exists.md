---
type: file_exists
path: .eval/require-uses-a-route-that-exists
weight: 3
---

A Bash tool_use input reaches for a route that ACTUALLY EXISTS past the halt:
`skill-manager sync <unit>`, or `remove`/`uninstall` before re-installing.
There is no install-over path, so the only wrong answers are inventing one or
stopping.

BOTH routes are accepted, and that is a correction rather than a looseness. The
first version of this rule required remove-then-install and failed a run that
answered `skill-manager sync tla-spec-dev --git-latest`. I had not tested sync
by hand, so I went and did: `sync --help` says "Refresh installed units and
re-run install side effects", `--git-latest` fetches the install-time gitRef,
and the run reported "synced 1 unit(s) — 1 merged" with the front door intact.
For the refresh this prompt asks for, sync is the BETTER answer, and the
installer's own help points at it. The agent was right and the grader was wrong
(SI-22, transcript step-23). Sees the command, not its result.
