# SI-20 — every `skt` verb, driven by hand, before any eval case existed

Measured 2026-09-23 in the ticket worktree
`/Users/hayde/IdeaProjects/wt-369-eval-ladder-skt`, branched from
`epic/self-improvement-substrate` at
`1cb00be76cc49ef3346775750e08b3ec94c3ab9b` on `haydenrear/tla-spec-dev-plugin`.
Every block below is captured output, in `transcripts/`, not a summary written
afterwards. Where a graph ran, the verdict is read from that run's own
`summary.json`; **no graph here is called green because a command returned 0.**

This file is committed **before** the eval cases. That order is the
deliverable: `GOAL-evals-earned` says no eval is written for behaviour nobody
has watched work, and the two commit shas are the check.

---

## 0. Which skt, exactly

`GOAL-one-plugin` is the reason this ticket exists after SI-16/SI-17, so the
first thing established is *which bytes ran*. Three copies of skt are reachable
on this machine and they are not the same code:

| copy | path | is it the code under review? |
|---|---|---|
| operator root home | `/Users/hayde/.skill-manager/plugins/tla-spec-dev/skills/skt` | no — the operator's installed bundle |
| this worktree's home | `<worktree>/.skill-manager/plugins/tla-spec-dev/skills/skt` | **no** — a clone pinned at `1efa0b4b`; `status.py` differs from the worktree's |
| a home built by hand | `<scratch>/gamut-home/plugins/tla-spec-dev/skills/skt` | **yes** — `rsync`ed from this worktree, then `install-skt.sh` run against it |

So the gamut below runs against the third, built the only way a real install is
shaped — the unit copied **into** a home, then its own install script run with
`$SKILL_DIR` pointing into that home:

```
$ rsync -a --exclude .git --exclude test_graph … <worktree>/ <scratch>/gamut-home/plugins/tla-spec-dev/
$ SKILL_MANAGER_BIN_DIR=…/bin/cli SKILL_MANAGER_CACHE_DIR=…/cache \
  SKILL_DIR=…/plugins/tla-spec-dev SKILL_MANAGER_HOME=…/gamut-home \
  bash <worktree>/skill-scripts/install-skt.sh
installed skt for skt at …/gamut-home/bin/cli/skt
  (python: /opt/homebrew/bin/python3.14,
   entrypoint: plugins/tla-spec-dev/skills/skt/src/skt/cli.py)
$ diff …/gamut-home/plugins/…/skt/src/skt/status.py <worktree>/skills/skt/src/skt/status.py
   → identical
```

The wrapper carries **no absolute home path** — only `rel=` and the
interpreter — which is the property SI-16 bought, and it is the reason
`<worktree>/.skill-manager/bin/cli/skt` silently answers with the *worktree
home's own* older copy rather than the source beside it. **That is not a
defect, it is the wrapper contract working; it is a trap for this ticket**,
because "I ran the contained skt" and "I ran the skt under review" are
different sentences and only the second one is evidence.

**`skt` is contained and the front door resolves.** No standalone `skt` unit is
installed in any home reached here; every invocation below resolved
`plugins/tla-spec-dev/skills/skt/src/skt/cli.py`. `GOAL-one-plugin`'s guard
holds on this evidence.

---

## 1. What was driven by hand

| # | verb | transcript | outcome |
|---|---|---|---|
| A | provisioning: `skt ticket new 369-eval-ladder-skt --base … --path …` | §2 | exit 0, worktree **present at the declared path**, branch **as declared** |
| B | `skt --version` | `transcripts/step-02-verb-gamut.txt` | `skt 0.8.2` |
| C | `skt status` (fixture home) and `--json` | same | exit 0, schema 3, tier `project` |
| D | `skt status` (this worktree's home) | same | exit 0, tier `worktree`, 19 units / 11 change-managed |
| E | `skt check --cached --json`, twice | same | exit 0, `cache_state: missing`, `from_cache: true` both times |
| F | `skt check` (live, network) | §6 | exit 0, `all current (11 change-managed unit(s))`, artifacts **not checked (timeout)** |
| G | `skt sync` / `skt sync no-such-unit` | `step-02` | exit 1 both, two different and correct messages |
| H | `skt build --dry-run`, `--all --dry-run` | `step-02` | **exit 1** — no `skill-manager` CLI pin in that home; remedy names a command that runs |
| I | `skt publish --check` | `step-02` | exit 0, `no edited units in this home` |
| J | `skt ticket list` | `step-02` | exit 0 — and see §5 |
| K | `skt ticket sweep` (dry run) | `step-02` | exit 0, **`23 would be removed`** — see §5 |
| L | `skt ticket new/info/close` round trip | §3, §4 | exit 0 / exit 0 / exit 0, both classifications |
| M | `skill-manager home close-out` | `transcripts/step-07-home-close-out.txt` | exit 2 (not-a-home), exit 1 (20 units would be lost) — see §7 |
| N | `skt publish <unit>`, `skill-manager home sync` | — | **UNEXERCISED, deliberately** — see §8 |
| O | `sktSurface` graph | `transcripts/step-01`, verdict in `step-06` | `summary.json` `"status":"errored"`, 4/5 nodes passed, `skt.ticket-roundtrip` **13 of 40 assertions red** |

---

## 2. The provisioning was the first observation

Two skt behaviours the issue warns about did **not** recur here, and saying so
is as much a measurement as saying they did:

- `SI-11-DF-04` (worktree rolled back, exit still 0): the path was tested, not
  the exit code. `/Users/hayde/IdeaProjects/wt-369-eval-ladder-skt` exists, is
  a linked worktree, and carries its own `.skill-manager`.
- `SI-09-DF-02` (branch derived from the ticket id, declared name ignored): the
  branch came out `feature/369-eval-ladder-skt`, which **is** the declared one.
  The behaviour is unchanged — the derivation still wins — but the assignment
  spells the ticket slug and the branch suffix identically, so the derivation
  and the declaration agree by construction. **No rename was needed. This is
  not evidence that the defect is fixed**, and an agent whose slug and branch
  differ will still be bitten.

---

## 3. `skt ticket new|info|close`, watched end to end

Driven against the by-hand home, in a fixture repo, with
`INTEGRATION_SKIP_HOME=1` (new-change.sh's own documented switch, so the home
provisioning — a skill-manager claim, not an skt one — is out of frame):

```
$ skt ticket new TG-1
created ticket worktree for TG-1:
worktree   …/outer/inner/subject-repo-TG-1
branch     feature/TG-1 (standalone repo subject-repo)
launch     none — this worktree has no home; an agent here uses the operator's GLOBAL home
close      skt ticket close — or: …/skills/skt/scripts/wt close TG-1

A skill edit inside that worktree's home is in no git diff; run `skt publish`
there before closing, or the close gate will refuse.

$ skt ticket close TG-1
closed …/outer/inner/subject-repo-TG-1
branch feature/TG-1 kept — delete once the change has landed
```

The round trip is real on both arms of §4: directory created, directory
removed, branch kept. `close` resolves the worktree **by search**, which is why
it found the one `new` had put somewhere the caller did not expect.

---

## 4. `EA-DF-02`: the finding is in the fixture, not in `skt`

The epic agent handed me `skt ticket new` exiting 0 and printing
`worktree = /Users/hayde/IdeaProjects/subject-repo-TG-1` — outside the
fixture tree — with `worktree exists: False`, and asked for a root cause rather
than a guess.

**Falsified both ways, one fixture, one variable.** Two arms, identical
subject repo, identical env, identical verb; the only difference is whether an
ancestor directory carries `integration.toml`
(`transcripts/step-05-ea-df-02-two-arms.txt`):

| arm | `integration.toml` above? | branch key printed | worktree landed |
|---|---|---|---|
| A | no | `feature/TG-1 (standalone repo subject-repo)` | **beside the repo**, inside the fixture tree |
| B | yes, two levels up | `feature/TG-1 (constituent repo subject-repo)` | **beside the planted integration root**, outside the fixture tree |

Both arms exit 0 and both round-trip cleanly. The placement rule is
`worktree_parent_dir()` at
`skills/git-issue-workflow/scripts/lib.sh:341 (worktree_parent_dir)`:
the worktree goes beside the **outermost** enclosing integration repo, and the
comment above it says why in full — a worktree's `.git` is a FILE, so a parent
`git add -A` stages the whole directory as a gitlink, which `INTEGRATION.md`
rule 1 forbids, and no `.gitignore` glob can separate `constituents/foo-TICKET`
from a real constituent named `foo`.

**Verdict: `EA-DF-02` is not a defect in `skt ticket new`.** It is a defect in
`test_graph/sources/skt_ticket_roundtrip.py`. The node builds its fixture repo
under `ctx.report_dir`, which is inside **this** repository, and this
repository carries `integration.toml` at its root. So the fixture repo is a
constituent, `skt` places the worktree beside `/Users/hayde/IdeaProjects/wt-…`,
and the node's hard-coded `expected_worktree = work / f"subject-repo-{ticket}"`
can never be right here. Four of the thirteen reds are that one mistake:
`new prints the worktree and branch keys`, `the worktree directory exists`,
`it is a LINKED worktree, not a copy`, `git knows about it`.

**And it is worse than a wrong assertion.** The node declares
`side_effects("fs:tmp", "net:external")` and then creates a real linked git
worktree in `/Users/hayde/IdeaProjects/` — the operator's checkout directory,
beside twenty-three live ticket worktrees. It is removed again only because
`close` searches for it. A run interrupted between `new` and `close` leaves it
there. Filed as `SI-20-DF-01`.

### 4a. The nine other reds: the refusals are obsolete, not reworded

The remaining nine reds all say `refusal [<case>]: names '<phrase>'`. The
epic agent left it undecided whether that is the same cause or simply reworded
messages. It is neither. Driven by hand, all four fixtures
(`transcripts/step-03-refusals-byhand.txt`):

```
CASE: no home at all                    rc=1
  error: not inside a git repository: /var/folders/…/skt-ticket-nohome-…
CASE: installed but no importable surface            rc=3
  error: no Skill Manager home could be created for this worktree
         (usually: …/subject-repo has no project home yet)
  fix:   …/skills/git-issue-workflow/scripts/bootstrap-home.sh --root …/subject-repo
CASE: declared in skill-project.toml but not installed rc=3   ← byte-identical to the above
CASE: neither installed nor declared                   rc=3   ← byte-identical to the above
```

Three findings, each falsified rather than inferred:

1. **The four-way discrimination is unreachable on this route.** The messages
   the node asserts come from `_giw_remedy` at
   `skills/skt/src/skt/ticket.py:66 (_giw_remedy)`, reached from
   `skills/skt/src/skt/ticket.py:122 (_import_wrapper)` only when
   `import skt.wt` **fails**. SI-17 moved `wt` into skt, so that import now
   always succeeds — the module's own docstring says so — and the only other
   caller is `epic_new`, i.e. the `--path` route the node does not take. The
   merged fix the node's docstring celebrates ("tell not-installed from
   not-synced, and name a remedy that runs", #25) is dead code on
   `skt ticket new`. `SI-20-DF-02`.

2. **The three home-bearing cases do not differ at all any more**, and the
   reason is `GOAL-one-plugin` itself: `wt` resolves git-issue-workflow's
   lifecycle scripts from **the plugin it ships in**, not from
   `$SKILL_MANAGER_HOME`. Rerun with `INTEGRATION_SKIP_HOME=1`
   (`transcripts/step-04-refusals-skip-home.txt`), all three **succeed, exit
   0, and create a worktree** — in a home with no git-issue-workflow installed,
   declared, or present in any form. The fault those four remedies describe
   *cannot occur* once skt and git-issue-workflow are contained in one plugin.
   The node's four "cases" are one case, four times, and their
   `exits non-zero` assertions pass on a coincidence: a missing **project
   home**, which is nothing to do with git-issue-workflow.

3. **The `no home at all` fixture never reaches the home check.** It runs in a
   bare `tempfile.mkdtemp()`, which is not a git repository, so skt refuses one
   step earlier with `not inside a git repository`. Point it at a real git repo
   and the same case **succeeds** (`step-04`, arm 2). The fixture has been
   testing a different refusal than its name claims since it was written.
   `SI-20-DF-03`.

---

## 5. `skt ticket sweep`, in a repository with fourteen epics

This is the largest thing found by hand and it is not in any graph.

```
$ skt status
checkout   integration repo, branch feature/369-eval-ladder-skt (ticket 369-eval-ladder-skt)
           (epic architectural-coherence available)
...
$ skt ticket sweep            # dry run, no -y
skt ticket sweep (dry run) — /Users/hayde/IdeaProjects/tla-spec-dev
epic       none discoverable
target     none — containment NOT checked (pass --epic <slug> or --target <ref>)
...
  would remove 368-eval-ladder- /Users/hayde/IdeaProjects/wt-368-eval-ladder-graph-scaffold
  would remove -                /Users/hayde/IdeaProjects/wt-epic-self-improvement-substrate
23 would be removed, 0 skipped for safety, 2 excluded
```

Two commands, one checkout, two different answers to "which epic is this":

- `skt status` says **`epic architectural-coherence available`** — an epic
  closed on 2026-08-03 — because
  `skills/skt/src/skt/context.py:192 (for ref in refs.splitlines())` takes the
  **first** `epic/*` ref and `break`s. There are fourteen.
- `skt ticket sweep` says **`epic none discoverable`** because
  `skills/skt/src/skt/sweep.py:419 (return slugs[0] if len(slugs) == 1)`
  requires **exactly one**. Its docstring claims "Same derivation as
  `context.gather`". It is not the same derivation.

The consequence of the second is the dangerous one: with no epic resolved,
containment is never checked, so **every** worktree comes back `clean — no
blocker`, including the epic's own worktree and every in-flight ticket
worktree of this wave. The dry run's default answer in a multi-epic repository
is *remove everything*, not *refuse until you name an epic*. The `-y` path does
re-run the `home close-out` gate per worktree, which is the only thing standing
between that plan and twenty-three deletions. `SI-20-DF-04`.

`skt status` reporting a long-closed epic as "available" is the same root
cause on the read-only side. `SI-20-DF-05`.

Also observed, and smaller: `skt status` says
`spec workflow 'self-improvement-substrate' active; no open tickets — this
branch's ticket is NOT in the plan`. It is in the plan; it is spelled `SI-20`
there and `369-eval-ladder-skt` on the branch, and
`skills/skt/src/skt/context.py:199 (ticket in all_tickets)` compares the two
literally. Every epic ticket worktree in this epic will be told it is not in
the plan. `SI-20-DF-06`.

---

## 6. `skt check`, and what it quietly does not check

```
$ skt check                       # live, network, this worktree's home
skt check: all current (11 change-managed unit(s), tier worktree)
  artifacts not checked (timeout): skill-manager artifacts stale --json did not finish inside 6.0s
  build: skt 0.8.2; skill-manager 0.28.1 @ artifact 641625cd3baf built 2026-09-17T17:34:42Z
```

Exit 0, headline `all current`, and one of the two things `check` claims to
report — stale artifacts — **was not checked at all**. It says so, on its own
second line, which is the honest half. The dishonest half is the exit code and
the headline: a caller that reads either gets "everything is fine" from a run
that measured one of two surfaces. This is the epic's recurring shape again —
*could not do the task* and *did the task* rendering the same.
`SI-20-DF-07`.

`--cached` is the throttled path and it is the one the session hook uses. Both
invocations returned `cache_state: "missing"` with `from_cache: true` and
touched no network; the second did not become `"fresh"`, because nothing had
written a cache entry (the fixture home has no change-managed units, so there
was nothing to record). Observed, not a defect — but it means **`--cached` on
an empty home is indistinguishable from `--cached` on a healthy one**, and
`"notifications": []` is the answer in both.

---

## 7. `skill-manager home close-out` — watch what it prints

The discovery note was right that this verb punishes a filter. Exercised three
ways (`transcripts/step-07-home-close-out.txt`):

- destination not a home → **exit 2**, and the message names the exact path to
  pass instead, and says `Nothing was read and nothing was written.`
- this worktree's home → an empty destination → **exit 1**, `20 unit(s) … would
  be lost if it were removed now`, 40 rows, the rest in a log file it names.
- `--json` → **3,748,517 bytes**, of which 3,774,707 belong to `units`.

And one schema fact worth having before anyone writes a consumer: the real
verdict's keys are
`['blockers','exitCode','home','into','safe','selfObtainable','units']` —
**there is no `clean` key**. The *error* verdict does carry `"clean":false`. So
a consumer keying on `clean` reads `None` from the verdict that matters and
`false` from the one that does not. Read `safe` and `exitCode`.
`SI-20-DF-08`.

The contract-mandated invocation —
`--home <worktree>/.skill-manager --into <main working tree>/.skill-manager` —
is recorded in the PR body; see §8 for what happened when it was attempted.

---

## 8. Unexercised, with the reason

- **`skt publish <unit>`** — writes outside the worktree, into the parent home
  and then to a unit's own git repo. The issue forbids it from this ticket.
  Exercised only as `publish --check`, which is read-only and exited 0 with
  `no edited units in this home`.
- **`skill-manager home sync`** — same, and the assignment reserves every home
  reconciliation for the epic agent at wave close.
- **`skt ticket sweep -y`** — the dry run says it would remove twenty-three
  worktrees including this epic's own. Running it would end the wave.
- **`skt build` (for real)** — the fixture home has no `skill-manager` CLI pin,
  and creating one means `skill-manager home shims`, which writes a home.
  `--dry-run` reached the same refusal, so the refusal *is* the observation.
- **`skill-manager home close-out --into <the operator's project home>`** — the
  exact command the assignment requires before stopping. Attempting it was
  **refused by this session's sandbox** as a shared-resource write, although
  the verb's own `--help` says `Writes nothing; safe to run repeatedly`. The
  same verb was run against the same source home into a scratch destination
  instead, and its verdict is in §7. Reported rather than worked around.

---

## What this record is allowed to be used for

- The eval cases in the next commit encode §0 (which copy ran, and how to tell)
  and §4/§4a (where a ticket worktree lands, and why a refusal fixture that
  never reaches its refusal is not coverage). Nothing else here is encoded.
- §5, §6 and §7 were observed and are **findings**, not cases. Turning each
  into a case on the day it was found is the volume this ticket exists to
  avoid.
- No `claude plugin eval` run is in this record. Nothing here is evidence about
  the eval suite's scores.
- `sktHooks` was not run here; the epic agent reported it passing and that is
  its evidence, not mine.
