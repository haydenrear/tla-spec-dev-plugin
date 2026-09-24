----------------------------- MODULE TlaSpecDevCli -----------------------------
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS
  SpecRoots,
  Tickets,
  NoRoot,
  NoReason

\* MF-022: bootstrap setup phase as a single ordinal rather than five parallel
\* booleans. 0 = nothing built, 1 = cli built, 2 = cli installed,
\* 3 = project scaffolded, 4 = budgets recorded, 5 = workflow scaffolded. The
\* old booleans (cli_built, cli_installed, project_scaffolded,
\* budgets_recorded, workflow_scaffolded) were pinned into a strict total order
\* by their own action guards, so only 6 of their 32 combinations were ever
\* reachable; the ordinal represents exactly the reachable set. Read cli_built
\* as >= 1, cli_installed as >= 2, project_scaffolded as >= 3,
\* budgets_recorded as >= 4, and workflow_scaffolded as >= 5.

\* MF-025: the whole per-ticket lifecycle as a single ordinal. This subsumes
\* MF-020's ticket_phase together with the two membership sets it lived
\* alongside. active_tickets (SUBSET Tickets), closed_tickets (SUBSET Tickets)
\* and ticket_phase ([Tickets -> 0..3]) were not three independent facts: they
\* were one lifecycle recorded three ways.
\*
\*   0  not yet opened
\*   1  active, phase 0 (opened)
\*   2  active, phase 1 (desired model updated)
\*   3  active, phase 2 (implementation landed)
\*   4  active, phase 3 (spec-unit tests passed)
\*   5  closed
\*
\* Why the collapse is exact rather than a packing trick:
\*   - OpenTicket guarded on the ticket being in NEITHER set, so a ticket is
\*     never reopened and the lifecycle is monotonic.
\*   - CloseTicket left ticket_phase UNCHANGED, so a closed ticket retains
\*     phase 3. There is no closed-with-some-other-phase state to represent.
\*   - NoOpenClosedOverlap already forbade being both active and closed.
\* Of the 8 x 8 x 64 = 4,096 declared combinations, exactly six per-ticket
\* combinations were reachable and they were totally ordered. TLC confirmed
\* both directions before the collapse: no seventh combination occurs in any
\* reachable state, and each of the six is individually reachable. The ordinal
\* therefore represents the reachable set exactly -- it neither drops a
\* reachable state nor admits an unreachable one.
\*
\* Read active_tickets as ActiveTickets, closed_tickets as ClosedTickets, and
\* the old ticket_phase[t] as ticket_state[t] - 1 while the ticket is active.

\* MF-020: ticket lifecycle phase as a single ordinal rather than three
\* parallel booleans, now absorbed into ticket_state by MF-025. The old
\* booleans were pinned to a strict total order by CurrentRequiresDesired /
\* SpecUnitTestsRequireCurrent, so only 4 of their 8 combinations were ever
\* reachable. Read desired_ready as >= TicketDesiredReady, current_ready as
\* >= TicketCurrentReady, and spec_unit_tests_passed as
\* >= TicketSpecUnitTestsPassed.
\* MF-013: effect_conformance is the effect conformance verdict -- whether the
\* adapters' observed side effects match the ports the model declares. Like
\* complexity_gate and corpus_gate this is a fact about the whole program
\* rather than about one ticket, so it is a single global variable.
\*
\* Five values, and the four non-"unknown" ones are NOT interchangeable:
\*   "clean"        -- every observed effect landed on a declared port, and
\*                     every declared port was exercised by some case.
\*   "gaps"         -- an effect crossed a boundary with no declared port.
\*                     The model is blind to real behavior.
\*   "dead_surface" -- a declared port no case ever exercised.
\*   "unobservable" -- MF-027: the sandbox could not see the target at all.
\*                     The oracle observes the in-process CPython runtime only,
\*                     so a JVM adapter, a JBang/uv Test Graph node, or an
\*                     adapter that delegates to a child process produces NO
\*                     observations. Before MF-027 that empty observation set
\*                     was indistinguishable from a clean one and the command
\*                     returned success. It is now its own verdict, and it
\*                     DOMINATES the others: a diff computed over a target that
\*                     was never seen carries no information, so reporting it
\*                     as "clean" -- or even as "gaps" -- would assert
\*                     something the run has no evidence for.
\*
\* "gaps", "dead_surface" and "unobservable" are kept apart rather than
\* collapsed into one "fail" because they are not the same finding and do not
\* have the same remedy: a gap is fixed by declaring the port or removing the
\* emission, dead surface by removing the port or adding a case, and an
\* unobservable target by running it in-process or checking that boundary with
\* a different mechanism. The distinction is externally visible in
\* `result.next`, which is why it is represented here instead of being
\* flattened.
\*
\* MF-027 is modeled rather than left to the implementation because the
\* verdict is externally-visible CLI behavior: it selects a distinct exit path
\* and a distinct `result.next`. Leaving it out would make the model blind to
\* a real outcome of a modeled command, which is the same defect the verdict
\* itself exists to report.
\*
\* Note what is deliberately ABSENT, exactly as for corpus_gate: there is no
\* override input, no justification input, and no transition from "gaps" to
\* "clean" that is not a re-measurement. Out-of-contract justifications were
\* WITHDRAWN on 2026-07-18 as degeneracy. Nothing suppresses a gap report --
\* not a manifest entry, not an annotation, not a recorded rationale. The only
\* ways to reach "clean" are to DECLARE the port or to CHANGE THE PROGRAM so it
\* no longer emits the effect. There is no third option.
\*
\* CA-04 REMOVED kill_test, the oracle-4 mutation kill-test verdict, together
\* with the RunKillTest action, its adapter, and the kill_mutants.toml
\* catalogues. It was the last HARD STATIC GATE in this repository:
\* kill_rate_floor was a value floor with no waiver, and the model specified it
\* as a command. The finding is RM-03-DF-05, which identified exactly this cut
\* and declined it because it was a model delta in a ticket declaring none --
\* "THE ONE HARD STATIC GATE LEFT IN THIS REPOSITORY IS A SPECIFIED ACTION OF
\* THE MODEL" -- and whose suggested_fix asked for "its own ticket against the
\* CLI model". The standing evidence is the epic record's "static gates catch
\* nothing -- seven epics, zero bugs caught by a static check".
\*
\* WHAT THE MODEL CAN NO LONGER EXPRESS, stated so it is not discovered later:
\* there is now no modeled notion of the representation being validated against
\* the PROGRAM. The three surviving gate variables record self-consistency
\* (TLC), tractability (corpus_gate) and boundary declaration
\* (effect_conformance); none of them can distinguish a faithful model from a
\* vacuous one, and kill_test was the only one that could. The cost caps
\* therefore no longer have a matching value floor in the model, so a model
\* shrunk toward nothing now satisfies every budget the model still states.
\* This is the ticket's PRICE, recorded rather than avoided.
\*
\* NOTE ON PLACEMENT: this comment sits ABOVE the VARIABLES block on purpose.
\* Comments interleaved between names inside the block are not parsed by
\* skills/spec-double-2/scripts/analyze_complexity.py, which silently dropped this variable from the
\* dimension table and the bound when it was written that way -- the declared
\* bound stayed at the pre-MF-013 34,992 while TLC measured 38,241 distinct
\* states, a bound below the measured reality. Keep declarations contiguous.
VARIABLES
  setup_phase,
  spec_root,
  ticket_state,
  lastCommand,
  result,
  complexity_gate,
  corpus_gate,
  effect_conformance,
  skt_answer

vars ==
  << setup_phase,
     spec_root,
     ticket_state,
     lastCommand,
     result,
     complexity_gate,
     corpus_gate,
     effect_conformance,
     skt_answer >>

\* ---------------------------------------------------------------- skt surface
\*
\* SI-20 ADDED THIS, AND BUG ATTRIBUTION IS WHY IT EXISTS. Four findings from
\* the by-hand gamut attributed to `UNMODELED/` bins -- checkout-context,
\* notification-check, worktree-sweep -- which is the record saying "the model
\* has nothing to attach this to". Each invariant below IS one repaired defect,
\* so a regression has somewhere to land that is not a bin.
\*
\* MODELLED AS ONE VARIABLE, DELIBERATELY. MF-023 measured modularity at
\* Q=0.012, found no clean cut, and kept a single module; a second module for
\* skt would decide that question by accident. What is modelled is skt's ANSWERS
\* -- what it claims after being asked -- because every one of the four defects
\* was a claim made over something unmeasured, never a wrong computation.
\*
\* NOT MODELLED: refusal wording, test graphs, fixtures. semantic_model_rule.
SktSilent ==
  [ epic_named        |-> FALSE,
    epic_unique       |-> FALSE,
    membership_claim  |-> FALSE,
    membership_joined |-> FALSE,
    verdict_current   |-> FALSE,
    surfaces_measured |-> FALSE,
    sweep_planned     |-> FALSE,
    containment_known |-> FALSE ]

SktAnswers ==
  [ epic_named        : BOOLEAN,
    epic_unique       : BOOLEAN,
    membership_claim  : BOOLEAN,
    membership_joined : BOOLEAN,
    verdict_current   : BOOLEAN,
    surfaces_measured : BOOLEAN,
    sweep_planned     : BOOLEAN,
    containment_known : BOOLEAN ]

\* MF-025: the lifecycle stages by name. Guards and invariants below read as a
\* lifecycle rather than as arithmetic on an integer.
TicketUnopened            == 0
TicketOpened              == 1
TicketDesiredReady        == 2
TicketCurrentReady        == 3
TicketSpecUnitTestsPassed == 4
TicketClosed              == 5
\* RC-01 (MF-026, owner decision 2026-08-01): a close taken under one of the
\* six GUARD-WEAKENING FLAGS -- --accept-new, --allow-open,
\* --no-promote-current, --validate-only, --force, --dry-run -- is a DIFFERENT
\* STATE from a close taken under the guard, and this is the stage that records
\* it. Before this ticket the flags were inventoried as presentation under the
\* per-flag granularity limitation, and the cost of that was specific rather
\* than theoretical: CloseTicket guards on TicketSpecUnitTestsPassed and TLC
\* proves ClosedTicketsPassedSpecUnitTests over 563,963 states (1,292,951
\* before the 2026-08-04 scanner removal), while
\* `--accept-new` (tla_spec_dev.py --accept-new) and `--allow-open` exist
\* SPECIFICALLY to bypass that precondition -- so the model proved an invariant
\* the shipped program has two documented flags to violate, no modeled state
\* recorded their use, and NO ORACLE IN THIS TOOLCHAIN COULD SEE THE
\* DIFFERENCE (the kill test seeds faults per declared port and per invariant,
\* i.e. only inside modeled boundaries). Six of the 78 options; the granularity
\* limitation covering the other 72 is untouched.
TicketClosedWeakened      == 6

\* MF-025: every site that meant "the set of active tickets" still says so.
ActiveTickets == {t \in Tickets : ticket_state[t] \in TicketOpened..TicketSpecUnitTestsPassed}
\* RC-01: BOTH closes are closes -- the ticket is out of the active set either
\* way, which is what NoOpenClosedOverlap is about. What differs is whether the
\* close passed through the guard, and that is the distinction
\* GuardedClosedTickets draws below.
ClosedTickets == {t \in Tickets : ticket_state[t] \in {TicketClosed, TicketClosedWeakened}}
\* RC-01: the closes that went through the precondition, and the ONLY ones any
\* invariant here may claim passed spec-unit tests.
GuardedClosedTickets  == {t \in Tickets : ticket_state[t] = TicketClosed}
WeakenedClosedTickets == {t \in Tickets : ticket_state[t] = TicketClosedWeakened}

\* RC-01: READ THE LIFECYCLE, NOT THE INTEGER. Every property below that used
\* to say `ticket_state[t] >= <stage>` meant "this ticket has been through
\* <stage> of the guarded lifecycle". TicketClosedWeakened is an ordinal ABOVE
\* every guarded stage and certifies LESS than any of them, so `>=` silently
\* answers TRUE for it -- and five invariants would have gone on holding, by
\* accident of the encoding, about a ticket that passed nothing. That accident
\* is exactly the class of defect the coverage audit opened this ticket for, so
\* the reader is named once and used everywhere instead of being patched at each
\* site.
TicketReached(t, stage) == ticket_state[t] \in stage..TicketClosed

CommandResult(ok, reason, nextStep) ==
  [accepted |-> ok, reason |-> reason, next |-> nextStep]

Init ==
  /\ setup_phase = 0
  /\ spec_root = NoRoot
  /\ ticket_state = [t \in Tickets |-> TicketUnopened]
  /\ lastCommand = "Init"
  /\ result = CommandResult(TRUE, NoReason, "BuildSkillCli")
  /\ complexity_gate = "unknown"
  /\ corpus_gate = "unknown"
  /\ effect_conformance = "unknown"
  /\ skt_answer = SktSilent

\* CD-11 (audit run 4, ESC-R4-3): `@port TlaSpecDevCliPort.<name>` names a
\* DECLARED EFFECT PORT -- an entry of
\* effects.components.TlaSpecDevCliPort.ports in spec_manifest.yaml -- and
\* each action's @port lines mirror its row in effects.actions. Before CD-11
\* the tag carried a per-command vocabulary (build_skill_cli, ...) whose
\* intersection with the declared port names was empty; the annotation layer
\* and the effects layer now use one vocabulary. Actions whose effects row is
\* deliberately empty (RecordBudgets, AnalyzeCorpus) carry no @port line and
\* say so. Comments only: nothing parses @port, and the model's states,
\* actions, guards, and invariants are unchanged.
\* The skill ships one local command built from Python entrypoint code.
\* @command BuildSkillCli
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.cli_artifact
BuildSkillCli ==
  /\ setup_phase = 0
  /\ setup_phase' = 1
  /\ lastCommand' = "BuildSkillCli"
  /\ result' = CommandResult(TRUE, NoReason, "InstallLocalCli")
  /\ UNCHANGED << spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* The local environment can invoke `tla-spec-dev ...` after install.
\* RC-02 (MF-026 round-3 N-1): three @port lines ADDED so this action's
\* annotation mirrors its effects.actions row again. RC-01 declared
\* cli_download, cli_artifact_delete and cli_selftest_process in the manifest's
\* ports block and attached them to no action, which broke the mirror rule
\* stated above in the OPPOSITE direction from round-2 G-1: G-1 was an action
\* with @port lines and no row, this was ports that no action's @port lines
\* mirrored. Comments only; the states, guards and invariants are unchanged.
\* @command InstallLocalCli
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.cli_artifact
\* @port TlaSpecDevCliPort.cli_download
\* @port TlaSpecDevCliPort.cli_artifact_delete
\* @port TlaSpecDevCliPort.cli_selftest_process
InstallLocalCli ==
  /\ setup_phase = 1
  /\ setup_phase' = 2
  /\ lastCommand' = "InstallLocalCli"
  /\ result' = CommandResult(TRUE, NoReason, "tla-spec-dev scaffold project")
  /\ UNCHANGED << spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> scaffold project`
\* Creates the accepted `program_model` baseline only.
\* @command ScaffoldProject
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
ScaffoldProject(root) ==
  /\ setup_phase = 2
  /\ root \in SpecRoots
  /\ spec_root' = root
  /\ setup_phase' = 3
  /\ lastCommand' = "tla-spec-dev scaffold project"
  /\ result' = CommandResult(TRUE, NoReason, "RecordBudgets")
  /\ UNCHANGED << ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: scaffold emits a `budgets:` block into spec_manifest.yaml and
\* instructs the agent to propose the documented defaults to the user, ask
\* which to adjust for this program, and record a one-line rationale per
\* changed value. Budgets are established before any generation action, so
\* every downstream gate reads them from the manifest.
\* @command RecordBudgets
\* @result CliWorkflowResult
\* No @port: the manifest row `RecordBudgets: []` is deliberately empty --
\* the CLI performs no distinct budgets effect (CD-10 DF-2 ruling).
RecordBudgets(root) ==
  /\ setup_phase = 3
  /\ root = spec_root
  /\ setup_phase' = 4
  /\ lastCommand' = "RecordBudgets"
  /\ result' = CommandResult(TRUE, NoReason, "tla-spec-dev scaffold workflow")
  /\ UNCHANGED << spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> scaffold workflow`
\* Creates project `current/`, `desired_program_model/`, and ticket plan.
\* @command ScaffoldWorkflow
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
ScaffoldWorkflow(root) ==
  /\ setup_phase = 4
  /\ root = spec_root
  /\ setup_phase' = 5
  /\ lastCommand' = "tla-spec-dev scaffold workflow"
  /\ result' = CommandResult(TRUE, NoReason, "tla-spec-dev open ticket <ticket>")
  /\ UNCHANGED << spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> open ticket <ticket-name>`
\* Creates ticket-local desired/results/Test Graph workspace (current/ only with --with-current, since 2026-09-14).
\* @command OpenTicket
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
OpenTicket(root, ticket) ==
  /\ setup_phase >= 5
  /\ root = spec_root
  /\ ticket \in Tickets
  \* MF-025: `\notin active_tickets /\ \notin closed_tickets` is exactly
  \* "has not entered the lifecycle yet". Both guards collapse into this one,
  \* and the never-reopened property is now structural.
  /\ ticket_state[ticket] = TicketUnopened
  /\ ticket_state' = [ticket_state EXCEPT ![ticket] = TicketOpened]
  /\ lastCommand' = "tla-spec-dev open ticket"
  /\ result' = CommandResult(TRUE, NoReason, "Update ticket desired TLA+ first")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* Agent step: update ticket desired model, adapters, and Test Graph bindings.
\* This is intentionally modeled because the CLI must print this instruction.
\* @command UpdateTicketDesired
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
UpdateTicketDesired(ticket) ==
  /\ ticket \in ActiveTickets
  /\ ticket_state[ticket] = TicketOpened
  /\ ticket_state' = [ticket_state EXCEPT ![ticket] = TicketDesiredReady]
  /\ lastCommand' = "UpdateTicketDesired"
  /\ result' = CommandResult(TRUE, NoReason, "Implement ticket and update current")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* Agent step: production implementation has landed (a current/ exists, and must match desired/, only when opened --with-current).
\* @command UpdateTicketCurrent
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
UpdateTicketCurrent(ticket) ==
  /\ ticket \in ActiveTickets
  /\ ticket_state[ticket] = TicketDesiredReady
  /\ ticket_state' = [ticket_state EXCEPT ![ticket] = TicketCurrentReady]
  /\ lastCommand' = "UpdateTicketCurrent"
  /\ result' = CommandResult(TRUE, NoReason, "tla-spec-dev run spec-unit-tests")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> analyze complexity <spec> <cfg>`
\* MF-011, amended by CD-09 (G2): measures the model against the manifest
\* budgets and records the verdict. The verdict is a fact about the whole
\* program, not about one ticket, so it is a single global variable rather
\* than a per-ticket map -- and it is ADVISORY: recorded as an observable
\* fact, consulted by no guard. Nothing downstream blocks on it; a dense
\* model is a finding the agent reads, not a refused build
\* (references/architecture_tractability.md, "Advisory, Not Blocking").
\* The outcome is nondeterministic here because it depends on the model being
\* analyzed, which is outside this state machine.
\* @command AnalyzeComplexity
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.evidence_report
AnalyzeComplexity(root) ==
  /\ setup_phase >= 4
  /\ root = spec_root
  /\ complexity_gate' \in {"pass", "fail"}
  /\ lastCommand' = "tla-spec-dev analyze complexity"
  /\ result' = CommandResult(TRUE, NoReason, "tla-spec-dev run spec-unit-tests")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> analyze corpus <cases-dir>`
\* MF-014: measures the GENERATED CORPUS against the manifest case caps
\* (max_internal_cases_per_component, max_external_cases_per_action). Like
\* complexity_gate this is a fact about the whole program rather than about one
\* ticket, so it is a single global variable.
\*
\* Note what is deliberately ABSENT: there is no override input, and there is
\* no transition that reduces a case count. Cases are never dropped, filtered,
\* sampled, or truncated to satisfy a budget -- not silently and not with a
\* recorded drop rule. Over cap the command reports the distribution per
\* (action, label class), which strata dominate, which are starved, and what
\* varies across the redundant group, then exits nonzero. The only two ways to
\* reach "pass" are to FIX THE DIAGRAM so the redundant cases are never
\* generated, or to RAISE THE CAP in the manifest with a recorded one-line
\* rationale. Both are re-measurements, which is why this action simply
\* records a fresh verdict.
\* @command AnalyzeCorpus
\* @result CliWorkflowResult
\* No @port: `AnalyzeCorpus: []` -- evidence_report removed as a dead
\* declared port (CD-11 R4-3; corpus_diagnostics.py prints only).
AnalyzeCorpus(root) ==
  /\ setup_phase >= 4
  /\ root = spec_root
  /\ corpus_gate' \in {"pass", "fail"}
  /\ lastCommand' = "tla-spec-dev analyze corpus"
  /\ result' = CommandResult(TRUE, NoReason, "Fix the diagram, or raise the cap with a rationale")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  complexity_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> run effect-conformance`
\* MF-013: executes component adapters in a sandbox (temp dirs, fake
\* transports, recorded boundaries), collects the side effects that actually
\* crossed a boundary, and diffs them against the ports declared in
\* actions.yml / spec_manifest.yaml. Writes the diff report as ticket evidence.
\*
\* This is the standalone reporting command. It records a fresh verdict and
\* advances no ticket -- reporting is its whole job. The ENFORCING copy of the
\* same measurement lives inside RunSpecUnitTests below, because the shipped
\* runner performs the diff during the spec-unit run rather than waiting to be
\* asked. That is deliberate: a gate you have to remember to invoke is not a
\* gate.
\*
\* Observation is passive in the implementation -- the sandbox patches the
\* real boundaries, so an adapter cannot decline to disclose an effect. The
\* model reflects that by letting the verdict range over all four outcomes
\* rather than making it an input the caller supplies.
\*
\* MF-027: passivity is not the same as reach. The patches live in one CPython
\* interpreter, so passive observation of a target running elsewhere observes
\* nothing. "unobservable" is that case, and it is a failure.
\* @command RunEffectConformance
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.evidence_report
\* @port TlaSpecDevCliPort.spec_tree
\* HP-04: the per-case work directory is emptied before each case, so the same
\* corpus on the same tree reports the same gap count. That delete is a real
\* effect and is declared rather than left silent.
\* @port TlaSpecDevCliPort.spec_tree_delete
\* MF-026 G-1: HP-04 declared that delete under spec_tree_delete (**/specs/**),
\* which is true of the DEFAULT work dir and false of the --work-dir FLAG, which
\* has no resolver. Constraining the flag to specs/ was tried and reverted --
\* a scratch dir is not spec-tree content and three legitimate callers use a
\* temp directory. So the DECLARATION widens to match the behaviour instead.
\* @port TlaSpecDevCliPort.case_work_dir_delete
RunEffectConformance(root) ==
  /\ setup_phase >= 4
  /\ root = spec_root
  /\ effect_conformance' \in {"clean", "gaps", "dead_surface", "unobservable"}
  /\ lastCommand' = "tla-spec-dev run effect-conformance"
  /\ result' = CASE effect_conformance' = "clean"
                      -> CommandResult(TRUE, NoReason, "tla-spec-dev run spec-unit-tests")
                 [] effect_conformance' = "gaps"
                      -> CommandResult(FALSE, NoReason, "Declare the port, or change the program so it no longer emits the effect")
                 [] effect_conformance' = "unobservable"
                      -> CommandResult(FALSE, NoReason, "Run the target in-process, or check that boundary another way -- this oracle does not cover it")
                 [] OTHER
                      -> CommandResult(FALSE, NoReason, "Remove the dead port, or add a case that exercises it")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> run spec-unit-tests`
\* Runs generated/adapted spec-unit validation for the ticket model: current/ when seeded, otherwise desired/.
\* CD-09 (coverage-audit run 2, gap G2): the complexity gate no longer appears
\* in this guard AT ALL, and the `override` input is gone. The shipped command
\* performs no complexity check -- the descriptor is ADVISORY (MF-036/CD-01):
\* the program proceeds on a failing scan with a warning and has no
\* --allow-over-budget flag (generate_cases_from_tlc_dump.py, the scan-first
\* generation path, proceeds-on-fail; skills/spec-double-2/scripts/tla_spec_dev.py
\* run_spec_unit_tests reads no gate). The old guard
\* `complexity_gate = "pass" \/ (complexity_gate = "fail" /\ override)`
\* modeled the withdrawn blocking gate: doctrine withdrew the flag on
\* 2026-07-18 as degeneracy, the removal was deferred to MF-023 and never
\* done, and the model kept asserting a refusal the program does not perform.
\* The recorded verdict itself survives as complexity_gate -- an observable
\* fact AnalyzeComplexity records, read by no transition.
\* @command RunSpecUnitTests
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.test_process
\* @port TlaSpecDevCliPort.runner_process
\* @port TlaSpecDevCliPort.spec_tree
\* MF-026 G-2, PRE-EXISTING AT THE EPIC BASE and surfaced by no previous audit
\* round: --no-batch spawns <python> <work_dir>/programs/case_*.py, matching
\* neither test_process (*pytest*) nor runner_process. Declared rather than
\* constrained -- the per-case program IS the unit under test on that path.
\* @port TlaSpecDevCliPort.case_program_process
\* MF-026 round 2: the write half of the same gap. With no --work-dir the runner
\* writes into tempfile.mkdtemp, placing the per-case program under programs/.
\* @port TlaSpecDevCliPort.case_program_write
RunSpecUnitTests(root, ticket) ==
  /\ setup_phase >= 2
  /\ root = spec_root
  /\ ticket \in ActiveTickets
  \* MF-025: was `ticket_phase[ticket] >= 2` on an active ticket. Active caps
  \* the lifecycle at TicketSpecUnitTestsPassed, so the range is 3..4. This
  \* stays a range rather than an equality on purpose: tightening it would
  \* delete the idempotent re-run self-loop on an already-passing ticket.
  /\ ticket_state[ticket] \in TicketCurrentReady..TicketSpecUnitTestsPassed
  \* MF-014: generation produces the corpus, then the case caps are measured
  \* over it. The corpus is complete either way -- the gate refuses, it never
  \* trims -- so a failing verdict advances nothing and reports instead.
  \* The case caps have no override and never will: raising the cap with a
  \* recorded rationale is the accept path, and that is a different verdict
  \* rather than a bypassed one.
  /\ corpus_gate' \in {"pass", "fail"}
  \* MF-013: the spec-unit run executes adapters in the effect sandbox, so it
  \* measures effect conformance in the same pass. The verdict is recorded
  \* whatever it is -- the report is written clean or not -- and a ticket
  \* advances only when BOTH gates are satisfied.
  \*
  \* Note the shape of the conjunction below: there is no override input, no
  \* justification input, and no disjunct that lets "gaps" through. An
  \* undeclared observed effect FAILS. Recording the gap is not an alternative
  \* to failing on it -- both happen, which is what the 2026-07-18 audit
  \* required after finding the original criteria made the failure optional.
  \* MF-027: "unobservable" joins the range here too. Note that the ticket
  \* advance below already requires effect_conformance' = "clean", so an
  \* unobservable target blocks a ticket exactly as a gap does -- without a
  \* new clause, because there was never a disjunct to widen.
  /\ effect_conformance' \in {"clean", "gaps", "dead_surface", "unobservable"}
  /\ ticket_state' = IF corpus_gate' = "pass" /\ effect_conformance' = "clean"
                       THEN [ticket_state EXCEPT ![ticket] = TicketSpecUnitTestsPassed]
                       ELSE ticket_state
  /\ lastCommand' = "tla-spec-dev run spec-unit-tests"
  /\ result' = CASE effect_conformance' = "gaps"
                      -> CommandResult(FALSE, NoReason, "Declare the port, or change the program so it no longer emits the effect")
                 [] effect_conformance' = "unobservable"
                      -> CommandResult(FALSE, NoReason, "Run the target in-process, or check that boundary another way -- this oracle does not cover it")
                 [] effect_conformance' = "dead_surface"
                      -> CommandResult(FALSE, NoReason, "Remove the dead port, or add a case that exercises it")
                 [] corpus_gate' = "fail"
                      -> CommandResult(FALSE, NoReason, "Fix the diagram, or raise the cap with a rationale")
                 [] OTHER
                      -> CommandResult(TRUE, NoReason, "tla-spec-dev close ticket <ticket>")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  complexity_gate, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> close ticket <ticket-name>`
\* Closes ticket after spec-unit tests passed and promotes desired/ (desired-only since 2026-09-14; current == desired applies only to --with-current tickets).
\* @command CloseTicket
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
\* @port TlaSpecDevCliPort.spec_tree_delete
\* @port TlaSpecDevCliPort.git_metadata
CloseTicket(root, ticket) ==
  /\ setup_phase >= 2
  /\ root = spec_root
  /\ ticket \in ActiveTickets
  \* MF-025: leaving active and entering closed was a single simultaneous
  \* move that left ticket_phase UNCHANGED, so it is exactly this one step.
  /\ ticket_state[ticket] = TicketSpecUnitTestsPassed
  /\ ticket_state' = [ticket_state EXCEPT ![ticket] = TicketClosed]
  /\ lastCommand' = "tla-spec-dev close ticket"
  \* SI-05: a finding whose target is in this repository owes this repository a
  \* proposed change. The close NAMES each finding that owes one and proposes
  \* none, and still succeeds -- the result stays TRUE with NoReason.
  /\ result' = CommandResult(TRUE, NoReason, "Dispose of each finding that names this repository, then open next ticket or close workflow")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `tla-spec-dev --spec-root <root> close ticket <ticket-name>` taken under
\* one of the six GUARD-WEAKENING FLAGS.
\* RC-01, owner decision 2026-08-01 (MF-026 round-2 reservation). This is the
\* SAME shipped command as CloseTicket; what differs is that `--accept-new`
\* skips the current == desired check and overwrites current/ from desired/,
\* and `--allow-open` accepts a ticket whose plan status is not closed/done.
\* Both bypass the precondition CloseTicket guards on, so the transition is
\* modeled with the precondition REMOVED rather than with a flag input: a flag
\* the guard ignores would be presentation, and presentation is what this
\* action exists to stop representing.
\*
\* Note what the guard below says and does not say. It requires the ticket to
\* be ACTIVE -- a ticket that was never opened cannot be closed by any flag --
\* and nothing else. TicketOpened is reachable here, which is exactly the
\* claim: a ticket can reach a closed stage having passed no spec-unit run.
\* ClosedTicketsPassedSpecUnitTests is narrowed to GuardedClosedTickets for
\* precisely this reason; see the tombstone on that invariant.
\*
\* Which of the six was used is NOT distinguished, and that is per-flag
\* granularity rather than an omission -- the inventoried limitation covering
\* the other 72 options is untouched. What each of them does, stated so the
\* transition is not read as more uniform than it is:
\*   --accept-new         (close ticket)        skips the current == desired
\*                                              check and overwrites current/
\*                                              from desired/;
\*   --allow-open         (close ticket)        snapshots a ticket whose plan
\*                                              status is not closed/done;
\*   --no-promote-current (close ticket)        closes without promoting ticket
\*                                              desired/ into project current/;
\*   --validate-only      (run spec-unit-tests) reports a passing run that
\*                                              executed no case body;
\*   --force / --dry-run  (scaffold, open)      overwrite, or write nothing at
\*                                              all, under a command whose whole
\*                                              contract is what it wrote.
\*
\* A RECORDED LIMIT OF OBSERVATION, not of this model: the first three reach the
\* close path and are recorded there (skills/spec-double-2/scripts/spec_evolution.py writes
\* `guard_weakening` into the append-only history entry, which is what makes
\* this state externally observable at all). The last three weaken an EARLIER
\* step, so a close that follows one of them is in fact one of these closes
\* while the close path cannot see which flag did it. The model represents the
\* fact -- this close did not pass the guarded precondition -- and the record
\* names the flags it can name.
\* @command CloseTicketWeakened
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.spec_tree
\* @port TlaSpecDevCliPort.spec_tree_delete
\* @port TlaSpecDevCliPort.git_metadata
CloseTicketWeakened(root, ticket) ==
  /\ setup_phase >= 2
  /\ root = spec_root
  /\ ticket \in ActiveTickets
  /\ ticket_state' = [ticket_state EXCEPT ![ticket] = TicketClosedWeakened]
  /\ lastCommand' = "tla-spec-dev close ticket --accept-new"
  /\ result' = CommandResult(TRUE, NoReason, "Closed under a guard-weakening flag -- the spec-unit precondition was not checked")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* REMOVED 2026-08-04 (owner direction): the state variables architecture_scan
\* and architecture_delta, and the action AnalyzeArchitecture that was the only
\* writer of either. Recorded here rather than deleted silently, the same rule
\* SpecUnitTestsRequireAnalyzedGate's tombstone follows: removed model surface
\* must be distinguishable at review from lost model surface.
\*
\* WHAT WENT: `tla-spec-dev analyze architecture`, skills/spec-double-2/scripts/analyze_architecture.py
\* (1,192 lines) and skills/spec-double-2/scripts/architecture_reflexion.py (2,325). The command
\* recorded two advisory verdicts -- a model-side architecture descriptor and a
\* code-side reflexion diff -- and no guard anywhere read either, so the model
\* loses no precondition and no invariant with them. What it loses is the
\* ability to REPRESENT those two outcomes, which is correct: the program no
\* longer produces them.
\*
\* WHY, in one measurement taken on this very module before the removal. The
\* descriptor's own decomposition verdict on TlaSpecDevCli was "the partition is
\* a cut -- every criterion met", at graph modularity Q = 0.0116, against a
\* published rule of `Q > 0` and a Newman threshold of 0.3 that the same table
\* printed and did not apply. The second component that earned that verdict was
\* { architecture_scan, architecture_delta } -- the scanner's own state,
\* touched by one action, owning nothing. The DECLARED four-component partition
\* of the same model, written by hand to be honest, measured Q = -0.0228 and
\* failed. A verdict that passes on the analyser's own bookkeeping and fails on
\* the considered cut is sensitive to model SIZE, not to structure.
\*
\* MEASURED COST OF THE REMOVAL, both directions of it. The declared-representation
\* bound falls 26,671,680 -> 1,111,320 (a factor of 4 x 6, the two domains), and
\* TLC on MC.cfg falls 32,122,220 -> 13,008,254 generated and 1,292,951 ->
\* 563,963 distinct, depth 26 -> 25, no error. This is the FIRST TIME either
\* figure has gone down in this project. Every earlier entry in the chain
\* (tests/test_analyze_complexity.py) is a multiplication, and each one was
\* justified by a real outcome the program produces. This division is justified
\* the only way a shrink honestly can be: the program stopped producing those
\* outcomes. Note what did NOT happen -- no invariant was weakened, no guard was
\* relaxed, no domain was narrowed, and no reachable behaviour was quotiented
\* away. Two variables and their sole writer left together.
\*
\* What the scanners measured is now written down as instructions an agent
\* follows and as a specification a future scanner must satisfy before it earns
\* any authority here: references/architecture_advice.md. Reinstating these
\* variables means reinstating a command that meets that specification.

\* CLI: `tla-spec-dev --spec-root <root> generate cases <spec.tla> <cfg> --out <dir>`
\* RC-01 (MF-026 G-6), the headline gap: CASE-MODULE GENERATION -- this epic's
\* flagship feature -- was ENTIRELY UNREPRESENTED. skills/spec-double-2/scripts/case_modules.py
\* shipped a standalone main() unreachable from build_parser, and
\* skills/spec-double-2/scripts/generate_cases_from_tlc_dump.py spawned java/TLC, rmtree'd its
\* metadir and wrote generated packages with no action, no port and no CLI
\* subcommand anywhere in the model. CM-01 and RP-03 BOTH CLOSED "ZERO MODEL
\* DELTA" against surface the model does not contain, and all four oracles
\* reported green -- because every oracle in this toolchain is bounded to what
\* is already modeled, so unmodeled surface is never generated into a case,
\* never adapted and never mutated. That is the whole reason the coverage audit
\* exists (a REVIEW since 2026-08-04, no longer a gate -- the sweep is the
\* valuable part and the refusal never was).
\*
\* Guarded on setup_phase >= 4 for the same reason AnalyzeCorpus and
\* RunKillTest are: generation measures the corpus against the manifest case
\* caps at the end of the run, and reading a cap before budgets are recorded
\* would silently measure against a default nobody negotiated.
\*
\* Records NO verdict. The command writes a corpus; it does not measure one.
\* corpus_gate deliberately stays UNCHANGED here -- setting it back to
\* "unknown" on every generation would falsify
\* SpecUnitTestsRequireMeasuredCorpus for a ticket that legitimately passed
\* earlier, which is asserting something the program does not do.
\* @command GenerateCases
\* @result CliWorkflowResult
\* @port TlaSpecDevCliPort.corpus_process
\* @port TlaSpecDevCliPort.spec_tree
\* @port TlaSpecDevCliPort.spec_tree_delete
GenerateCases(root) ==
  /\ setup_phase >= 4
  /\ root = spec_root
  /\ lastCommand' = "tla-spec-dev generate cases"
  /\ result' = CommandResult(TRUE, NoReason, "tla-spec-dev analyze corpus <cases-dir>")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance, skt_answer >>

\* CLI: `skt status`
\* SI-20-DF-05 and SI-20-DF-06. `unique` is whether the checkout carries exactly
\* one epic/* ref; `joined` is whether the branch was joined to a spec id
\* through `github_issue`. Naming an epic without uniqueness reported an epic
\* closed on 2026-08-03; claiming membership without the join told every ticket
\* worktree in this epic that its ticket was not in the plan.
\* @command SktStatus
\* @result CliWorkflowResult
SktStatus(unique, joined) ==
  /\ skt_answer' = [ skt_answer EXCEPT
                       !.epic_unique       = unique,
                       !.epic_named        = unique,
                       !.membership_joined = joined,
                       !.membership_claim  = joined ]
  /\ lastCommand' = "SktStatus"
  /\ result' = CommandResult(TRUE, NoReason, "skt check")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance >>

\* CLI: `skt check`
\* SI-20-DF-07. `measured` is whether EVERY surface the command reports on was
\* measured -- units and artifacts both. A headline of "all current" over an
\* artifact probe that timed out is a verdict about something never looked at.
\* @command SktCheck
\* @result CliWorkflowResult
SktCheck(measured) ==
  /\ skt_answer' = [ skt_answer EXCEPT
                       !.surfaces_measured = measured,
                       !.verdict_current   = measured ]
  /\ lastCommand' = "SktCheck"
  /\ result' = CommandResult(TRUE, NoReason, "skt sync")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance >>

\* CLI: `skt ticket sweep`
\* SI-20-DF-04, severity data-loss-adjacent. `contained` is whether containment
\* against a resolved target was actually measured. Planning removals without it
\* offered to retire 23 worktrees, including in-flight ticket worktrees.
\* @command SktTicketSweep
\* @result CliWorkflowResult
\* @port SktPort.worktree_removal
SktTicketSweep(contained) ==
  /\ skt_answer' = [ skt_answer EXCEPT
                       !.containment_known = contained,
                       !.sweep_planned     = contained ]
  /\ lastCommand' = "SktTicketSweep"
  /\ result' = CommandResult(TRUE, NoReason, "skt ticket sweep --yes")
  /\ UNCHANGED << setup_phase,
                  spec_root,
                  ticket_state,
                  complexity_gate,
                  corpus_gate,
                  effect_conformance >>

Stutter ==
  UNCHANGED vars

Next ==
  \/ BuildSkillCli
  \/ InstallLocalCli
  \/ \E root \in SpecRoots:
      ScaffoldProject(root)
  \/ \E root \in SpecRoots:
      RecordBudgets(root)
  \/ \E root \in SpecRoots:
      ScaffoldWorkflow(root)
  \/ \E root \in SpecRoots, ticket \in Tickets:
      OpenTicket(root, ticket)
  \/ \E ticket \in Tickets:
      UpdateTicketDesired(ticket)
  \/ \E ticket \in Tickets:
      UpdateTicketCurrent(ticket)
  \/ \E root \in SpecRoots:
      AnalyzeComplexity(root)
  \/ \E root \in SpecRoots:
      AnalyzeCorpus(root)
  \/ \E root \in SpecRoots:
      GenerateCases(root)
  \/ \E root \in SpecRoots:
      RunEffectConformance(root)
  \/ \E root \in SpecRoots, ticket \in Tickets:
      RunSpecUnitTests(root, ticket)
  \/ \E root \in SpecRoots, ticket \in Tickets:
      CloseTicket(root, ticket)
  \/ \E root \in SpecRoots, ticket \in Tickets:
      CloseTicketWeakened(root, ticket)
  \/ \E unique \in BOOLEAN, joined \in BOOLEAN:
      SktStatus(unique, joined)
  \/ \E measured \in BOOLEAN:
      SktCheck(measured)
  \/ \E contained \in BOOLEAN:
      SktTicketSweep(contained)
  \/ Stutter

TypeInvariant ==
  /\ setup_phase \in 0..5
  /\ spec_root \in SpecRoots \cup {NoRoot}
  \* RC-01: 0..6 -- TicketClosedWeakened is the sixth stage.
  /\ ticket_state \in [Tickets -> 0..6]
  \* MF-025: retained by name. Both are now structurally true, since
  \* ActiveTickets and ClosedTickets are defined by comprehension over
  \* Tickets, but a named safety property that is deleted is
  \* indistinguishable at review from one that was lost.
  /\ ActiveTickets \subseteq Tickets
  /\ ClosedTickets \subseteq Tickets
  /\ complexity_gate \in {"unknown", "pass", "fail"}
  /\ corpus_gate \in {"unknown", "pass", "fail"}
  /\ effect_conformance \in {"unknown", "clean", "gaps", "dead_surface", "unobservable"}
  /\ skt_answer \in SktAnswers

\* MF-022: the four bootstrap ordering invariants below are retained by name
\* even though the setup_phase ordinal now enforces them structurally, so each
\* is a tautology. This follows the precedent MF-020 set for ticket_phase:
\* deleting a named safety property is indistinguishable at review from losing
\* it, and retaining it documents that the ordering is still required and is
\* now guaranteed by construction rather than by checking.
CliInstalledRequiresBuilt ==
  setup_phase >= 2 => setup_phase >= 1

WorkflowRequiresProject ==
  setup_phase >= 5 => setup_phase >= 3

\* Budgets are per-program state established during scaffolding.
BudgetsRequireProject ==
  setup_phase >= 4 => setup_phase >= 3

\* Every generation action runs behind recorded budgets: the workflow (and
\* therefore every ticket, spec-unit run, and close) cannot be scaffolded
\* until the budgets block exists in the manifest.
WorkflowRequiresBudgets ==
  setup_phase >= 5 => setup_phase >= 4

\* Not a tautology: this relates setup_phase to the separate spec_root
\* variable and still does real work.
ProjectChoosesKnownSpecRoot ==
  setup_phase >= 3 => spec_root \in SpecRoots

\* MF-025: retained by name. The ordinal makes this a tautology -- a ticket
\* has one state, and TicketClosed is not in TicketOpened..TicketSpecUnitTestsPassed
\* -- but the property is still required and is now guaranteed by construction
\* rather than by checking.
NoOpenClosedOverlap ==
  ActiveTickets \cap ClosedTickets = {}

\* RC-01: TicketReached, not >=. See the tombstone on
\* ClosedTicketsPassedSpecUnitTests -- a weakened close reached NEITHER of
\* these stages, and `>=` would have claimed it reached both.
CurrentRequiresDesired ==
  \A ticket \in Tickets:
    TicketReached(ticket, TicketCurrentReady)
      => TicketReached(ticket, TicketDesiredReady)

SpecUnitTestsRequireCurrent ==
  \A ticket \in Tickets:
    TicketReached(ticket, TicketSpecUnitTestsPassed)
      => TicketReached(ticket, TicketCurrentReady)

\* CD-09 (G2): SpecUnitTestsRequireAnalyzedGate REMOVED, deliberately and with
\* this tombstone rather than silently -- a deleted safety property must be
\* distinguishable at review from a lost one (the MF-020/MF-022 retention
\* precedent, applied in reverse). The invariant asserted that no ticket
\* passes spec-unit tests before analyze complexity records a verdict. That
\* was the blocking-gate era's property: it held only because the old
\* RunSpecUnitTests guard refused to fire while complexity_gate = "unknown".
\* The shipped program has no such refusal -- `run spec-unit-tests` performs
\* no complexity check, and the descriptor is advisory (MF-036/CD-01) -- so
\* the invariant claimed an assurance the program does not provide, which is
\* precisely the defect coverage-audit run 2 recorded as gap G2. TLC evidence
\* of the removal being real: states with a ticket at
\* TicketSpecUnitTestsPassed and complexity_gate = "unknown" are now
\* reachable (distinct states grew when the guard came out).

\* MF-014: no ticket ever passes spec-unit tests without its generated corpus
\* having been measured against the case caps. Reaching phase 3 means cases
\* were generated and run, and RunSpecUnitTests records a cap verdict on every
\* such transition -- so a corpus that was never measured cannot be behind a
\* passing ticket. The companion property, that a case is never removed to make
\* the verdict "pass", is structural rather than checkable here: no action in
\* this module reduces a case count, and no override input reaches the cap.
\* RC-01: TicketReached. TLC FOUND THIS ONE -- with `>=` the first weakened
\* close from TicketOpened violated it in 1,094 states, because a ticket sitting
\* at TicketClosedWeakened satisfied `>= TicketSpecUnitTestsPassed` while no
\* corpus had ever been measured. That violation is the property working: the
\* invariant is about corpora behind PASSING tickets, and a weakened close is
\* not a passing ticket.
SpecUnitTestsRequireMeasuredCorpus ==
  (\E ticket \in Tickets: TicketReached(ticket, TicketSpecUnitTestsPassed))
    => corpus_gate /= "unknown"

\* MF-013: no ticket ever passes spec-unit tests while the representation is
\* blind to a real effect, or while it carries a port no case exercises.
\* Reaching TicketSpecUnitTestsPassed means adapters ran in the sandbox and the
\* diff came back clean -- "unknown" is excluded because the run always records
\* a verdict, and "gaps"/"dead_surface"/"unobservable" are excluded because
\* they are failures. MF-027 added the third: a ticket must not pass on a
\* target the oracle could not see, which is a weaker claim than a gap only in
\* the sense that it reports the absence of evidence rather than the evidence
\* of a defect. Both are disqualifying.
\*
\* This is the invariant form of the rule the 2026-07-18 audit restored. The
\* companion property, that no justification can make a gap acceptable, is
\* structural rather than checkable here: no action in this module takes a
\* justification input, and no transition maps "gaps" to a passing ticket.
\* tests/test_effect_conformance.py proves the same thing about the shipped
\* implementation by asserting a recorded justification does NOT prevent the
\* failure.
\*
\* Why "/= unknown" and not "= clean": RunEffectConformance is a standalone
\* re-measurement enabled at any point after setup, so a later run can legally
\* find gaps in a program whose ticket passed earlier -- that is a real
\* sequence, and TLC finds it. Asserting "= clean" here would therefore be a
\* false invariant, and weakening the ACTION to make it true would delete the
\* re-measurement rather than describe the program. The gate itself lives where
\* it belongs, in RunSpecUnitTests: ticket_state advances only when
\* effect_conformance' = "clean", with no override and no justification input
\* anywhere in the conjunction. This invariant states the part that holds
\* globally -- a ticket never passes on an unmeasured effect surface -- and
\* matches SpecUnitTestsRequireMeasuredCorpus, which is weakened for exactly
\* the same reason.
SpecUnitTestsRequireMeasuredEffects ==
  (\E ticket \in Tickets: TicketReached(ticket, TicketSpecUnitTestsPassed))
    => effect_conformance /= "unknown"

\* MF-025: retained by name; now structurally true, since TicketClosed (5)
\* is itself >= TicketSpecUnitTestsPassed (4) and the only way into it is
\* through that stage.
\*
\* RC-01 NARROWING, recorded here rather than done silently -- a weakened
\* safety property must be distinguishable at review from one that was lost
\* (the MF-020/MF-022 retention precedent, applied to a weakening). The
\* quantifier moved from ClosedTickets to GuardedClosedTickets. It had to.
\* TicketClosedWeakened is 6, and 6 >= 4, so leaving the quantifier over
\* ClosedTickets would have kept this invariant TRUE BY ACCIDENT OF THE ORDINAL
\* ENCODING while a weakened close never passed a spec-unit run -- the model
\* would read as an assurance that every closed ticket was validated, which is
\* exactly what `--accept-new` and `--allow-open` exist to make false.
\*
\* What this invariant now claims is the whole of what TLC can prove: a close
\* taken THROUGH THE GUARD passed spec-unit tests. What it deliberately no
\* longer claims is anything about a close taken around the guard, and the
\* absence of that claim is the finding. There is no companion invariant
\* asserting the weakened path is safe, because it is not.
ClosedTicketsPassedSpecUnitTests ==
  \A ticket \in GuardedClosedTickets:
    TicketReached(ticket, TicketSpecUnitTestsPassed)

\* RC-01: the companion, and the only new named property this ticket adds. It
\* states what a weakened close IS, positively, so the narrowing above cannot be
\* read as the model simply having less to say: a ticket closed around the guard
\* never reached the spec-unit stage, and no invariant in this module may be
\* read as evidence that it did.
\*
\* It is deliberately NOT "weakened closes are forbidden". The shipped CLI
\* offers the flags, they have legitimate uses, and an invariant asserting a
\* refusal the program does not perform is precisely the defect CD-09's G2
\* removed. What is asserted is that the record distinguishes the two, which is
\* the thing that was missing: `--accept-new` and `--allow-open` bypassed a
\* precondition TLC proved over 563,963 states and no oracle could see it.
WeakenedClosesCertifyNothing ==
  \A ticket \in WeakenedClosedTickets:
    ~TicketReached(ticket, TicketSpecUnitTestsPassed)

\* ---- the four skt honesty invariants; each one is a repaired defect --------
\*
\* They share a shape, and the shape is the finding: an answer is only allowed
\* when the thing it answers about was measured. `blockers` in sweep.py states
\* it in prose -- "an evidence gap is not a clean bill of health ... could not
\* tell must never read as nothing here" -- and three commands did not obey it.

\* SI-20-DF-05: `skt status` named the FIRST of sixteen epic refs.
SktNamesNoEpicItCannotResolve ==
  skt_answer.epic_named => skt_answer.epic_unique

\* SI-20-DF-06: membership was decided by comparing a branch slug to a spec id.
SktClaimsNoMembershipItDidNotJoin ==
  skt_answer.membership_claim => skt_answer.membership_joined

\* SI-20-DF-07: "all current" over an artifact probe that timed out.
SktVerdictCoversEverySurfaceItNames ==
  skt_answer.verdict_current => skt_answer.surfaces_measured

\* SI-20-DF-04: 23 worktrees planned for removal with containment never asked.
SktPlansNoRemovalWithoutContainment ==
  skt_answer.sweep_planned => skt_answer.containment_known

Spec ==
  Init /\ [][Next]_vars

=============================================================================
