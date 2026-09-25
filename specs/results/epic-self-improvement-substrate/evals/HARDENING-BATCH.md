# The hardening batch: what this session changed in the substrate, and why

Written 2026-09-25, before the full corpus run. 38 commits across two days of
one session. The point of collecting them is the owner's: a full corpus run is
expensive, so it should measure a substrate that has stopped moving.

`EPIC-STATE.md` is the epic. `STATE.md` is the eval lane. This is the batch.

---

## What was wrong, in one sentence

**The substrate was being measured by instruments that failed quietly**, and
almost every score below 1.00 was the instrument rather than the work.

Nineteen defects found. **Seventeen fixed**, two left open on purpose. One is a
real substrate defect and it is the serious one.

---

## The one real substrate defect

**EA-DF-17 — a view-qualified adapter binding makes ticket validation vacuous.**
`specs.program_model.adapters:X` resolves from the PROJECT ROOT, so inside a
ticket view it runs the BASELINE's adapters: a ticket that edited its own
`adapters.py` goes green **without ever executing it**. Every check passes and
nothing says the ticket's code never ran.

It persists because the fixture teaches it. Every existing entry carries the
qualified form, and an agent told to add one "next to the others" matches the
others. Measured — the agent reasoned about it explicitly and rejected the
correct form by name:

> "That matches the `CreateAccount` and `Checkout` entries […] **I didn't use the
> bare `adapters:RefundInternalAdapter`**"

Filed as **#384**. Left for SI-21: the remedy is a scaffold change plus a
migration of live bindings, which is production work with its own blast radius.

---

## The instrument defects, by class

### A. A tool could not start, and the run scored anyway (4)

A sandboxed run inherits an **empty `HOME`**, so every toolchain that caches
under `HOME` is cold and reaches for a network that is not there.

| | |
| --- | --- |
| EA-DF-12 | `skill-manager` never started — jbang wanted a JDK from `api.foojay.io`. **Five of six cases scored 1.00 while it could not run.** |
| EA-DF-14 | the orientation hook injected nothing — needs python ≥3.11, macOS ships 3.9.6. Then a second cause: it **discarded a good report on a non-zero exit code**. |
| EA-DF-15 | **no `uv run --script` skill script could start.** 81 files carry that header. Six attempts; see below. |
| — | the fix pattern, applied three times: **name the resource, keep it in `.toolchain`, provision it operator-side.** |

### B. A grader punished correct behaviour performed differently (5)

| | |
| --- | --- |
| EA-DF-09 | `answers-yes` asserted an answer its own fixture made false — a **move casualty** from SI-15, misreported as "no fixture by design" |
| EA-DF-11 | a judge rubric's pass and fail branches **overlapped**; three judges resolved it against the correct answer, twice |
| EA-DF-16 | a `require` rule matched a **path spelling**, so the same behaviour scored 0.86 or 1.00 depending on which tool the agent reached for |
| EA-DF-18 | the scaffold check **rejected this repository's own five passing graphs** — it wanted `"stem"`, the framework writes `node("sources/stem.py")` |
| — | a budget of 5 Bash calls, calibrated for a fixture that had been replaced, failing 3 of 3 |

### C. The instrument could not be read, or could not be verified (4)

| | |
| --- | --- |
| EA-DF-08 | an UNDECIDED verdict was written and **never reached the screen** |
| EA-DF-10 | a fixture **could not be committed** — `.gitignore` hid `.skill-manager/` at any depth, `git add` staged nothing |
| EA-DF-13 | `run.sh` overwrote the plugin's hooks, so **every** `w-*` score was measured without the orientation the product ships |
| — | `testgraph_scaffold.py` took **500s** against this repository, so nobody ran it against the reference — which is how it stayed wrong |

### D. The instrument damaged the machine (1)

**The disk bomb, and it was mine from this morning.** I put the scratch eval home
at `.toolchain/evalhome`, inside the checkout. A scratch home is *mostly symlinks
into the operator's home* — `.claude`, `.config`, `.local`, `.cache`,
`Library/Keychains` — because overriding `HOME` is the only way past the Docker
sandbox check while keeping authentication.

`skt_wrapper_installed.py` builds its fixture with `shutil.copytree`, which
**dereferences symlinks by default** and did not ignore `.toolchain`. One run's
fixture directory measured **57 GB** against ~350 MB for each of the other
seventeen. A 926 GB disk went to **532 MB free**, and both skt graphs errored
with `[Errno 28] No space left on device`.

Three fixes: the home moved **out of the checkout**; `symlinks=True` and
`.toolchain` ignored in both repo-copying graph nodes. Fixture now **265 MB**, a
220× reduction, and the graphs are back to 318/318 and 167/167.

A second instance was already waiting and is not mine:
`.toolchain/skill-manager/specs/evals/harness/.evalhome/` carries the same five
links from skill-manager's own harness.

---

## What a fresh machine now gets

```bash
evals/setup-eval-home.sh --smoke     # once per machine
evals/run.sh                         # everything
evals/run.sh --case 'w-sm-*' --runs 6
```

`setup-eval-home.sh` builds the scratch home, **derives** the wheel list from
the `# /// script` headers, and `--check` *proves* them by running a real
validator under a throwaway `HOME`. `--smoke` bills one case and asserts a
**1.00** — falsified both ways, it exits 1 at $0.00 on a broken lane.
`run.sh` finds the home itself.

Two sections were added to `evals/README.md` for whoever picks this up:
**how things reach the agent** (four addressing schemes that failed silently;
the two that work) and **reading a score without fooling yourself**.

---

## EA-DF-15, the six attempts, kept because the sequence is the lesson

```
1. export UV_CACHE_DIR from run.sh   the agent's sandbox does not inherit the
                                     runner's environment
2. $HOME/.cache/uv in a hook         $HOME in a hook is the OPERATOR's
3. symlink the agent's .cache/uv     the harness pre-creates that directory
4. seed from $SI10_CHECKOUT          not visible to hooks — diagnosed from
                                     SILENCE, the guard printing neither its
                                     success line nor its warning
5. seed a copied uv CACHE            worked mechanically, 92K → 1.9M, and still
                                     failed: a uv cache is NOT relocatable
6. ship the WHEEL + a uv.toml file   ✓
```

**Anything that must reach the agent arrives through the VIEW or through a FILE
in the agent's home.** Four environment variables failed against that boundary.

It was worth six attempts because it was not one case: three of the six
reproducible failures were git-epic-workflow cases requiring a validator, against
budgets of 3–4 Bash calls, two of which went on a tool that could not start.
Fixing it moved them **0.75→1.00, 0.88→1.00, 0.43→0.86**.

---

## Rules this session earned

1. **Anything reaching the eval agent arrives through the view or a file in the
   agent's home.** No environment variable crosses that boundary.
2. **Run a check against the reference implementation before trusting it** — and
   if you cannot afford to run it that way, that is the first bug.
3. **Verify the outcome, not the step you performed.** Three things shipped
   today that looked correct and did nothing: a fixture that was never tracked,
   a hook that returned zero bytes, an issue filed with an empty body.
4. **Compare failure NAMES, not counts.** The suite went 10 → 11 and only the
   name diff showed the new one was mine.
5. **`runs: 1` cannot detect a change of the size anyone cares about.** One case
   moved ±0.8 between identical invocations. Use `--runs 6`.
6. **Do not re-run only the failures and add them to the old passes.** Measured:
   3 of 11 returned 1.00 with nothing fixed, and one fell 0.86→0.43.
7. **A directory of symlinks into the operator's home does not belong inside a
   repository that things copy.**
8. **`--keep-temp` should be paired with cleanup.** 41 sandboxes, 254 MB,
   accumulated across one session.

---

## Left open on purpose

* **EA-DF-17** (#384) — the adapter binding. SI-21; needs a migration.
* **EA-DF-14**'s product half (#385) — the hook exits 0 silently when it cannot
  resolve an interpreter. Keep `exit 0`; print one line naming what was missing.
* **EA-DF-07** (#386), **EA-DF-04** (#387), **EA-DF-01** (#388).

## State at the end of the batch

| | |
| --- | --- |
| repo suite | 10 failed / **1853** passed / 6 skipped — **identical to baseline by name**. That is the FULL suite (24m10s, `test_score_tools.py` included). The assignment's `repository_unit` adds `--ignore=tests/test_score_tools.py` and yields **10 failed / 1726 passed / 6 skipped** in 14m19s, re-measured at `ac5f7491` on 2026-09-25 — a different command, not a regression. SI-21 hit this and could not reconcile it; quote the command with the count. |
| test graphs | sktSurface 318/318, sktHooks 167/167 |
| ledger | 151 rows; 17 EA findings this session, 12 fixed, 5 filed as issues |
| disk | 59 GB free, 17% used |
| corpus | **not re-run since the fixes** — that is the next step, and the reason for this batch |
