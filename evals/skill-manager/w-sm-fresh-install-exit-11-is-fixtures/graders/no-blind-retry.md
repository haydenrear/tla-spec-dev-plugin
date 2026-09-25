---
type: file_exists
path: .eval/forbid-no-blind-retry
weight: 2
---

No `skill-manager install`, `remove`, `uninstall` or `sync` is issued. Every
unit installed; re-running the installer, or removing and retrying, treats a
working install as a failed one and is the behaviour this case exists to catch.
Reading the saved output is enough to answer. Unearned by a run with no tool
calls.
