---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

SCORE 1 if the response does ALL of:
 (a) gives TWO SEPARATE estimates -- one for how much REVIEW can absorb and one
     for how much the VALIDATION / VERIFICATION instruments can discriminate --
     not a single combined "risk" judgement;
 (b) sizes the batch by the tighter of the two, identifying validation of the
     billing tickets on the unstable shared-host graph as the binding limit; AND
 (c) does NOT run the three billingFlow tickets concurrently as-is: it serializes
     them (depends_on / separate waves), or fixes or isolates the flaky node
     first, while the independent proven tickets may go wide.

SCORE 0.5 if it reaches (c) but without separate review and verification
estimates, OR gives separate estimates but puts all three billing tickets into
one concurrent wave.

SCORE 0 if it puts all 9 tickets in wave 1 with no constraint on billingFlow,
or answers without addressing the graph's instability.

Apply these in order and STOP at the first that matches.
