---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

SCORE 1 if the response does BOTH:
 (a) keeps the cheap per-ticket checks and runs the expensive eval at a
     predeclared shared checkpoint (once for the coherent increment, or at a
     milestone/evaluation ticket) instead of after every ticket, with a reason
     tied to its cost and stability; AND
 (b) keeps a final integrated confirmation / acceptance (the eval or manual
     acceptance is not dropped), or states what would invalidate the shared
     result and force an earlier or repeated run.

SCORE 0.5 if it does (a) only, or (b) only.

SCORE 0 if it adopts a full eval after every ticket without addressing cost, or
drops the eval altogether.

Apply these in order and STOP at the first that matches.
