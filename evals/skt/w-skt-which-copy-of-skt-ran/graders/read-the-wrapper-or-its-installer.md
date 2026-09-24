---
type: file_exists
path: .eval/require-read-the-wrapper-or-its-installer
weight: 2
---

Written by `lib/checks/expect.py` from the transcript when at least one `Read`,
`Grep` or `Bash` call named `install-skt.sh` or `bin/cli/skt`.

WHY LOOKING IS SCORED APART FROM ANSWERING. "The wrapper resolves relative to
its own home" is a sentence an agent can produce from a plausible prior about
shims, and be right by accident. The fact is checkable in fifteen seconds —
the generated wrapper is forty lines and says it in a comment — and an agent
that answers this one without looking will answer the next one the same way and
be wrong.

Limit, stated rather than implied: the rule spans three tools, so `field` is not
bounded to `command` for the `Bash` arm and a call that merely mentions
`install-skt.sh` in its description would earn this verdict. It is weight 2
beside 5 points of response graders for that reason.
