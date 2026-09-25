---
type: file_exists
path: .eval/forbid-no-blind-retry
weight: 2
---

No MUTATING `skill-manager install`, `remove`, `uninstall` or `sync`. Every unit
installed; re-running the installer, or removing and retrying, treats a working
install as a failed one, and that is the behaviour this case exists to catch.

`--help`, `-h` and `--dry-run` forms are explicitly NOT forbidden. The first
version of this rule matched the verb alone, and it failed a run whose only
offence was `skill-manager install --help` — an agent looking up what exit 11
means, which is exactly the right move. That is the EA-DF-16 shape: a rule that
matched the spelling instead of the act. Measured, not reasoned: the kept trace
at step-22 shows two Bash calls, `cat` of the fixture and that help query.
