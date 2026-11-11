# GOAL-ESD-ARCH: hold-out application of the graph-architecture-review checklist

Blind evaluator. Goal measured: "attributable validation-infrastructure failures become concrete
repo-specific preflight review priorities". Instrument: the checklist in
`skills/test-graph/references/graph-architecture-review.md` (rule ids A1..H4), branch
`feature/240-evaluation`.

## Method

**Read:** all of `graph-architecture-review.md` (including its worked review); all 117 rows of
`specs/results/evidence-sized-delivery/ESD-01/inventory.yaml`. When the row text was too thin to
decide, I opened these primary records (read-only):

- CDC `specs/results/mvp-stabilization/red-attribution.yaml` (M2-LOAD-01A, M2B-LOAD-01, MS020-RV-03,
  MS-031, SM402 rows) and `deferred-ledger.yaml` (MS-012-DF-07);
- CDC `specs/results/cdc-index-successor/attribution.yaml` (ATTR-234-03, -07, -18, -25, -26, -49);
- meta-harness `specs/.history/meta-harness-{mvp,loop}/closed-snapshot/deferred_findings.yaml`
  (DEF-070, DEF-110, DEF-112, DEF-126, DEF-156, DEF-282, DEF-283, DEF-310, DEF-360, DEF-393, DEF-402,
  DEF-412, DEF-502, DEF-520);
- polymarket `specs/results/E02-R2/validation.json`, `E02-R6/attribution.yaml`,
  `E02-R1/home-provenance.json`, `deferred/E02-R1.yaml`;
- effectful-learning `specs/results/deferred/EL-NOTEBOOK-WEB-01.yaml` (PREP-010 and the OBSERVER rows);
- skill-manager `specs/evals/results/attribution.yaml` (EV-I-12);
- this repo `specs/results/deferred_findings_final.yaml` (SI-18-DF-01, SI-19-DF-04, SI-25-DF-06,
  EA-DF-17, SI-15-DF-05, EA-DF-08) and `specs/results/deferred/attribution/attribution.yaml:53-86`;
- GitHub issues (`gh issue view`, read-only): skill-manager #344, #293, #386; effectful-learning
  #143, #170; commit-diff-context-parent #390; tla-spec-dev-plugin #246.

**Not read (bias control):** `ESD-03/`, `review/`, `ESD-06/`, and anything found by searching for
the flag/miss table. I did not read `ESD-01/local-signal.md` or `failure-families.md`.

**Verdict rules applied.** I judged each node or instrument **as it was before the failure**. I did
not use the fix as evidence that a rule applied.

- **F**: a named rule names the defect or its exact precondition, and the defect lives in a graph
  node or its `support/` code, where a reviewer using this page would look.
- **P**: a rule raises the risk or the review question, but would not have prevented or detected this
  failure. This covers an inferred mechanism, a fix that is runtime or dispatch policy, and a defect
  outside a graph node: an eval harness, a pytest/JUnit test, a CLI, a provider, a workflow doc.
- **M**: no rule id reaches it.

I cite only the numbered rules. The five preamble questions (oracle validity, false-green/false-red
risk, ...) reach almost every row, so they do not count. The un-numbered sentence "a changed contract
also reruns every instrument that asserts it" also does not count. Where it is the only thing that
reaches a row, I say so.

**Contamination note.** `BS-03-DF-01` and `#186 / BS-13` were not on the exclusion list, but the
checklist cites them as evidence (B1 and G2). `BS-03-DF-01` stays in the hold-out and is marked.
`#186` is excluded as product-origin anyway.

### Exclusions

**Author-scored rows (40 inventory rows), excluded as instructed:** RP-07-DF-01, BS-07-DF-05,
#226/BS-HP-05, #195/BS-10, #194/BS-09, BS-07-DF-04, #245, #247, #248, SI-27-DF-01,
missing-rung family (REACH), SI-12-DF-05/SI-13-DF-01, SI-25-DF-01, SI-27-DF-06/verify.sh BLIND,
SI-19-DF-05, EA-DF-15, EA-DF-09, SI-08-DF-01, HP-01-DF-01, R4-DF-03/DEF-001, #241 (polymarket#115),
#233 fixture, SM402-ISOLATION family, CDC #262, GO-PERSISTER-TIMEOUT family, HOST-LOAD family,
MS-027-ENV-TOOLCHAIN-PIN, ATTR-234-36, DEF-124, DEF-154, DEF-110, DEF-503, E02-R11/polymarket #115,
OBS-EVAL-MANAGER-LOCK-001, E10-OWNER-GRAPH-STARTUP-001, E10-NAV-OWNER-BLIND-001, SM #295, DEF-OHV-140,
DEF-OHV-010/SM #294, SM #378/DEF-OHV-011/DEF-OHV-180. BS-13-DF-02 is not a row of its own. It is a
residual inside `#186 / BS-13`, which is excluded below as product.

**Excluded as product-origin (21):**

| Row | Reason |
|---|---|
| #185 / BS-11 | test-graph `run.py` reporting is this plugin's product (worked review: "its defects are product-origin here") |
| #175 / BS-03 | same, runner reporting of a dead Gradle |
| #186 / BS-13 | same, runner resume front door (BS-13-DF-02 is inside it) |
| SI-19-DF-01 | test-graph `scaffold.py` next-steps text, a product of this plugin |
| BS-01-DF-01 | spec-double-2 manifest loader cannot parse YAML anchors |
| BS-08-DF-03 | `close_tickets.py` truncates the refusal message |
| BS-21-DF-02 | `spec_evolution` snapshot basename collision |
| BS-HP-02 | `skt ticket sweep` squash-merge detection (the fixture blindness is a consequence) |
| BS-27 / DEF-HP9-002 | plugin skill text asserted cross-repo; the defect is the text |
| M2-BEAM-02 | GradleLibrarySources archive-wide byte bound |
| M2B-BEAM-02 | LanguageServerPool recycle (the gate tolerance is a contributing blind spot, not the origin) |
| ATTR-234-28 | the CLI never reads the server edge set |
| DEF-302 | batch spec-step deadlock (the Cursor fixture shape is contributory) |
| DEF-352 | events follow never ends |
| DEF-504 | driver discards the set_config_option result |
| DEF-520 | inventory says fixture defect, but the primary record's surface and fix are production `crates/mh-acp` model selection: product |
| E02-EVAL-FORWARD-CAUSAL | `frozen.py` evaluate_pair causal order |
| E02-R13-DF-04 | diagnostics journal canonicalisation |
| E10-FINAL-HISTORY / VIEW-INTENT | notebook product guidance |
| SM eval round (product rows) | skt / skill-manager CLI front-door defects |
| SM #292 / DEF-HBR-003 | uninstall does not prune the census |

DEF-520 is the only row whose class I changed after reading the primary record.

**Excluded as unattributed, or not an instrument failure (8):**

| Row | Reason |
|---|---|
| BS-10-DF-01 | a prose claim in a finding record, not an executable instrument |
| BS-08-DF-01 | spec actions without adapter bindings; class unresolved, owner-batched spec gap |
| BS-08-DF-02 | a deliberately red control kept red by owner decision |
| BS-17 budget-only fails | unresolved, cause inferred, no base measurement |
| BS-17 catch-the-drift | unresolved eval noise |
| FINAL2-LOAD-01 | unresolved, sender of the signal unknown |
| OBS-EOF-HISTORICAL-UNRESOLVED / #49 | unresolved, did not reproduce |
| SM #297 | unresolved |

**Arithmetic:** 117 − 40 author-scored = 77. Of those 77, 21 are excluded as product (the 21 rows in
the product table) and 8 as unattributed or not an instrument, leaving **48 selected**.

**Inclusion calls worth auditing:**

- `SM #293` is included, although its inventory class is "product bug". Its origin text is the
  switched-off CI graph schedule that hid the product defect.
- `BS-03-DF-02`, `DEF-282/283/360/402` and `*-HOME-CUSTODY` are included because the prompt's origin
  list names environment, home and provider.
- `E02-ADVISORY-READER-01` is included because, from polymarket's side, the tla-spec-dev close-out
  advisory acts as a checker that produced a false red.

## Hold-out table (48 rows)

| # | Row id | Repo | Family / class | Node or instrument | Verdict | Rules | Reasoning | Source |
|---|---|---|---|---|---|---|---|---|
| 1 | BS-08 checkout-dependent test | tla-spec-dev-plugin | false red, test determinism | pytest `test_ticket_retirement` | M | none | Selecting by checkout mtime is a nondeterminism no rule names, and the instrument is a pytest, not a node. | row |
| 2 | BS-03-DF-01 (cited by B1) | tla-spec-dev-plugin | env, home tier | agent session PATH / 8 eval runs | P | B1 | B1 names root-vs-project home skew exactly, but the defect is the agent session PATH and the eval lane, not a graph node. | row |
| 3 | BS-03-DF-02 / BS-05-DF-03 | tla-spec-dev-plugin | env, agent sandbox | auto-mode permission classifier | M | none | A permission classifier blocking a workflow command is outside every rule. | row |
| 4 | #246 | tla-spec-dev-plugin | env, eval sandbox | eval case w-giw-wt-refusal-quotes-subject | P | H4 | H4 would make a sandbox-blocked git a named precondition, but nothing in the page reviews eval sandbox capabilities, and it is not a node. | primary |
| 5 | SI-14-DF-01 | tla-spec-dev-plugin | false green, eval harness | `claude plugin eval` drops hooks | P | B1 | B1's "what does it actually execute against, and does the report say so" raises it, but the defect is upstream eval CLI behavior. | row |
| 6 | SI-19-DF-04 | tla-spec-dev-plugin | false red, machine state | pytest `test_eval_toolchain_pin` | P | C1 | C1 names "green warm, red in a fresh worktree" exactly, but the instrument is a pytest, not a node. | primary |
| 7 | SI-18-DF-01 | tla-spec-dev-plugin (oracle in skill-manager) | false red, oracle stability | skill-manager home-leak oracle node | F (borderline) | C4 | C4 asks what the node shares with concurrent writers, including "a shared home"; here the live Claude client rewrites a watched tree about every 4 min, inside a graph node's oracle. | primary |
| 8 | EA-DF-17 | tla-spec-dev-plugin | false green, eval fixture | eval fixture + scaffold bindings | P | B1, H1 | B1 (the binding runs the baseline copy, not the one under test) and H1 raise it, but the defect is in an eval fixture and the scaffold, not a node. | primary |
| 9 | SI-15-DF-05 / EA-DF-08 | tla-spec-dev-plugin | eval harness capacity / verdict plumbing | `place.sh` / `verify.sh` | P | H4 | H4's "a name a reader can attribute" names EA-DF-08 (the UNDECIDED reason never reaches the score), but it is eval harness code, and the 20k ceiling is a CLI capacity limit. | primary |
| 10 | M2-LOAD-01A | CDC | invalid assertion, measurement | `persister_cost_summary` in cdcOverlayLoadTest | M | none | The verdict aggregated every cold base as one; no rule asks whether a verdict's aggregation is correct (H1/H2 cover vacuity and red controls, not a wrong sum). | primary |
| 11 | M2B-LOAD-01 | CDC | fixture defect + misattribution | harness `onboard_reference` scratch dir | P | F3, H4 | F3 ("name who creates it") and H4 (named precondition) raise it, but F3 is a hypothesis rule and the misattribution came from report truncation at 400 chars, which no rule covers. | primary |
| 12 | MS-031-review-matrix-start-progress | CDC | invalid assertion, timing | JUnit `WorktreeDaemonStartProgressTest` | P | D2 | D2 names a fixed budget against a load-scaling cost, but this is a JUnit test, not a node. | primary |
| 13 | MS020-RV-03 | CDC | false green, vacuous gate | `intellij_step_time_verdict` (cdcOverlayLoadTest assertion) | F | H2, H1 | `verdict({}) == True` is exactly "zero exercised is not a pass". | primary |
| 14 | ATTR-234-07 | CDC | orchestration, fixed budget | `test_graph/support/cdc_project_toolchains.py` `_git_output` | F | D2 | A flat 10 s nested bound against a cost that scales with tree size and 8 concurrent nodes is D2's "fixed budget ... false red waiting for a busy host". | primary |
| 15 | ATTR-234-18 | CDC | false green, vacuous gate | `test_graph/support/cdc_merkle_reconciliation.py` | F | H2, H1 | Gates passed with comparedEqual 0 everywhere: H2 (count > 0) names it. | primary |
| 16 | ATTR-234-25 | CDC | orchestration, coverage gap | 32 graphs, one reaching the server fact path | M | none | No rule asks which graphs reach a given product path; the checklist is per node. | primary |
| 17 | ATTR-234-49 | CDC | false green, assertions never ran | cdcCliQuery dummy fixture | F | H1, A3 | H1 demands a cited red on a planted wrong answer, which is impossible when the fixture never builds the index and the assertions never execute. | primary |
| 18 | ATTR-234-03/04/39 | CDC | invalid assertion, tautology | TLA+ model conjuncts (TLC) | P | H1 | A mutation control (H1) would expose a tautology, but the instrument is a spec model, not a graph node. | primary |
| 19 | ATTR-234-26/27 | CDC | env, cluster | `telemetry_reached_a_live_collector` / local k3d | P | H4, D1 | The node was right about the environment. H4 helps attribution, and D1's "a readiness predicate can itself be wrong" touches the misleading port check; nothing prevents a crash-looping cluster. | primary |
| 20 | CDC #390 | CDC | env, fresh worktree / OTLP / load | several JUnit tests | P | C1, D2, H4 | Fresh-worktree prerequisites (C1), the memory/load bound (D2) and the reason pushed out of the stderr tail (H4) are raised, but the instruments are unit tests, and OTLP noise has no rule. | primary |
| 21 | DEF-156 | meta-harness | false green, corpus generation | `generate cases --state-projector` (workflow doc) | P | B1, H1 | Using the project projector instead of the ticket's own is an identity skew (B1), and a planted wrong value in the new field would show it (H1), but the defect is a documented command, not a node. | primary |
| 22 | DEF-310 / DEF-411 | meta-harness | false green, binding | case_adapters bindings + `test_graph/support/mh_spec_cases.py` | F (borderline) | H1, B1 | The node support asserted the three adapters "byte-identical so harmless"; a mutation of the ticket's adapters (H1) would not have gone red. MH-38's red-on-base is exactly H1's control. | primary |
| 23 | DEF-017 / DEF-126 | meta-harness | env, home tier | `mh.spec.external-baseline` node env | F | B1 | The node fell through to the default root home when `SKILL_MANAGER_HOME` was unset: B1's "must not fall through to the next candidate". | primary |
| 24 | DEF-021 / MH #56 | meta-harness | env, CI provisioning | CI lane (cannot install test-graph) | M | none | CI provisioning of the runner is outside node review. C2 is about a node's own downloads and the CI already printed NO GRAPH RAN. | row |
| 25 | DEF-393 | meta-harness | invalid assertion | `test_graph/sources/dogfood_parity.py` `sse_events` | P | D1, H1 | Closure measured with one `readline` is close to D1 (poll the condition) and H1 (red/green controls), but no rule names an instrument that agrees with the defect via its client helper. | primary |
| 26 | DEF-412 | meta-harness | stale path after layout move | `test_graph/support/mh_guards.py` `home_skill()` | P | B1, H4 | The node refused with a named error (H4 held). B1 covers resolution but not a hard-coded rung that a layout move invalidated; same family as missing-rung. | primary |
| 27 | DEF-502 | meta-harness | stale assertion after contract change | `mh.deploy.lifecycle` | M | none (un-numbered preamble only) | Only the un-numbered sentence "a changed contract reruns every instrument that asserts it" reaches it; H3 is about source text, not an old behavioral contract. | primary |
| 28 | DEF-282/283/360/402 | meta-harness | provider defects (skill-manager 0.26.0) | homes / image build | M | (B1 for DEF-402 only) | Token copying, baked absolute paths and silent reanchor are provider defects outside every rule; only DEF-402 (versions never enforced) touches B1. | primary |
| 29 | DEF-054/070/071/093 / MH #52 | meta-harness | invalid assertion, non-discriminating | `test_graph/sources/concurrency_suite.py` etc. | F | H1 | "Asserts a property holds but not that it discriminates" is H1 verbatim. | primary |
| 30 | E02-R2 / E02-R5 MODEL-TARGET | polymarket | orchestration, target lifecycle | `pe04.model` | P | B1, F3 | Which target the node resolved (B1) and the lifetime of the ticket path (F3) raise it; no rule names a target selected from an archived ticket. | primary |
| 31 | E02-R6-FIXTURE-PATH-ENV | polymarket | false green, harness tests | six harness tests over the fixture execution contract | P | H1, F1, B1 | The seeded node regressions that caught it are H1's control; child env and private paths are F1/B1 territory. The blind instruments were unit tests that mirrored layout. | primary |
| 32 | E02-R13-DF-03 | polymarket | invalid assertion, platform | permission-counter fixture | M | none | A platform-dependent exact count (Darwin adds EPERM) has no rule. | row |
| 33 | polymarket full-sweep triage 20261109-003240 | polymarket | env / portfolio staleness | 15 errored graphs | P | C2, H4, D2 | Deferred-Kubernetes fixtures should be opt-in (C2), preconditions named (H4), timeouts (D2); obsolete nodes and portfolio staleness have no rule. | row |
| 34 | OBS-METRIC-SCOPE-001 | polymarket | false green | observability correlation harness | F | H1 | An unrelated counter satisfying the assertion is what an H1 planted wrong answer (wrong-source control) detects; the fix was 22 such controls. | row |
| 35 | E02-ADVISORY-READER-01 | polymarket | false red, checker parser | tla-spec-dev close-out advisory YAML reader | M | none | A parser miscounting duplicate keys is outside every rule. | row |
| 36 | *-HOME-CUSTODY (R1..R8) | polymarket | env, home provenance | cloned unit gitdirs in homes | P | B1 | B1's "publish the resolved identity: path, commit, source" names unverifiable provenance, but it is home custody, not a node. | primary |
| 37 | EL #143 | effectful-learning | fixture race | native HTTP fixture port bind/release/rebind | M | (C4 tangential) | No rule covers port allocation; C4's host-sharing question would need the reviewer to think of ephemeral ports. | primary |
| 38 | EL #163 / #170 / #105 | effectful-learning | stale fixture contract | releasePackaging / streamOrganization fixtures | M | (H4 for #105 only) | Fixtures driving a legacy `/input` envelope after a product contract change match only the un-numbered preamble; #105's missing provider setup touches H4. | primary |
| 39 | EL-NOTEBOOK-WEB-01 OBSERVER rows (29) | effectful-learning | invalid assertion, browser observer | notebook web graphs | P | D1, D2, E2, F3, A1, H2 | Read 29 summaries. About 9 are reached: frame-readiness cuts (D1), 316 MB copy timeouts (D2), non-idempotent detach and fixture process custody (E2), destructive mount ordering (F3/A1), wrong-prefix empty match (H2). The majority, oracle precision about product semantics, are M. | primary |
| 40 | EL-NOTEBOOK-WEB-01 PREP-010 | effectful-learning | env, PATH precedence | managed command preparation | P | B1 | B1 names it (record and refuse the CLI actually resolved), but it is an operator preparation step, and no mismatch was observed. | primary |
| 41 | SM eval round (instrument rows, EV-I-08 TMPDIR) | skill-manager | env, eval sandbox | eval harness | P | H4, B1, F1 | An unset TMPDIR and PATH aliasing would be named preconditions (H4) or a hermetic env (F1), but this is eval harness, not a node. | row |
| 42 | EV-I-12 | skill-manager | false red, harness | eval Stop hook exits before writing verdict | M | none | A grader that can never pass because its hook exits early is not reached; H1 is about red controls, not a never-green instrument. | primary |
| 43 | EV-I-02 | skill-manager | invalid assertion, grader | eval extractor | P | H3 | Matching literal spellings is the H3 "text, not behavior" shape, but in an eval grader. | row |
| 44 | DEF-OUN-023 | skill-manager | false green, aggregation | local Gradle sweep + stale reports | P | A1, G2 | A1 notes the stop-on-first-failure skip, and G2 asks for a rerun from the start before anyone calls it green, but counting stale reports at sweep level is outside node review. | row |
| 45 | SM #344 | skill-manager | invalid assertion, shared node vs planted defect | `home.fixpoint.law` | M | none | A shared law node binding to an exit code that a sibling fixture deliberately breaks has no rule (A1 is about data edges, H1 about red controls). | primary |
| 46 | SM #293 | skill-manager | CI scheduling | graphs suspended on push/PR | M | none | Graph scheduling and CI triggers are not in the checklist. | primary |
| 47 | DEF-OHV-121 | skill-manager | fixture shared state | node deletes `pm/` in a shared fixture home | F | A1, E2, F2 | A1's "write that shared state down as a dependency instead of relying on list order" names graph-order dependence on shared fixture state, and E2 scopes cleanup to what the node created. | row |
| 48 | SM #386 / #102 | skill-manager | env, toolchain version skew | bundled uv 0.4.18; testgraphsdk skew | P | B1 | B1 (publish the resolved version, refuse a mismatch) raises the version skew, but both are provider defects outside any node. | primary |

### Hold-out counts (n = 48)

| Verdict | Count | Share |
|---|---|---|
| F | 10 (2 borderline: SI-18-DF-01, DEF-310/411) | 21% |
| P | 24 | 50% |
| M | 14 | 29% |

Source: 35 rows needed the primary record, and 13 were decided on the row text alone.

Strict F, without the two borderline rows: 8/48 (17%). F+P: 34/48 (71%).

By location of the defect:

| Location | Rows | F / P / M |
|---|---|---|
| Inside a graph node or its `support/` | 21 | 10 / 6 / 5 |
| Outside any node (eval harness, unit tests, CLI, provider, CI, workflow) | 27 | 0 / 18 / 9 |

Inside-node rows: SI-18-DF-01, MS020-RV-03, ATTR-234-07, -18, -49, DEF-310/411, DEF-017/126,
DEF-054 family, OBS-METRIC-SCOPE-001, DEF-OHV-121 (F); M2B-LOAD-01, ATTR-234-26/27, DEF-393, DEF-412,
E02-R2, OBSERVER rows (P); M2-LOAD-01A, DEF-502, E02-R13-DF-03, EL #163/#170/#105, SM #344 (M).

## Task 2: independent re-score of 12 author-scored rows

| Row | Verdict | Rules | Reasoning | Source |
|---|---|---|---|---|
| RP-07-DF-01 | F | E1, C3, A3, A4 | The pre-failure node was an assertion running a nested Gradle build with Kotlin's default daemon strategy; E1 names pinning `kotlin.compiler.execution.strategy=in-process` and C3 names KotlinCompileDaemon as shared state. | row |
| #241 (polymarket#115) / E02-R11 | P | C4 | C4 asks what the node shares with a concurrent run (the output tree), but the race is in the canonical run/discover commands, and the fix is a runtime lock, not a node change. | row |
| DEF-154 | P | C4, D2 | C4 raises host contention, but the remedy is a serial-dispatch rule; no node review prevents two tickets saturating one host. | row |
| missing-rung family (REACH) / SI-25-DF-06 | F (for SI-25-DF-06); family otherwise P | B1 | `_resolve_giw` in `skt.ticket-roundtrip` fell through to cloning upstream and tested the wrong code, exactly B1's "must not fall through to the next candidate". The other 8 recurrences are product resolvers outside nodes. | primary |
| SM402-ISOLATION family | P | D2, C1, H4 | The testbed `cdc.skill-manager-worktree.provisioned` already named the precondition (H4 held). D2/C1 raise its fixed 120 s bound against a scaling upstream whole-home sync, but the cause and fix are upstream skill-manager#402. | primary |
| EA-DF-15 -> #248 | P | C1, C2, H4 | C1/C2/H4 name the mechanism exactly (cold empty uv cache, no network, wheels absent fail silently as reds), but both defects are in the eval lane and skill-script launch, not a graph node. | row |
| E10-OWNER-GRAPH-STARTUP-001 | P | C1, A2 | C1 (cold Gradle per launch) and A2's note that the SDK describes every script raise the cost, but the planning cost is runner behavior, and no node change removes it. | row |
| DEF-503 | P | C3, F1 | C3 (shared caches/build output are shared state) raises it, but the symlinked `target/` came from worktree provisioning, outside any node. | row |
| DEF-124 | P | H2, H1 | H2 names "green over zero cases" exactly, but the defect is in the plugin's `run spec-unit-tests` CLI, run by an operator (primary record: `test_graph: []`), not in a graph node. | primary |
| DEF-110 | M | none | A product surface-parity bug that no assertion covered. H1 asks for red controls on existing assertions, and no rule asks whether any graph reaches a surface. | primary |
| #226 / BS-HP-05 | P | B2, G2 | B2 raises the risk of trusting documented resume and tells you how to check that a fix is installed, but no node-level rule detects a runner defect; it was found by a consumer close-out. | row |
| SI-19-DF-05 | M | none | Exporter stack-trace noise with no collector is not reached by any rule. C2 is about downloads; there is no log-hygiene rule. | row |

### Re-score counts (n = 12)

| Verdict | Count |
|---|---|
| F | 2 (RP-07-DF-01; SI-25-DF-06 instance only) |
| P | 8 |
| M | 2 |

## Where the checklist misses

1. **Verdict arithmetic and parsing.** A verdict that computes the wrong number is not a vacuity
   problem, so H1/H2 do not reach it. Examples: summing bases (M2-LOAD-01A), a YAML reader
   miscounting (E02-ADVISORY-READER-01), a platform-dependent exact count (E02-R13-DF-03).
2. **Stale behavioral assertions after a contract change.** DEF-502 and EL #170 are reached only by
   an un-numbered preamble sentence. H3 covers source text only. This is a candidate for a numbered
   rule.
3. **Never-green instruments.** H1 asks for a red control, and nothing asks for a green control on
   correct behavior. Examples: EV-I-12 (a hook exits before writing), DEF-393 (an instrument that
   agrees with the defect).
4. **Coverage and portfolio questions above the node.** Which graphs reach a surface (ATTR-234-25,
   DEF-110), CI triggers and suspensions (SM #293, DEF-021), and sweep aggregation over stale reports
   (DEF-OUN-023). The checklist is per node, with only two graph-level notes.
5. **Cross-node fixture coupling.** A shared law node versus a defect a fixture plants on purpose
   (SM #344). Bind/release/rebind port races (EL #143).
6. **Non-node instruments.** Eval harnesses, graders, sandboxes, pytest/JUnit tests, spec models and
   CLIs make up more than half of the hold-out (27/48), and none of the 27 reaches F. The checklist
   names many of these mechanisms correctly (C1/C2/H4 for eval toolchains, D2 for timing tests, B1
   for home skew), but it is scoped to graph nodes, so those hits are P. Applying the same rules to
   eval and unit-test instruments is the largest lever.
7. **Provider and home defects.** Token copying, baked wrapper paths and silent reanchor
   (DEF-282/283/360), and the agent permission classifier (BS-03-DF-02). B1 reaches only the
   version-enforcement member.
8. **Telemetry and log noise.** No rule covers OTLP exporter noise drowning a diagnostic tail
   (SI-19-DF-05, CDC #390 OTLP item).

Where it is strong: vacuous or non-discriminating gates inside nodes (H1/H2), home/identity
fall-through inside a node (B1), fixed nested budgets (D2), shared fixture state (A1/E2), and Gradle
daemon ownership (E1/C3).
