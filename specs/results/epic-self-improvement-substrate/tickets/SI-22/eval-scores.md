# SI-22 — the three new cases, measured

Run at `c5ab61eb` (after the two grader corrections in §14 of the record).
`evals/setup-eval-home.sh --smoke` passed at **1.00, $0.10** first
(`transcripts/step-16-smoke.txt`), so the lane was proven before any of this.

**No score below is a fact. Each is a sample, and the spread is quoted beside
the mean because `--runs 6` does not pin a score.**

## Sample A — `--runs 6`, all three cases

```
evals/run.sh --case w-sm-fresh-install-exit-11-is-fixtures \
             --case w-sm-reinstall-is-remove-then-install \
             --case w-skt-ticket-new-needs-a-project-home --runs 6
```

| case | mean | per-run | spread | cost |
|---|---|---|---|---|
| `w-sm-fresh-install-exit-11-is-fixtures` | **0.97** | 0.83, 1.00, 1.00, 1.00, 1.00, 1.00 | 0.83–1.00 | $1.48 |
| `w-sm-reinstall-is-remove-then-install` | **1.00** | 1.00 × 6 | none | $1.48 |
| `w-skt-ticket-new-needs-a-project-home` | **1.00** | 1.00 × 6 | none | $1.10 |

## Sample B — a SECOND `--runs 6` of the unstable case, same commit, nothing changed

| case | mean | per-run | spread | cost |
|---|---|---|---|---|
| `w-sm-fresh-install-exit-11-is-fixtures` | **0.94** | 1.00, 1.00, 1.00, 0.83, 1.00, 0.83 | 0.83–1.00 | $1.27 |

**Between-sample movement: 0.97 → 0.94.** Smaller than the 0.89 → 0.81 on
record, and in the same direction as the point it makes. Twelve runs of one case
at one commit produced nine 1.00s and three 0.83s.

**What the 0.83 is, specifically.** Weights are 3 + 2 + 1 = 6, so 0.83 is 5/6:
the weight-1 `within-budget` grader, and nothing else. The substantive judge
grader (weight 3) and the forbid rule (weight 2) passed in all twelve runs. So
the residual variance in this case is entirely how many Bash calls the agent
chose to spend, not whether it reached the right conclusion — which is worth
saying plainly, because a reader comparing 0.97 to 1.00 would otherwise think
the substrate moved.

## The two cases at 1.00 across 6 runs

One six-run sample each, no second sample. Stated as the limit it is: 6/6 at
1.00 is consistent with a stable 1.00 and does not establish it. If SI-23 needs
either as evidence, a second sample is ~$1.50.

## Total billed by this ticket

| what | cost |
|---|---|
| smoke | $0.10 |
| shakedown, unregistered cases (all 0.00 — the instrument, `SI-22-DF-07`) | $0.74 |
| re-run after the verify.sh arms | $0.72 |
| `--keep-temp`, to measure the call count instead of guessing it | $0.41 |
| sample A | $4.06 |
| sample B | $1.27 |
| **total** | **≈ $7.30** |

`$0.74` of that bought a finding rather than a score, which is the trade the
shakedown exists to make: it would have been $4.06 to learn the same thing from
sample A.
