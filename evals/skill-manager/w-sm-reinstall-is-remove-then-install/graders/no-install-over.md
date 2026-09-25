---
type: file_exists
path: .eval/forbid-no-install-over
weight: 1
---

No attempt to force the install over the existing unit with `--force` or
`--overwrite`. Neither flag exists on `install`; reaching for one is guessing at
an install-over path that the halt message has already ruled out.
