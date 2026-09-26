# `GOAL-epic-owns-the-model` — Evaluation B (SI-23)

**Measured 2026-09-26 at base `8b6d97e8` (the epic tip), worktree
`../wt-372-evaluation-b`, branch `feature/372-evaluation-b`.**

> **Statement.** At every wave close the epic agent has applied the wave's model
> delta, placed every anchor, written the card row, and applied or declined every
> proposed skill change — and ticket PRs no longer carry model edits.
>
> **Metric.** the four required blocks present in each wave review artifact;
> files under `specs/` touched by ticket PRs other than `results/`.
>
> **Baseline (b7a7d203).** the artifact schema has no such blocks —
> `human-review.md` §3.4 is prose; ticket agents open and close their own spec
> tickets today.
>
> **Target (two clauses).** four blocks in every wave artifact from wave 4 on
> (wave 1–3 artifacts are the baseline shape), **and** no ticket PR after SI-07
> changes a file under `specs/` except under `results/`.
>
> **Harness.** `scripts/validate_epic_plan.py --verbose` (warns, never errors, on
> a missing block); `git diff --name-only` over each ticket PR filtered to
> `specs/`.

---

## Two defects in the goal as declared, found before anything could be measured

**1. The harness path does not exist.** `scripts/validate_epic_plan.py` is not a
file. The script is at
`skills/git-epic-workflow/scripts/validate_epic_plan.py` (1,599 lines) — moved by
the plugin migration, with the goal text never repaired. The **same stale path is
also printed inside `skills/git-epic-workflow/references/human-review.md` §3.4**,
so the reference page tells the next reader to run something that is not there.
Filed `SI-23-DF-08`.

**2. The goal says FOUR blocks. The substrate defines FIVE.** Both authorities
agree with each other and disagree with the goal:

- `human-review.md` line 315: `#### The five blocks`
- `validate_epic_plan.py` lines 85–96, `WAVE_BLOCKS`: *model delta applied ·
  anchors placed · improvement-card row · skill changes applied or declined ·
  **model corrections owed by merged tickets***

The goal's statement, metric, baseline and target are all stale by one block. The
goal **under-specifies what shipped**, so this is a defect that flatters nothing
— but it must be repaired before the goal text is restated anywhere. Filed
`SI-23-DF-09`. The verdict below is reported on **both** readings; they agree.

---

## Clause 1 — "four blocks in every wave artifact from wave 4 on"

### VERDICT on the metric as written: **MET — 12 of 12 artifacts carry 5 of 5 blocks, waves 4–22, zero gaps.**
### VERDICT on the statement the clause is written under: **NOT MET for waves 19–22, by the epic agent's own admission, and thin for waves 4–16.**

Both are reported because a single token would have to choose, and — as
`goals-and-evaluation.md` puts it — *it will choose the flattering one*.

### The block census

Artifact root `specs/results/epic-self-improvement-substrate/review`, confirmed
from `review_policy.artifact_root`. Population: 16 directories on disk;
`wave-0-kickoff` correctly does not match `WAVE_DIR`; **15 match, covering waves
1–22 with no gap** (asserted `len(matching)==15` and
`covered == set(range(1,23))`; both passed — wave 23 is this ticket's own
in-flight wave and has no close).

| waves | artifact | blocks present |
|---|---|---|
| 1, 2 | `wave-1`, `wave-2` | 0/5 — **exempt** (baseline shape) |
| 3 | `wave-3` | 1/5 — **exempt** |
| 4 · 5 · 6 · 7 · 8 · 9 · 10 · 11-12 · 13-15 · 16 · 17-18 · 19-22 | twelve artifacts | **5/5 each** |

Matching is a case-insensitive substring search over the whole lowercased
`review.md`, so it can be satisfied by incidental prose. Spot-checked against the
real document structure: `wave-19-22/review.md` lines 20/57/78/105/130 are
`## Block 1 — Model delta applied` … `## Block 5 — …`, with the same shape at
`wave-4` and `wave-16`. The match is not a false positive here.

### The harness ran and warned and did not refuse

```
out=$(uv run --python 3.12 --with pyyaml python \
  skills/git-epic-workflow/scripts/validate_epic_plan.py --verbose 2>&1); rc=$?
→ EXIT=0
```

Every missing-block diagnostic is a `WARNING`; the run still prints
`OK: ... (29 tickets, 0 retired, 29 active/delivered across 23 waves, 10 goals)`.
The only missing-block warnings are waves 1–3 — exactly the exempt set — plus a
`wave-23` warning that the plan declares a wave with no review directory under
any spelling, which is `#386`'s second half working as designed. Three unrelated
scheduling warnings also appear (SI-08 must depend on / promote after SI-27 and
SI-29) — not this goal's business, but real, and recorded because they are the
kind of thing that goes unread.

This also settles the `GOAL-no-new-gates` question for this instrument: it warns
and exits 0.

### The second half of the statement — the model delta itself

This is the part the epic agent flagged as its own gap, and it is verified.

Wave boundaries defined as the commit that **added each `review.md`** (15
boundaries, asserted strictly chronological). `specs/.history/` excluded — a
625-file snapshot archive that inflates every `.tla` count — along with `.git`,
plugin caches and vendored copies. Population: 26 `.tla` under `specs/` at HEAD;
the epic touched 20.

**The project model — `specs/current`, `specs/program_model`,
`specs/desired_program_model`, which is what Block 1 is defined over — changed in
exactly 3 of 22 waves: 1, 3, and 17–18.** Waves 4–12 changed only
`specs/tickets/SI-xx/desired/TlaSpecDevCli.tla`, the per-ticket workspace
scaffolded for the next wave, which is not in Block 1's scope. Waves 13–15, 16
and 19–22 changed no `.tla` at all.

**Waves 19–22: the allegation is VERIFIED under four independent boundary
choices.**

```
git diff --name-only 10e16817..37ada6f4 -- '*.tla'   (w17-18 close .. w19-22 close)  -> 0
git diff --name-only ac5f7491..b909fd90 -- '*.tla'   (the artifact's own range)      -> 0
git diff --name-only 10e16817..8b6d97e8 -- '*.tla'   (w17-18 close .. HEAD)          -> 0
git diff --name-only bf1bbe54..0f7157b4 -- '*.tla'   (SI-20 merge .. SI-29 merge)    -> 3
```

The fourth is the only non-zero and it is a boundary artefact: those three files
were written by `5a8527bf` (*"model the skt surface, so four findings stop being
UNMODELED"*) and `2e7ba795`, both landing **before** `10e16817` — they are the
**wave 17–18** delta, not the 19–22 one.

**Non-vacuity for that window:** `git diff --name-only 10e16817..8b6d97e8 --
specs/` returns **122 paths**, 121 under `specs/results/` and exactly one outside
(`ticket_plan.yaml`, the epic agent's own). The sweep was looking at a live,
populated window. The zero is a real zero.

**The wave-19-22 artifact says so itself**, at line 20:

> **Block 1 — Model delta applied.** **None applied, and that is a gap I own
> rather than a property of the waves.** […] **Carried to SI-23 as evidence
> against `GOAL-epic-owns-the-model`, not for it.**

I am taking it at its word, and so must the verdict. Reporting this goal MET
because the tickets behaved would invert the sentence the goal is written in.

**And the `none`s are the pattern, not the exception:**

| block | substantive entry | wrote `none` |
|---|---|---|
| Block 1 — model delta | **1 of 12** (wave 17-18) | 11 of 12 |
| Block 3 — improvement-card row | **2 of 12** (waves 4, 10) | 10 of 12 |

Blocks 2, 4 and 5 carry substance throughout. `human-review.md` line 317
explicitly legitimises `none` (*"`none` is a claim, and an absent block is not
one"*), so this is not a schema violation. **But clause 1 measures that the epic
agent now reports at every wave close, not that it acts at every wave close.**
The block was written 12 of 12 times and said `none` 11 of those 12. That is
this project's own named failure mode — *filing a finding is routing, not
consumption* — reappearing one level up, in the instrument built to prevent it.

### And `install-pipeline` is 6, not 5

Parsed on the `attribution` key with PyYAML, not grepped:

| file | count | ids |
|---|---|---|
| `specs/results/deferred/SI-22.yaml` | 5 | SI-22-DF-01, -03, -04, -05, -06 |
| `specs/results/deferred/SI-28.yaml` | 1 | SI-28-DF-01 |

**Six findings in `UNMODELED/install-pipeline`**, all still unabsorbed (zero of
the 151 rows in `deferred_findings_final.yaml` mention the bin). The amendment
and `REVIEW-BEFORE-SI-23.md` §4 both say five. Corrected here.

Full bin census for findings filed during waves 19–22 (20 rows, each carrying
exactly one `attribution`; asserted and passed):

```
6  UNMODELED/install-pipeline          1  UNMODELED/measurement-harness
3  UNMODELED/eval-harness              1  UNMODELED/progressive-disclosure
3  UNMODELED/record-keeping            1  UNMODELED/retirement-receipt
2  UNMODELED/bootstrap-preconditions   1  UNMODELED/scorecard-harness
18 UNMODELED across 8 bins  +  RunSpecUnitTests 1, RunEffectConformance 1
```

**A further defect in the wave-19-22 artifact itself.** Its Block 2 bin table
(lines 29–36) accounts for **15 rows where the ledgers hold 20**: it undercounts
`install-pipeline` by one (omits `SI-28-DF-01`), undercounts `eval-harness` by
one (omits `SI-29-DF-03`), and **omits three bins entirely** —
`measurement-harness`, `retirement-receipt`, `scorecard-harness`, all three of
them SI-21's, the first of the four waves that artifact covers. So the anchor
census in the very artifact that self-reports a Block-1 gap is itself incomplete.
Filed `SI-23-DF-10`.

## Clause 2 — "no ticket PR after SI-07 changes a file under `specs/` except under `results/`"

### VERDICT: **MET, decisively — 0 violations across all 14 post-SI-07 ticket PRs, confirmed from both directions.**

`git log --merges b7a7d203..8b6d97e8` → 118 merges, **23 ticket-PR merges**,
mapped to tickets via `github_issue` in `ticket_plan.yaml`. SI-07's merge is
`e9b04917`; **14 ticket PRs merged after it**: SI-12, SI-09, SI-13, SI-14, SI-15,
SI-08, SI-16, SI-17, SI-19, SI-20, SI-21, SI-22, SI-28, SI-29.

The naive `git diff <merge>^1 <merge>^2` was **discarded**: it falsely flagged
SI-13, SI-14 and SI-16 as touching `ticket_plan.yaml`, when that file had moved
on the *epic* side while the ticket branch sat still. Two correct measures were
used instead — `^1...^2` (merge-base to branch tip), and the file set of commits
authored only on the ticket branch. **Both return zero violations for all 14.**

**Non-vacuity, two independent proofs:**

1. The branch-commit sweep walked **176 non-merge commits** across those 14
   branches and saw **259 distinct `specs/results/` paths** (asserted
   `ncommits > 50`, `results_paths > 20`; both passed). Every ticket writes its
   close-out and findings under `specs/results/`, so a zero there would have
   proved blindness.
2. **Complement sweep from the opposite direction**: of all 526 non-merge commits
   on `b7a7d203..8b6d97e8` (654 `specs/results/` touches seen), **39** touch
   `specs/` outside `results/` after SI-07. Cross-referenced against the **378
   commits authored on a ticket branch**: **0 of the 39 are on a ticket branch.**
   All 39 are epic-branch commits — 32× `ticket_plan.yaml` amendments, 8× ticket
   workspace scaffolds, 2× the wave-17-18 model delta. That is exactly the
   division of labour the goal asks for.

**Instrument coverage hole, recorded rather than waved past.** Six tickets have
**no ticket-PR merge at all** — SI-18, SI-24, SI-25, SI-26, SI-27 (and SI-23, in
flight). Their work landed as single-parent commits directly on the epic branch.
Clause 2's instrument says *"no ticket **PR**"* and is structurally blind to 5 of
the 22 closed tickets. I verified separately that no post-SI-07 commit touches an
SI-18/24/25/26/27 ticket workspace or any `specs/` path outside `results/`, so
the verdict does not change — but *"no ticket PR did X"* is a weaker statement
than it reads when 5 of 22 tickets had no PR. Filed `SI-23-DF-11`.

---

## Summary

| clause | baseline | measured | target | verdict |
|---|---|---|---|---|
| four blocks in every wave artifact from wave 4 on | schema has no such blocks | **12 of 12 artifacts at 5/5** (waves 4–22); harness warns on waves 1–3 only and **exits 0** | four (really five) in every artifact | **MET on the metric** |
| — the statement it is written under: *delta applied, card row written, at every wave close* | ticket agents own their own spec tickets | project-model delta applied at **1 of 12** closes; card row at **2 of 12**; **waves 19–22: zero `.tla`, verified four ways, admitted in the artifact** while 18 UNMODELED findings were filed, 6 into one bin | applied at every close | **NOT MET for waves 19–22; thin for 4–16** |
| no ticket PR after SI-07 changes `specs/` outside `results/` | ticket agents edit the model | **0 violations / 14 PRs**, two methods; complement sweep: 0 of 39 such commits are on a ticket branch | zero | **MET** |

**Moved by:** SI-07 (`e9b04917`) established the block schema and the
model-ownership rule; SI-18 and the wave-17-18 close produced the one substantive
model delta (`5a8527bf`, `2e7ba795` — the skt surface, four findings de-UNMODELED
one-to-one).

**Instrument limits stated:** the harness path in the goal is stale and had to be
located; block matching is substring-based over the whole document and can be
satisfied by prose; clause 2's instrument cannot see the 5 closed tickets that
never opened a PR; and `validate_epic_plan.py` checks that a block is *present*,
never that its content is non-`none` — which is why the metric and the statement
settle differently.
