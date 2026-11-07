# Bug Attribution

*What the record keeps about where defects come from, what caught them, and —
the part nothing has ever kept — **where nobody looked**.*

**AT-01 output. This page is read, not executed.** No script reads it, nothing
gates on it, and no exit code anywhere depends on a field described here. The
only mechanical property any of it has is that the file it lives in parses,
which `tests/test_spec_yaml_valid.py` already guards for every
`specs/**/*.y*ml` outside `.history`.

---

## 1. The problem, stated as the shape of the record

**A finding only exists where something was found.**

The cumulative ledger has **364 findings** and not one row for a place nobody
looked. The record is dense exactly where the instruments work and empty exactly
where they are blind — **and it reads the same either way.** A reader cannot
distinguish "we looked here and it was clean" from "nothing has ever looked
here", because only the first kind of place produces rows.

> **STATUS, 2026-09-23 (`SI-27`, #382).** That sentence was still literally true
> of this repository until this date: every row in every ledger was a CATCH, and
> REACH, BLIND and PRICE existed as prose on this page and as **nothing typed
> anywhere**. Measured case-sensitively and word-bounded in
> `examples/validation/agent_rounds/SELF-IMPROVEMENT-MATRIX.md`: CATCH 5,
> REACH 0, BLIND 9, PRICE 1 — and all fifteen are narrative, not rows.
>
> **The first typed rows are at
> `specs/results/deferred/attribution/attribution.yaml`** — 6 REACH, 9 BLIND,
> 3 PRICE, seeded from findings this epic had already measured. §4's box below
> says where it should eventually live.
>
> **And the counting instrument is a trap.** `grep -ciE "\bBLIND\b"` —
> case-INsensitive — counts the English words "blind" and "reach", which this
> project says constantly ("blind dispatch", "blind review"), and returned 28
> for BLIND. A second pattern aimed at structured rows returned 0 for **all
> four including CATCH**, which was the non-vacuity control failing and saying
> the pattern was broken, not that the record was empty. Two wrong answers in
> opposite directions, from one hour's measuring. Use case-sensitive,
> word-bounded patterns, and carry a control that MUST match.

Three failures paid for this page, and **none of them would have been prevented
by a better finding**:

| | what happened | what no record held |
|---|---|---|
| `DEF-124` | an invariant enforced on `bin/cli` and `bin/mcp`, unenforced on `skills/`, `plugins/` and the agent dirs | **the second list.** Three live homes, eight days after the fix |
| `DEF-115` | a node green for weeks; every fixture planted a wrapper and repair cannot read a symlink | **that green meant *could not look*** |
| budgets | `gate_passed: False` on **16 of 16 runs**, nothing stopping | **a price declared before**, so the measurement had nowhere to land |

---

## 2. Four record kinds

| kind | direction | the question it answers |
|---|---|---|
| **CATCH** | backward, from a failure | A defect was found. What caught it, what area was it in, what pins it now? |
| **REACH** | forward, from a rule | An invariant exists. Which surfaces enforce it — **and which do not**? |
| **BLIND** | forward, from a green | A case passes. What could it **never** have caught? |
| **PRICE** | forward, from a proposal | A change was proposed. What was it priced at **before** — and what did it cost? |

**CATCH is the only one indexed by a failure.** The other three are the negative
space, and they are the reason this page exists.

**Four, and one that is missing on purpose.** §6a records a fifth direction —
*a red that was never about the code it was charged to* — measured, named, and
deliberately left without a schema, because nobody has run a round with one.
It is BLIND's twin and it belongs on this list the moment somebody does.

**And a CATCH does not require something to have caught it.** The `channel` may
be in the `reading` class (§4.1) — a defect found by a person or an agent looking at the code, with
nothing red anywhere. Round 3 made the case concretely: a ticket agent hit ZERO
regressions and found one MAJOR pre-existing defect by reading, and because
every clause was scoped to *"a regression happened"*, the most valuable thing
that seat produced had no clause to land in. It reached the matrix only because
somebody read the transcript afterwards. **A defect found by reading is a CATCH
whose channel is in the `reading` class (§4.1) and whose `pinned_by` is usually
empty** — `reading` is a class, never a `channel:` value — and the
empty pin is the interesting half, not a reason to leave it unrecorded.

### 2a. `skill_change` — the one field every kind carries

**`SI-04`.** All four kinds above answer *what was found*. None of them answered
*what changed in the substrate because of it*, and the fastest-growing rows in
the matrix — `UNMODELED/skill-manager-home`, `UNMODELED/agent-harness`,
`UNMODELED/record-keeping` — are precisely the rows where the defect is in the
substrate and the record stops at having noticed.

**So every record kind carries one more field, with one grammar:**

```
skill_change: none | proposed(<unit>, <diff or issue>) | applied(<commit>) | declined(<reason>) | UNDECIDED
```

| value | means |
|---|---|
| `none` | a claim: no change to any skill was needed for this one |
| `proposed(<unit>, <ref>)` | the change is written down somewhere that is not this record |
| `applied(<commit>)` | the substrate is different now, and here is the commit |
| `declined(<reason>)` | somebody decided not to, and said why |
| `UNDECIDED` | the row was looked at and nobody has answered yet — §3's answer to an absent input, counted on its own and never terminal |

**An absent `skill_change` is not `none`.** §3 governs this and it is the whole
reason the field is worth having: `none` is a claim somebody made, absent is
nobody having been asked. A reader that collapses the two reports the entire
pre-`SI-04` record as having considered the question and answered no.

**`recorded-local` is the state this field exists to end.** Thirteen findings in
`specs/results/skill_feedback.md` carry it: written up in full, in this
repository, and filed nowhere. Each one is a defect somebody found, understood
well enough to describe, and left exactly where it was.

**The rule it serves, which is `consumption.md`'s D4:** *a finding anchored to a
skill is consumed only by a change to that skill.* Routing such a finding to a
ticket and closing the ticket changes nothing about the skill.

**Nothing refuses on it.** `scripts/improvement_ledger.py` reads this field
across all four record files and warns; it has no exit-code path at all. §8's
first bullet still holds for this page, and `GOAL-no-new-gates` holds for the
ticket that added the field.

---

## 3. THE RULE THAT MAKES REACH AND BLIND WORTH ANYTHING

**An empty unenforced-list and an empty blind-spot are CLAIMS. They are never
defaults.**

This is `DEF-124` and `DEF-115` in one sentence. A REACH saying *"enforced
everywhere"* and a BLIND saying *"this case could have caught anything"* are the
two most dangerous rows either kind can carry: they read as maximum coverage and
cost nothing to write.

Both are therefore governed by the rule `SS-02` already landed for absent inputs:

> **The correct answer to an absent input is UNDECIDED or a refusal — never
> PASS.**

Applied here:

- *"I did not enumerate the surfaces"* → **`unenforced: UNDECIDED`**, with the
  reason.
- *"I enumerated them and found none uncovered"* → **a claim**, and it names
  **how** it enumerated.

**These must never be written the same way.** A record that cannot tell them
apart has shipped `SS-02`'s class in a new field, and it will read as coverage
for however long it takes the next `DEF-124` to arrive.

---

## 4. CATCH — the channel, the area, the pin

A CATCH is an ordinary finding in the project's cumulative ledger, carrying
three things beyond the existing schema.

> **WHERE THE LEDGER IS, because this sentence has already misled an agent.**
> In a repository that has one, it is `specs/deferred_findings.yaml`. **This
> repository does not have one on `main`** — the 364 rows live in the sealed
> epic results (`specs/results/deferred_findings_*.yaml`), and creating
> `specs/deferred_findings.yaml` from a branch would collide with all of them on
> merge.
>
> **ON `epic/self-improvement-substrate`, SINCE `SI-27` (#382), THE LEDGER IS
> `specs/results/deferred_findings_final.yaml` — 120 rows, and nothing else in
> this repository is it.** It had been two: that file held 87 rows and
> `specs/results/deferred/<ticket>.yaml` held 28 more that nothing read, so a
> query for `SI-16-DF-02` and `SI-16-DF-03` returned NOT FOUND for both while
> the epic agent was citing them as the two blockers before any scored eval
> run. The 28 were absorbed; the per-ticket files are now INBOX STUBS. A ticket
> still files into its own inbox file, and the epic agent absorbs at wave close
> — that step is what had never happened. **A row lives in exactly one of the
> two places, never both**, and nothing reads the inbox directory as a
> population.
>
> **`disposition.py` cannot see any of this.** Its `LEDGER` is
> `specs/desired_program_model/deferred_findings.yaml`, which does not exist
> here, so D1/D2/D3 have never been evaluated over these rows at all — 80 of
> 115 were unsettled for a whole epic with nothing reporting it. That is a
> REACH row in the seeded record, not a footnote.
>
> **So when that path is absent, write the rows into the ticket's own
> `results/attribution.yaml`** and say in a header where they belong and when
> they move. In THIS repository the seeded REACH/BLIND/PRICE record is at
> `specs/results/deferred/attribution/attribution.yaml`, and that path is a
> compromise the file's own header explains: SI-27's conflict keys did not
> reach `specs/results/attribution.yaml`, and a SUBDIRECTORY of the inbox is
> the one place a `specs/results/deferred/*.yaml` glob cannot mistake it for a
> backlog of findings. **It should move to `specs/results/attribution.yaml`
> under a ticket whose keys allow it.** A blind agent following §4 literally went looking for the file,
> did not find it, and was one step from creating the colliding path — it was
> saved only by stumbling on a comment in a file nothing routes to. **That is a
> `DOC-COULD-HAVE-SAID`, and this is the doc saying it.**

```yaml
- id: AT-01-DF-01
  # ... the existing finding fields ...
  channel: test-graph                    # the vocabulary in §4.1
  channel_note: "specWorkflow node ..."  # existing free text, optional
  area: "the workflow-close path"        # PROSE, written by whoever found it
  pinned_by: "tests/test_x.py::test_y"   # or omitted, with pin_note saying why
  skill_change: applied(9f2c1ab)         # §2a — absent is NOT `none`
  goal: GOAL-findings-become-changes     # the measurement this bears on, if any
```

### Final epic manual-testing escapes

In an epic, the full integrated Test Graph runs before one final manual
product-testing phase (`git-epic-workflow/references/finalize.md` §2c).
Record defects discovered there as CATCH rows with their original channel
(`operator-doing-the-work` for manual product interaction), reproduction,
affected area/model anchor and missed graph coverage.
Add a BLIND for a passing instrument that could not observe the defect. Where
feasible, add a Test Graph regression assertion, demonstrate red before the fix
and green after, and cite it in `pinned_by`. Otherwise supply `pin_note` with
the automation limit and remaining manual coverage. Preserve the original
catch channel when the regression later becomes automated. Repairs rerun the
affected dependency closure and the final integrated confirmation; the manual
phase stays at epic finalization rather than recurring during every ticket.

### 4.1 The channel vocabulary, and its class

**Ten tokens.** Seven are `CA-02`'s, unchanged and not relabelled. Three —
`test-graph`, `tlc` and `cross-implementation` — are added because the record
could not name them. **`reading` is a CLASS, not a token**: a defect found by
reading is filed under `census`, `independent-review` or `blind-judges` when a
reader was looking for defects, and under `operator-doing-the-work` when it was
noticed while doing something else. `UNDECIDED` (§3) is not a token either; it
is the honest entry when nobody can say which token applies, and
`scripts/disposition.py` does not report it as off-vocabulary.

**The class is a lookup, not a judgement.** *"Was this caught by an automated
instrument or by a hand?"* is answered by finding the token in this table. **No
`channel_note` is read.**

| channel | class | what it means |
|---|---|---|
| `test-graph` | **automated** | a Test Graph node went red — **new** |
| `the-suite` | **automated** | pytest |
| `tlc` | **automated** | the model checker — **new** |
| `operator-running-a-shipped-instrument` | **automated** | a standing instrument reported it; a person invoked it |
| `operator-doing-the-work` | **hand** | found while doing something else |
| `operator-running-own-instrument` | **hand** | a probe written for the occasion and thrown away |
| `cross-implementation` | **automated** | two implementations of the same contract disagreed — **new**, and see below |
| `census` | **reading** | a systematic sweep of the record |
| `independent-review` | **reading** | a reviewer reading the change |
| `blind-judges` | **reading** | a scored card's judge |

**The line between `automated` and `hand` is one question:** *would it catch this
again tomorrow, with nobody watching?*

> **THE TIE-BREAK THAT QUESTION DOES NOT SETTLE, measured.** Two agents met the
> same situation — *a person ran `close ticket` by hand and read the refusal* —
> and classed it opposite ways. `AT-EX-CATCH-02` filed it
> `operator-doing-the-work` (**hand**); a round-2 agent filed it
> `operator-running-a-shipped-instrument` (**automated**), reasoning that the
> instrument stands and would refuse again tomorrow. **Both readings are
> defensible from the sentence above, and they flip the one number §4.1 exists
> to protect.**
>
> **The tie-break is: did the instrument REPORT the defect, or did the operator
> notice something the instrument stayed silent about?**
>
> - The gate refused and its message named the problem → **automated**. The
>   instrument did the work; the person only invoked it.
> - The command succeeded, or refused for an unrelated reason, and the person
>   spotted the defect anyway → **hand**. The instrument was silent, and
>   silence is what `hand` means.
>
> Under that rule `AT-EX-CATCH-02` is **`operator-doing-the-work`** and stays as
> filed: the close gate there refused on plan status, and the archive-seam
> defect was something the operator noticed while dealing with it. **The
> existing row is not amended** — the rule was written after it, and refiling it
> would be fitting the record to the rule.

**`cross-implementation` is `automated` by that question and is worth its own
token because nothing else finds what it finds.** It was added after two
independently-written fixes to the same YAML parser were run against each
other's corpora and each turned out to be wrong in ways its own tests reported
clean on — then two further defects surfaced that had survived both. A single
implementation cannot produce this signal at any budget, and the only
prerequisite is that a second implementation of the same contract exists.
`PyYAML` is that second implementation here; `#298` and `#307` are the record. That is why
`operator-running-a-shipped-instrument` is automated — the instrument stands —
and `operator-running-own-instrument` is **hand** — the probe does not. **A
throwaway probe that found a real bug is a hand catch wearing a script.**

### 4.2 The pin

**Any CATCH whose class is not `automated` names the assertion that will catch it
next time**, as a test node id or `path::test_name`.

```yaml
  pinned_by: "tests/test_absent_invariants_refuse.py::test_empty_invariants_refuse"
```

**Where no assertion was added, the record says so and says why:**

```yaml
  pin_note: "not pinned: the failure is in the installer, which has no fixture
             here. Filed as skill-manager#261."
```

**A blank is not an answer.** `pin_note` present with `pinned_by` absent is a
complete record; both absent is not.

**Automated catches need no pin** — the thing that caught it is the pin, and
adding a second assertion is duplication, which
`references/architecture_advice.md` §5 names as a standing instruction to
duplicate.

> **This is wider than `GOAL-hand-catches-name-their-pin`'s text, which says
> hand.** It is widened to `reading` deliberately: a bug found by a reviewer has
> nothing standing that would find it again, which is the entire reason the pin
> exists. The widening is recorded here rather than applied silently, and
> `AT-04` scores the goal on its own text.

---

## 5. REACH — an invariant, and the surfaces it does not cover

**Written by whoever wrote the invariant**, because they are the only party who
knows what they were aiming at.

```yaml
reach:
  - invariant: "every executable entrypoint resolves its home before writing"
    enforced_on:
      - "bin/cli"
      - "bin/mcp"
    unenforced_on:
      - "skills/"
      - "plugins/"
      - "the agent directories"
    enumerated_by: "read every directory containing an executable; 5 found, 2 covered"
    note: "DEF-124. The unenforced list is why three live homes were lost eight
           days after the fix was called done."
    skill_change: applied(4c1d0e2)   # §2a. A REACH whose unenforced list was
                                     # never acted on is a list, not a reach.
```

**`unenforced_on` is the field this kind exists for.** `enforced_on` is what
anybody would write anyway.

**`enumerated_by` is mandatory whenever `unenforced_on` is empty**, and it says
how the surfaces were enumerated — §3. An empty list with no `enumerated_by` is
malformed, not clean.

**Where the surfaces were not enumerated:**

```yaml
    unenforced_on: UNDECIDED
    enumerated_by: "not enumerated — I checked the two entrypoints I changed"
```

**That row is honest and it is more useful than a confident empty list.**

---

## 6. BLIND — a green, and what it could never have caught

**Written by whoever wrote the case**, at the time they write it. A BLIND
reconstructed later by a reader is a different and weaker artifact, because the
author is the only one who knows what the fixture was standing in for.

```yaml
blind:
  - case: "test_repair_restores_wrapper"
    passes: true
    could_not_have_caught: "any defect reachable only through a symlinked home —
      every fixture plants a real wrapper, and repair cannot read a symlink, so
      the symlink path is never executed"
    why: "fixture construction, not assertion strength"
    note: "DEF-115. Green for weeks. Green meant COULD NOT LOOK."
    skill_change: declined("the symlinked-home path is being removed outright;
                   pinning it would pin a shape we are deleting")
```

**An empty `could_not_have_caught` is a claim** — §3 — and needs the same
treatment as an empty `unenforced_on`. *"I did not work out what this case is
blind to"* is `UNDECIDED`, and it is the correct entry when it is true.

**This repository has a starting population and it is not zero.**
`CA-10-DF-14` records **3 vacuous passes**; `SS-06` re-measured the vacuous
population at **six**. Those are BLIND records that already exist as findings and
have never had a place to be written as reach.

**A BLIND does not fail a green and does not gate a close.** It annotates one.

---

## 6a. THE INSTRUMENT'S OWN DEFECTS, and the red that was never a defect

Measured, in the first eval suite built on `references/plugin_evals.md`
(`haydenrear/skill-manager`, fourteen runs of one case, ~$12):

| defects the round produced | count |
|---|---|
| in the product — shipped CLIs and skills | **4** |
| in the instrument — the suite's own cases, fixtures and environment | **~12** |

**The instrument out-produced the product three to one**, and this is the
ordinary case rather than a bad round. An apparatus is newer than the thing it
measures and gets less scrutiny.

Two consequences, and they are different problems.

### The instrument's defects are CATCHes, and the `area` is what keeps them apart

Nothing new is needed for these. A defect in a fixture is a defect: it has a
channel, it has a pin or an honest empty one, and §4 already carries it. **What
it needs is for `area` to say the apparatus** — because `area` is prose and
prose is optional in practice, and a record that does not distinguish them
produces a count in which twelve of sixteen defects are the measuring stick.
Read as product quality, that number is not merely imprecise; it is inverted.

So: **an `area` on an instrument defect names the instrument.**
`"the eval harness's TMPDIR handling"`, not `"worktree creation"` — even though
a worktree command is what went red.

### The red that was not a defect at all, which has no kind

This is the part the four kinds do not reach, and it is worth stating rather
than filling.

Each of those twelve instrument defects **produced a red against innocent
code**. Eight consecutive runs failed on an unset `TMPDIR`; the score said the
skill could not create a worktree. *Only the trace told them apart* — and a
trace is not a record, it is a file somebody has to read.

Line that up against §2 and the gap is exact:

> **BLIND** is a **green** that could not have caught something.
> This is a **red** that was never about the code it was charged to.

They are twins, and only one of them has a kind. A green that cannot look and a
red that measures the apparatus are the two ways a signal reports on something
other than its subject, and this page currently records the first and loses the
second.

**What that record would need is not obvious, and §3 governs the answer.** An
absent input is UNDECIDED, never a PASS — so the honest state of this section
is: **UNDECIDED, and named.** What is known:

- it is not a BLIND: the case is red, and `could_not_have_caught` is the wrong
  question — the case caught something, just not in the code;
- it is not a plain CATCH either: a CATCH is indexed by a defect in the subject,
  and here the subject is clean;
- the useful field is probably a **retraction** — *this many reds against this
  area were the instrument, and here is the trace* — because the failure mode
  is a later reader counting reds and concluding the area is fragile.

**Nobody has run a round with such a record, so this page does not ship a
schema for it.** A schema written from the armchair is a claim, and §3 says
what this page does with claims. What this section fixes is the cheaper half:
the reds are now *known* to be uncounted, instead of being counted.

---

## 7. PRICE — declared before, measured after

```yaml
price:
  - proposal: "collapse the three manifest parsers into one"
    declared_before:
      value: "≈400 lines removed, 2 days, one behaviour change to the fallback path"
      declared_at_commit: "902cfd7"
    measured_after:
      value: "612 lines removed, 3 days, two behaviour changes"
      measured_at_commit: null      # null until it is actually measured
    verdict: null                   # null until both halves exist
    skill_change: proposed(spec-double-2, "#319")   # §2a
```

**Two fields, written at two different times, and the record makes backfilling
visible rather than convenient.** `declared_at_commit` is the point of the whole
kind: a price whose declaration commit is *after* the measurement commit is not a
price, it is a retrospective, and anyone reading the two shas can see it.

**Why this kind exists:** `gate_passed: False` on **16 of 16 runs with nothing
stopping.** The cost was measured every single time. It was never priced, so
sixteen measurements had nothing to be measured *against* and sixteen times
nothing happened.

**A refused proposal keeps its `declared_before`.** That is the record of what it
would have cost, and it is the only reason a refusal is reviewable later.

---

## 7a. The influence graph, and the matrix it accumulates into

**The four kinds are per-finding. The influence graph is what they add up to.**

The arc for one defect is **found → area → pinned**:

```
a defect was found  (a regression, OR something noticed by reading)
  -> what CAUGHT it            (CATCH.channel, class automated | hand | reading)
  -> what AREA it lived in     (CATCH.area, prose, from whoever found it)
  -> what PINS it now          (CATCH.pinned_by, or pin_note saying why not)
```

**The area is recorded as prose by the finder, and ANCHORED TO A TLA+ ACTION by
the epic agent.** The model is the semantic representation of the program and it
outlives the code — files are renamed, split and moved; `CloseTicket` is not. A
defect that fits no declared action is anchored `UNMODELED`, and **the size
of that bucket measures how much of the real bug surface the model does not
reach.** Do not stretch an action to cover something it does not mean; stretching
destroys that number.

Accumulated per anchor across tickets and epics, that is
`examples/validation/agent_rounds/SELF-IMPROVEMENT-MATRIX.md`. **The column that
matters is `escaped to hand`** — the only one that says an automated instrument
was blind.

**An area that escapes once is noise. An area that escapes in three rounds is
telling you something about its shape.** That is the whole reason to keep the
graph over time rather than per epic.

**It is maintained by prompting, not by a tool, and that is a decision rather
than a gap.** Computing it would mean parsing findings, inferring areas and
joining across epics — three inference steps, each a place to put a bug into the
instrument used to find bugs. `prompts/regression_architecture.md` is the ask;
`prompts/regression_judge.md` judges the transcripts blind. **No checker, gate,
lint or static analyzer is the answer here** — that route is measured and closed
(`references/architecture_advice.md`), and if a tool is built later it belongs in
a separate library with this page as its specification.

**What the graph cannot currently say, stated so nobody reads it as more than it
is: there are no denominators.** An area with one escape in two invocations and
one with one escape in a hundred look identical in the matrix. Until a round
carries per-area invocation counts, a concentration in that table may be a
concentration of attention rather than of defects.

## 7b. CONSERVATION — what happens to findings when the model changes

**The model may shrink. The record may not.**

This is the whole rule, and it exists because the matrix anchors findings to
TLA+ actions, which makes the model a place where counts live — and anything
that holds a count can be improved by editing the container instead of the
contents.

**There is no prohibition here and there should not be one.** Reducing
complexity where defects aggregate is one of the two responses this programme
wants, and it legitimately removes model surface. A ban on removal would put
that response in direct conflict with the record that motivates it. So removal
stays available and is made *pointless* instead:

> **Total findings is invariant under any model change. Only their distribution
> moves.**

Drop an action and its findings re-anchor — to whatever absorbed the behaviour,
or to `UNMODELED`. Merge two and the rows add. Split one and the parts sum to
the whole. **Nothing evaporates**, and a reader checks it by summing a column.

### Why arithmetic and not a rule against deleting

**Spreading findings across more of the model and hiding a concentration are the
same edit.** Both split a heavy row into light ones; both are a diff that adds
actions. No prohibition can separate them, because there is nothing in the
change itself to separate. The sum can: after a legitimate split the parts still
add to the original, and the concentration is visibly redistributed rather than
reduced.

That also disposes of the four quieter versions of the same move — **merge**,
**widen an action's meaning until the bug is not in it**, **re-anchor to
`UNMODELED`**, and **drop**. Under conservation all four are relabelling, and
relabelling does not change a total.

### What a model change must therefore record

Every model change is recorded in the matrix's carry-through log, and each
affected row says **carried**, **dropped** or **split/merged** — that part is
unchanged. Conservation adds one line to the entry:

```
findings before: N    findings after: N    (re-anchored: <id> -> <new anchor>, ...)
```

**If the two numbers differ, the entry is wrong**, and it is wrong in a way that
is visible without reading any of the prose around it.

### The corollary, which is the point of the whole loop

A proposal that reduces an action's escape count **by removing the action** has
reduced nothing, and under conservation it cannot even appear to. So the only
way the count at an action falls is the honest one: **something started catching
the defects before they escaped.**

That is what makes "fewer escapes" mean anything, and it is why this rule sits
next to PRICE rather than in a governance section. It is not a control. It is
the thing that makes the measurement mean what it says.

## 7c. SEMANTIC BINS — where findings accumulate outside the model

**`UNMODELED` is not one place. It is a space of named bins**, and the name is
already being collected: §7a requires every unanchored finding to *say what it
sits beneath*, and refuses to let an action be stretched to cover it. That string
is the bin. **Nothing new is recorded here** — what is new is that findings are
grouped by it instead of pooled.

```
UNMODELED/<bin>          e.g.  UNMODELED/yaml-parser
                               UNMODELED/skill-composition
```

**Why grouping is the whole point.** Seven findings pooled in `UNMODELED` reads
as one gap. Seven findings in one bin is a gap with a shape; seven across five
bins is a model that is thin everywhere. **Those want different answers, and the
pooled count cannot tell them apart.**

### The disposition of a bin, which is NOT in-scope / out-of-scope

A bin is not waiting for a yes/no about whether it belongs in the model. It is
carrying a claim about **representability**, and there are four:

| disposition | means | what the bin is waiting for |
|---|---|---|
| `MODELABLE` | this could be an action today; nothing is stopping it | **a decision.** Accumulating here is now a choice, and it is the choice §7a's `UNMODELED` number exists to make visible |
| `DEFERRED` | representable in principle, **not validatable with what exists** | a **named capability**, not a mood. *"No runner exists that can drive a multi-skill plugin end to end"* is a blocker. *"Hard to test"* is not |
| `RECORD-ONLY` | not expected to become an action | nothing. It accumulates because **the accumulation is evidence about the architecture**, which is useful whether or not it ever becomes a model element |
| `UNDECIDED` | nobody has classified it | classification. **This is the default for a new bin** — §3, an absent input is `UNDECIDED`, never a PASS |

**`DEFERRED` is the case this section exists for.** Bugs in prompts, in skills,
and in the composition of several skills inside one plugin are real, they
recur, and **no test graph binding can drive them today.** They are not out of
scope and they are not modelable-now. They are waiting on a runner that does not
exist yet, and *that sentence is the record* — not a shrug, and not a deletion.

> **AND THAT BLOCKER HAS PARTLY EXPIRED — rule 2 below, applied to this page's
> own example.** A runner that drives a multi-skill plugin end to end now
> exists and has been measured: `claude plugin eval` loads several units in one
> run and scores them, and `references/plugin_evals.md` §3.5 records three
> loaded together. The first suite built on it, in `haydenrear/skill-manager`,
> **found four defects in shipped CLIs and skills that 258 passing unit tests
> did not** — all four about an agent's path through a CLI, which is precisely
> the shape this bin was opened to hold.
>
> **The bin does not close, and the blocker is rewritten, not deleted.** What
> expired is *"no runner exists"*. What is still true is narrower and it is the
> sentence that should now be in the bin: **no `test_graph` binding drives one**
> — `plugin eval` is a separate runner with its own environment, its own cost,
> and no graph node, so the findings it produces still arrive by hand. Whether a
> binding is possible is UNDECIDED and nobody has tried it.
>
> Rewriting a blocker to the narrower true statement is the only move rule 2
> permits here. Closing the bin would claim the graph reaches these defects;
> leaving *"no runner exists"* in place would be the record going stale in the
> exact way rule 2 exists to catch.

### Three rules, and they are what keep a bin from being a wastebasket

1. **A bin accumulates regardless of disposition. Deferral is not closure.** A
   `DEFERRED` or `RECORD-ONLY` bin keeps counting forever. Nothing is ever moved
   into a disposition in order to stop counting it.

2. **A `DEFERRED` bin's blocker is re-read every round.** If the named capability
   now exists and the bin did not move, **that is a finding** — about the record,
   not the code.

3. **A growing `DEFERRED` bin is a PRICE on the missing capability.** This is the
   useful output and it is the reason deferral is worth writing down rather than
   waving at: the bin says *what deferring has cost so far*, in findings, and
   that is the evidence the capability gets built on. It is `gate_passed: False`
   on 16 of 16 runs, avoided — **a cost measured against something.**

### The degeneracy this closes, which is the twin of §7b's

§7b makes **removing from the model** harmless, because findings are conserved.

The version conservation cannot see is **refusing to add** — *"that is just
infrastructure"* — which achieves the same silence and never touches the model at
all. So the escape is not blocked; it is made **loud**: the refusal becomes a
named bin, with a disposition, that **keeps counting.** A decision not to model
something stays visible and re-reviewable instead of being the quiet way to make
a number stop growing.

### And a bin still feeds the architecture read

**A bin that can never be modeled can still say an area is too complex.** The
inability to represent something in TLA+ does not remove it from the record and
does not exempt it from response **(a)**. `RECORD-ONLY` is a statement about
*representation*, never about relevance.

### When a bin becomes an action

Conservation — §7b — does real work here for the first time. The bin's findings
**re-anchor out of `UNMODELED/<bin>` and into the new action**; the totals before
and after are equal. **That is what proves the extension absorbed the history
rather than restarting the count**, and it is the difference between extending
the model and quietly opening a fresh one.

## 8. What this page deliberately does not do

- **It does not gate.** Nothing refuses, nothing blocks a close, no exit code
  moves. `references/architecture_advice.md` opens with why: *"Every mechanical
  gate this project shipped was defeated cheaply and none of them ever caught a
  bug."*
- **It does not derive the area or the surfaces.** No path map, no taxonomy. Both
  are prose from the person who knows. A model reading twenty records can group
  prose; it cannot recover an area from a token chosen to make a count look
  better — `references/architecture_tags.md` §5 enumerates that attack as `A1`.
- **It does not touch `surface`.** That field is for parallel-ticket conflict
  detection — `git-epic-workflow/references/deferment.md` — and bending it into
  an architecture axis breaks what it does do. Measured, it would not help
  anyway: `workflow` is non-empty on **309** of 364 rows and `production` on
  **77**.
- **It does not touch `references/eval_scorecard.md`.** The judged card's `N-D1`
  already asks what the cases caught and missed, unscored. Editing it moves the
  served digest and forces a version bump across 95 sealed cards for no new
  question. **Byte cost to `serve`: 0.**
- **It builds no index.** The record is read by reading it. If answering one of
  §2's four questions requires a tool, the schema is wrong. The seeded
  `attribution.yaml` is a FILE, not an index: it is YAML so that it parses, and
  it is read the same way this page is.
- **It does not make a BLIND a reason to delete a green.** Every BLIND row in
  the seeded record annotates a case that still runs. Two of the nine describe
  greens that are correct today and blind anyway (`validate_epic_plan.py`'s
  wave check, shipped deliberately; the eval suite's 1.00, refused rather than
  built on), and naming that is the whole point — a reader can now tell those
  two apart from the seven that are defects waiting for an owner.

---

## 9. The drift this page inherits, measured

**`CA-02` closed the channel vocabulary. The very next epic put four tokens
outside it on 27 rows, and `disposition.py`'s `ADVISORY (not a clause)` line
printed on every one of them.**

At the `epic/stabilize-substrate` tip — 364 findings, **144 with a channel
(39.6%)**:

| token | rows | disposition |
|---|---|---|
| `execution` | 23 | see below |
| `review` | 3 | → `independent-review` |
| `reading` | 1 | see below |

**All 27 are `SS-*`. Not one is from any other epic.** The advisory worked
exactly as designed — it advised, and was ignored, twenty-seven times, by the
epic standing closest to it.

**And the disposition is mostly UNDECIDED, because the evidence is not there.**
`channel_note` exists on **45 of 364** rows overall and on **9 of the 27**
drifted ones. **Eighteen of the 27 carry no prose at all.**

- **`review` → `independent-review`.** A mechanical rename of a synonym, not a
  classification. 3 rows.
- **`execution` (23) and `reading` (1) → UNDECIDED where no `channel_note`
  exists.** `execution` plausibly means `the-suite`, `tlc` or
  `operator-running-a-shipped-instrument`, and **those are three different
  classes in §4.1's table** — the guess would decide the automated/hand split for
  23 rows on nothing. `references/consumption.md` already names this move as the
  thing to avoid: *assigning a channel from somebody else's prose is the hand
  classification this programme exists to remove.*

**UNDECIDED is the correct answer here and its count is a result, not a failure.**

### `blind-judges`

**Declared by `CA-02`, selected zero times in 364 findings.** It is **retained**,
not retired: it is the one token naming a channel that produced findings this
project has published at length — the four judges of the `hexagonal-prompting`
rerun produced 4 findings the round's own ratio omitted. **The token is not dead;
the filing is.** A token retired because nobody typed it would delete the
evidence that a channel exists and is not being recorded, which is this page's
entire subject.
