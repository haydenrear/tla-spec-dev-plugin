# ESD-01 failure families

These families are ranked over the 117-row sample in `inventory.yaml`. Row IDs refer to that file.

**Ranking criterion.** Families are ordered by three things together:

1. how many repositories the family recurs in;
2. how often it recurs, counting recurrence inside a row;
3. the cost evidence in `cost.md`.

The ranking is a judgement over a sample. It is not a computed score.

**Origin is kept separate from the detection channel.** Each family is defined by **where the
defect lived**. The "seen through" line lists the channels that reported it. A family seen
through `test-graph` is usually **not** a defect in Test Graph. For example, the probe false reds
(F1) and the skill-manager home faults (F2) both turned graphs red, but neither originated in
the graph.

> **The two goals this file feeds.**
> - For GOAL-ESD-ARCH, the *validation-origin* families are F1, F2, F4, F5 and F6, plus the
>   eval half of F7. These are the ones ESD-03's preflight/review guidance should flag.
> - F3 (vacuous greens) is validation-origin too, but it costs escapes rather than time.
> - F8 (Test Graph's own product bugs) is product-origin for this repository. The bug-sweep
>   largely retired it.

---

## F1. Shared-host contention and process lifecycle under validation

**Origin.** Validation runs that share a host, a build output tree, or a process tree with other
runs. Examples:

- nested builds forking daemons that outlive their node;
- concurrent agents writing the same Gradle report directory;
- fixed time budgets that do not scale with load.

**Rows.**

| Repo | Row | What happened |
|---|---|---|
| plugin | `RP-07-DF-01` | KotlinCompileDaemon descendant |
| plugin | `BS-07-DF-05` | single-use Gradle daemon. **13 errored specWorkflow runs across 7 innocent tickets** |
| plugin | `#241 (polymarket#115)` | |
| polymarket | `E02-R11 / polymarket #115` | |
| CDC | `HOST-LOAD family` | ×14 |
| CDC | `GO-PERSISTER-TIMEOUT family` | ×6 |
| CDC | `MS-031-review-matrix-start-progress`, `FINAL2-LOAD-01`, `ATTR-234-07` | |
| MH | `DEF-154` | spec_unit about 70 min alone, projected about 20 h with two concurrent tickets |
| effectful-learning | `E10-NAV-OWNER-BLIND-001`, `EL #143` | |

**Seen through.** test-graph (most rows), the-suite, operator-doing-the-work.

**Cost evidence.**
- ≥ 1,281 s of recorded graph time spent re-running the probe, with 6 of the 13 runs untimed
  (cost.md C5).
- `spec.reference.adapters_resolve` **never ran** in bug-sweep milestone 1, because it sits
  behind the probe (`review/wave-3/review.md`).

**Candidate interventions.**

1. **Treat the validation host as a scheduled resource.** At most one graph per project output
   tree: #241's lock covers the canonical `run.py`/`discover`, but a raw `gradlew` is not
   covered. Ticket dispatch should be aware of host load (MH's DEF-154 "serial dispatch rule").
2. **Make the executor name what it reaps.** `RP-07-DF-01`'s carried half asks for this: print
   the command lines of surviving descendants, not bare PIDs. BS-07 needed a `ps` sampler again
   (`BS-07/probe-lingering-descendant-ps.txt`) to learn what the executor already had.
3. **Scale time budgets with what they bound, or report "budget exceeded" as errored rather than
   failed.** CDC's AT header calls this "a fixed budget against a cost that scales".

**Counterexamples and uncertainty.**
- The probe **passed** at kickoff on a quiet host (`baseline/graphs-default.txt`, 2 m 15 s). It
  also passed on the wave-5 tip at load average 21-30 on 10 cores (`review/wave-5/review.md`).
  So host load is not *sufficient* to cause the red.
- BS-07-DF-05's cause stays **inferred**. Nobody ran the controlled A/B that RP-07 ran for the
  Kotlin daemon.
- #241 was validated with fake `gradlew` children only. Whether it addresses BS-07-DF-05 is
  **untested**.

---

## F2. Home, toolchain and version skew (environment identity)

**Origin.** The validation ran against a different toolchain than the one under test. Examples:

- the wrong Skill Manager home tier on PATH;
- a floated or dropped pin;
- the installed copy of a skill instead of the branch copy;
- a path layout that changed when skills moved into the plugin;
- an operator-specific `java.home`.

**Rows.**

| Repo | Rows |
|---|---|
| plugin | `BS-03-DF-01` (plus **8 voided eval runs** in BS-17 traced to the same cause; cost.md C10), `BS-03-DF-02 / BS-05-DF-03`, `#194 / BS-09` (consequence), `BS-27 / DEF-HP9-002`, `missing-rung family (REACH)` (**9 recurrences**), `SI-25-DF-01`, `#248` |
| CDC | `SM402-ISOLATION family` (12 rows; cdcWorktreeOverlayIsolation 14 of 15 runs red in #234), `MS-027-ENV-TOOLCHAIN-PIN` |
| MH | `DEF-017 / DEF-126`, `DEF-412`, `DEF-282/283/360/402` |
| polymarket | `OBS-EVAL-MANAGER-LOCK-001`, `*-HOME-CUSTODY` (×6) |
| effectful-learning | `EL-NOTEBOOK-WEB-01 PREP-010` |
| skill-manager | `SM #386 / #102` |

**Seen through.** operator-doing-the-work, test-graph, eval, ci.

**Ranked first** because it is the only family present in **all six repositories**. It also has
the largest recurrence (the 9-recurrence REACH row and 12 CDC isolation rows).

**Cost evidence.**
- 12 voided eval runs, $2.71 (cost.md C10).
- CDC's environment/skill-manager, skill-manager-home and pins subcategories account for 18 of
  118 attributed reds (`velocity-retrospective.json`).
- **Counter-signal:** CDC environment reds carried only **2.73 known machine hours**, against
  28.28 h for product reds (C20). This family is cheap per run and expensive in cycles: reruns,
  waits, hand workarounds.

**Candidate interventions.**

1. **A preflight that prints and asserts the resolved toolchain identity** before any graph or
   eval runs, and refuses with a named error on a mismatch. It would cover which `skt`, which
   `skill-manager` version, which test-graph copy (installed or branch), unit pin SHAs and the
   home tier.
   - CDC built exactly this as "rank 3: the environment pre-flight" (`evaluation-20261104.md`),
     so a working precedent exists.
   - #248 asks for the same behaviour for eval wheels.
2. **Run graphs against the branch's units, not the installed home.** #194 made the installed
   copy authoritative, which reintroduced skew: doc-smoke and onboarding stay red until release
   (wave-5 review §3), and tickets fell back to the in-repo runner (wave-3 review §2).

**Uncertainty.** Several rows are classed `package/provider/environment` but **originate in this
plugin's own code**. The missing-rung resolvers are product code that assumed one layout, and
they are classed `product bug` in the inventory. The boundary between "environment" and "our
resolver did not handle the environment" is judgement.

---

## F3. Vacuous and blind greens: instruments that cannot fail

**Origin.** A gate, test, counter or fixture whose green does not depend on the behaviour it
claims to check. Examples:

- zero cases executed;
- wrong adapter imported;
- empty input passes;
- the fixture shape cannot produce the failure.

**Rows.**

| Repo | Rows |
|---|---|
| MH | `DEF-124 (with DEF-032, DEF-112)` (3 routes), `DEF-156`, `DEF-310 / DEF-411`, `DEF-302`; also `DEF-110` and `DEF-504`, both escaped every graph |
| plugin | `EA-DF-17`, `SI-14-DF-01`, `SI-27-DF-01` (recurrence 2), `SI-08-DF-01`, BLIND rows on `BS-HP-02` and `#226 / BS-HP-05` |
| CDC | `MS020-RV-03`, `ATTR-234-18`, `ATTR-234-36`, `ATTR-234-49`, `M2B-BEAM-02` (gate tolerance) |
| skill-manager | `DEF-OUN-023` (stale report count hid a real regression) |
| polymarket | `E02-R6-FIXTURE-PATH-ENV`, `E02-R13-DF-04`, `OBS-METRIC-SCOPE-001` |

**Seen through.** Mostly **hand and reading channels**: operator-doing-the-work,
independent-review, manual-final-testing. That is the signature of a blind instrument: by
construction, the instrument does not report itself.

**Cost.** Escapes rather than hours. DEF-110 escaped 123,132 spec-unit cases and 3,724 external
cases. DEF-124 produced a 6-second green over zero cases.

**Candidate interventions.**

1. **Every new or changed gate demonstrates red before it is trusted:** a planted-wrong control,
   mutation, or red-on-base. This plugin already requires it of bug fixes, and the bug-sweep
   proved 19/19 milestone-1 tickets red-on-base → green-on-branch (`review/wave-3/review.md`).
2. **Instruments report what they exercised, and zero means UNDECIDED.** Example: "0 cases ran"
   (DEF-124) or "0 edges retracted" (ATTR-234-36). This is `bug_attribution.md` §3's rule applied
   to run output.

**Counterexamples (successes).**
- MH-38 turned the `current` target **red** where it had been green. That proved the DEF-411 fix
  discriminates.
- CDC's new `cdcServerFactPath` gate caught a blocking product bug (`ATTR-234-28`) in 20 runs
  with 1 red.

**Uncertainty.** This family's size is a lower bound. By definition a blind green is found only
when somebody looks.

---

## F4. Stale and invalid assertions after a contract change

**Origin.** An assertion or fixture that encoded an old contract, or that was wrong from the
start, and went red on correct code. Examples:

- line-number citations;
- a literal version;
- an old restart contract;
- implicit activation;
- a negator searched on one line only.

**Rows.**

| Repo | Rows |
|---|---|
| plugin | `BS-07-DF-04` (48 stale line citations, recurrence 2), `BS-26-D1` (in the bug-sweep ledger), `#245`, `#247`, `EA-DF-09` |
| MH | `DEF-502`, `DEF-393`, `DEF-054/070/071/093 / MH #52` |
| effectful-learning | `EL #163 / #170 / #105` ("This is a validation instrument defect"), `EL-NOTEBOOK-WEB-01 OBSERVER rows` (29) |
| polymarket | obsolete OBS scaffold inside `polymarket full-sweep triage 20261109-003240`, `E02-R13-DF-03` |
| CDC | `M2-LOAD-01A`, plus 12 "test/stale-gate" reds in the CDC retrospective |
| skill-manager | `SM #344`, `EV-I-02` |

**Seen through.** test-graph, the-suite, eval, ci.

**Candidate interventions.**

1. **Apply `validation-review.md`'s "a changed contract reruns every instrument that asserts it"
   at ticket time.** This needs the binding from contract to asserting nodes, and it must cover
   **other repositories' assertions too**. BS-27 shows skill-manager graphs asserting this
   plugin's text, while this repository stays green.
2. **Prefer behavioural assertions over source-text pins.** Line citations and literal versions
   are a standing source of false reds.

**Counterexample.** polymarket's E02-CI-EVAL profile went 14/14 green in 934.87 s after its
repair tickets. Stale assertions *can* be retired to a stable state within one epic.

---

## F5. Fixture isolation, leaked state and checker scan scope

**Origin.** Validation side effects escaping their sandbox, or checkers reading what validation
left behind. Examples:

- graphs writing the operator's root home;
- leaked temp homes filling the disk;
- shared fixture state that makes results order-dependent;
- shared `target/` directories;
- checkers that walk build output as if it were source.

**Rows.**

| Repo | Rows |
|---|---|
| CDC | `CDC #262` |
| skill-manager | `SM #378 / DEF-OHV-011 / DEF-OHV-180` (recurrence 2, the same day), `DEF-OHV-010 / SM #294` (35k dirs / 41 GiB; **27 of 46 wide-round-1 eval runs died on ENOSPC**), `DEF-OHV-121` |
| MH | `DEF-503` |
| plugin | `SI-27-DF-06 / verify.sh BLIND` (fixed one instance at a time **3 times**), `HP-01-DF-01` |

**Seen through.** operator-doing-the-work, the-suite, test-graph.

**Candidate interventions.**

1. **Hermetic fixture homes:** never parent on a real home, and add a post-run assertion that
   the temp tree was removed. Inverting `test_graph/README.md`'s "nested probe build must own
   every process it starts" gives the matching file-system rule.
2. **Checkers enumerate with `git ls-files`, not a directory walk.** This is the
   attribution.yaml BLIND row's own recommendation.

---

## F6. Cold setup and planning overhead (a cost family, not a defect family)

**Origin.** Fixed per-launch costs before any node asserts anything. Examples:

- fresh Gradle and serial describe;
- cold uv caches;
- per-worktree offline wheels;
- multi-hour onboarding of real repositories.

**Rows and evidence.**

| Repo | Row | Evidence |
|---|---|---|
| effectful-learning | `E10-OWNER-GRAPH-STARTUP-001` | 52% of accepted-run invocation outside node windows; median 93 s before the first node (cost.md C26) |
| skill-manager | `SM #295` | cold 3 × 180 s killed; warm 4 m 50 s (C28) |
| plugin | `EA-DF-15` → `#248` | the fix for the cold uv cache created the per-worktree wheel defect |
| CDC | Beam onboard | 8,335 s (C21) |

**Candidate interventions.**

1. **Warm, shared, per-host setup** for caches and describe results, with an explicit
   cold/warm label on every run report so the two can be compared.
2. **Tension with F1:** long-lived daemons are the obvious warm-reuse tool, and they are exactly
   what the process-ownership contract reaps (RP-07-DF-01). Any warm-reuse design must state its
   process-ownership story.

**Uncertainty.** No repo records a matched cold and warm run of the same graph, except
skill-manager #295. The warm-reuse benefit is **unmeasured**.

---

## F7. Eval-instrument defects (the eval harness is newer than what it measures)

**Origin.** The eval lane's own cases, graders, sandbox and toolchain.

**Rows.**

| Repo | Rows |
|---|---|
| plugin | `#245`, `#246`, `#247`, `#248`, `BS-17 budget-only fails`, `SI-15-DF-05 / EA-DF-08`, `SI-14-DF-01` |
| skill-manager | `SM eval round 2026-09-07 (instrument rows, incl. EV-I-08 TMPDIR)`, `EV-I-12`, `EV-I-02` |

**Measured ratio.**
- skill-manager's first round: **4 product vs ~12 instrument** (primary record:
  `skill-manager/specs/evals/results/2026-09-07-epic-provisions-a-ticket-worktree.md`, $13.06 for
  14 runs).
- Its ledger over 2026-09-07 to 09-10: product 11, instrument 18.
- BS-17: 15 cases failed, and 7 of those were explained without a comparison
  (`specs/evals/bug-sweep/README.md`).
  - 4 were instrument defects: a case targeting a skill not in the plugin, a grader false
    negative, the sandbox, and a missing fixture.
  - 3 failed only on the tool-call budget.
  - A further 12 runs were voided for setup reasons.

**Candidate intervention.** The eval lane refuses to start, with a named error, when its
prerequisites are absent: wheels, a sandbox capability, a fixture. This is #248's own ask, and
the plugin_evals.md TMPDIR lesson. It costs $0 per refused case.

**Counterexample (success).** The eval graders caught EV-P-03..08, which are real product
defects. EV-P-07 cut a case from 38 to 14 Bash calls and from $1.83 to $1.00.

---

## F8. Test Graph's own reporting and resume defects (product origin, largely retired)

**Rows.** `#175 / BS-03`, `#185 / BS-11`, `#195 / BS-10`, `#186 / BS-13`, `#226 / BS-HP-05`,
`SI-19-DF-01`, `SI-19-DF-05`; also `DEF-OHV-140` (OTLP exporter blocking).

**Status.** The bug-sweep fixed the first five with red/green proof. Five of five graphs passed on
the tip (`review/wave-5/review.md`). #226 was found **by a consumer epic's close-out**
(skill-manager #411), not by any graph: see the BLIND row.

**Still open:**
- BS-13-DF-02 (macOS `/var` vs `/private/var` lexical refusal);
- SI-19-DF-01 (scaffold's own next step is red);
- SI-19-DF-05 / DEF-OHV-140 (OTLP noise and blocking with no collector).

**Why it is ranked last.** It is the one family where the epic-sized intervention demonstrably
worked.

---

## Reliable and successful graphs: what the failures should not hide

| Graph or instrument | Record | What made it reliable or useful |
|---|---|---|
| plugin cliWorkflow, effectProviderExamples, sktSurface, sktHooks | passed through bug-sweep milestone 1 on the in-repo runner (wave-3 `sanity/`) and 5/5 on 2f3e85c4 | no nested builds; self-contained temp repos |
| plugin bug-sweep red-on-base → green-on-branch | 19/19 tickets (wave-3 review) | demonstrated discrimination per fix (the F3 intervention, already practised) |
| CDC cdcServerFactPath | 20 runs / 1 red; caught blocking `ATTR-234-28` | created from a census coverage gap (`ATTR-234-25`); exercises the real server path |
| CDC Beam full lifecycle (manual-final-testing) | main catcher of scale product bugs (`M2-BEAM-02`, `M2B-BEAM-02`) | a real repository whose sources lie outside its directory; no synthetic corpus had that shape |
| CDC cdcServedIndexGate | 9 runs / 0 red | clean, but **not shown to discriminate**. It is a candidate F3 BLIND, not a proven success |
| MH metaHarnessConcurrency / Durable / Parity / Compaction | 5/5 green locally; DEF-352 caught by graph | — |
| polymarket epic02Acceptance | caught `E02-EVAL-FORWARD-CAUSAL` (blocking) | integrated acceptance over real evaluation code |
| polymarket E02-CI-EVAL | 14/14 PASS, 934.87 s | after the R1..R13 repair series |
| skill-manager artifact-dag | stable red on real bug #292 ("stable, not flaky") | a reliable red is as valuable as a reliable green |

**Common thread** (inferred from the rows above):
- Graphs that drive **real systems or real repositories** catch product bugs.
- Graphs that demonstrate a **red control** can be trusted.
- The unreliable graphs share a host, a home or a process tree with something else (F1, F2, F5).

## Cross-cutting observation for ESD-03

**The seven classes mix two axes.** `product bug`, `graph … defect`,
`package/provider/environment fault` and `invalid assertion` name an **origin**. `false green` and
`false red` name a **signal effect**.

The second reading in `local-signal.md` disagreed on 3 of 10 classes. All three disagreements sit
exactly on this boundary: false red vs invalid assertion, and invalid assertion vs fixture defect.

Recording both, as the inventory's `consequence` field does for many rows, removes the ambiguity
without a new schema.
