# GOAL-ESD-CAPACITY: held-out replay of step-sizing.md

Instrument: `skills/git-epic-workflow/references/step-sizing.md` at worktree head 5404a3c1
(2026-11-10). Evaluator: one blind-as-possible agent, read-only on all four episode repositories.

## Method

1. Read step-sizing.md in full first. Its §9 worked examples cite polymarket `E02-CI-EVAL` 14/14
   after R1-R13 (C27), CDC `M2B-BEAM-02` and `SM402-ISOLATION family`, and §2 cites meta-harness
   `DEF-110`. I saw these, so the instrument itself leaks outcome facts for E1 and E4 (see leakage).
2. Did NOT read `specs/results/evidence-sized-delivery/` (ESD-01 cost/inventory, ESD-04, reviews).
3. Per episode: chose one batch-sizing decision, rebuilt decision-time facts with
   `git show <commit>:<path>` / `git log --before`, applied the page (§1-§7) and wrote the estimates,
   decision and falsifier (this section, written before reading what happened next; the
   "Outcome" subsections were appended afterwards).
4. Scored agreement, defensibility (follows from decision-time facts via the page's rules) and
   ambiguity.

Scope items are the page's unit (one behavior change at one boundary; +1 per interacting pair).
"Batch" here is the unit of the decision: a repair round or eval-cycle batch, not ticket count.

## Bias and leakage statement

- The page's §9 names the E1 outcome (R1-R13 then 14/14) and the E4 finding id M2B-BEAM-02 and the
  CDC isolation-gate fault family. I therefore knew before E1 that the repair series ran to R13.
- Hunting decision points with `git log` on result paths showed later commit subjects: E1 (R3,
  causal repair, "local20-of20"), E2 (scroll/view-intent/import-gesture repairs, final close
  2026-11-09), E3 ("round 2: full graph 14/14", "20 of 28 settled"), E4 (MS-017 review, MS-018 "M2c
  reds", MS-019). Commit subjects only; bodies read only after estimates were written.
- Facts I could not date are listed per episode.

## E1. polymarket E02: first milestone-3 repair round (R1 + R2)

**Decision point.** 2026-11-08 14:44-14:47 (827e488 prepares E02-R1 at revision9; be70024 prepares
E02-R2 at revision10), right after 667a8dd (14:31, wave-3 integration). Planner chose: two disjoint
repairs implemented in parallel, promoted serially; EVAL (wave 5) gains both as dependencies; human
gate after related graphs + combined review.

**Decision-time facts (source).**
- Plan: waves 1-3 one implementation ticket each (PE-16, PE-04, PE-05); EVAL wave 4;
  `review_policy: cadence milestone, gate true, milestones [3]` (667a8dd ticket_plan.yaml).
- Three prior review points (wave-1/2/3 review.md + independent-review.md). Each held many hot
  spots; wave-3 review caught ~8 temporal/provenance/packaging bugs before deployment; owner close
  then caught omitted default config/manifest declarations (escape review -> owner close, metadata).
- Images, deployment, scoped graph outcomes, manual/full acceptance all "pending" at 667a8dd
  (wave-3 review §3); whole model "unproved after original timeout".
- Actual final-image build at 667a8dd failed: invalid wheel filename (R1 work-order); same family in
  label worker found by review. Original channel: owner final-image build; it is a product
  (deployment) defect in a reviewed area. Severity not recorded; blocks milestone images.
- pe04Model graph FAIL at 19:44:58Z (14:44 local) from a hardcoded archived path in the graph target
  (R2 amendment): validation-origin (instrument) fault.
- run-plan.md: one exclusive fixture actor; Docker became unavailable before the last image attempt
  (environment change); "known source-changing retry gap"; stop repetitions on recurring
  defect-family triggers.
- `deferred_findings.yaml`: empty. Model/reviewer identity: not found in these records -> `unknown`.
- Could NOT date: the exact wall time of the image-build log under /Volumes/dev/polymarket-e02-tools
  (outside repo; inferred from the work order committed 14:44).

**Scope items.** R1 feature image wheel name (1), R1 label worker wheel name (1), shared final-source
image build/attestation pair (+1); R2 pe04Model target path (1). Total 4.

**REVIEW capacity.** 3-5 items; low confidence (model unknown, §7). Items carry red-on-base (original
failure retained) and are small; three prior review points but at one-ticket waves.
**VERIFICATION capacity.** 2-4 items per cycle; low confidence. Real image builds are faithful
(red shown) and one build discriminates both wheel sites; pe04Model is a cheap (875 ms) separate
instrument but just produced an instrument red; one exclusive fixture/host; Docker instability; cold
rebuild of all custom images; source-changing retry gap. **Binding: verification** (lower bound 2).

**Overrides (§6).** escape in reviewed area (deployment build), validation-origin fault on pe04Model,
environment change (Docker) -> **decrease**: halve; fix/isolate the instrument before expanding.
**Provisional batch / controls.** Strictly, 4 items > lower bound 2, so the page serializes: R2
(instrument fix, 1 item) first, R1 (3 items, irreducible: one family, one build) as its own step,
EVAL `depends_on` both, serial `promotion_order`, related graphs once on the merged tip, review at the
end of the repair step with `gate: true`. Leniently (2 tickets, disjoint `conflict_keys`, each with
red-on-base), running R1 and R2 in parallel is within "group independent items with proof".
Decision: **decrease** (from a 3-ticket milestone to 1-2 single-boundary repairs).
**Falsifier.** After R1+R2 the related graph pass finds no new failure outside these two boundaries
(then the page's caution was unnecessary). Prediction from page: verification is binding and most
graphs are still unexecuted, so expect further repair rounds, each surfacing 1-2 new failures.

**Outcome (read after the above).** R1 merged 15:02, R2 15:09 (PRs #100, #101), each one lap;
combined repair-wave review 15:11 (cb3e30f). Deployment hardening was then deferred (f62b8f2), the
local EVAL ran and exposed a causal measured miss -> R3 (18:35), R4 cutoff (18:56), R5 graph closeout
(19:04), then a complete graph audit planned R6-R13 validation-reliability repairs (da8ba2e, 20:47).
**Verdict: agrees.** The planner's 2-disjoint-repair round equals the page's lenient reading, both
converged in one lap, and the page's prediction (verification binding, further 1-2-failure rounds,
validation-origin faults dominating later) held. Defensible: yes from decision-time facts, but the
strict reading of §3 (batch <= lower bound) would have serialized R1 after R2 for no observed gain.
Leakage: high (page §9 C27 told me R1-R13 existed before I started).

## E2. effectful-learning epic-10: final-evaluation fixture batch (revision 72)

**Decision point.** 2026-11-08 16:25:20, 2ab23d20 "Batch all known pending visibility witnesses
before fresh final run" (scope-amendment72-r2/-r3). Planner chose: after a read-only "full37 family
audit", batch pulse-fixture isolation + two Pending-witness sites (4 helper paths) into one change,
then ONE fresh full37 notebook run, instead of one fix per run.

**Decision-time facts (source, all from 0838ba1a or earlier).**
- Evaluation ticket 235 already had assignments r64-r67 and scope amendments 64-72 in ~22 h
  (final-evaluation-preparation/). Amendments 68, 69, 70, 71 each record one red, one discriminator,
  one test/fixture-side cause (stale assertion, vacuous Home check, fixture focus move, Cell
  auto-reveal hiding GoTo) and one rerun that then failed at a later node. Product was fault only in
  the scroll/Home repair line (68-69); 70-72 attribute the red to the fixture ("No product focus
  steal"; "SUT correctly enforced unchanged bound").
- Amendment 72: original full37 run 13 PASS / 14 FAIL (2 cascades) / 23 SKIP; the pulse fixture
  added a 9th thread past the native 8-thread limit. Focused pulse discriminator 10.9 s green.
- One fresh full37 run is the required acceptance (clause el-notebook-eval-01.2), within a one-hour
  parent window; 15 as-run external entries pinned and reusable.
- Reviewer/verifier model: `unknown` (no model name in epic-10 results; only harness names).
- Could NOT date: whether the "full37 family audit" itself was finished before 16:25 or written into
  the r2/r3 records at commit time (same commit).

**Scope items.** Pulse isolation (1); Pending witness site A (1); site B (1); A-B share the Cell
auto-reveal behavior and one browser journey (+1); pulse shares the native thread budget with the
journey (+1). Total 5.

**REVIEW capacity.** 4-6 items; moderate confidence: many prior review points in this epic,
test-only helpers, independent review of the 3 helpers is cheap; pulse item has a focused green but
the two Pending sites have no red-on-base proof (audit was read-only).
**VERIFICATION capacity.** 1-2 items per cycle; low confidence. One instrument (fresh full37) per
cycle, ~1 h, serial; the graph cascades/skips after the first failure (23 SKIP), so a run attributes
roughly the first failing item only; four consecutive validation-origin reds on the same graph.
**Binding: verification**, lower bound 1.

**Overrides.** "repeated validation-origin faults on the same instrument" fires (70, 71, 72) ->
decrease/hold; "fix or isolate the instrument before expanding". Prior batch was 1 fix per run, so
halving leaves 1.
**Provisional batch / controls (page).** 1 item (pulse isolation) per fresh37 run; the Pending sites
wait until each has a red-on-base witness; `eval_budget`/evaluation ticket unchanged; review after
the run. Decision: **hold at 1** (no increase). Planner batched 3 fixes (5 items): the page, applied
literally, **disagrees**.
**Falsifier (of the page's choice).** If the batched fresh37 run is fully green, or fails only at a
node outside the batched sites, the batch did not hurt attribution and the page's "hold at 1" was
too conservative (fixed-cost amortization dominated). If it fails at a batched site or a pulse/Pending
interaction, the page was right.

**Outcome (read after the above).** First batched run (fresh72, 21:34Z) went from 13 PASS to
20 PASS and failed at `activity.capture21`, outside the batched pulse/Pending sites (amendment 73,
5587eb4a); the planner kept batching (rev 74 batched two more measurement fixes). Product repairs
(scroll/history, ACK view-intent, import gesture) followed; final evaluation closed 2026-11-09 01:57.
**Verdict: disagrees.** The batch of 3 fixes did not harm attribution and saved at least two ~1 h
serial cycles; the page's literal "halve / hold at 1" was too conservative here. The decision the page
yields is defensible by its own rules but the rules (halve on repeated instrument faults) mis-fire when
the batch *is* the instrument repair and the cycle's fixed cost dominates (§4 amortization vs §6).
Leakage: medium (commit subjects only).

## E3. meta-harness epic finalization: repair after round 1

**Decision point.** 2026-11-04 06:56:02, 62c8169 (finalization round 1 README): "Next: a repair
ticket for DEF-502, 504 and 505, then a fresh full integrated confirmation and the manual rechecks".

**Decision-time facts (source: 62c8169 finalization/README.md unless noted).**
- Full sweep at d2842f5: 11/14 green; Smoke and Court red from DEF-503 (shared `target/` symlink
  bakes another worktree's paths: environment/instrument), Deploy red from DEF-502 (node asserts the
  pre-MH-43 contract: instrument, minor). metaHarnessExternal 2,175 s green (earlier: 21m52s MH-17,
  33m15s MH-26, 34m20s MH-07).
- Manual regression vs claude-agent-acp 0.33.1, model `CLAUDE_sonnet` (named tester identity; no
  version). It found DEF-504 (major: refused model swallowed) and DEF-505 (major: timeout finishes
  as `completed`, events after `execution.finished`). BLIND row: echo double cannot refuse or be
  slow, so no graph could reach them. Same pattern as DEF-110 (Aug 2026, found by first manual run;
  mh-echo-agent.rs comment "blind to DEF-110, DEF-200 and DEF-338").
- Epic had ~47 tickets with per-ticket MATRIX/review artifacts (many comparable review points).
- Could NOT date: whether the reviewer for the repair would be the same model.

**Scope items.** DEF-504 (episode/model-refusal at harness boundary), DEF-505 (execution lifecycle
outcome + event ordering), 504-505 share the episode outcome/manifest path (+1), DEF-502 (Deploy node,
instrument), DEF-503 (shared target dir, instrument/environment). Total 5 (3 product-side, 2 instrument).

**REVIEW capacity.** 3-5 items; moderate confidence (many prior review points; tester model named but
reviewer version unknown). 504/505 lack red-on-base proof unless the echo double gains refusal and
slow modes.
**VERIFICATION capacity.** 2-3 items per cycle; low-moderate. Full graph ~40+ min wall
(External 36 min); two validation-origin faults this round (one hit two graphs); 504/505 reachable
only by manual reach (BLIND). **Binding: verification**, lower bound 2.

**Overrides.** two major escapes in a verified area (graphs green, manual caught) -> decrease;
instrument faults -> fix/isolate instrument first; §9.4 falsifier "escape its instruments could not
have caught -> lower verification capacity and add coverage".
**Provisional batch / controls (page).** Step 1: instrument ticket (DEF-502 node update, DEF-503
isolate `target/`), ahead via `depends_on`. Step 2: product ticket DEF-504+505 (coupled, small
batch of 2) with new fault-injecting double modes as red-on-base controls. Then one full integrated
confirmation + manual rechecks m2/m3. Decision: **decrease** (split instrument from product).
Planner: one repair ticket bundling all three. Page **partly disagrees** (structure), agrees on
"repair then fresh confirmation + manual recheck".
**Falsifier.** If round 2 is green on the full graph and manual rechecks with no new instrument
fault and no reopened boundary, the bundling cost nothing and the split was unnecessary.

**Outcome (read after the above).** MH-49 (one ticket, 06:57-10:36) first added echo-agent
model-option and slow-turn knobs and pinned DEF-504/505 RED on base (41707ad), fixed all three
(44e763a), took a review-corrections lap (cd82dea) and found a new defect DEF-520 in the same
model-selection path (9629f68). DEF-503 was not fixed; carried upstream and avoided by sweeping from
the main checkout. Round 2: full graph 14/14, corpus 204,452/204,452, manual rechecks r1-r4 pass.
**Verdict: partly agrees.** The page's controls (red-on-base via new double modes, fresh integrated
confirmation + manual recheck, instrument faults not charged to product) are exactly what happened;
its split of instrument from product work was unnecessary: the bundle converged in 2 laps (the §6
"at most two laps per layer" bound). Defensible: yes. Leakage: medium-high (round-2 subject seen;
page cites DEF-110 from this repo).

## E4. CDC mvp-stabilization (#462): MS-017 batch B7d-m2b-reds

**Decision point.** 2026-10-23 17:14:16, 769fde9f "plan(#462): MS-017 (#493), the M2b reds". Planner
chose: one ticket, wave 16, carrying M2B-LOAD-01, M2B-BEAM-01, M2B-BEAM-02, 12 graphs, gate-first
(red at tip, green after), load test only at milestones.

**Decision-time facts (source: 769fde9f / its parent).**
- M2B-LOAD-01: product regression introduced by the previous batch's REVIEW fix (MS-016 review,
  94cfe9ba); pipeline parity reference refused on every corpus. High severity (blocks M2 parity).
- M2B-BEAM-01: product, DEF-232 family (unbuilt jar on classpath), reached only now.
- M2B-BEAM-02: memory rule, measured over a partial onboard that stopped at BEAM-01.
- red-attribution.yaml before: M2-LOAD-01A/B-python (test), M2-BEAM-01 (test), MS016-RV-01A,
  DF04-DF06 (test), MS016-RV-ISO (environment: cdcWorktreeOverlayIsolation timeout 60 s after
  suites + 9 graphs on the same machine; "headroom thin"; node not replay-safe). So repeated
  validation-origin reds on the load fleet and one host-load fault on the isolation gate.
- review_policy: cadence milestone, gate false, milestones [1,4,5]; batches B2..B7c one ticket each.
- Model: commit trailers name "Claude Opus 5.5" on planner, implementation and review commits
  (identity known by name, version as written; harness not recorded).
- Could NOT date: the M2b load/Beam run directories outside the repo (/Volumes/dev/cdc-test-substrate);
  taken from the committed note.

**Scope items.** LOAD-01 (CREATE target parent, worktree-daemon-create) 1; BEAM-01 (Gradle project
dependency, gradle-native) 1; BEAM-02 (pyrefly pool memory) 1; BEAM-01/BEAM-02 share the Beam
onboard run and its measurement (+1). Total 4.

**REVIEW capacity.** 3-5 items; moderate confidence (same named model across many review points;
gate-first red proofs make items cheap) but last review introduced a regression.
**VERIFICATION capacity.** 2-3 items; low-moderate. 12 graphs per ticket on one host; isolation gate
has thin headroom under load; BEAM-02 needs a real Beam lifecycle run (manual/milestone reach) and
its evidence is invalidated once BEAM-01 changes the onboard (§8). **Binding: verification**, 2.

**Overrides.** high-severity escape from a reviewed area (LOAD-01), repeated validation-origin reds
on the load fleet -> **decrease**: halve, coupled items alone, `cadence: wave` + `gate: true` (§9.3).
**Provisional batch / controls (page).** Wave A: LOAD-01 + BEAM-01 (independent, each with
red-on-base). Wave B: BEAM-02 `depends_on` BEAM-01, remeasured on a full Beam onboard on an idle host.
Isolation gate: run last/alone or give its replay-safety its own ticket. Decision: **decrease**.
Planner: one ticket with all three -> page **disagrees** on structure.
**Falsifier.** If MS-017 closes all three in one lap, BEAM-02 holds after BEAM-01's fix, and the next
milestone (M2c) shows no red traceable to MS-017, bundling was fine.
**Outcome (read after the above).** MS-017 closed 2026-10-24 02:22 (one ticket; one fix commit per
finding, then review commits reopening BEAM-01 and BEAM-02 sizing). At M2c (tip 98cd89ef) new reds:
M2C-STEP-01 (later attributed to pre-epic layer-merge durability, not B7d), M2C-BEAM-02 (first reach
of the library phase, enabled by BEAM-01), and M2C-BEAM-03: the pyrefly-tree memory rule still over
budget on Beam (1887 vs 1664 MiB; "the B7d review predicted 1474 by the driver-only measure"; gates
ran under a VIRTUAL_ENV and were blind to the host-interpreter leak). MS-018/019 continued the family.
**Verdict: agrees (partly).** The page's falsifier fired against the bundled plan: BEAM-02 was closed
on a gate that could not see the real-Beam behavior, and the family recurred at the next milestone;
serializing BEAM-02 behind BEAM-01 with a real Beam remeasure is the control that would have looked.
But the recurrence's root cause predates the epic, so bundling did not cause it, and LOAD-01/BEAM-01
converged in one lap. Defensible: yes. Leakage: high (§9.3 of the page summarizes this outcome).

## Summary

| Episode | Both estimates? | Defensible decision? | Agrees with outcome? | Leakage risk |
|---|---|---|---|---|
| E1 polymarket E02 R1+R2 round | yes (review 3-5, verif 2-4; model unknown) | yes (lenient reading; strict §3 over-serializes) | agrees | high (page §9 cites C27/R1-R13) |
| E2 effectful-learning epic-10 rev72 | yes (review 4-6, verif 1-2; model unknown) | yes by literal §6 rule | **disagrees** (batch of 3 fixes worked) | medium |
| E3 meta-harness finalization repair | yes (review 3-5, verif 2-3; tester model named, no version) | yes | partly (controls match; split unnecessary) | medium-high |
| E4 CDC MS-017 / B7d | yes (review 3-5, verif 2-3; "Claude Opus 5.5" in trailers) | yes | agrees (partly; BEAM-02 recurred) | high (page §9.3 cites it) |

Metric: 4/4 held-out episodes yielded both estimates and a decision derivable from decision-time
facts. Outcome agreement 2 agree (both leak-contaminated), 1 partial, 1 disagree. No `§4` cost
comparison could be filled: every cost component was `unknown` at decision time in all four.

## Page ambiguities and defects found

1. §6 "**halve the next batch**, and put coupled items alone." The batch unit is undefined when the
   prior batch is one ticket (E2: halving 1 is 1) or a whole milestone/finalization (E1, E3).
2. §6 "**Fix or isolate the instrument** before expanding when the cause is validation-origin." Silent
   on whether several instrument fixes may be batched; E2 shows batching them was right, while the
   halve rule says the opposite. §4 amortization and §6 halving have no tie-break.
3. §3 / intro "A batch is **never larger than the tighter estimate**." No rule for an irreducible group
   larger than the lower bound (E1 R1: two sites, one build, 3 items vs bound 2).
4. §3.2 "Put coupled high-risk items **alone or in a small batch**." Leaves the split choice open
   (E3 DEF-504/505; E4 BEAM-01/02), so two evaluators can derive different batches.
5. §2 "A pair of items that share state, **a host resource** or an interface is an interacting effect."
   On a one-host epic every pair shares the host; the item count then grows quadratically. Needs
   "a contended host resource the items both exercise".
6. §6 override "a **high-severity escape (`blocking` or `major`)**". Severity is often unrecorded
   (E1's image-build failure); the page says write `unknown` but not whether an `unknown`-severity
   escape fires the override.
7. §1 "The reviewer/verifier identity is `unknown` in almost every audited row. ESD-01 found a named
   model in one record only." CDC commit trailers name "Claude Opus 5.5" on planner, implementer and
   reviewer commits; the Input table should list commit trailers as a source (identity, not version).
8. §6 "Increase only when **two consecutive review points**..." Undefined inside finalization/eval
   repair loops (E2 had nine scope amendments in a day; are those review points?).
9. Process defect: §9 worked examples use held-out episodes (C27, M2B-BEAM-02, DEF-110). Any held-out
   replay of this page on those repos is contaminated; future held-out sets should exclude them.
