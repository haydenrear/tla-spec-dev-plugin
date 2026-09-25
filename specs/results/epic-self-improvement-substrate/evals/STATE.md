# The eval ladder: what is done, what is left, what was decided

Written 2026-09-24. Branch tip `ee237e21`; plugin `main` at `212b8387`.
This is the handoff document for SI-21 through SI-23 and for whoever picks the
eval lane up next. It supersedes nothing; it collects what is otherwise spread
across sixteen commit messages.

---

## The one-line summary

**The substrate scores well. Its instruments did not, and that was the work.**
Of the fourteen low scores examined today, **every one investigated to the end
was an instrument defect, not a substrate defect** — and each produced a
plausible number rather than an error.

---

## Where the corpus stands

Full run at `3fe0888f`, 64 cases, **$16.20**, 46 minutes:

| | |
| --- | --- |
| decidable | **58 of 64** (6 UNDECIDED, correctly named) |
| at 1.00 | **45 of 58 — 78%** |
| decidable mean | **0.931** |

Four cases have been repaired since that run and re-measured at 1.00 or better,
so the corpus is now better than those numbers. **It has not been re-run whole
since the repairs**, and that is the first thing SI-23 should do.

**Every case is `runs: 1`.** One case was measured swinging **±0.8 between
identical invocations on an unchanged commit**. Until that is addressed, no
single-sample score in this corpus supports a claim, and SI-23 must either
raise `runs` for the cases it reads or state the limit in its verdicts.

---

## What was fixed (nine instrument defects, one day)

| id | defect | evidence it is fixed |
| --- | --- | --- |
| EA-DF-08 | an UNDECIDED verdict was written and never reached the screen | stanza names all 6 under the table; silent on `w-skt-*` (the control) |
| EA-DF-09 | a grader asserted an answer its own fixture denied — the home was lost in SI-15's move and misreported as "no fixture by design" | 0.67 → **1.00** |
| EA-DF-10 | the fixture could not be committed; `.gitignore` hid `.skill-manager/` at any depth and `git add` staged nothing | 0 → **37 files** |
| EA-DF-11 | a judge rubric's pass and fail branches overlapped; three judges resolved it against the correct answer, twice | FAIL×3 → **PASS×3** |
| EA-DF-12 | `skill-manager` could not start — jbang wanted a JDK from the network | CLI reports its pinned commit |
| EA-DF-13 | `run.sh` overwrote the plugin's hooks, so **every** `w-*` score was measured without the orientation the product ships | orientation delivered **6/6** |
| EA-DF-14 | the orientation hook discarded a good report on a non-zero exit code | no-home case now prints its diagnostic |
| EA-DF-15 | **no `uv run --script` skill script could start** — cold uv cache, no network | primed, resolves under `UV_OFFLINE=1` |
| EA-DF-16 | a `require` rule matched a path spelling, not the act of reading | 0.86 → **1.00**, twice |

Plus a budget calibrated for a fixture that had been replaced, and a vacuous
pass in the setup checker itself (`find` on an absent directory reports zero
symlinks, so "no home at all" printed "ok").

### The class worth carrying into the next epic

Three of those are one shape, found three times in a day:

```
skill-manager    could not start — no JDK          EA-DF-12
orientation hook could not start — no python       EA-DF-14
every uv script  could not start — cold cache      EA-DF-15
```

**A sandboxed run inherits an empty `HOME`, so every toolchain that caches under
`HOME` is cold and reaches for a network that is not there.** The tool is
absent, the run scores anyway, and the number reads as a statement about the
agent. Anything else caching under `HOME` will do the same, silently.

The remedy, applied three times: **name the cache, keep it in `.toolchain`,
prime it operator-side.**

A second class, four instances: **a grader that punishes correct behaviour
performed differently than its author imagined** — `answers-yes` against a
fixture that made "no" true, overlapping judge branches, a budget from a
replaced fixture, a path spelling instead of a filename. The common error is
writing down *the path the author walked* instead of *the destination*.

---

## Decisions taken

**Fix the instruments before running more evals.** The owner's call, and it was
right: a conflict key keeps two *concurrent* writers off a surface, and SI-21
was never dispatched. Deferring to an undispatched ticket is bookkeeping, not
safety.

**Remove the need for the network rather than open it.** Asked to allow the JDK
download, the machine turned out to have twelve JDKs already. Pointing jbang at
one removes the request instead of permitting it — smaller change, stronger
isolation, sandbox keeps no network at all. The same reasoning produced the
primed uv cache.

**`HOME`, not `SKILL_MANAGER_HOME`, and not `DOCKER_CONFIG`.** Both alternatives
were tried. `DOCKER_CONFIG` elsewhere does nothing: the check reads `~/.docker`
regardless and the refusal is byte-identical. `SKILL_MANAGER_HOME` selects which
skill-manager home a run uses and has no bearing on the sandbox's scan. `HOME`
is the only lever — and overriding it breaks authentication, so the scratch home
must link `Library/Keychains`. The two constraints are only satisfiable
together.

**The fixture home belongs at the workspace root.** `./.skill-manager` is what
the substrate means by "this project's home" and where `skt status` looks. Under
`cases/<case>/` the orientation hook reported, truthfully and uselessly, "no
skill-manager home found". The workspace root is `<sandbox>/home/cwd`, made per
run and destroyed with it, so this is exactly as isolated — **verified: 0 files
modified in the repo's `.skill-manager` and 0 in the operator's root home across
six runs.**

**Stage the shipped hooks.** SI-16 declined to, because it "would move scores in
a ticket that is not about evals". That was right then; moving scores is the
point now. A score should describe what ships.

**Measure with `--runs 6`, not `--runs 1`, before claiming a change.** Learned
the hard way: four changes were made to one case reading noise as signal before
anyone took a real sample.

---

## The measurement that decided the orientation question

Three six-run samples of `w-sm-verify-is-not-currency`, same case:

| arm | mean |
| --- | --- |
| hook suppressed, home under `cases/` | **0.53** |
| hook delivered, home under `cases/` | **0.69** |
| hook delivered, home at the workspace root | **0.81** |

Monotone; the endpoint difference is about t≈2.7 at n=6 per arm. The middle step
alone is **not** significant and was wrongly claimed as an improvement at the
time. Cost stayed flat (~$1.45 per six runs), so the gain is not from doing less
work — it is from not working blind.

---

## What is left

### Immediate

1. **Re-run the full corpus** at the current tip. The 45/58 above predates nine
   fixes. ~$16, 46 minutes.
2. **Triage the remaining low scores**, three of which are unread:
   - `w-sdc-complexity-ledger-is-advisory` 0.75 — judge FAIL×3. Its rubric asks
     whether the agent treats a complexity warning as advisory rather than
     blocking. That is `GOAL-no-new-gates` as an executable test, so a real
     failure here is **high value**.
   - `w-giw-wt-refusal-quotes-subject` 0.75 — regex on `last_message`; same
     shape as EA-DF-09, unverified.
   - `w-giw-wt-close-no-force-on-unpublished` 0.86 — requires reading
     `close.txt`, already a bare filename, and the agent surfaced the blocker
     correctly in three turns without opening it. Over-specifies the means.
3. **The three likely-real gaps**, which have a different signature — they fail
   a `require-*` marker a *successful action* would have written, not a content
   assertion:
   - `w-sdc-ticket-binding-bare-adapter-module` **0.17**, 4 of 20 turns
   - `start-from-the-spec-not-the-source` **0.33**, 14 of 40 turns
   - `compose-a-behavioural-graph` **0.33**, 42 of 60 turns, no graph produced
   These are the best candidates in the corpus for genuine capability gaps and
   should be read before anything else is tuned.
4. **Three `within-budget`-only failures** (`w-skt-check-record-disagrees-with-checkout`,
   `w-epic-force-when-owner-decided`, `w-epic-assignment-no-force-on-blocking`)
   at `max_calls: {Bash: 3..4}`. Every substantive grader passes. The budget
   counts **Bash** calls only, so an agent that uses `Read` spends fewer — the
   ceiling conflates efficiency with tool choice. Recalibrate from a measured
   call count, not a guess.

### Tickets

- **SI-21** (eval ladder 3/4) — the tla-spec-dev CLI's seven verbs. Manual
  record first, as rungs 1 and 2 did and as git can be made to prove. Note
  `run spec-unit-tests --ticket` is KNOWN-WEAK (SIS-KICKOFF-F-04): encode what
  it does, not what it documents.
- **SI-22** (eval ladder 4/4) — skill-manager CLI per agent type, from a fresh
  home. Two things it must know: `w-sm-verify-is-not-currency` can only exercise
  its fallback branch until it gets a stale-home fixture that a currency check
  can actually read; and the six needs-a-home cases stay UNDECIDED until
  something smaller than a 41,000-entry home is found.
- **SI-23** (Evaluation B) — decides six goals. Must state: every score is a
  single sample; the corpus was re-instrumented mid-ladder so pre-`ee237e21`
  numbers are not comparable; and all scores are against the **pinned**
  `skill-manager 0.28.1+g7941f4e1dd9e`, which every run reports as drifted from
  the branch tip.

### Product-side, filed not fixed

- **EA-DF-14's second half.** The orientation hook exits 0 silently when it
  cannot resolve an interpreter. Keep `exit 0` — the contract is right — but
  print one line naming what was missing. On a stock macOS PATH (`python3` is
  3.9.6) every session silently loses the substrate's only discoverability
  mechanism, which is what the progressive-disclosure goal runs through.
- **The 74 manifest edits** remain uncommitted in 74 other repositories.
- **Restart Claude/Codex** — the MCP gateway re-registration printed
  `ACTION_REQUIRED` and has not been actioned.

---

## How to run this, so nobody rediscovers it again

```bash
evals/setup-eval-home.sh --smoke     # once per machine; builds, checks, proves
evals/run.sh                         # everything
evals/run.sh --case 'w-sm-*' --runs 6
```

`run.sh` finds `.toolchain/evalhome` by itself. The whole toolchain — pinned
checkout, jbang cache, uv cache, scratch home — is under `.toolchain/`, which is
gitignored, so **`rm -rf .toolchain` is the reset button** and `--smoke` rebuilds
and re-proves it for about ten cents.

`--smoke` asserts a **1.00**, not an exit code, and was falsified both ways: it
passes on a working lane and fails (exit 1, $0.00) on a broken one. Run it after
any change to `run.sh`, `lib/place.sh`, `lib/verify.sh` or the hooks — all four
changed today, and each could have silently voided the suite.
