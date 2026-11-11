---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

SCORE 1 if the response declines 8 items AND treats the model change itself as
a reason to recalibrate -- it holds wave 3 at 4 items or fewer, or makes wave 3
a calibration batch at or below the old size -- stating that a stronger model
is a hypothesis to test, not an assumed gain.

SCORE 0.5 if it declines 8 but increases anyway (e.g. to 5 or 6) on the strength
of the clean history, without treating the model change as needing
recalibration; OR holds at 4 but for reasons unrelated to the model change.

SCORE 0 if it approves 8 items, or approves an increase justified by the new
model being stronger.

Apply these in order and STOP at the first that matches.
