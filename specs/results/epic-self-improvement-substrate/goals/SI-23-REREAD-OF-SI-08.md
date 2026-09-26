# The four goals SI-08 froze, re-read beside Evaluation A

**SI-23 (Evaluation B), 2026-09-26, base `8b6d97e8`, worktree
`../wt-372-evaluation-b`.**

SI-08 froze four goals at wave 10, base `2131cdad`. This file shows both
readings **clause by clause**, so the pair says what the restructure cost or
bought. Where a clause moved, the ticket that moved it is named. Where it did
not, that is said plainly rather than dressed up.

**Two of the four moved. One of the two moved less than the epic has been
saying, and the correction is in §2.**

| goal | SI-08, wave 10, base `2131cdad` | SI-23, wave 23, base `8b6d97e8` | moved? |
|---|---|---|---|
| `GOAL-one-unit` | **SPLIT** — project MET, root NOT MET | **MET in both homes** | **YES** |
| `GOAL-findings-become-changes` | **NOT MET** — 19 of 121 (16%) | **NOT MET** — 71 of 193 (36.8%) like-for-like | **YES, and the 47% headline is wrong** |
| `GOAL-pinned-eval-toolchain` | **MET** | **MET**, and the pin never covered the bootstrap CLI | no |
| `GOAL-blockers-propose` | **NOT MET** — discrimination fails | **unchanged — no round run, by SI-08's own request and it is still unmet** | no |

---

## 1. `GOAL-one-unit` — SPLIT → MET. The epic's clearest structural win.

| clause | SI-08 (`2131cdad`) | SI-23 (`8b6d97e8`) | moved by |
|---|---|---|---|
| **1** — one installed unit, zero standalone copies in root **or** project | **NOT MET.** Project home clean (0 dirs, 0 records, plugin present). **Root home: 8 standalone substrate skill dirs + 8 install records, plugin not installed at all.** | **MET in both, and in the worktree home too.** root 0/0 · project 0/0 · worktree 0/0; plugin installed in all three; `skt` contained at exactly one path in each | **SI-24** (root home rebuilt from a recorded manifest), **`EA-DF-05`** (46 duplicate `plugins/skt` dirs cleared), **`EA-DF-06`** (the 74 project manifests that would have regenerated them) |
| **2** — every listed graph and eval case green | **SPLIT.** Graphs 3/3 MET. Eval cases **UNDECIDED** — 61 cases, **0 ever scored**, the two-case population the target names no longer existed | **SPLIT, and worse on the graph half.** Graphs **4 of 5 green; `specWorkflow` RED** (69 assertions, 64 passed, 5 failed in `spec.workflow.failure_cleanup_probe`). Eval cases: **75 cases, last whole run 52/58 at 1.00 with 6 UNDECIDED-with-reason and 6 not green**; no scored run at this tip | graphs regressed by **`7d696715`** (SI-28 review fix), see `SI-23-DF-21`; cases scored for the first time by the ladder + the hardening batch |
| **3** — change-managed: git source, no `NEEDS_GIT_MIGRATION`, `skt sync` able to update it | **MET**, sync verified by **detection**, not execution | **MET**, and unchanged. Install records in all three homes read `kind: GIT`, `errors: []` | — |

**`EA-DF-05` without `EA-DF-06` would have been a sweep that undid itself** — the
46 homes would have been regenerated from the 74 manifests that declared what the
carrier already ships. Both halves were needed and both were done; that is the
substantive content of this goal moving.

**Non-vacuity, and why it needed building this time.** SI-08 got a positive
control for free: the root home's 8 hits proved its detector fired. At 0/0/0
there is no such control, so one was constructed — `GOAL-one-plugin/evidence/poscontrol.py`
runs the identical predicate against a synthetic home in scratch space with two
planted standalone copies and reports `2` and `2`. **The detector fires**; the
zeros are measurements, not silent misses. No real home was written to.

**One thing clause 1 does not say.** All three homes have the plugin installed at
`gitRef: main, gitHash: a3761e30` — **82 commits behind the epic tip and 36
behind `origin/main`**. The goal asks whether *one unit* provides the substrate,
and it does. It does not ask whether that unit is *current*, and it is not. See
`GOAL-one-plugin/SI-23-EVALUATION-B.md` clause 1 and `SI-23-DF-05`.

## 2. `GOAL-findings-become-changes` — real movement, and the headline overstates it

| clause | SI-08 (`2131cdad`) | SI-23 (`8b6d97e8`) | verdict |
|---|---|---|---|
| **1** — 0 `recorded-local` at epic close | **MET** — 0, under both the partial and the full read | **MET** — `recorded-local, filed nowhere .......... 0` | **MET**, unchanged |
| **2** — every finding carries a `skill_change` disposition | **NOT MET** — **19 of 121** parseable (16%); 94 absent, 8 malformed | **NOT MET** — **71 of 193** parseable (**36.8%**) like-for-like; 108 absent, 14 malformed | **NOT MET**, moved ~2.3× |
| **3** — applied / declined-with-reason / not-a-skill | **NOT MET** — 9 terminal, 10 proposed, 45 pending | **NOT MET** — **31 terminal** (11 applied + 9 declined + 12 `none` ≈ not-a-skill), **39 proposed** | **NOT MET**, moved |

### The correction: "71 of 151 = 47%" is not comparable to SI-08's 16%

SI-08's 16% is a **four-file** figure: the ledger's own population across
`deferred_findings_final.yaml`, `skill_feedback.md`,
`SELF-IMPROVEMENT-MATRIX.md` and `deferred_findings_next.yaml`. The 47% quoted in
the amendment, in `REVIEW-BEFORE-SI-23.md` §1 and §5, and in SI-29's
`local-signal.md` is a **single-file** ratio over `deferred_findings_final.yaml`
alone.

Run at this tip with the same instrument and the same interpreter discipline
SI-08 used (`uv run --python 3.12 --with pyyaml python
skills/spec-double-2/scripts/improvement_ledger.py`, exit 0):

```
improvement ledger -- 193 record(s) across 4 file(s)

by source                        records  skill-anchored  skill_change recorded
  deferred_findings_final.yaml       151              48                     66
  skill_feedback.md                   29              19                      5
  SELF-IMPROVEMENT-MATRIX.md           7               2                      0
  deferred_findings_next.yaml          6               0                      0

skill_change verbs: absent 108 · applied 11 · declined 9 · malformed 14 · none 12 · proposed 39
```

Parseable = 193 − 108 − 14 = **71 across four files**, i.e. **71/193 = 36.8%**.

The ledger attributes **66**, not 71, to `deferred_findings_final.yaml`. So the
quoted "71 of 151" pairs a **four-file numerator** with a **one-file
denominator**. Measured three ways, the single-file ratio is 66/151 = 43.7%
(ledger grammar), 71/151 = 47.0% (as quoted), or 72/151 = 47.7% (my looser
independent regex, `evidence/ledger_indep.py`). **None of them is the number to
set beside SI-08's 16%.**

**Like-for-like, on the instrument the goal names: 16% → 36.8%.** Still real,
still roughly 2.3×, still NOT MET against *"every finding"* — and about ten
points short of what the epic has been reporting. Filed `SI-23-DF-22`.

### `SI-08-DF-11` is still open: the partitions remain invisible

SI-08 found the ledger hardcodes its sources and cannot see
`specs/results/deferred/<ticket>.yaml`. `BACKLOGS` at
`improvement_ledger.py:81-84` is **unchanged**, and SI-29's own local signal
confirms it was left alone deliberately.

Measured now (`evidence/partitions2.py`, asserting the `findings` key per file —
see the PR body for the bug this assert caught in my first attempt): the earlier
inboxes have been **absorbed** and hold 0 rows; **four open inboxes hold 20 rows**
— SI-21 5, SI-22 8, SI-28 2, SI-29 5 — which matches `REVIEW-BEFORE-SI-23.md`'s
"151 absorbed + 20 in four open inboxes". Of those 20, **only SI-29's five carry
a parseable `skill_change`**; SI-21's, SI-22's and SI-28's fifteen carry none.

True population **213**, of which **76** parseable = **35.7%**. The bias SI-08
named still runs in the same direction and is now smaller because absorption is
working.

### What neither reading establishes

The ledger counts records. It does not verify that an `applied(<sha>)` token
names a commit that exists or that changed the unit it claims. Of the 10
`applied` rows, **3 begin with a commit sha**; a fourth resolves under
`git cat-file` only because this repository has a **remote** named `test-graph`,
so a resolvability check would score that row a pass while pointing at an
unrelated commit. That is why SI-29 documented a form constraining **shape**, and
added no validator. **No clause here should be read as "the change was made" —
only as "the record says so."**

## 3. `GOAL-pinned-eval-toolchain` — MET, unchanged, and one thing it never covered

| clause | SI-08 (`2131cdad`) | SI-23 (`8b6d97e8`) |
|---|---|---|
| **1** — every full-suite run records the ref | **MET for the one run — 1 of 1**, and the denominator was 0 until SI-08 made it 1 | **MET and no longer a ratio of one.** `CORPUS-2026-09-25.md` records a 64-case full-suite run naming its toolchain; `evals/run.sh` writes a `si14.toolchain-run-record.v1` per run |
| **2** — the ref is pinned in the repository, not resolved from the operator's home | **MET**, and the pin demonstrably changes which bytes run (pinned `286a3694` vs ambient `0f380781`) | **MET**, unchanged. `evals/lib/toolchain.lock.toml` still pins 40-hex commits and `toolchain.py` still refuses anything shorter |
| **3** — the runner asks and refuses to guess silently | **MET**; refusal and override **exercised**, the tty branch read not executed | **MET**, unchanged; the tty branch is **still** unexecuted — no interactive full-suite run has been made by any ticket |

**No re-measurement was needed and none is claimed.** This goal did not move, and
the honest addition is a boundary rather than a number:

**The pin covers the *eval* toolchain and has never covered the *bootstrap*
CLI.** `evals/lib/toolchain.lock.toml` pins `skt` and `skill-manager` for scored
runs. Nothing pins the `skill-manager` a fresh machine installs — that is
Homebrew's `0.28.2`, which moved to `0.28.2` (artifact `03c0143ec45e`, built
2026-09-26) during this epic. SI-28 added `bootstrap-floor.toml` to *declare* a
floor and `skt check` to *report* it; neither pins it, and `SI-28-DF-01/02`
record that `install --dry-run` does not parse the manifest and no manifest field
carries a CLI floor. Also note `~/.skill-manager/bin/cli/skt` hardcodes
`/opt/homebrew/bin/python3.14` — an unpinned interpreter that is the one
**without PyYAML** on this machine.

So: **MET as scoped, and the scope is narrower than "the toolchain".**

## 4. `GOAL-blockers-propose` — unchanged, and the measurement SI-08 asked for was not taken

| clause | SI-08 (`2131cdad`) | SI-23 (`8b6d97e8`) |
|---|---|---|
| the card **runs** | **MET** — 4 judges, 2 subjects, 4 usable cards, 0 failures | unchanged; no round run |
| two judges **agree within 1** | **MET** — max spread 1, on 1 of 10 pairs | unchanged; no round run |
| it **discriminates** proposer vs non-proposer | **NOT MET** — I2 = 2 on all four cards | unchanged; **still NOT MET** |

**I did not run a judged round, and this is the one place where this evaluation
leaves something undone that its predecessor explicitly asked for.** SI-08's
reading closes: *"A round with a genuine non-reporter as the negative arm has not
been run. `SI-23` should run one before treating this goal as decided in either
direction."*

**Stated plainly: I have not run one, so this goal is not decided in either
direction by me.** It stands at SI-08's NOT MET, with SI-08's confound intact —
subject A was chosen as the negative control on the strength of its `none met`
and was **not a clean negative control**, because both A-judges found it
reporting blockers elsewhere in the same body.

**Why it is worth running now, which it was not then.** SI-08's diagnosis was
that both subjects hit the same ceiling: *I2 rung 3 requires a diff, a commit, or
an issue, and neither subject has one*. That ceiling has since moved. The epic
now holds **10 `applied(...)` rows, 3 of them naming a commit sha**
(`4caab479`, `d09d8326`, `f212cbe3`), and several tickets carried findings out as
GitHub issues (`#384`, `#385`, `#387`, `#392`). A round with a proposer that
carries a **commit** against a genuine non-reporter is now constructible, and it
is the first time in this epic that it has been. Recommended to the owner as the
single highest-value follow-up measurement. Filed `SI-23-DF-23`.

**The disclosure obligation does not arise for this ticket**, because no judged
round was run: there is no dispatch path to record and no judge to report what it
received. It is stated here so the absence is on the record rather than inferred
from silence. `goals-and-evaluation.md` is explicit that dropping the word or
withdrawing the number both destroy the record; neither was done, because there
is no new number.

---

## What the pair says, overall

**Bought:** one unit genuinely became one unit, in every home, and it took three
coordinated actions rather than one sweep. The eval corpus went from *61 cases,
none ever scored* to *75 cases with a whole-corpus run and named UNDECIDED
verdicts*. Disposition coverage roughly doubled and `recorded-local` stayed at
zero.

**Cost:** `specWorkflow` is red at the tip and was green at wave 10 — a
regression introduced today by a review-driven fix (`7d696715`). The
installed-vs-source gap widened to 82 commits. And two of the four frozen goals
are still NOT MET for the same reasons SI-08 gave, with the instrument for one of
them unchanged and the deciding round for the other still unrun.

**The pattern worth carrying:** of the four, the two that moved were moved by
**changing what the substrate does** (rebuilding a home, sweeping manifests,
building a ladder). The two that did not move are the two whose closure requires
**a measurement nobody has taken** — a judged round with a clean negative arm,
and a ledger that reads its own per-ticket partitions. That is this epic's own
lesson about filing versus consumption, visible in the shape of its goal table.
