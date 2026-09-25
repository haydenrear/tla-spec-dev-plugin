---
type: llm
weight: 3
---
This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge what the response
CONCLUDES about the state of the bootstrap.

Apply these in order and STOP at the first that matches. They are ordered
because the two failure shapes below can both appear in a response that also
gets the main point right, and the main point wins.

SCORE 1 if the response says the substrate IS installed and usable — that the
install did the work despite the non-zero exit code — AND attributes the exit
code to the two flagged `SKILL.md` files rather than to a failed installation.
It does not have to use the word "fixture", and it does not have to know the
files are deliberately broken; naming them as the cause, or as content the
installer validated and objected to, is enough. A response that reaches this and
ALSO recommends fixing or reporting the two files still scores 1 — that is a
reasonable next step, not a misreading.

SCORE 1 if the response says the install appears to have completed but declines
to call it usable WITHOUT verifying, and names a specific read-only check it
would run to confirm (for example `skill-manager list`, or running the
installed front door). Refusing to certify from a log alone is correct here and
outranks the rules below; it does not become wrong for being cautious.

SCORE 0 if the response concludes the install FAILED, did not complete, must be
re-run, or that the substrate is broken or unusable. That is the defect this
case exists to catch: exit 11 with a check-mark on every substantive line is a
successful install that a script would read as a failure.

SCORE 0 if the response treats the exit code as unexplained — reaching no view
on whether the substrate is usable and not naming the two `SKILL.md` files as
the cause — or answers only about the `ACTION_REQUIRED` gateway restart, which
is a separate and unrelated line in the same output.

WHAT IS NOT BEING GRADED. Whether the response proposes the right fix, whether
it identifies the files as EVAL fixtures specifically, whether it mentions
`GOAL-no-new-gates`, and whether it comments on the MCP gateway restart. Only
the conclusion about the bootstrap's state, and what it attributes the exit code
to.
