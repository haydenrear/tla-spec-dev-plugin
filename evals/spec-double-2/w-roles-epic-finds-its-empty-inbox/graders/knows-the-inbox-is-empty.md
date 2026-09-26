---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

Question 3 asked how many findings the epic agent's inbox holds now, how many
have ever been filed in it, and why that matters.

GROUND TRUTH, so this grader does not punish the correct answer: the file holds
ZERO rows today and exactly ONE has ever been filed in it -- EA-DF-01, which a
later ticket absorbed into the ledger, leaving its id behind under absorbed_ids.
So "zero" and "one" are BOTH right depending on which question is being answered,
and a response that separates the two has given the best answer, not a confused
one. The first version of this grader demanded the single word zero and scored
that correct answer FAIL three judges out of three; it was recalibrated against
the measured response rather than left to punish precision.

SCORE 1 if the response gets the quantity substantively right -- empty now, at
most one ever -- AND draws the consequence: the role responsible for consuming
findings has essentially no record of ever having filed one itself, which is why
this loop is fragile. Any wording of that consequence counts. Naming the absorbed
id, or saying the count is nearly nil rather than exactly zero, still scores 1.

SCORE 0.5 if the quantity is substantively right but no consequence is drawn, or
if the response identifies the epic role and its destination correctly but
declines to give any count.

SCORE 0 if it claims the inbox holds many findings, or gives a number it does not
support, or never identifies itself as the EPIC agent, or routes its finding to a
ticket PR section -- which it does not have.

Apply these in order and STOP at the first that matches.
