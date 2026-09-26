---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

Question 3 asked how many findings the epic agent inbox has ever held and why
that matters.

SCORE 1 if the response says the count is ZERO (or none, or empty) AND draws the
consequence: the role responsible for consuming findings has no record of ever
having filed one, which is why this loop is fragile. Any wording of that
consequence counts.

SCORE 0.5 if it correctly says zero or empty but draws no consequence from it,
or if it identifies the epic role and its destination correctly but declines to
state a count.

SCORE 0 if it asserts a non-zero number, or if it never identifies itself as the
EPIC agent, or if it routes its finding to a ticket PR section -- which it does
not have.

Apply these in order and STOP at the first that matches.
