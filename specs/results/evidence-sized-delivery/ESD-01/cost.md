# ESD-01 cost reconstruction

What the records let us say about elapsed and active time, and what they do not.
**Rule used throughout:** a number appears only with its primary timestamp source. A number
derived from a primary source is marked **derived**. A number a record projected or argued is
marked **inferred**. Anything else is **unknown**. Parallel work is reported as a
**sum over parallel runs**, labelled as such, and is never added to wall-clock time.

## 0. What the timestamp sources can and cannot carry

| Source | What it timestamps | What it cannot give |
|---|---|---|
| `specs/.history/*/*/manifest.json` `created_at_utc` (plugin 129, CDC 244, MH 48, polymarket 41, effectful-learning 60, skill-manager: all entries) | the **close** of a ticket or workflow | **No manifest in any of the six repos records an open, dispatch or start time.** Batched closes make even close-to-close spacing meaningless. For example, the plugin's attribute-the-catch epic closed 5 tickets in 48 s (2026-09-06T20:38:09Z to 20:38:57Z), effectful-learning epic-01 closed 4 tickets in 2 s, and skill-manager CHM retired 23 tickets in 12 s. |
| PR `createdAt` / `mergedAt` / commit dates (gh) | when work was **published** and merged | Agents commit and open the PR after the work. The median PR open-to-merge time is 0.02 h (polymarket, effectful-learning) and 0.14 h (skill-manager). Most bug-sweep PRs carry 1-3 commits made within minutes of PR creation. **Not implementation time.** |
| Evidence files (`BUILD … in`, `pytest … in Ns`, `outcome.json duration_seconds`, test_graph `startedAt/endedAt`) | **instrument execution** time per run | When the run started relative to the work, and runs that never wrote a duration |
| Eval result JSON (`secs`, `cost`, result timestamps) | per-case agent seconds and USD | setup/voided time outside cases |
| Review and owner-decision artifacts | dates only (for example `owner-decisions.md` "2026-11-07") | the wait duration |
| Agent session transcripts | would carry active time | **Not read by this audit** (bounded scope). This is the one source that could measure implementation active time, so ESD-06 should use it. |

## 1. tla-spec-dev-plugin: bug-sweep epic (#199), the deepest-read record

| # | Component | Value | Kind | Source |
|---|---|---|---|---|
| C1 | Kickoff to last milestone-1 merge (19 tickets, waves 1-3, run in parallel) | 2026-11-07 17:09:24Z → 19:43:55Z = **2 h 34 m wall** | derived | `git log df48724c` (kickoff commit); `gh pr view 221` mergedAt |
| C2 | Kickoff to epic merge (#250) | 17:09:24Z 11-07 → 17:22:56Z 11-09 = **48 h 13 m wall** | derived | git and `gh pr view 250` |
| C3 | Milestone-1 instrument execution (pytest + Gradle durations in `specs/results/bug-sweep/BS-0x..BS-22/*`) | pytest 8,584 s + Gradle 2,547 s = **11,131 s (3.09 h), summed over parallel tickets** | derived | 141 duration lines in 115 evidence files (`grep "BUILD … in"`, `" in N s"`); the per-ticket split is in §1a |
| C4 | Runs with no recorded duration in milestone 1 | **≥ 11 run records** (BS-11 local-signal and real-sdk runs, BS-12 specWorkflow VERDICT, BS-13 resume-on-cliWorkflow, BS-15 specworkflow, BS-19 graph-sktSurface, BS-20 real-fixture ×2 and sktHooks-post-merge, BS-21 specWorkflow-nodes, BS-15 census) | count | the same files |
| C5 | Repeat cost: specWorkflow red that was the probe, not the ticket (BS-07-DF-05) | **13 errored runs across 7 tickets**. Durations are recorded for 7 of them: BS-07 826 s, BS-02 303 s + 27 s, BS-08 125 s → **≥ 1,281 s**, a lower bound | derived; 6 runs have unknown duration | `specs/results/bug-sweep/{BS-02,BS-07,BS-08}/…` |
| C6 | BS-08 (red suite → 0) | pytest 3,940 s + Gradle 212 s. Full-suite lap 1 took 2,010 s (7 failed, 8 errors); after repair, lap 2 took 1,404 s. Commit span 18:17:34Z → 19:42:57Z (85 m). | derived; the start of implementation is unknown | `BS-08/repository-unit-full-branch{-lap1,}.txt`; `gh pr view 221` commits |
| C7 | BS-16 evaluation suites | 1,630 s + 2,218 s = 3,848 s | primary | `BS-16/suite-{closed-tree,tip}.txt` |
| C8 | BS-17 eval lane, tip | 74 cases, **5,308 agent-seconds, $17.76**. Cases ran one at a time from 2026-11-09T00:44Z to 02:32Z. | primary | `specs/evals/bug-sweep/tip.json` |
| C9 | BS-17 base vs tip comparison | 8 cases × 3 runs × 2 sides, **$10.03**. Result timestamps run 02:36Z to 03:33Z; per-run seconds are not recorded. | primary; seconds unknown | `specs/evals/bug-sweep/compare.json` |
| C10 | BS-17 repeats: voided runs | **12 runs, 666 s, $2.71**. 8 were voided because the agent could have run the root home's skt (BS-03-DF-01), and 4 because there were no offline uv wheels in the worktree (#248). | primary | `tip.json` `voided` |
| C11 | Eval PRICE: declared vs measured | Declared "about $66 for base + tip" in the wave-3 review. Measured **$30.50** (C8 + C9 + C10). | primary on both sides | `review/wave-3/review.md` §5; C8-C10 |
| C12 | Owner gate and evaluation hold (wait) | From the last M1 merge (11-07 19:43:55Z) to the first eval case (11-09 00:44Z) is **29 h 0 m wall**. Wave 4 (BS-23, 03:32Z 11-08) and wave 5 (BS-24..27, 23:28Z-23:48Z 11-08) ran inside that window, so the window holds owner wait plus the skill-manager epic hold plus wave-4/5 work. **The split between them is unknown.** | derived (window); split unknown | `owner-decisions.md` ("Evaluation on hold"); `gh pr view 223/228/230/231/232` |
| C13 | Implementation active time for any ticket | **unknown** | unknown | no start timestamp in any record (§0) |
| C14 | Review active time (wave-3 and wave-5 milestone reviews) | **unknown** (artifacts are dated, not timed) | unknown | `review/wave-{3,5}/review.md` |
| C15 | Cold setup vs warm reuse | **unknown** for this plugin. The baseline specWorkflow took 2 m 15 s and included a `build-logic` compile, but no warm-reuse run of the same graph is recorded. | unknown | `baseline/graphs-default.txt` |
| C16 | Manual testing loop (BS-18) | **not run**; waived by the owner 2026-11-09 | primary (record of absence) | #198 comments, PR #250 body |

### 1a. Milestone-1 instrument seconds by ticket (C3 detail)

Source: duration lines in each ticket's evidence directory. These are summed per ticket. They are not wall-clock time.

| Ticket | pytest s | Gradle s | | Ticket | pytest s | Gradle s |
|---|---|---|---|---|---|---|
| BS-01 | 653 | 0 | | BS-11 | 681 | 166 |
| BS-02 | 539 | 330 | | BS-12 | 530 | 0 (graph duration not recorded) |
| BS-03 | 76 | 127 | | BS-13 | 461 | 67 |
| BS-04 | 209 | 0 | | BS-14 | 16 | 89 |
| BS-05 | 179 | 0 | | BS-15 | 425 | 0 (graph duration not recorded) |
| BS-06 | 168 | 0 | | BS-19 | 282 | 0 (graph duration not recorded) |
| BS-07 | 126 | 826 | | BS-20 | 196 | 113 |
| BS-08 | 3,940 | 212 | | BS-21 | 101 | 0 (graph duration not recorded) |
| BS-09 | 1 | 101 | | BS-22 | 1 | 0 |
| BS-10 | 0 | 516 | | **sum** | **8,584** | **2,547** |

BS-08 alone accounts for 46% of milestone-1 pytest time. It was the one ticket assigned the full
suite.

## 2. Consumer repositories (delegated read, spot-checked)

| # | Repo | Component | Value | Kind | Source |
|---|---|---|---|---|---|
| C17 | CDC | #394 batch phases (20 batches; phases overlap, so these are **summed phase hours**) | implementation **44.0 h**, review **81.5 h**, graphs+merge **50.3 h**, close 0.9 h; idle between batches 39.2 h | derived by the repo's own retrospective | `specs/results/mvp-stabilization/goals/GOAL-MS-VELOCITY/velocity-retrospective.json` `batch_phases` |
| C18 | CDC | #462 batch phases (11 batches) | implementation **36.8 h**, review **87.4 h**, graphs+merge **6.5 h**, close 7.2 h; idle 56.7 h | derived (same) | same |
| C19 | CDC | graph machine hours | #234: 16.1 h (14.5 h red); #394: 64.9 h (25.2 h red); #462: 46.4 h (20.0 h red) | primary (Gradle verdict lines) | same, `graph_runs` |
| C20 | CDC | machine hours of the 118 attributed reds, by fix-owning channel | product 28.28 h (21 of 36 reds timed); test 14.58 h (16/33); environment 2.73 h (16/35); process 0 h (0/14). **Timestamp coverage: 53 of 118 reds.** | primary/derived | same, `red_attribution.overall` |
| C21 | CDC | Beam cold onboard | 8,335.5 s against a 10,800 s bound; FINAL2 onboard cut at 3,603.8 s by a 3,600 s window | primary | `specs/results/mvp-stabilization/red-attribution.yaml` (MS-024-RV-DF-02-MARGIN; FINAL2 rows) |
| C22 | CDC | warm reuse | **unknown**: no warm-reuse measurement found | unknown | — |
| C23 | MH | local graph wall time | 64 runs, 3.23 h (min node start to max node end per run); 12 of 64 errored | derived from `startedAt/endedAt` | `test_graph/build/validation-reports/*` |
| C24 | MH | metaHarnessExternal | 2,285 s, 2,161 s, 2,158 s, 2,175 s in the finalization sweep, against 1,284 s on 08-29 | primary | same |
| C25 | MH | contention | spec_unit about 70 min alone, **projected** about 20 h with two tickets concurrent (DEF-154) | inferred (projection) | `specs/.history/meta-harness-loop/closed-snapshot/deferred_findings.yaml:1363` |
| C26 | effectful-learning | epic-10 validation timing | 13 accepted runs: 2,615.8 s invocation, of which **1,258.5 s in node windows and 1,357.3 s outside them** (median 93.1 s before the first node). Failed or refused runs 1,499.3 s; preparations 1,048.3 s. Union wall 5,163 s within a 13,845 s range. **144.7 of 230.8 audit minutes are unclassified.** | primary (the repo's own audit) | `specs/results/epic-10/review/finalization/validation-timing-audit.json` |
| C27 | polymarket | E02-CI-EVAL final profile | 14/14 graphs passed, `profile_seconds` 934.87 | primary | `specs/results/E02-CI-EVAL/final-assessment.json` |
| C28 | skill-manager | cold vs warm | cold uv cache: 3 × 180 s attempts killed (#295); warm rebuild 4 m 50 s. home-verdicts took 18 min against about 2 min once the OTLP hang was removed (DEF-OHV-140). | primary | issue #295; `results/epic-one-home-one-verdict/tickets/OHV-8/deferred.yaml` |
| C29 | skill-manager | eval spend | first round 2026-09-07 **$13.06 / 14 runs** (one case); OHV round $7.74 / 12; wide rounds total $163.36 (R3 $60.58, 92 runs, 4,003 s); wide R1 had 27 of 46 runs fail on ENOSPC at $0 | primary | `specs/evals/results/2026-09-07-epic-provisions-a-ticket-worktree.md`; round READMEs |
| C30 | all five consumers | implementation active time, review active time, queue/wait split | **unknown** | unknown | §0 |

## 3. Local-signal count (b): cost rows by timestamp source

Counted over the 30 rows C1-C30 above:

| Classification | Count | Rows |
|---|---|---|
| Cites a primary timestamp/duration source (primary or derived from one) | **23** | C1-C12, C17-C21, C23, C24, C26-C29 |
| Inferred (projection, no measurement) | **1** | C25 |
| Unknown | **6** | C13, C14, C15, C16 (the loop never ran, so its cost is unknown), C22, C30 |

**Partial coverage inside the "primary" rows:** C5 (7 of 13 runs timed); C9 (no per-run seconds);
C12 (window known, split unknown); C20 (53 of 118 reds timed); C4 (≥11 untimed runs).

## 4. The owner's observation: "validation takes 10-100× implementation"

**What can be measured:**

- **Phase-separated data exists in one repo only (CDC).** There, review + graphs/merge divided by
  implementation is **(81.5 + 50.3) / 44.0 = 3.0×** for #394 and **(87.4 + 6.5) / 36.8 = 2.6×** for
  #462 (C17, C18). Two caveats push in opposite directions:
  - CDC's "implementation" starts at the first PR commit, so pre-commit agent work falls into
    "idle". That understates implementation and overstates the ratio.
  - CDC's "review" runs from PR creation to the last commit, so it includes repair coding driven
    by validation. That inflates the validation side with implementation-like work.
  - The 39-57 h of idle is attributed to neither side.
- **Machine time:** graph machine hours divided by implementation hours is 64.9/44.0 = **1.5×**
  (#394) and 46.4/36.8 = **1.3×** (#462). Machine hours run in parallel, so they are not elapsed
  time.
- **bug-sweep milestone 1:** 3.09 h of summed instrument time inside a 2.57 h wall window for 19
  tickets (C1, C3). Implementation time is unknown.
- **Overhead inside validation:** effectful-learning spent 52% of accepted-run invocation time
  outside any node window (cold Gradle plus serial describe: C26). The bug-sweep spent ≥ 1,281 s
  re-running a probe that was red for reasons unrelated to the tickets (C5). CDC spent 14.5 of
  16.1 graph machine hours of #234 on red runs (C19).

**What this supports:**

- On the only phase-separated data, validation/review/repair takes roughly **2.5-3×** the
  measured implementation phase.
- **Measured from end-to-end elapsed time, the multiple is much larger**, because waiting
  dominates. In the bug-sweep, the 19-ticket milestone landed in 2 h 34 m, but the epic took 48 h
  13 m to merge (C1, C2). Most of the remainder is the owner gate, the evaluation hold, waves 4-5
  and evals (C12), and the records cannot split it. A **ratio near 19×** (48.2 / 2.57) is
  therefore available only by dividing **total elapsed** by the **fastest implementation window**.
  That compares unlike quantities, and it is not evidence for the 10-100× claim.

**What stays unknown:** the implementation active time of any ticket in any repo (C13, C30). With
that denominator unmeasured, **the 10-100× observation can be neither confirmed nor refuted from
the records**. The evidence does show two things about where elapsed time goes:

- **Waiting and repeats dominate elapsed time**, and they appear in every repo: the owner gate and
  hold (C12); repeat reds caused by the environment or the instrument (C5, C10, C19, C20); and
  unclassified time (C26).
- **Instrument execution alone does not reach 10×** on any measured slice.

**What would settle it (for ESD-06):** start-of-work timestamps. Reading agent session
transcripts, or recording a dispatch/start time beside the close manifest's `created_at_utc`,
would supply the missing denominator. This is filed as deferred finding `ESD-01-DF-01`.
