---
type: regex
pattern: '(?is)(3\.11|python ?3\.1[1-9]|standard library|stdlib|built[- ]?in)'
weight: 4
---

THE DIAGNOSIS. `tomllib` entered the standard library in Python 3.11. It is not
a package and there is nothing to install. The traceback means the interpreter
is older than 3.11 — here `/usr/bin/python3` on macOS, which is 3.9.6.

The agent passes by naming the version floor or by saying `tomllib` is stdlib.
Either is the same understanding; the case does not care which half is said out
loud.

An answer that treats this as a dependency problem — a missing package, a
broken virtualenv, a `requirements.txt` gap — fails here even if it happens to
suggest a newer python somewhere else, because the reason decides whether the
next such traceback is read correctly.

OBSERVED, NOT INFERRED. SI-21 worktree at `ac5f7491`, 2026-09-25: the identical
command under 3.14.6 returns `0 violation(s)` and exit 0.

Reads the FINAL RESPONSE only.
