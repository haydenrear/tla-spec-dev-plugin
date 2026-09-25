# SI-22 — local signal, reported against `expected_effect`

Two goals, both `direct`, both decided by **SI-23** on the integrated epic. A
local signal is a signal, not a gate, and neither line below is a verdict.

---

## `GOAL-evals-earned`

* **`expected_effect`**: *fourth stage, manual record first*
* **`local_signal`**: *the fresh-home chain is walked by hand and recorded*

**MET, and checkable without reading a word of my prose.**

| | |
|---|---|
| record commit | `679f76f1893f80ed97b7f20bc0d859510850e642` |
| first case commit | `3dc106fb61e341192ab6dbbf6871ca559d0f2bdf` |
| `git merge-base --is-ancestor <record> <case>` | **rc=0** |
| `case.yaml` files in the record commit | **0** (with a non-vacuity control: 20 files present) |

The ladder is now four for four:

```
SI-19   8e362bbb → eefe3aa8
SI-20   70549f90 → 7daa8e18
SI-21   bec1934b → c96de147
SI-22   679f76f1 → 3dc106fb     ← this one
```

The record is `manual-verification.md`: 28 transcripts, 20 by-hand interactions
in a table, each naming its transcript and its exit code.

**The honest qualifier.** Section 14 of the record was written *after* the cases
ran, because two of my three graders were wrong and the runs proved it. That
does not weaken the claim — the record still precedes the cases, and §14 is
labelled as later evidence — but a reader should know the file was appended to.
Its most important content is a case where the **agent was right and my grader
was wrong**, and where I went and measured the behaviour by hand (`step-23`)
rather than widening the rule to make the red go away. That is the goal working
as intended, one rung after it was written down.

---

## `GOAL-one-plugin`

* **`expected_effect`**: *the brew → CLI → plugin chain is demonstrated end to end*
* **`local_signal`**: *a fresh home reaches a working front door*

**MET with two stated qualifiers.** Neither is hidden and neither is mine to
decide.

**What was reached.** From one empty directory, with `HOME` and
`SKILL_MANAGER_HOME` both fresh and outside every checkout: brew's
`skill-manager 0.28.1` started, installed the plugin from its git coordinate,
and produced `bin/cli/skt`. `skt status` → rc=0. `skt ticket new` → a worktree
with its own Skill Manager home. **The front door resolves from a fresh home.**

**Against SI-08's baseline** (2 installed units plus a brew formula; root home
NOT MET, project home MET):

| | SI-08 | now |
|---|---|---|
| standalone `skt` unit in the **root** home | present → **NOT MET** | **none — MET** |
| standalone `skt` unit in the project home | none → MET | **none — MET** |
| standalone `skt` unit in a worktree home | — | **none — MET** |
| the CLI comes from brew | formula | **MET at every tier** — the project-tier shim is a *pin* that `exec`s `/opt/homebrew/bin/skill-manager` (line 209) |
| `skt` inside the plugin | — | **MET** — a contained skill *and* a plugin-level CLI dep |
| `wt` inside `skt` | — | **MET** — `plugins/tla-spec-dev/skills/skt/scripts/wt` |

**Qualifier 1 — "one installed plugin", and three installed units.** The
operator names **one** coordinate. `deploy-helm` and `tracing-observability`
resolve and install as transitive references, so `skill-manager list` in the
fresh home shows **3**. Whether the metric means *one named* or *three present*
is SI-23's call; both numbers are reported rather than the flattering one.

**Qualifier 2 — a genuinely fresh machine cannot complete the chain.** The
plugin repository is **private** (`SI-22-DF-02`). The install fails at the clone
with rc=9 under a fresh HOME and succeeds under the operator's. The minimum seed
is one symlink, `Library/Keychains`, because `credential.helper=osxkeychain`
comes from the *system* gitconfig but the keychain it reads is HOME-relative —
the same constraint `evals/README.md` documents for the Docker sandbox, reached
by a different route. **So what is demonstrated is "fresh home, operator's
credential", not "a machine that has nothing".**

**And one thing the target sentence omits.** `skt ticket new` is the front door,
and it is not the first command a fresh machine can run in a repository: it
refuses with rc=3 until that repository has a project home, naming
`bootstrap-home.sh --root <repo>` on its own `fix:` line. The refusal is clean —
path-tested, nothing left behind — and the remedy works verbatim. One hop, well
signposted, and absent from the goal statement.

**Finally, the thing SI-23 most needs to weigh.** A *successful* install of this
substrate **exits 11**, and so does `sync` (`SI-22-DF-01`). Two deliberately
broken eval fixtures are validated as shippable skills. Every hop of the chain
works; the one command the goal is about reports failure to any script that
reads `$?`.

---

## Per agent type — the evidence, not the verdict

The plan's acceptance is "named and covered or explicitly deferred". **Six
workflow roles and three harnesses named; each covered or deferred by name**
(record §9). Nothing silently skipped.

The measurement is a **negative result**, stated as one: **session-start
disclosure does not branch on agent type.** Both shipped hooks carry zero
role/agent-type conditionals (`grep` rc=1, with a non-vacuity control returning
203 matches on the same path); `role:` takes exactly `implementation |
evaluation` and is read by the plan validator, never by a hook; and the
disclosure that does vary, varies by **home tier and checkout state**. An epic
agent and a ticket agent standing in the same directory receive byte-identical
disclosure.

One number for the progressive-disclosure question: **31,063 entries** land in
the agent's plugin cache to deliver 11 skills, identically for every agent type.

Whether that is right is SI-23's to decide. That it is the current design is now
measured rather than assumed.
