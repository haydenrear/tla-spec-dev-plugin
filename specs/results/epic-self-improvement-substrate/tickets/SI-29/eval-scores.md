# SI-29 — eval scores, with sample count and spread

Measured on the pushed commit `d2e89c40`, worktree
`/Users/hayde/IdeaProjects/wt-391-role-routed-disclosure`.

**A mean is not reported alone anywhere in this file.** `--runs 6` does not pin a
score — the epic's own record has 0.89→0.81 and 0.97→0.94 on unchanged cases at
one commit — so every figure below carries its sample count and its per-run
spread, and the per-run lines are the primary record.

## The lane, first

```
$ evals/setup-eval-home.sh --smoke
  w-harness-smoke run 1/1: score 1.00  $0.14
  smoke: PASSED -- w-harness-smoke scored 1.00, so the lane is real
  rc=0
```

One advisory MISS, not fixed and not this ticket's: *no offline uv wheels — every
`uv run --script` skill script fails in a sandboxed run*. None of these five cases
runs a skill script.

Pre-billing checks, all run before any money was spent:

| check | result |
|---|---|
| `python3 evals/lib/check_graders.py evals` | `50 regex grader(s) compile under the JS engine` |
| `evals/lib/check_cases_parse.py evals` | `75 case file(s) parse.` **only with PyYAML** — see `SI-29-DF-03` |
| `python3 evals/lib/checks/expect.py --self-test` | `0 failure(s)` |
| `pytest tests/test_agent_integration_harness.py tests/test_eval_toolchain_pin.py` | 55 passed |

## The measured run

```
$ evals/run.sh --case 'w-roles-*' --runs 6
```

| case | runs | per-run scores | mean | spread | pass% | cost |
|---|---|---|---|---|---|---|
| `w-roles-ticket-finds-its-back-channel` | 6 | 1.00 ×6 | **1.00** | 0.00 | 100% | $1.24 |
| `w-roles-epic-finds-its-empty-inbox` | 6 | 1.00 ×6 | **1.00** | 0.00 | 100% | $1.49 |
| `w-roles-review-finds-its-destination` | 6 | 1.00, 1.00, 1.00, **0.64**, 1.00, 1.00 | **0.94** | 0.36 | 83% | $1.47 |
| `w-roles-testing-finds-its-destination` | 6 | 1.00 ×6 | **1.00** | 0.00 | 100% | $1.37 |
| `w-roles-propagation-is-checkable` | 6 | 1.00, **0.67**, 1.00, 1.00, 1.00, 1.00 | **0.94** | 0.33 | 83% | $1.38 |

`5 case(s) · 781s · $6.96`. With the shakeout ($1.18) and the smoke ($0.14) this
ticket billed **$8.28** over 36 case-runs.

**All five are green.** No case is UNDECIDED and none needed a reason.

### What the two single bad runs were

- `w-roles-review-finds-its-destination` run 4/6, 0.64 —
  `separates-diff-from-substrate` FAIL FAIL FAIL. That grader requires two
  *different* destinations with the split the right way round; one run in six sent
  both findings to the same place. **Not recalibrated**, because on the same
  prompt five runs in six got it right: the grader is discriminating between two
  real behaviours, which is what it is for. Turning a 5-of-6 into a 6-of-6 by
  widening the grader is the move this epic has paid for before.
- `w-roles-propagation-is-checkable` run 2/6, 0.67 —
  `writes-the-value-in-the-grammar`: *pattern not found in last_message*. That
  grader matches `proposed(` followed by one of the twelve real unit names, so one
  run in six wrote the value in a shape the pattern does not accept. Also **not
  recalibrated**: the whole point of the case is that the slot carries a unit
  name, and 5 of 6 did it.

**Both are held as measured rather than tuned away.** They are the honest
statement that the routing is read correctly about five times in six, not six.

## The one grader that WAS recalibrated, and why that is different

The shakeout run (1 run each, $1.18) scored
`w-roles-epic-finds-its-empty-inbox` **0.64**, with
`knows-the-inbox-is-empty` FAIL FAIL FAIL.

**The agent was right and the substrate was wrong.** `agent_roles.md` claimed
`EPIC-AGENT.yaml` "has held zero findings since it was created". It has held
**one** — `EA-DF-01`, absorbed by SI-27, its id still under `absorbed_ids`. Zero
rows *today* is true; zero *ever* is false. The grader demanded the word "zero",
so a response that correctly separated the two scored FAIL.

Three things changed, all at `d2e89c40`: the false claim in `agent_roles.md` and
on the `git-epic-workflow` card, the ambiguous prompt, and the grader — which now
states the ground truth so it cannot punish precision again, and records its own
recalibration in its body.

After: **1.00 on 6 of 6 runs.**

That is a grader corrected because it was *wrong about the world*, which is a
different act from widening a grader because a run failed. The two single bad runs
above are the second kind and were left alone.

## What these scores are NOT evidence of

- Not that the descriptions still trigger skill selection in a live session.
  Activation VOCABULARY is measured per unit in `local-signal.md` and is at or
  above base everywhere after the review restoration; whether the harness selects
  on it is a different claim and is unmeasured.
- Not that 592 words holds against the next nested unit.
- Not a re-measurement of any case outside `w-roles-*`; the other 70 were not run.

---

## Post-review confirmation run (after the activation restoration)

The review restored activation vocabulary to `skill-manager`, `skt`,
`unit-authoring` and `discovery`, which changed **eight of eleven** descriptions.
Descriptions are the surface these cases depend on — every case grades
`reaches-a-skill`, and `spec-double-2`'s description is the cold-session entry to
the role map — so the corpus was re-run rather than assumed unaffected.

```
$ evals/run.sh --case 'w-roles-*'        # 1 run each, on aceb7bf3
  w-roles-epic-finds-its-empty-inbox     1.00  100%  1  $0.23
  w-roles-propagation-is-checkable       1.00  100%  1  $0.24
  w-roles-review-finds-its-destination   1.00  100%  1  $0.27
  w-roles-testing-finds-its-destination  1.00  100%  1  $0.23
  w-roles-ticket-finds-its-back-channel  1.00  100%  1  $0.21
  5 case(s) · 131s · $1.18 · rc 0
```

**All five at 1.00 on one run each.** Routing survived the redistribution.

**This is one sample, not six, and it does not replace the table above.** The
6-run means and spreads stand as measured at `d2e89c40`; two of those cases have a
known one-in-six bad run, so a clean 1-run sweep here is consistent with them and
is not evidence that the spread closed. Total billed for this ticket is now
**$9.46** across 41 case-runs.
