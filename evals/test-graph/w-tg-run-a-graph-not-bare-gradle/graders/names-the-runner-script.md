---
type: regex
pattern: '\brun(-graphs)?\.py\b'
weight: 3
---

THE BEHAVIOUR. The command that runs a registered graph in a fresh checkout is
the skill's runner — `skills/test-graph/scripts/run.py <graph>` — or the
repository's own front door `test_graph/run-graphs.py`, which wraps it. Either
spelling passes; `cd test_graph && ./gradlew <graph>` does not, and that is the
answer this case exists to separate out.

OBSERVED, NOT INFERRED. Both arms were driven by hand in the SI-19 worktree at
`f4b42169` on 2026-09-23:

    $ ./gradlew cliWorkflow
    Included build '.../test_graph/build-logic' does not exist.
    BUILD FAILED in 2s                                          exit=1

    $ python3 skills/test-graph/scripts/run.py cliWorkflow
    BUILD SUCCESSFUL in 21s                                     exit=0
    summary.json: "status":"passed", 2/2 nodes

Transcripts: `specs/results/epic-self-improvement-substrate/tickets/SI-19/transcripts/`,
`step-A-bare-gradlew-control.txt` and `step-E-run-cliworkflow.txt`.

Reads the FINAL RESPONSE only: the agent was told not to run the command, so
the command it would issue exists only in its reply.
