# `GOAL-progressive-disclosure` — Evaluation B (SI-23)

**Measured 2026-09-26 at base `8b6d97e8` (the epic tip), worktree
`../wt-372-evaluation-b`, branch `feature/372-evaluation-b`.**

> **Statement.** The plugin discloses progressively: little loads at session
> start, a card is short, and the rest is reached through a reference map when
> the task needs it.
>
> **Metric.** words of skill description (loaded every session) and words of card
> body (loaded when the skill is used), per skill and in total.
>
> **Baseline (b7a7d203).** descriptions 923 words over the six units that become
> the plugin; card bodies 15,479 words total, ranging 933 (discovery) to 4,114
> (git-epic-workflow).
>
> **Target.** descriptions <= 600 words in total; every card body <= 1,500 words
> with the remainder behind the reference map; no wide-lane budget case
> regresses.

The target is **three clauses**. They settle differently, and one of them cannot
be settled by its own named instrument.

---

## The instrument, and the two controls it had to reproduce first

Pinned by the epic owner in SI-09 and restated by SI-29:

```
bodies:        awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2' skills/<u>/SKILL.md | wc -w
descriptions:  the YAML-parsed `description` scalar of skills/<u>/SKILL.md, .split()
```

A plain `wc -w` counts frontmatter and inflates every figure; it was not used.

I re-implemented both in `evidence/wordcount.py`, which reads any git ref via
`git show`, so the same code measures every commit named below. It was validated
against both recorded controls **before** being used on anything:

| control | expected | reproduced |
|---|---|---|
| `spec-double-2` body at `b0e6b54c` (the kickoff figure SI-09 names) | 1,839 | **1,839** |
| SI-29's full 11-unit table at `7ba79bee` | 1,005 desc · 6 of 11 bodies over 1500 · `skt` 2,242 | **exact on all 11 units, both metrics** |

Non-vacuity: the script asserts a non-empty `skills/*/SKILL.md` population, a
closing frontmatter delimiter, and a non-empty `description` scalar per unit. It
**fired** — see the baseline note below.

### Correction 1 — the declared baseline is not re-derivable at the commit it names

Run at `b7a7d203`, the commit the goal's `baseline` field names, the instrument
**asserts and stops**:

```
AssertionError: NON-VACUITY FAIL: no skills/*/SKILL.md found at b7a7d203
```

`b7a7d203` has exactly **two** `SKILL.md` files and no `skills/` tree at all: one
at the repository root and one under
`examples/agent_integration/eval-plugin/skills/spec-double-compiler/`. At that
commit this repository *was* the `spec-double-compiler` skill, and the six units
lived in six separate repositories.

So the baseline figures (923 / 15,479 / discovery 933 / git-epic-workflow 4,114)
were measured across six external repositories and **cannot be reproduced here
by the pinned instrument**. They are not wrong; they are not checkable at the
named ref. Every baseline→measured comparison in this goal therefore crosses
both a repository-layout change and a **population change from 6 units to 11**.
The body total moving 15,479 → 15,400 looks like "no change" and is in fact
eleven units where there were six.

Filed `SI-23-DF-01`.

### Correction 2 — SI-09's description figures are inflated by one word per block scalar

My count at `b0e6b54c` is 1,212 description words; SI-09's "before" column sums
to 1,217. The difference is exactly five units, each off by exactly one:

| unit | SI-09 "before" | measured | style |
|---|---|---|---|
| discovery | 91 | 91 | `'...'` inline |
| spec-double-2 | 82 | 82 | `'...'` inline |
| test-graph | 55 | 55 | plain inline |
| git-epic-workflow | 248 | **247** | `>-` block |
| git-integration-repo | 117 | **116** | `>-` block |
| git-issue | 149 | **148** | `>-` block |
| git-issue-workflow | 301 | **300** | `>-` block |
| plugin-repository | 174 | **173** | `>-` block |

The five that differ are precisely the five whose `description:` uses a `>-`
folded block scalar: SI-09's method counted the **fold indicator `>-` as a
word**. Consequence for the record: SI-09's headline *"descriptions <= 600 total:
MET, at exactly 600"* was measured by a method that overcounts, so its true
figure was below 600 and its "zero headroom" reading was pessimistic.

This does **not** affect the verdict below: SI-29's figures and mine both use the
YAML-parsed scalar, and my 592 at the tip reproduces SI-29's exactly. Filed
`SI-23-DF-02`.

---

## Clause 1 — "descriptions <= 600 words in total"

### VERDICT: **MET at the epic tip (592). NOT MET on the default branch (1,005).**

Command: `uv run --python 3.12 --with pyyaml python evidence/wordcount.py . <ref>`

| ref | resolved | units | description words | verdict |
|---|---|---|---|---|
| `epic/self-improvement-substrate` | `8b6d97e8` | 11 | **592** | **MET**, 8 words of headroom |
| `origin/main` (the default branch) | `ac5f7491` | 11 | **1,005** | **NOT MET**, 405 over |

Per unit at the tip: discovery 59 · git-epic-workflow 44 · git-integration-repo
38 · git-issue 47 · git-issue-workflow 55 · plugin-repository 39 · skill-manager
77 · skt 80 · spec-double-2 49 · test-graph 40 · unit-authoring 64.

Moved by **SI-29** (`b909fd90`), from 1,005 at `7ba79bee`. SI-09 (`4d563e2d`
lane) had previously reached 600 over 8 units and nesting three more units
regrew it to 1,005 — so this clause has now been met twice and lost once.

**`SI-29-DF-05` stands: nothing makes 592 hold.** Eight words of headroom and no
check. Restated here rather than closed.

## Clause 2 — "every card body <= 1,500 words with the remainder behind the reference map"

### VERDICT: **MET on the word count at the epic tip (0 of 11 over 1,500). NOT MET on the default branch (6 of 11). The "remainder behind the reference map" half is MET by relocation evidence, not by a check.**

| ref | bodies over 1,500 | which |
|---|---|---|
| `8b6d97e8` | **0 of 11** | — |
| `ac5f7491` | **6 of 11** | git-epic-workflow 1820 · git-issue-workflow 1788 · skill-manager 1648 · skt 2242 · spec-double-2 1567 · unit-authoring 1797 |

Body total 15,400 at the tip over 11 units.

`SI-09-DF-03` — the owner decision that `git-epic-workflow` (1,820) and
`git-issue-workflow` (1,775) would stay over the clause, filed rather than closed
by deletion — **is now moot**: both are under, at 1,498 and 1,497. It was closed
by routing, not by deletion, and the filing was the right call at the time.

The second half of the clause ("with the remainder behind the reference map") is
evidenced by SI-29's twelve recorded relocations, each appending the removed
clause to a reference page in the same commit. **Nothing computes it**, and no
check exists that a clause removed from a card landed anywhere. Reported as MET
on the available evidence with the absence of an instrument stated.

## Clause 3 — "no wide-lane budget case regresses"

### VERDICT: **UNDECIDED — the named instrument cannot decide it, for two independent reasons.**

SI-09 left this clause undecided and said so; it was handed to SI-23. It is still
undecided, and this reading says *why* rather than *that*.

**The population exists.** 32 `graders/within-budget.md` files, of which **22
carry a threshold <= 4**; thresholds actually range 2 to 9, so the harness's
shorthand "Bash <= 4" describes 22 of 32 cases, not the set.

(Note for the record: my first sweep searched `case.yaml` only, found zero budget
graders, and would have reported the instrument absent. The graders are sibling
files under `<case>/graders/`. That is the wave-6 error — a non-vacuity assert
over the wrong population — caught here by re-checking the population rather than
the assert.)

**Reason 1: the only reading available predates the change the clause is about.**
The corpus is `CORPUS-2026-09-25.md`, run at `323497e7` on 2026-09-25 over **64**
cases. SI-29's disclosure cut is `b909fd90`, 2026-09-26.
`git merge-base --is-ancestor 323497e7 b909fd90` → rc=0: **the corpus predates
the cut by a day.** `evals/results/` is gitignored and empty in this worktree; no
scored run exists at or after the cut. There is a before and no after, so
"regresses" has nothing to compare.

Eleven of the tip's 75 cases were never in the corpus at all (64 at `323497e7`,
75 at `8b6d97e8`).

**Reason 2: at this sample count a regression is not distinguishable from
noise.** Every case is `runs: 1` — verified independently: all 75 case files
declare `runs: 1`. The instrument's own recorded spread on **unchanged** cases at
one commit is 0.89→0.81 and 0.97→0.94 at `--runs 6`, and `CORPUS-2026-09-25.md`
records one case moving ±0.8 between identical invocations. A single post-cut
sample could not establish "no regression" even if it were taken.

One budget case was already below 1.00 at the pre-cut reading:
`w-giw-bootstrap-cross-home-is-not-old-cli` at **0.83**, where
`CORPUS-2026-09-25.md` records both substantive graders passing (judge PASS×3)
and "only the weight-1 budget missed".

Filed `SI-23-DF-03`.

---

## The finding this goal most needs: the target is satisfiable by degrading the substrate

**Stated as a verdict on the goal, not on the ticket that met it.**

SI-29's first pass scored **588** description words — a *better* number than the
592 that shipped — and got there by deleting activation vocabulary:
`skill-manager` was left with **no `use when` clause at all** (its description
said what the skill is and never when to invoke it), and `skt` lost five of its
ten quoted trigger phrases, covering sweep, retire and disk-reclaim.

A description is the text a harness matches an intent against. Under this goal's
target, **588 scores strictly better than 592**, and nothing in the target
requires the words to do anything. The restoration landed at 612 (over target)
and was compressed to 592 with all eleven activation clauses and all 42 quoted
phrases intact — `skill-manager` now carrying five quoted trigger phrases where
the baseline carried zero.

The goal did not need relaxing, and it was not relaxed. But it was **satisfiable
by breaking the thing it governs**, and the only thing that caught it was a
measurement *neither the goal nor the ticket required* — the epic agent's review.

**`GOAL-progressive-disclosure` is a defective goal as written.** A word-count
target over a text whose function is activation will always prefer the emptier
text. Saying so is within an evaluation ticket's charter; editing the target is
not, and it was not done. Filed `SI-23-DF-04` with a successor recommendation:
any future form of this goal needs a clause the count cannot satisfy — an
activation-coverage floor measured beside the budget, not folded into it.

---

## Summary

| clause | baseline | measured | target | verdict |
|---|---|---|---|---|
| descriptions <= 600 total | 923 words / 6 units, **not re-derivable at `b7a7d203`** | **592** at `8b6d97e8` · **1,005** at `origin/main` | <= 600 | **MET at the epic tip; NOT MET on the default branch** |
| every body <= 1,500, remainder behind the reference map | 15,479 / 6 units, same caveat | **0 of 11** over at `8b6d97e8` · **6 of 11** at `origin/main`; total 15,400 | 0 over | **MET at the epic tip** (relocation half evidenced, not checked); **NOT MET on the default branch** |
| no wide-lane budget case regresses | — | 32 budget graders, 22 at <= 4; **only reading predates the cut**; `runs: 1` on all 75 cases | no regression | **UNDECIDED** — no post-cut sample, and one sample cannot decide it |

**Moved by:** SI-29 (`b909fd90`) for clauses 1 and 2; SI-09 earlier and
partially undone by nesting.

**Instrument limits stated:** `runs: 1` on all 75 cases; `--runs 6` does not pin
a score (0.89→0.81, 0.97→0.94 on unchanged cases at one commit); the corpus's
52/58 at 1.00 is **not** improvement over the previous 45/58 because eleven
instrument defects were fixed between the two runs — the earlier number was
wrong, and no trend may be drawn from two points across an instrument change; the
scorecard itself still has no eval case.
