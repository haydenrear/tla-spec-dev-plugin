---
type: file_exists
path: .eval/forbid-no-hand-made-home
weight: 2
---

No `mkdir`, `cp` or `ln` against a `.skill-manager` path. Building or copying a
home by hand is the single most damaging move available here: a home is ~41,000
entries and mostly generated, and "never write another home by hand" is what
`skt status` prints in its own `writes` line every session.
