---
type: regex
pattern: 'integration\.toml'
weight: 3
---

THE BEHAVIOUR. The thing on disk that decides where a ticket worktree goes is
the presence of `integration.toml` in an ANCESTOR directory — not the contents
of that file, and not anything about the repo running the command.
`checkout_kind()` calls a repo with such an ancestor a **constituent**, which is
why the captured output says `feature/TG-1 (constituent repo subject-repo)`.

The prompt quotes that word because the tool printed it; it never names the
marker file, which is what this grader scores.

OBSERVED, NOT INFERRED. Two arms, one fixture, one variable, driven by hand in
the SI-20 worktree at `1cb00be7` on 2026-09-23:

    arm A, no integration.toml above:
      branch   feature/TG-1 (standalone repo subject-repo)
      worktree .../outer/inner/subject-repo-TG-1          beside the repo

    arm B, integration.toml planted two levels up:
      branch   feature/TG-1 (constituent repo subject-repo)
      worktree .../B-constituent/subject-repo-TG-1        beside the planted root

Both arms exit 0 and both round-trip cleanly.
Transcript: `specs/results/epic-self-improvement-substrate/tickets/SI-20/transcripts/step-05-ea-df-02-two-arms.txt`.

Reads the FINAL RESPONSE only: the agent was told not to create a worktree, so
the diagnosis exists only in its reply.
