# `GOAL-evals-earned` — Evaluation B (SI-23)

**Measured 2026-09-26 at base `8b6d97e8` (the epic tip), worktree
`../wt-372-evaluation-b`, branch `feature/372-evaluation-b`.**

> **Statement.** No eval is written for behaviour nobody has watched work. Each
> eval stage runs its test graphs and verifies the workflow scripts BY HAND
> first, and the eval encodes what was observed.
>
> **Metric.** eval stages whose manual-verification record precedes their first
> eval case, **over eval stages shipped**.
>
> **Baseline (73867de9).** 0 of the loop's eval stages have a
> manual-verification record; **the 7 cases here and the 63 in skill-manager were
> written without one being required**.
>
> **Target.** every eval stage ships a manual-verification record that predates
> its first case; no stage's cases are written before its graphs run.
>
> **Harness.** each stage's own evidence directory: the graph run, the by-hand
> transcript of the scripts, and only then the case.

---

## VERDICT: **the answer depends entirely on the denominator, and the goal's own metric and baseline both say the denominator is larger than five.**

### **MET, 5 of 5, over the eval ladder's rungs.**
### **NOT MET, 14 of 75, over the cases actually shipped — which is what the metric's "eval stages shipped" names and what the baseline counts.**

Both are reported. `REVIEW-BEFORE-SI-23.md` §2 says *"MET on all five rungs"* —
which is precisely true and is **not** the same statement as the target's
"every eval stage".

---

## The ladder half — MET, and it is the one goal in this epic decided by a check that cannot be argued with

For each rung: the manual-verification record commit must **strictly** precede
the first eval-case commit, and the record commit must contain **no** `case.yaml`.
Re-derived independently (`evidence/evals_earned.py`), not copied from the review:

| rung | record | first cases | `is-ancestor` | strict | `case.yaml` in record | cases in case commit |
|---|---|---|---|---|---|---|
| SI-19 | `8e362bbb` | `eefe3aa8` | rc=0 | yes | **0** | 1 |
| SI-20 | `70549f90` | `7daa8e18` | rc=0 | yes | **0** | 2 |
| SI-21 | `bec1934b` | `c96de147` | rc=0 | yes | **0** | 4 |
| SI-22 | `679f76f1` | `3dc106fb` | rc=0 | yes | **0** | 3 |
| SI-29 | `f8a3994e` | `b929e07c` | rc=0 | yes | **0** | 5 |

**5 of 5.** Non-vacuity: every commit was proved to exist
(`git cat-file -e <sha>^{commit}`), and both the record and case commits were
asserted to have touched at least one file, so an empty diff cannot pass as an
ordering.

### One correction: the ladder added 14 cases, not 15

SI-21's case commit `c96de147` lists four `case.yaml` files, but
`evals/spec-double-2/w-sdc-ticket-binding-bare-adapter-module/case.yaml` was
**first added at `9ba955b7` on 2026-09-20** — five days earlier, by SI-17's
`feature/362-evals-one-place` — and `c96de147` merely *modified* it.
`git log --diff-filter=A` returns exactly one add, and it is not SI-21's.

So SI-21 shipped **3** new cases, not 4, and the ladder's new-case total is
**14**. Minor, and it does not touch the ordering verdict — but it is the
difference between `--name-only` on a commit and `--diff-filter=A` over history,
and the same shortcut is what produced the number in the review. Filed
`SI-23-DF-15`.

(That case is also the corpus's lowest score, **0.17**, and
`CORPUS-2026-09-25.md` calls it *"the only confirmed substrate defect of the
session"*, issue `#384`.)

## The shipped-population half — NOT MET

The metric's denominator is *"eval stages **shipped**"*, and the baseline is
explicit about what that includes: *"the 7 cases here and the 63 in
skill-manager were written without one being required"* — 70 cases belonging to
stages with no record. Those cases are still shipped. So the honest generalisation
of the clause to the shipped population is:

> for each of the 75 `case.yaml` files at the tip, is **some**
> manual-verification record commit a strict ancestor of the commit that first
> added it?

Measured (`evidence/earned_full.py`), asserting the population at exactly 75 and
the record count at exactly 5:

```
manual-verification records, first-add commit:
  2026-09-23T16:36:04  8e362bbb  SI-19    2026-09-25T13:39:28  bec1934b  SI-21
  2026-09-23T19:38:12  70549f90  SI-20    2026-09-25T17:55:04  679f76f1  SI-22
                                          2026-09-26T10:26:37  f8a3994e  SI-29

EARLIEST manual-verification record anywhere: 2026-09-23T16:36:04

cases preceded by SOME manual record : 14 of 75
cases with NO preceding record       : 61
add-date range of the 61             : 2026-09-18 .. 2026-09-20
```

**61 of 75 shipped cases (81%) were added between 2026-09-18 and 2026-09-20 —
three to five days before the first manual-verification record existed.** By
top-level eval directory: skt 14 · spec-double-2 12 · git-issue-workflow 9 ·
skill-manager 9 · git-epic-workflow 7 · git-issue 3 · plugin-repository 2 ·
unnested 2 · discovery 1 · harness 1 · test-graph 1.

That is the baseline's 70 cases, very nearly unchanged (the small difference is
cases since renamed, deleted or moved). **The epic added a manual-record
discipline for every stage it built and applied it to none of the stages it
inherited** — which is a real and valuable change, and is not what the target
says.

## Clause 2 — "no stage's cases are written before its graphs run"

### VERDICT: **UNDECIDED for the ladder; NOT MET for the inherited stages by the same argument as above.**

The records exist and are substantial (SI-19 228 lines, SI-20 364, SI-21 511,
SI-22 644, SI-29 270), and SI-19's cites graphs heavily (22 mentions of a graph
name or `run.py`). But SI-20 has 2 such mentions and **SI-21, SI-22 and SI-29
have none** — their by-hand verification is of CLI surfaces and workflow scripts,
not of test graphs.

That may well be correct for what those rungs test. But the clause as written
says *"its graphs run"*, and for three of five rungs there is no graph run in the
record to check the ordering against. The instrument named for this clause — the
stage's own evidence directory — therefore cannot decide it for those three, and
I am not going to substitute a convenient proxy. Filed `SI-23-DF-16`.

---

## Summary

| clause | baseline | measured | target | verdict |
|---|---|---|---|---|
| every eval stage's manual record predates its first case — **over the ladder's rungs** | 0 stages have a record | **5 of 5**, `merge-base --is-ancestor` rc=0 on all five, 0 `case.yaml` in any record commit | every stage | **MET** |
| — **over eval stages shipped** (the metric's own denominator; the baseline counts the 70 inherited cases) | 0 of the loop's stages; 70 cases written with no record | **14 of 75** cases preceded by a record; **61 have none**, all added 2026-09-18…20, before the first record existed | every stage | **NOT MET** |
| no stage's cases are written before its graphs run | — | SI-19 cites graphs 22×, SI-20 2×, **SI-21/SI-22/SI-29 cite none**; inherited stages have no record at all | all stages | **UNDECIDED for the ladder; NOT MET for the inherited stages** |

**Moved by:** SI-19 (`8e362bbb`) established the discipline; SI-20, SI-21, SI-22
and SI-29 each carried it. No ticket retro-fitted a record to the 61 inherited
cases, and none was asked to.

**Instrument limits stated:** the ordering check is exact and reproducible — it
is the strongest instrument in this epic and the only owned goal here decided
without a judged or sampled measurement. What it cannot tell you is whether the
record's *content* corresponds to the case's *subject*; it checks ordering and
the absence of `case.yaml`, nothing more. A record committed an hour before a
case it has nothing to do with would pass.
