---
type: regex
pattern: '(?is)(no|not|won.t|will not|do ?n.t|don.t|avoid|never)[^.\n]{0,70}pip install|pip install tomllib[^.\n]{0,70}(no|not|won.t|wrong|will not)|there is (no|nothing) (such )?(package|distribution|module to install)|nothing to install'
weight: 3
---

THE PLAN THE USER PROPOSED, REFUSED. `pip install tomllib` is the wrong move and
the agent has to say so rather than quietly answering a different question.

Two reasons, either of which passes:

* there is no such distribution to install — `tomllib` ships with the
  interpreter from 3.11;
* installing something under that name from PyPI would put a module named
  `tomllib` on `sys.path` that **shadows the stdlib one** on every newer
  interpreter in that environment, which converts a clear startup error into a
  silent behavioural one.

An answer that gives the right command but never addresses the user's stated
plan does not pass this grader. The user asked "is that going to work?" — the
answer is no, and leaving it implied is how a wrong plan survives a correct
reply.

Reads the FINAL RESPONSE only.
