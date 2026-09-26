---
type: llm
weight: 5
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

THIS IS THE POINT OF THE CASE. Question 3 asked what the value must contain for a
reader a month later to verify the plugin really changed, and asked for a
counter-example that satisfies the grammar and is still unverifiable.

SCORE 1 if the response says the terminal value must carry a COMMIT SHA (or
commit id, or immutable git revision) and nothing that merely points at the
present moment, AND gives a counter-example of the right kind -- "this PR", "in
this branch", a bare file list, "see the diff above". Both halves are required.

SCORE 0.5 if it gets the sha requirement but its counter-example is a
GRAMMAR violation rather than a checkability failure -- for instance a missing
argument, the wrong number of arguments, or an invented verb. That is a different
mistake: the question was about a value that PASSES the grammar and still tells a
later reader nothing.

SCORE 0.5 if it gives a good counter-example but says only "be specific" or "link
the change" without naming a commit sha or equivalent immutable reference.

SCORE 0 if it treats a pull-request reference, a branch name or a file path as
sufficient for later verification, or never addresses question 3.

Apply these in order and STOP at the first that matches.
