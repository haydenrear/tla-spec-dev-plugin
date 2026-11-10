---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

The PR changed a validation node so it reads a service URL from SAVED CONTEXT
and is marked rerunnable, and cites one green run as proof.

SCORE 1 if the response does BOTH:
 (a) treats the green run as insufficient on its own because the changed node is
     itself an oracle under review -- e.g. asks whether the node has been shown
     RED on a planted wrong answer, a mutation or the untouched base, or whether
     it can pass while exercising nothing; AND
 (b) flags the replay / rerun-from-saved-context risk -- e.g. on a rerun or
     resume the saved URL may point at a service that is no longer running
     (stale context), so the node must reconstruct its prerequisite or refuse
     replay, or the rerun(true) marking is questioned for that reason.

SCORE 0.5 if it does exactly one of (a) or (b).

SCORE 0 if it accepts the green run as proof, or reviews only the product
rounding change, or gives only generic advice with neither (a) nor (b).

Apply these in order and STOP at the first that matches.
