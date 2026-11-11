# GOAL-ESD-CAPACITY — verdict (ESD-06)

**Metric:** held-out audited episodes for which `step-sizing.md` yields BOTH estimates and a
defensible batch decision using only decision-time information. **Baseline:** unmeasured (no
capacity estimate existed in the instructions). **Target:** report-only. **Verdict: measured
(no threshold): 4/4 both estimates + defensible decision; agreement with outcome 1 agree, 2 partly,
1 disagree — weak evidence of predictive skill.**

Instrument run: `holdout-replay.md`, by a delegated reader who did NOT open
`specs/results/evidence-sized-delivery/**`, wrote each decision before reading what happened next,
and records leakage per episode. Not billed.

| Episode (decision point) | Both estimates? | Defensible decision? | Agrees with outcome? | Leakage |
| --- | --- | --- | --- | --- |
| E1 polymarket E02 R1+R2 (827e488/be70024, 2026-11-08) | yes (review 3-5, verification 2-4; model unknown) | yes on a lenient reading; strict §3 would serialize R1 after R2 | agrees | high (page §9 cites C27) |
| E2 effectful-learning epic-10 rev 72 (2ab23d20, 2026-11-08) | yes (review 4-6, verification 1-2; model unknown) | yes by the literal §6 rule | **disagrees**: page said one fix per run; the batched run moved 13→20 PASS and failed outside the batch | medium |
| E3 meta-harness finalization repair (62c8169, 2026-11-04) | yes (review 3-5, verification 2-3; tester `CLAUDE_sonnet`, no version) | yes | partly: controls match what was done; the instrument/product split was unnecessary (converged in 2 laps) | medium-high |
| E4 CDC mvp-stabilization MS-017 B7d (769fde9f, 2026-10-23) | yes (review 3-5, verification 2-3; "Claude Opus 5.5" in trailers) | yes | partly agrees (BEAM-02 closed on a gate blind to real Beam; family recurred at M2c) | high (page §9.3) |

Deviation from the brief: for "CDC #234" the reader chose the closest batch-sizing decision with
decision-time records (mvp-stabilization MS-017); recorded, not corrected.

**Reading.**
- Operability: 4/4 (sample 4; the §4 cost comparison could not be filled in any episode — every
  component `unknown` at decision time, so "total cost per accepted increment" was unexercised).
- Predictive agreement: 1 clean agree, 2 partial, 1 disagree of 4 held-out (+ ESD-04's 3 agree /
  1 undecided of 4, not blind). The one disagreement (E2) is the policy being **too conservative**
  (no tie-break between §4 amortization and §6 halving). The two agreements carry high leakage
  because §9 of the page itself describes those episodes.
- Model recalibration: exercised for the first time (E3, E4 named a model); E4 shows commit
  trailers are a model-identity source §1 does not list.
- Bias: the ESD-06 author has read the outcomes (ESD-01); the reader had not but met commit
  subjects while locating records. Uncertainty: n = 4, one reader.

**Page ambiguities found (instruction defects, deferred as `ESD-06-DF-02`):** halving unit undefined
for one-ticket/whole-milestone batches; no tie-break between §4 amortization and §6 "fix or isolate
the instrument before expanding" (whether instrument fixes may batch); no rule for an irreducible
group larger than the lower bound; "alone or in a small batch" underdetermined; "a host resource"
makes every pair interact on a one-host epic (quadratic count); severity-unrecorded escapes; commit
trailers missing from identity sources; "two consecutive review points" undefined inside repair
loops; §9 worked examples use the held-out episodes, contaminating future replays.
