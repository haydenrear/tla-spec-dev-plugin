# ESD-03 local signal: the checklist against audited failures

**Signal (GOAL-ESD-ARCH, `local_signal`).** Apply the checklist in
`skills/test-graph/references/graph-architecture-review.md` to
`spec.workflow.failure_cleanup_probe` and to the audited nodes and instruments in
ESD-01's inventory. Tabulate which historical failures it would flag and which
it would miss.

**Expected effect.** "The review checklist flags most confirmed
validation-origin failure families from ESD-01 at authoring/review time; each
miss named."

**Procedure.** For each row, the question was whether a named checklist rule,
applied to the node's source and declaration *before the failure*, would have
raised the defect.

- **F (flagged):** a rule names the defect or its exact precondition.
- **P (partial):** a rule raises the risk or the review question, but it would
  not have prevented or detected this specific failure. For example, the
  mechanism is inferred, the fix is runtime or dispatch policy, or the defect
  lies outside a graph node.
- **M (missed):** no rule reaches the failure.

**Caveats.**

- The same agent wrote the checklist and applied it, in one session, with the
  rows in view. That biases toward F. ESD-06 applies the merged guidance to
  ESD-01's held-out families and is the stronger reading.
- The run was done once. Nothing was re-run or tuned. Rows are ESD-01 row ids
  (`specs/results/evidence-sized-delivery/ESD-01/inventory.yaml`), and rule ids
  are the review page's (A1-H4).

## A. `spec.workflow.failure_cleanup_probe` (specWorkflow)

The checklist applied to the node at `3e57ea9e` flags these rules:

| Rule | Finding on the probe |
|---|---|
| A1 | `dependsOn("spec.workflow.close")` but reads only `spec.workflow.repo`'s `sourceRepo`. The edge is ordering. |
| A3 | an `assertion` that copies a Test Graph project and runs a nested Gradle build |
| A4 | declares `fs:tmp` only; `process:gradle` is missing |
| C3 | the nested build shares `~/.gradle` and Kotlin compile daemons with the outer build and with concurrent agents. Mitigated by its in-process pins. |
| C4 | heavy nested work on a shared host; `#241`'s lock does not cover the nested `gradlew` |
| D1 | good: a bounded 20 s drain that names its residue |
| D2 | a fixed 180 s budget over a cold `build-logic` compile plus the drain |
| E1 | good: no daemon, in-process Kotlin on both channels, and its own descendant assertion |
| H1 | good: the nested graph is a deliberate red control, and the node asserts per-node statuses, not just a non-zero exit |
| finalizer tag | runs after upstream failures, and is listed before `spec.reference.adapters_resolve` |

## B. Flag/miss table

| # | Row | Family | Node or instrument | Verdict | Rules |
|---|---|---|---|---|---|
| 1 | `RP-07-DF-01` | F1 | `spec.workflow.failure_cleanup_probe` | **F** | A3, A4, C3, E1 |
| 2 | `BS-07-DF-05` (false red, 13 runs / 7 tickets) | F1 | same | **P**: the design hazard is flagged; the cause is inferred, and the checklist cannot show it would have prevented the reds at load 28-47 | A3, A4, C4, D2, E1 |
| 3 | `BS-07-DF-05` (effect: `adapters_resolve` skipped) | F1 | specWorkflow order | **F** | A1, plus the finalizer note |
| 4 | `#241 (polymarket#115)` / `E02-R11` | F1 | canonical commands / runner | **P**: raised as a review question; the fix is runtime | C4 |
| 5 | `HOST-LOAD family` (CDC ×14) | F1 | several CDC gates | **P** | C4, D2 |
| 6 | `GO-PERSISTER-TIMEOUT family` (CDC ×6) | F1 | go persister suite | **F**: a fixed 1,200 s bound against code that ran 877 s | D2 |
| 7 | `DEF-154` (MH) | F1 | spec_unit under contention | **P**: the fix is dispatch policy | C4 |
| 8 | `E10-NAV-OWNER-BLIND-001` | F1 | home audit vs receipt observer | **P** (the cause is inferred) | C4 |
| 9 | `#194 / BS-09` | F2 | all graphs (home copy, not branch copy) | **F** | B1, B2 |
| 10 | `missing-rung family (REACH)` / `SI-25-DF-06` | F2 | `skt.ticket-roundtrip` | **F** | B1 |
| 11 | `MS-027-ENV-TOOLCHAIN-PIN` | F2 | CDC preflight | **F** | B1 |
| 12 | `SI-25-DF-01` | F2 | Gradle wrappers (`java.home`) | **P**: only if the reviewer reads wrapper properties; not a node | B1 |
| 13 | `SM402-ISOLATION family` | F2 | `cdcWorktreeOverlayIsolation` | **P**: identity would show the upstream version; the defect is upstream | B1 |
| 14 | `OBS-EVAL-MANAGER-LOCK-001` | F2 | eval lock (not a node) | **P** | B1 |
| 15 | `R4-DF-03 / DEF-001` | F2 | effectProviderExamples replay | **F** | G1, G2, B1 |
| 16 | `EA-DF-15` → `#248` | F2/F6 | eval uv scripts | **F** | C1, C2 |
| 17 | `SM #295` | F6 | `gateway.python.venv.ready` | **F** | C1, D2 |
| 18 | `SI-12-DF-05 / SI-13-DF-01` | F6 | bare `gradlew` in a fresh worktree | **F** | C1, C4 |
| 19 | `E10-OWNER-GRAPH-STARTUP-001` | F6 | runner startup (describe of 250 sources) | **M**: a runner cost; C1 only labels it | none |
| 20 | `CDC #262` / `SM #378` | F5 | fixture home parented on the real home | **F** | F1 |
| 21 | `DEF-OHV-010 / SM #294` | F5 | leaked temp homes, ENOSPC | **F** | E2, F1 |
| 22 | `DEF-503` | F5 | shared `target/` symlink | **F** | F1, C3 |
| 23 | `SI-27-DF-06` / `HP-01-DF-01` | F5 | checkers walking the checkout | **P**: F1 reduces what graphs leave behind; the defect is in the checkers | F1 |
| 24 | `SI-27-DF-01` | F3 | `skt.wrapper-installed` / bootstrap counter | **F** | H1, H2 |
| 25 | `DEF-124` | F3 | spec-unit runner, zero cases | **F** | H2 |
| 26 | `ATTR-234-36` | F3 | step retraction gate, zero edges | **F** | H2 |
| 27 | `SI-08-DF-01` | F3 | ledger without PyYAML | **F** (an instrument, not a node) | H2, H4 |
| 28 | `DEF-110` | F3 (BLIND) | none caught it | **M**: no node rule finds an unwritten scenario | none |
| 29 | `BS-07-DF-04` | F4 | source citations (suite) | **P**: applies only if H3 is applied to the suite | H3 |
| 30 | `#245`, `#247`, `EA-DF-09` | F7 | eval cases and graders | **M**: eval cases are outside a graph-node checklist | none |
| 31 | `#226 / BS-HP-05` | F8 | runner resume | **P**: guards anyone relying on resume; does not detect the defect | B2 |
| 32 | `BS-13-DF-02` | F8 | runner `/var` vs `/private/var` | **P** | B2 |
| 33 | `#195 / BS-10` | F8 | describe phase | **P**: the node-side describe hygiene only | A2 |
| 34 | `SI-19-DF-05` | F8 | OTLP noise, no collector | **M** | none |
| 35 | `DEF-OHV-140` | F8 | OTLP export blocking on a hung port | **M** | none |
| 36 | `#233 fixture` | F8 | executor unit-test fixture | **M**: not a graph node | none |

Rows 34-36 are product-origin for this plugin, which ships the runner
(`bug_attribution.md` §4.3). They are tabulated so the misses are named.

**Outside the ESD-01 sample, found by applying the checklist.**
`spec.workflow.cleanup` deletes `Path("")` (= `.`, the `test_graph/` project)
when `repoPath` is absent. Rule E2 flags it. It is the shape of the recorded
"27 tracked files of `test_graph/` deleted" incident (self-improvement-substrate
wave-3 review, item 3) and is unguarded at `3e57ea9e`. It is deferred as
`ESD-03-DF-01`.

## Result

| Verdict | Rows | Share |
|---|---|---|
| F (flagged) | 17 | 17 / 36 |
| P (partial) | 13 | 13 / 36 |
| M (missed) | 6 | 6 / 36 |

**By family (validation-origin families named for this goal: F1, F2, F4, F5,
F6, the eval half of F7; plus F3).**

| Family | F | P | M | Reading |
|---|---|---|---|---|
| F1 contention / process lifecycle | 3 | 5 | 0 | **Flagged as a risk** in every row. It is prevented outright only where the defect is in the node's own contract (`RP-07-DF-01`, `GO-PERSISTER`, ordering). Host load and dispatch remain policy. |
| F2 home / toolchain / version skew | 5 | 3 | 0 | flagged where a node resolves identity; partial where the skew sits in a wrapper, a lock or upstream |
| F3 vacuous / blind greens | 4 | 0 | 1 | zero-exercised and red-control rules hit; a missing scenario (`DEF-110`) is not reachable |
| F4 stale assertions | 0 | 1 | 0 | H3 covers graph nodes. The audited row is a suite test. |
| F5 isolation / leaked state | 3 | 1 | 0 | flagged; checker scan scope is the checkers' problem |
| F6 cold setup | 3 (incl. row 16) | 0 | 1 | runner startup cost is missed |
| F7 eval half | 0 | 0 | 1 | missed: eval cases are not graph nodes |
| F8 (product here) | 0 | 3 | 3 | expected: runner defects need runtime fixes. B2 only stops reliance on them. |

**Against the expected effect.** The goal names six validation-origin
families: F1, F2, F4, F5, F6 and F7's eval half. Four of them (F1, F2, F5, F6)
have rows flagged outright. F4 is only partial, because its one audited row is a
suite test, and F7's eval half is missed. F3, which is also validation-origin,
is flagged. So "most" holds at family level, 4 of 6 plus F3, with F4 and F7
named as the gaps. At row level, 17 of 36 rows are flagged outright and 30 of
36 are at least partly raised. Row 16 counts under both F2 and F6 in the family
table. **Named misses:** `E10-OWNER-GRAPH-STARTUP-001`,
`DEF-110`, the F7 eval rows (`#245`, `#247`, `EA-DF-09`), `SI-19-DF-05`,
`DEF-OHV-140` and `#233 fixture`. This is a same-author signal, not a verdict.
ESD-06 decides.
