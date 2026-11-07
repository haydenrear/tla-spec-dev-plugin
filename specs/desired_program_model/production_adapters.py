"""Ticket-local adapters for the shipped tla-spec-dev CLI entrypoint."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


# MF-032: the shared before-state builder, projector and field comparator were
# promoted out of this file into a dedicated MODULE (adapter_case_runtime) --
# deliberately NOT a base class, because the adapters' apply() signatures are
# incompatible. Every case-executing adapter below imports these free functions
# and composes them inside its own run(). apply() stays the spec-unit surface.
#
# The module sits beside this file; add its directory to sys.path so it resolves
# whether this file is imported by the runner (--import-root), loaded from the
# promoted specs/current tree, or exec'd by a spec-unit test via
# importlib.util.spec_from_file_location.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter_case_runtime import (  # noqa: E402
    BeforeStateUnreachable,
    CURRENT_READY_MARKER,
    DESIRED_READY_MARKER,
    SETUP_PIPELINE,
    TICKET_CLOSED,
    TICKET_CURRENT_READY,
    TICKET_DESIRED_READY,
    TICKET_OPENED,
    TICKET_SPEC_UNIT_PASSED,
    TICKET_UNOPENED,
    UNPROJECTABLE_FIELDS,
    _ensure_ticket_in_plan,
    _mark_ticket_tree,
    _negotiate_budgets,
    compare_projection,
    enforce_projection,
    materialize_before,
    project_state,
    project_ticket_state,
    recover_ticket_except_index,
    repo_root,
    run_cli,
)


class UpdateTicketAdapterBase:
    """MF-031: the two ticket agent steps, made case-executable.

    MF-028 found `UpdateTicketDesired` and `UpdateTicketCurrent` had no adapter
    anywhere; their absence blocked 72.5% of the corpus, because no adapter
    advanced `ticket_state`, so no before-state with an active ticket could be
    materialized. These adapters restore that signal.

    Neither action is a CLI command -- each is the model's record of the human
    editing the ticket's desired, then current, model. So `run()`:

      1. materializes the before-state, INCLUDING the ticket segment, by driving
         the real CLI (`open ticket`) and replaying the agent edits;
      2. recovers the `ticket` argument by MF-029 except-index on `ticket_state`;
      3. performs the transition -- the agent edit this action models -- against
         the recovered ticket's tree;
      4. projects `ticket_state` back from the filesystem (never from the case's
         after-state) and every UNCHANGED variable from the before-state;
      5. compares the projection to the model's after-state, field by field, and
         fails on any disagreement.

    The value asserted for the changed ticket is derived from the before-state
    and the transition's meaning, then OBSERVED from the edit the adapter made.
    Each subclass has a negative control (a deliberately wrong after-state)
    proven to make step 5 fail -- see the ticket's spec-unit tests.
    """

    action_name = "UpdateTicket"
    #: The ticket_state stage this action requires in the before-state.
    from_stage = TICKET_UNOPENED
    #: The stage the transition advances the recovered ticket to.
    to_stage = TICKET_UNOPENED
    #: (tree, marker) the agent edit writes to reach `to_stage`.
    ready_tree = ""
    ready_marker = ""
    last_command = ""

    def can_run(self, case: object) -> tuple[bool, str | None]:
        action = getattr(case, "input").action
        if action != self.action_name:
            return False, f"case action {action} is not {self.action_name}"
        try:
            ticket = recover_ticket_except_index(case)
        except BeforeStateUnreachable as exc:
            return False, str(exc)
        before_stage = int(dict(getattr(case, "before").get("ticket_state") or {}).get(ticket, TICKET_UNOPENED))
        if before_stage != self.from_stage:
            return False, (
                f"{self.action_name} is enabled only when the ticket is at stage "
                f"{self.from_stage}; before-state has {ticket} at {before_stage}"
            )
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)

        # MF-029: recover the ticket argument from the state pair, never trust an
        # out-of-band value. `params` carries the same recovery, but re-deriving
        # here keeps the adapter self-contained and the recovery auditable.
        ticket = recover_ticket_except_index(case)

        # Perform the modelled agent edit against the recovered ticket.
        _mark_ticket_tree(target_repo, spec_root, ticket, self.ready_tree, self.ready_marker)

        applied_accepted = True
        projected = project_state(
            target_repo,
            spec_root,
            prior=dict(getattr(case, "before")),
            last_command=self.last_command,
            accepted=applied_accepted,
        )
        # OBSERVE ticket_state from the filesystem for every ticket the case
        # names -- the CHANGED variable must never be carried from the
        # before-state, or the check would pass under a corrupted after-state.
        ticket_tokens = sorted(set(dict(getattr(case, "before").get("ticket_state") or {})) |
                               set(dict(getattr(case, "after").get("ticket_state") or {})))
        projected["ticket_state"] = project_ticket_state(target_repo, spec_root, ticket_tokens)

        comparison = compare_projection(case=case, projected=projected)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "ticket": ticket,
                "from_stage": self.from_stage,
                "to_stage": self.to_stage,
                "replay": replay,
                "projected": projected,
                "comparison": comparison,
            },
        }


class UpdateTicketDesiredAdapter(UpdateTicketAdapterBase):
    action_name = "UpdateTicketDesired"
    from_stage = TICKET_OPENED
    to_stage = TICKET_DESIRED_READY
    ready_tree = "desired"
    ready_marker = DESIRED_READY_MARKER
    last_command = "UpdateTicketDesired"


class UpdateTicketCurrentAdapter(UpdateTicketAdapterBase):
    action_name = "UpdateTicketCurrent"
    from_stage = TICKET_DESIRED_READY
    to_stage = TICKET_CURRENT_READY
    ready_tree = "current"
    ready_marker = CURRENT_READY_MARKER
    last_command = "UpdateTicketCurrent"


class StutterAdapter:
    """MF-028 spike scaffolding, NOT a deliverable of this ticket.

    The runner's coverage gate is WHOLE-CORPUS: it refuses before executing
    anything unless every label in the corpus has a binding. Running a single
    ScaffoldProject case therefore required binding `Stutter` too, and no
    Stutter adapter exists at the epic tip.

    This is a finding about ordering, not a fix. MF-023's stuttering work and
    its `case_adapters.toml` bindings are on open PR #50; this class exists only
    so the spike could reach its measurement, and it should be DELETED in favour
    of PR #50's version rather than merged alongside it.
    """

    action_name = "Stutter"

    def run(self, case: object, work_dir: Path | None = None):
        before, after = dict(getattr(case, "before")), dict(getattr(case, "after"))
        if before != after:
            raise AssertionError(f"{getattr(case, 'name')}: stutter changed state")
        return {"output": None, "after": None, "semantic_output": {"stutter": True}}


class BuildSkillCliAdapter:
    action_name = "BuildSkillCli"

    def apply(self) -> dict[str, object]:
        root = repo_root()
        entrypoint = root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"
        # SI-11 moved the skill-script installers to the PLUGIN root: a `skill-script:`
        # CLI dep is resolved by the INSTALLED UNIT's name, and a contained skill's
        # name never reaches the resolver (SIS-W2-F-05). Applied here by the epic
        # agent, which owns the model, so BuildSkillCli reports accepted: true.
        installer = root / "skill-scripts" / "install-tla-spec-dev.sh"
        return {
            "accepted": entrypoint.is_file() and installer.is_file(),
            "entrypoint": str(entrypoint),
            "installer": str(installer),
        }

    # MF-028: the FLOOR case. Included because it is the cheapest possible
    # `run()` in the repository and therefore calibrates the bottom of the
    # difficulty scale -- not because it is representative. Its before-state is
    # setup_phase=0, which materializes to an empty directory, so it exercises
    # execution and projection but NOT before-state construction. Read the
    # ScaffoldProject run() below for the first honest measurement.
    def can_run(self, case: object) -> tuple[bool, str | None]:
        if getattr(case, "input").action != self.action_name:
            return False, f"case action {getattr(case, 'input').action} is not {self.action_name}"
        if int(dict(getattr(case, "before"))["setup_phase"]) != 0:
            return False, "BuildSkillCli is enabled only at setup_phase = 0"
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)
        applied = self.apply()
        projected = project_state(
            target_repo,
            spec_root,
            prior=dict(getattr(case, "before")),
            last_command="BuildSkillCli",
            accepted=bool(applied["accepted"]),
        )
        # BuildSkillCli advances the pipeline but writes nothing into the target
        # repo, so filesystem evidence cannot distinguish phase 0 from phase 1.
        # The adapter reports the phase it actually achieved: the entrypoint and
        # installer it just verified ARE the postcondition of BuildSkillCli.
        projected["setup_phase"] = 1 if applied["accepted"] else 0
        projected["spec_root"] = "NoRoot"
        comparison = compare_projection(case=case, projected=projected)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "replay": replay,
                "projected": projected,
                "comparison": comparison,
            },
        }


class InstallLocalCliAdapter:
    action_name = "InstallLocalCli"

    def apply(self, bin_dir: Path, cache_dir: Path) -> dict[str, object]:
        root = repo_root()
        env = {
            **os.environ,
            "SKILL_MANAGER_BIN_DIR": str(bin_dir),
            "SKILL_MANAGER_CACHE_DIR": str(cache_dir),
            # The dep is declared on the PLUGIN now, so skill-manager sets SKILL_DIR to
            # the plugin root and SKILL_NAME to the plugin name. This adapter
            # reproduces the real install environment, so it moves with it.
            "SKILL_DIR": str(root),
            "SKILL_NAME": "tla-spec-dev",
        }
        install = subprocess.run(
            ["bash", str(root / "skill-scripts" / "install-tla-spec-dev.sh")],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        wrapper = bin_dir / "tla-spec-dev"
        version = subprocess.run(
            [str(wrapper), "--version"],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        ) if wrapper.exists() else None
        return {
            "accepted": install.returncode == 0 and version is not None and version.returncode == 0,
            "install_exit_code": install.returncode,
            "version_exit_code": None if version is None else version.returncode,
            "version": "" if version is None else version.stdout.strip(),
            "wrapper": str(wrapper),
        }

    # MF-032: TRIVIAL band (MF-028 report section 4). InstallLocalCli's
    # before-state is setup_phase=1, which materializes to an EMPTY directory --
    # the tla-spec-dev checkout the install concerns is already built in any
    # working tree -- so this exercises execution and projection but not
    # before-state construction, the same floor BuildSkillCli calibrates. The
    # transition changes only setup_phase (1->2); every other variable is
    # UNCHANGED and carried from the before-state.
    def can_run(self, case: object) -> tuple[bool, str | None]:
        if getattr(case, "input").action != self.action_name:
            return False, f"case action {getattr(case, 'input').action} is not {self.action_name}"
        if int(dict(getattr(case, "before"))["setup_phase"]) != 1:
            return False, "InstallLocalCli is enabled only at setup_phase = 1"
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)
        # Drive the REAL installer into the case's own work dir; nothing leaks
        # into the target repo, whose emptiness is the modelled before-state.
        bin_dir = work_dir / "bin"
        cache_dir = work_dir / "cache"
        bin_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        applied = self.apply(bin_dir, cache_dir)
        projected = project_state(
            target_repo,
            spec_root,
            prior=dict(getattr(case, "before")),
            last_command="InstallLocalCli",
            accepted=bool(applied["accepted"]),
        )
        # Like BuildSkillCli, the install writes nothing into the target repo, so
        # filesystem evidence cannot distinguish phase 1 from phase 2. The adapter
        # reports the phase it actually achieved: a working `tla-spec-dev
        # --version` wrapper IS the postcondition of InstallLocalCli. The value is
        # derived from the install the adapter just performed, never from
        # case.after -- so the negative control below genuinely fails.
        projected["setup_phase"] = 2 if applied["accepted"] else 1
        projected["spec_root"] = "NoRoot"
        comparison = compare_projection(case=case, projected=projected)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "replay": replay,
                "wrapper": applied["wrapper"],
                "projected": projected,
                "comparison": comparison,
            },
        }


class ScaffoldProjectAdapter:
    action_name = "ScaffoldProject"

    def apply(self, target_repo: Path, *, spec_root: str = "specs", name: str = "CliProject") -> dict[str, object]:
        root = repo_root()
        result = subprocess.run(
            [
                sys.executable,
                str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                "--spec-root",
                spec_root,
                "scaffold",
                "project",
                "--name",
                name,
            ],
            cwd=target_repo,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "accepted": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "program_model": str(target_repo / spec_root / "program_model" / f"{name}.tla"),
        }

    # MF-028: THE MEASURED CASE. ScaffoldProject is the simplest adapter whose
    # before-state is non-vacuous AND whose action mutates persistent state:
    #
    #   * before-state setup_phase=2 is a real prefix (built + installed), so
    #     materialization is actually exercised rather than skipped;
    #   * the action writes a program_model tree, so the after-state is
    #     recoverable from the filesystem instead of being asserted on stdout;
    #   * it changes exactly two observable variables (setup_phase, spec_root),
    #     so a mismatch localizes instead of producing a wall of diffs.
    #
    # Everything cheaper than this (BuildSkillCli, InstallLocalCli,
    # ValidateTestGraphCli) has an empty before-state and no persistent effect,
    # and so cannot measure the thing the ticket asked about.
    def can_run(self, case: object) -> tuple[bool, str | None]:
        if getattr(case, "input").action != self.action_name:
            return False, f"case action {getattr(case, 'input').action} is not {self.action_name}"
        if int(dict(getattr(case, "before"))["setup_phase"]) != 2:
            return False, "ScaffoldProject is enabled only at setup_phase = 2"
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)

        # MF-028 HEADLINE FINDING, caught by this spike's own negative control.
        #
        # ScaffoldProject(root) is PARAMETERIZED, but the generated case carries
        # `params={}` -- and so does every one of the 57,617 cases in the
        # corpus. The generator recovers action arguments from a
        # `lastInternalAction` marker variable; this model declares no such
        # variable, so every argument to every parameterized action is lost.
        #
        # The adapter therefore cannot know which root the model chose. The
        # first draft of this method defaulted to `case.after["spec_root"]`,
        # which made the `spec_root` check a TAUTOLOGY: it read the expected
        # answer out of the case and echoed it back as an observation. A
        # deliberately corrupted after-state still passed. That is exactly the
        # false signal MF-016 caught in the kill rate.
        #
        # So: the adapter picks its own root, and `spec_root` is declared
        # UNCHECKED rather than compared. An unverifiable field is reported
        # unverifiable.
        params = dict(getattr(case, "input").params or {})
        root_token = str(params["root"]) if "root" in params else None
        chosen = "specs" if root_token in (None, "default_specs") else str(root_token)

        applied = self.apply(target_repo, spec_root=chosen)
        projected = project_state(
            target_repo,
            chosen,
            prior=dict(getattr(case, "before")),
            last_command="tla-spec-dev scaffold project",
            accepted=bool(applied["accepted"]),
        )
        # Map the concrete directory back to a symbolic token where one was
        # actually supplied. With no params in the corpus this stays None, and
        # spec_root is declared unobservable below rather than compared.
        projected["spec_root"] = root_token if root_token is not None else f"<unparameterized:{chosen}>"
        unobservable = () if root_token is not None else ("spec_root",)
        comparison = compare_projection(case=case, projected=projected, unobservable=unobservable)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "replay": replay,
                "exit_code": applied["exit_code"],
                "projected": projected,
                "comparison": comparison,
            },
        }


class ScaffoldWorkflowAdapter:
    action_name = "ScaffoldWorkflow"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-123",
        title: str = "CLI scaffold ticket",
    ) -> dict[str, object]:
        root = repo_root()
        result = subprocess.run(
            [
                sys.executable,
                str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                "--spec-root",
                spec_root,
                "scaffold",
                "workflow",
                ticket_id,
                title,
            ],
            cwd=target_repo,
            text=True,
            capture_output=True,
            check=False,
        )
        return {
            "accepted": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "current": str(target_repo / spec_root / "current"),
            "desired": str(target_repo / spec_root / "desired_program_model"),
        }

    # MF-032: MODERATE band (MF-028 report section 4). Before-state setup_phase=4
    # is a real prefix -- built, installed, project scaffolded, budgets
    # negotiated -- replayed by the shared `materialize_before`. The action
    # writes `current/` and `desired_program_model/`, so setup_phase=5 is
    # recovered from the FILESYSTEM by `project_state`, not asserted on stdout.
    # ScaffoldWorkflow(root) is parameterized but the corpus carries params={};
    # `root = spec_root` is UNCHANGED, so the materialized spec_root is authentic
    # rather than guessed.
    def can_run(self, case: object) -> tuple[bool, str | None]:
        if getattr(case, "input").action != self.action_name:
            return False, f"case action {getattr(case, 'input').action} is not {self.action_name}"
        if int(dict(getattr(case, "before"))["setup_phase"]) != 4:
            return False, "ScaffoldWorkflow is enabled only at setup_phase = 4"
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)
        applied = self.apply(target_repo, spec_root=spec_root)
        projected = project_state(
            target_repo,
            spec_root,
            prior=dict(getattr(case, "before")),
            last_command="tla-spec-dev scaffold workflow",
            accepted=bool(applied["accepted"]),
        )
        # setup_phase is read back from the real tree: current/ + desired/ now
        # exist, so project_state reports 5 without any hint from case.after.
        comparison = compare_projection(case=case, projected=projected)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "replay": replay,
                "exit_code": applied["exit_code"],
                "projected": projected,
                "comparison": comparison,
            },
        }


def prepare_ticket_workflow(
    root: Path,
    target_repo: Path,
    *,
    spec_root: str,
    ticket_id: str,
    title: str,
) -> list[subprocess.CompletedProcess[str]]:
    return [
        run_cli(root, target_repo, "--spec-root", spec_root, "scaffold", "project", "--name", "CliProject"),
        run_cli(root, target_repo, "--spec-root", spec_root, "scaffold", "workflow", ticket_id, title),
    ]


# MF-019: closing a ticket requires a filled-in complexity ledger input. `open
# ticket` scaffolds it with TODO sentinels that fail the gate on purpose, so
# every adapter that drives a real close fills it first. There is deliberately
# no bypass flag -- the standing objective is a required close-out step, so the
# adapters go through the real gate rather than around it.
PASSING_COMPLEXITY_LEDGER = """\
validated_refactor:
  tlc_before:
    status: "green"
    evidence: "results/tlc-before.txt"
  tlc_after:
    status: "green"
    evidence: "results/tlc-current.txt"
  behavior_tests:
    status: "pass"
    evidence: "results/behavior-tests.txt"
  descriptor_comparison:
    status: "recorded"
    evidence: "results/descriptors-before-after.txt"
retention:
  kill_rate:
    status: "pass"
    evidence: "results/kill-test.json"
  effect_conformance:
    status: "clean"
    evidence: "results/effect-conformance.txt"
  external_coverage:
    status: "pass"
    evidence: "results/external-coverage.txt"
justification: "Adapter fixture close; no model growth claimed."
refinement:
  searched: true
  outcome: "none"
refinement_note: "searched, found none"
narrative: "Adapter fixture ledger narrative."
"""


#: CD-09: the honest post-pivot retention record -- the fuzzing-era members
#: RECORDED as not run (they are experimental and did not run), with the
#: validated-refactor basis green. This is the input an honest validated
#: decrease closes with.
NOT_RUN_FUZZING_LEDGER = (
    PASSING_COMPLEXITY_LEDGER
    .replace('status: "pass"\n    evidence: "results/kill-test.json"',
             'status: "not_run"\n    evidence: "experimental since the 2026-07-21 pivot"')
    .replace('status: "clean"\n    evidence: "results/effect-conformance.txt"',
             'status: "not_run"\n    evidence: "experimental since the 2026-07-21 pivot"')
    .replace('status: "pass"\n    evidence: "results/external-coverage.txt"',
             'status: "not_run"\n    evidence: "experimental since the 2026-07-21 pivot"')
)


def fill_complexity_ledger(target_repo: Path, spec_root: str, ticket_id: str) -> Path:
    """Fill the scaffolded per-ticket complexity ledger input before a close."""
    path = target_repo / spec_root / "tickets" / ticket_id / "results" / "complexity_ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PASSING_COMPLEXITY_LEDGER, encoding="utf-8")
    return path

#: A fixture model with three state variables, used to establish a measurable
#: baseline so that a later one-variable model is a genuine DECREASE. Variable
#: count is one of the direction metrics, so this works without depending on
#: the analyzer inferring domain cardinality for a throwaway module.
#:
#: CM-01: these are COMPLETE modules that FIXTURE_CFG actually configures.
#: They used to be a single VARIABLES line dropped on top of a scaffolded
#: three-module baseline, leaving `MODULE Fixture` paired with the baseline's
#: External.cfg -- exactly the CM-F1 shape the ledger now refuses to measure
#: ("I could not measure this"). A fixture that only worked because nothing
#: checked the pair is not a fixture worth keeping.
def _fixture_model(variables: str) -> str:
    names = [name.strip() for name in variables.split(",")]
    vars_tuple = "<< " + ", ".join(names) + " >>"
    init = " /\\ ".join(f"{name} = 0" for name in names)
    return (
        "---- MODULE Fixture ----\n"
        f"VARIABLES {variables}\n"
        f"vars == {vars_tuple}\n"
        f"Init == {init}\n"
        "Next == UNCHANGED vars\n"
        "Spec == Init /\\ [][Next]_vars\n"
        "====\n"
    )


BASELINE_FIXTURE_MODEL = _fixture_model("a, b, c")
SHRUNK_FIXTURE_MODEL = _fixture_model("a")
FIXTURE_CFG = "SPECIFICATION Spec\n"
#: CM-01: the measured model is declared, not discovered. Without this the
#: ledger would pick the outermost view of the scaffolded baseline and find the
#: fixture module under a name that does not match its cfg.
FIXTURE_MODEL_DECLARATION = "\nmodel:\n  tla: External.tla\n  cfg: MC.cfg\n"


def set_ticket_model(target_repo: Path, spec_root: str, ticket_id: str, text: str) -> None:
    """Write a fixture model into BOTH ticket trees, with a cfg that configures it.

    Both trees, because ticket current and desired must stay equal -- otherwise
    the close is refused by the equality gate and a test asserting on the
    ledger's refusal would be asserting against the wrong one.
    """
    for tree in ("current", "desired"):
        model_dir = target_repo / spec_root / "tickets" / ticket_id / tree
        for tla in model_dir.glob("*.tla"):
            if not tla.name.startswith("MC"):
                tla.write_text(text, encoding="utf-8")
        (model_dir / "MC.cfg").write_text(FIXTURE_CFG, encoding="utf-8")
        manifest = model_dir / "spec_manifest.yaml"
        if manifest.is_file():
            current = manifest.read_text(encoding="utf-8")
            if "\nmodel:\n" not in current:
                manifest.write_text(current + FIXTURE_MODEL_DECLARATION, encoding="utf-8")



class OpenTicketAdapter:
    action_name = "OpenTicket"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-124",
        title: str = "CLI ticket lifecycle",
    ) -> dict[str, object]:
        root = repo_root()
        setup = prepare_ticket_workflow(root, target_repo, spec_root=spec_root, ticket_id=ticket_id, title=title)
        result = run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket_id)
        ticket_dir = target_repo / spec_root / "tickets" / ticket_id
        return {
            "accepted": all(record.returncode == 0 for record in setup)
            and result.returncode == 0
            and (ticket_dir / "desired" / "Internal.tla").is_file()
            and (ticket_dir / "current" / "Internal.tla").is_file()
            and "Edit" in result.stdout
            and "desired" in result.stdout,
            "setup_exit_codes": [record.returncode for record in setup],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "ticket_dir": str(ticket_dir),
        }

    # MF-032: MODERATE band (MF-028 report section 4). OpenTicket is the first
    # adapter whose transition advances `ticket_state` rather than `setup_phase`,
    # so it reuses MF-031's ticket-segment projection. MF-028 banded it moderate
    # and "parameterized -> hit by the params={} finding"; the ticket argument is
    # recovered the same way UpdateTicket does it -- MF-029 except-index over the
    # single ticket_state entry that changed -- never read out of case.after.
    #
    # Before-state: a scaffolded workflow (setup_phase 5) with the target ticket
    # Unopened. `materialize_before` builds exactly that; `run()` then drives the
    # real `open ticket` CLI command and projects ticket_state back from the
    # filesystem.
    def can_run(self, case: object) -> tuple[bool, str | None]:
        action = getattr(case, "input").action
        if action != self.action_name:
            return False, f"case action {action} is not {self.action_name}"
        try:
            ticket = recover_ticket_except_index(case)
        except BeforeStateUnreachable as exc:
            return False, str(exc)
        before = dict(getattr(case, "before"))
        if int(before["setup_phase"]) < 5:
            return False, "OpenTicket is enabled only with a scaffolded workflow (setup_phase >= 5)"
        before_stage = int(dict(before.get("ticket_state") or {}).get(ticket, TICKET_UNOPENED))
        if before_stage != TICKET_UNOPENED:
            return False, (
                f"OpenTicket is enabled only when the ticket is Unopened; "
                f"before-state has {ticket} at {before_stage}"
            )
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)
        root = repo_root()

        # MF-029: recover the ticket argument from the state pair, never from an
        # out-of-band value the corpus does not carry.
        ticket = recover_ticket_except_index(case)

        # Perform the modelled transition: the real `open ticket` CLI command.
        plan_path = target_repo / spec_root / "desired_program_model" / "ticket_plan.yaml"
        _ensure_ticket_in_plan(plan_path, ticket)
        opened = run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket)
        if opened.returncode != 0:
            raise BeforeStateUnreachable(f"open ticket {ticket} failed: {opened.stderr[-600:]}")

        projected = project_state(
            target_repo,
            spec_root,
            prior=dict(getattr(case, "before")),
            last_command="tla-spec-dev open ticket",
            accepted=(opened.returncode == 0),
        )
        # OBSERVE ticket_state from the filesystem for every ticket the case
        # names -- the CHANGED variable is never carried from the before-state.
        ticket_tokens = sorted(
            set(dict(getattr(case, "before").get("ticket_state") or {}))
            | set(dict(getattr(case, "after").get("ticket_state") or {}))
        )
        projected["ticket_state"] = project_ticket_state(target_repo, spec_root, ticket_tokens)

        comparison = compare_projection(case=case, projected=projected)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "ticket": ticket,
                "replay": replay,
                "projected": projected,
                "comparison": comparison,
            },
        }


# MF-031 FINDING -- the CloseTicket label collision is a BINDING-MODEL
# LIMITATION, not an adapter defect (evidence: results/closeticket-collision.txt).
# Four classes below share action_name = "CloseTicket": CloseTicketAdapter,
# ClosePromotionPreservesCurrentAdapter, SkillFeedbackCloseOutAdapter, and
# ComplexityLedgerCloseOutAdapter. The runner binds one adapter per label
# (adapter_for_case returns a single mapping; the toml is keyed by label), so at
# most one of the four is ever reachable from the corpus -- no run() they grow
# changes that. And that is the correct outcome: the other three are multi-close
# CONFORMANCE BATTERIES (SkillFeedback drives 3 closes, ComplexityLedger 5) that
# assert accumulation/gating across several closes, not one transition, so they
# cannot be single-case executors even in principle. They are correct exactly as
# the spec-unit apply() tests they already are. Separately, the canonical
# CloseTicketAdapter's own before-state needs a ticket at
# ticket_state=SpecUnitTestsPassed(4), which requires the spec-unit/close gate
# machinery MF-031 refuses as out-of-segment -- so making CloseTicket
# case-executable is gated on that surface (MF-023), not resolvable here.
class CloseTicketAdapter:
    action_name = "CloseTicket"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-125",
        title: str = "CLI close ticket lifecycle",
    ) -> dict[str, object]:
        root = repo_root()
        setup = prepare_ticket_workflow(root, target_repo, spec_root=spec_root, ticket_id=ticket_id, title=title)
        opened = run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket_id)
        plan_path = target_repo / spec_root / "desired_program_model" / "ticket_plan.yaml"
        if plan_path.exists():
            plan_path.write_text(plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1), encoding="utf-8")
        fill_complexity_ledger(target_repo, spec_root, ticket_id)
        result = run_cli(
            root,
            target_repo,
            "--spec-root",
            spec_root,
            "close",
            "ticket",
            ticket_id,
            "--summary",
            "closed from ticket lifecycle adapter",
        )
        ticket_dir = target_repo / spec_root / "tickets" / ticket_id
        history_dir = target_repo / spec_root / ".history" / "desired-ticket-workflow" / f"ticket-000-{ticket_id}"
        return {
            "accepted": all(record.returncode == 0 for record in setup)
            and opened.returncode == 0
            and result.returncode == 0
            and not ticket_dir.exists()
            and (history_dir / "manifest.json").is_file()
            and (target_repo / spec_root / "current" / "Internal.tla").is_file(),
            "setup_exit_codes": [record.returncode for record in setup],
            "open_exit_code": opened.returncode,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "history_dir": str(history_dir),
        }


class ClosePromotionPreservesCurrentAdapter:
    """MF-021: drive the shipped CLI and prove promotion does not destroy specs/current.

    Runs the real ``scaffold -> open ticket -> close ticket`` lifecycle against
    a throwaway repository. Between ``open`` and ``close`` it writes two kinds
    of path into project ``specs/current``:

    * ``unseeded_only.py`` -- created after the workspace was seeded, and
      ``probe-dir/note.txt`` inside a current-only directory. Neither was ever
      offered to the ticket, so promotion must preserve both. This is the exact
      shape of the loss that destroyed MF-012's budgets retention test and
      MF-020's ``refinement-probe/`` directory.
    * the project workflow test, which ``open ticket`` excludes from the ticket
      workspace by design and which promotion therefore must never delete.

    It also asserts the close output *enumerates* what it preserved: a silent
    survival would still leave the next regression undetectable.
    """

    action_name = "CloseTicket"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-127",
        title: str = "CLI close promotion preserves current",
    ) -> dict[str, object]:
        root = repo_root()
        setup = prepare_ticket_workflow(root, target_repo, spec_root=spec_root, ticket_id=ticket_id, title=title)
        opened = run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket_id)

        specs_current = target_repo / spec_root / "current"
        unseeded = specs_current / "unseeded_only.py"
        unseeded.write_text("MUST_SURVIVE_PROMOTION = True\n", encoding="utf-8")
        probe = specs_current / "probe-dir" / "note.txt"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("current-only directory\n", encoding="utf-8")
        workflow_test = specs_current / "tests" / "test_current_ticket_workflow.py"
        workflow_test_existed = workflow_test.is_file()

        plan_path = target_repo / spec_root / "desired_program_model" / "ticket_plan.yaml"
        if plan_path.exists():
            plan_path.write_text(plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1), encoding="utf-8")
        fill_complexity_ledger(target_repo, spec_root, ticket_id)
        result = run_cli(
            root,
            target_repo,
            "--spec-root",
            spec_root,
            "close",
            "ticket",
            ticket_id,
            "--summary",
            "closed from promotion-preservation adapter",
        )

        survived = unseeded.is_file() and probe.is_file()
        workflow_test_survived = (not workflow_test_existed) or workflow_test.is_file()
        enumerated = "unseeded_only.py" in result.stdout and "preserved" in result.stdout

        return {
            "accepted": all(record.returncode == 0 for record in setup)
            and opened.returncode == 0
            and result.returncode == 0
            and survived
            and workflow_test_survived
            and enumerated,
            "setup_exit_codes": [record.returncode for record in setup],
            "open_exit_code": opened.returncode,
            "exit_code": result.returncode,
            "current_only_file_survived": unseeded.is_file(),
            "current_only_directory_survived": probe.is_file(),
            "project_workflow_test_seeded": workflow_test_existed,
            "project_workflow_test_survived": workflow_test_survived,
            "preservation_enumerated_in_output": enumerated,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


class SkillFeedbackCloseOutAdapter:
    """MF-017: drive the shipped CLI and prove close-out runs the Phase 6 retro.

    Closes a fixture workflow twice against a throwaway repository and asserts:

    * the first close emits ``<spec-root>/results/skill_feedback.md`` carrying
      all four prompt sections and the instruction to file each item as a
      ticket or PR against spec-double-compiler;
    * the history manifest records the filing status -- ``feedback_filed``
      false while the retro is unreviewed;
    * a finding filled in between the two closes survives the second close
      (the document accumulates; it is never regenerated over real content),
      while the second history entry remains unresolved until its own newest
      close-out block is reviewed.
    """

    action_name = "CloseTicket"

    #: A real finding from this epic (GitHub #22): ticket-close promotion
    #: destroyed regression tests unique to specs/current.
    FINDING = (
        "\n### SF-001 — ticket-close promotion destroyed files unique to specs/current\n"
        "- category: profile-schema-cli\n"
        "- target: scripts/spec_evolution.py::replace_tree\n"
        "- observed_on: tla-spec-dev @ MF-012, MF-020, MF-021\n"
        "- evidence: tests/test_promotion_preserves_current.py\n"
        "- severity: silent-data-loss\n"
        "- root_cause: tool\n"
        "- surface: tla-spec-dev close ticket\n"
        "- forced_workaround: restore deleted regression tests from git history\n"
        "- data_loss: yes\n"
        "- recommendation: ticket https://github.com/haydenrear/tla-spec-dev/issues/22\n"
        "- status: filed\n"
    )

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-129",
        title: str = "CLI close-out skill feedback",
    ) -> dict[str, object]:
        import json

        root = repo_root()
        setup = prepare_ticket_workflow(root, target_repo, spec_root=spec_root, ticket_id=ticket_id, title=title)
        plan_path = target_repo / spec_root / "desired_program_model" / "ticket_plan.yaml"

        def close(ticket: str) -> object:
            run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket)
            if plan_path.exists():
                plan_path.write_text(
                    plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1),
                    encoding="utf-8",
                )
            fill_complexity_ledger(target_repo, spec_root, ticket)
            return run_cli(
                root, target_repo, "--spec-root", spec_root,
                "close", "ticket", ticket, "--summary", "closed from skill-feedback adapter",
            )

        first = close(ticket_id)

        feedback = target_repo / spec_root / "results" / "skill_feedback.md"
        emitted = feedback.is_file()
        text = feedback.read_text(encoding="utf-8") if emitted else ""
        sections = ["surviving-mutants", "unmodelable-effects", "budget-and-metric", "profile-schema-cli"]
        has_sections = all(section in text for section in sections)
        instructs_filing = "spec-double-compiler" in text and "ticket or PR" in text

        history_root = target_repo / spec_root / ".history" / "desired-ticket-workflow"
        first_manifest_path = history_root / f"ticket-000-{ticket_id}" / "manifest.json"
        first_manifest = json.loads(first_manifest_path.read_text(encoding="utf-8")) if first_manifest_path.is_file() else {}

        # A second close proves the document accumulates rather than being
        # regenerated, so the fixture plan needs a second ticket entry.
        second_ticket = f"{ticket_id}-B"
        if plan_path.exists():
            plan_path.write_text(
                plan_path.read_text(encoding="utf-8")
                + f'  - id: {second_ticket}\n    title: "second close"\n    status: next\n    depends_on: []\n',
                encoding="utf-8",
            )

        # Fill in a real finding, then close that second ticket.
        if emitted:
            feedback.write_text(
                text.replace("- feedback_status: unreviewed", "- feedback_status: items-recorded", 1) + self.FINDING,
                encoding="utf-8",
            )
        second = close(second_ticket)

        after = feedback.read_text(encoding="utf-8") if feedback.is_file() else ""
        finding_survived = "SF-001" in after and "issues/22" in after
        second_manifest_path = history_root / f"ticket-000-{second_ticket}" / "manifest.json"
        if not second_manifest_path.is_file():
            candidates = sorted(history_root.glob(f"ticket-*-{second_ticket}/manifest.json"))
            second_manifest_path = candidates[0] if candidates else second_manifest_path
        second_manifest = json.loads(second_manifest_path.read_text(encoding="utf-8")) if second_manifest_path.is_file() else {}

        first_filed = first_manifest.get("feedback_filed")
        second_filed = second_manifest.get("feedback_filed")
        filed_where = second_manifest.get("feedback_filed_where", [])

        return {
            "accepted": all(record.returncode == 0 for record in setup)
            and first.returncode == 0
            and second.returncode == 0
            and emitted
            and has_sections
            and instructs_filing
            and first_filed is False
            and finding_survived
            and second_filed is False
            and filed_where == [],
            "setup_exit_codes": [record.returncode for record in setup],
            "exit_code": first.returncode,
            "second_exit_code": second.returncode,
            "template_emitted": emitted,
            "feedback_path": str(feedback),
            "prompt_sections_present": has_sections,
            "instructs_filing_against_skill_repo": instructs_filing,
            "first_close_feedback_filed": first_filed,
            "finding_survived_second_close": finding_survived,
            "second_close_feedback_filed": second_filed,
            "feedback_filed_where": filed_where,
            "stdout": first.stdout,
            "second_stdout": second.stdout,
            "stderr": first.stderr,
        }


class RunSpecUnitTestsAdapter:
    action_name = "RunSpecUnitTests"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-126",
        title: str = "CLI run spec-unit tests",
    ) -> dict[str, object]:
        root = repo_root()
        setup = prepare_ticket_workflow(root, target_repo, spec_root=spec_root, ticket_id=ticket_id, title=title)
        opened = run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket_id)
        ticket_current = target_repo / spec_root / "tickets" / ticket_id / "current"
        test_path = ticket_current / "tests" / "test_spec_unit_cli.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text("def test_spec_unit_cli():\n    assert True\n", encoding="utf-8")
        result = run_cli(root, target_repo, "--spec-root", spec_root, "run", "spec-unit-tests")
        return {
            "accepted": all(record.returncode == 0 for record in setup)
            and opened.returncode == 0
            and result.returncode == 0
            and str(ticket_current) in result.stdout
            and "spec-unit validation passed" in result.stdout,
            "setup_exit_codes": [record.returncode for record in setup],
            "open_exit_code": opened.returncode,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "ticket_current": str(ticket_current),
        }


class TestGraphCliAdapter:
    action_name = "ValidateTestGraphCli"

    def apply(self) -> dict[str, object]:
        root = repo_root()
        build = root / "test_graph" / "build.gradle.kts"
        readme = root / "test_graph" / "README.md"
        required_sources = [
            root / "test_graph" / "sources" / "tla_spec_dev_cli_install.py",
            root / "test_graph" / "sources" / "spec_workflow_create_repo.py",
            root / "test_graph" / "sources" / "spec_workflow_start_ticket.py",
            root / "test_graph" / "sources" / "spec_workflow_complete_ticket.py",
            root / "test_graph" / "sources" / "spec_workflow_spec_units.py",
            root / "test_graph" / "sources" / "spec_workflow_close_ticket.py",
            root / "test_graph" / "sources" / "spec_workflow_failure_cleanup_probe.py",
            root / "test_graph" / "sources" / "spec_workflow_cleanup.py",
        ]
        build_text = build.read_text(encoding="utf-8") if build.exists() else ""
        readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""
        required_fragments = [
            "testGraph(\"specWorkflow\")",
            "sources/tla_spec_dev_cli_install.py",
            "sources/spec_workflow_start_ticket.py",
            "sources/spec_workflow_spec_units.py",
            "sources/spec_workflow_close_ticket.py",
            "sources/spec_workflow_failure_cleanup_probe.py",
            "sources/spec_workflow_cleanup.py",
        ]
        return {
            "accepted": all(path.is_file() for path in required_sources)
            and all(fragment in build_text for fragment in required_fragments)
            and "tla-spec-dev --spec-root specs run spec-unit-tests" in readme_text
            and "cleanup after both passing and failing" in readme_text,
            "build": str(build),
            "readme": str(readme),
            "required_sources": [str(path) for path in required_sources],
            "missing_sources": [str(path) for path in required_sources if not path.is_file()],
        }


class RecordBudgetsAdapter:
    """Scaffolding establishes per-program budgets before any generation action.

    Runs the real scaffold into a temp dir and asserts the emitted manifest
    carries the budgets block with the documented defaults, and that the
    scaffold output instructs the agent to negotiate them with the user.
    """

    action_name = "RecordBudgets"

    def apply(self, target_repo: Path, *, spec_root: str = "specs", name: str = "BudgetProg") -> dict[str, object]:
        root = repo_root()
        sys.path.insert(0, str(root / "skills" / "spec-double-2"))
        from scripts.budgets import DEFAULT_BUDGETS, load_budgets

        result = subprocess.run(
            [
                sys.executable,
                str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                "--spec-root",
                spec_root,
                "scaffold",
                "project",
                "--name",
                name,
            ],
            cwd=target_repo,
            text=True,
            capture_output=True,
            check=False,
        )

        manifest = Path(target_repo) / spec_root / "program_model" / "spec_manifest.yaml"
        manifest_text = manifest.read_text() if manifest.is_file() else ""
        recorded = load_budgets(manifest, warn=False) if manifest.is_file() else {}
        stdout = result.stdout

        prompt_phrases = (
            "Propose these defaults to the user",
            "Ask which to adjust for this program",
            "one-line rationale",
        )

        return {
            "accepted": (
                result.returncode == 0
                and "budgets:" in manifest_text
                and recorded == DEFAULT_BUDGETS
                and all(phrase in stdout for phrase in prompt_phrases)
            ),
            "exit_code": result.returncode,
            "budgets_block_emitted": "budgets:" in manifest_text,
            "budgets": recorded,
            "defaults_match": recorded == DEFAULT_BUDGETS,
            "prompts_user": all(phrase in stdout for phrase in prompt_phrases),
            "manifest": str(manifest),
            "stderr": result.stderr,
        }

    # MF-032: MODERATE band (MF-028 report section 4). RecordBudgets is the
    # transition with NO corresponding CLI command: the shipped CLI emits the
    # budgets block as part of `scaffold project` and expects the agent to
    # negotiate the values, so replaying the transition is an in-place manifest
    # edit (`_negotiate_budgets`), not a command. `apply()` above -- which
    # re-scaffolds a project to assert the emitted defaults -- stays the
    # spec-unit surface; `run()` performs only the one modelled transition.
    #
    # Before-state setup_phase=3 (a scaffolded project without negotiated
    # budgets) is replayed by `materialize_before`. The action sets
    # `source: negotiated` in the manifest; `project_state` reads that marker
    # back as setup_phase=4, so the changed variable is OBSERVED, not copied.
    def can_run(self, case: object) -> tuple[bool, str | None]:
        if getattr(case, "input").action != self.action_name:
            return False, f"case action {getattr(case, 'input').action} is not {self.action_name}"
        if int(dict(getattr(case, "before"))["setup_phase"]) != 3:
            return False, "RecordBudgets is enabled only at setup_phase = 3"
        return True, None

    def run(self, case: object, work_dir: Path | None = None):
        work_dir = Path(work_dir or Path.cwd())
        target_repo, spec_root, replay = materialize_before(case, work_dir)
        # The modelled transition: mark the scaffolded budgets block negotiated.
        # This is the shared helper `materialize_before` itself uses to replay
        # the RecordBudgets prefix, so the transition and its replay agree.
        negotiate = _negotiate_budgets(target_repo, spec_root)
        projected = project_state(
            target_repo,
            spec_root,
            prior=dict(getattr(case, "before")),
            last_command="RecordBudgets",
            accepted=(negotiate.returncode == 0),
        )
        # setup_phase=4 is recovered from the "source: negotiated" marker the
        # transition just wrote -- never from case.after.
        comparison = compare_projection(case=case, projected=projected)
        enforce_projection(case, comparison)
        return {
            "output": None,
            "after": None,  # reported through semantic_output; see enforce_projection
            "semantic_output": {
                "case": getattr(case, "name"),
                "adapter": type(self).__name__,
                "replay": replay,
                "projected": projected,
                "comparison": comparison,
            },
        }


UNDER_BUDGET_TLA = """---------------------------- MODULE UnderBudget ----------------------------
EXTENDS Naturals

CONSTANTS Slots

VARIABLES armed, fired

vars == << armed, fired >>

Init ==
  /\\ armed = FALSE
  /\\ fired = FALSE

Arm ==
  /\\ ~armed
  /\\ armed' = TRUE
  /\\ UNCHANGED << fired >>

Fire ==
  /\\ armed
  /\\ ~fired
  /\\ fired' = TRUE
  /\\ UNCHANGED << armed >>

Next == Arm \\/ Fire

TypeInvariant ==
  /\\ armed \\in BOOLEAN
  /\\ fired \\in BOOLEAN

Spec == Init /\\ [][Next]_vars
=============================================================================
"""

UNDER_BUDGET_CFG = """SPECIFICATION Spec

CONSTANTS
  Slots = {s1, s2}

INVARIANTS
  TypeInvariant
"""

OVER_BUDGET_TLA = """---------------------------- MODULE OverBudget ----------------------------
EXTENDS Naturals

CONSTANTS Nodes

VARIABLES a, b, c, d

vars == << a, b, c, d >>

Init ==
  /\\ a = [n \\in Nodes |-> 0]
  /\\ b = [n \\in Nodes |-> 0]
  /\\ c = {}
  /\\ d = {}

BumpA ==
  /\\ \\E n \\in Nodes: a' = [a EXCEPT ![n] = 1]
  /\\ UNCHANGED << b, c, d >>

BumpB ==
  /\\ \\E n \\in Nodes: b' = [b EXCEPT ![n] = 1]
  /\\ UNCHANGED << a, c, d >>

AddC ==
  /\\ \\E n \\in Nodes: c' = c \\cup {n}
  /\\ UNCHANGED << a, b, d >>

AddD ==
  /\\ \\E n \\in Nodes: d' = d \\cup {n}
  /\\ UNCHANGED << a, b, c >>

Next == BumpA \\/ BumpB \\/ AddC \\/ AddD

TypeInvariant ==
  /\\ a \\in [Nodes -> 0..9]
  /\\ b \\in [Nodes -> 0..9]
  /\\ c \\subseteq Nodes
  /\\ d \\subseteq Nodes

Spec == Init /\\ [][Next]_vars
=============================================================================
"""

OVER_BUDGET_CFG = """SPECIFICATION Spec

CONSTANTS
  Nodes = {n1, n2, n3, n4, n5, n6}

INVARIANTS
  TypeInvariant
"""

BUDGET_MANIFEST = """module: Fixture
budgets:
  max_distinct_states: 50000
  max_component_variables: 6
  max_component_actions: 8
"""

# Deliberately unmeetable budgets applied to the *small* fixture. This is how
# the generation refusal and its override are exercised: the gate must fail,
# but TLC must still finish instantly when the override lets it through. Using
# the genuinely huge OverBudget fixture here would hang forever -- which is
# precisely the failure this command exists to prevent.
TIGHT_MANIFEST = """module: Fixture
budgets:
  max_distinct_states: 2
  max_component_variables: 1
  max_component_actions: 1
"""


def _write_fixture(
    directory: Path, module: str, tla: str, cfg: str, manifest: str = BUDGET_MANIFEST
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    tla_path = directory / f"{module}.tla"
    cfg_path = directory / "MC.cfg"
    tla_path.write_text(tla, encoding="utf-8")
    cfg_path.write_text(cfg, encoding="utf-8")
    (directory / "spec_manifest.yaml").write_text(manifest, encoding="utf-8")
    return tla_path, cfg_path


class AnalyzeComplexityAdapter:
    """`tla-spec-dev analyze complexity` DESCRIBES a model against its thresholds.

    MF-036: complexity is a scanner, not a gate
    (references/architecture_tractability.md, "Advisory, Not Blocking").
    CD-01: it is a DESCRIPTOR -- facts, not judgment -- and emits no suggested
    move and no recommendations. Runs the REAL command against two fixture
    specs -- one comfortably under threshold, one far over it -- and asserts
    the descriptor output, that BOTH sides exit 0 (a complex model is a
    finding, not a failure), that the over-threshold side emits a WARNING that
    states the fact, and that case generation ADVISES but never refuses.

    The over-threshold fixture is 6 nodes x two 0..9 functions x two powersets:
    10^6 * 10^6 * 2^6 * 2^6, far above the default threshold. It produces a
    warning-bearing REPORT (exit 0), never a promotion failure.
    """

    action_name = "AnalyzeComplexity"

    def apply(self, target_repo: Path, *, spec_root: str = "specs") -> dict[str, object]:
        root = repo_root()
        target_repo = Path(target_repo)

        under_tla, under_cfg = _write_fixture(
            target_repo / "under", "UnderBudget", UNDER_BUDGET_TLA, UNDER_BUDGET_CFG
        )
        over_tla, over_cfg = _write_fixture(
            target_repo / "over", "OverBudget", OVER_BUDGET_TLA, OVER_BUDGET_CFG
        )

        def cli(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                 "--spec-root", spec_root, "analyze", "complexity", *args],
                cwd=target_repo, text=True, capture_output=True, check=False,
            )

        under = cli(str(under_tla), str(under_cfg))
        over = cli(str(over_tla), str(over_cfg))

        # Case generation must ADVISE above the threshold and proceed anyway --
        # never refuse. Exercised against a SMALL model carrying unmeetable
        # thresholds, so the advisory path is reached but generation completes.
        tight_tla, tight_cfg = _write_fixture(
            target_repo / "tight", "UnderBudget", UNDER_BUDGET_TLA, UNDER_BUDGET_CFG,
            manifest=TIGHT_MANIFEST,
        )

        def generate(*extra: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(root / "skills" / "spec-double-2" / "scripts" / "generate_cases_from_tlc_dump.py"),
                 # RC-02 (MF-026 round-3 N-2): `generate cases` refuses an --out that
                 # resolves outside a `specs/` directory -- the tree spec_tree and
                 # spec_tree_delete declare, and the tree the metadir rmtree is
                 # derived from. This probe is about the ADVISORY complexity path,
                 # so it writes where the declaration says it may.
                 str(tight_tla), str(tight_cfg), "--out",
                 str(target_repo / "specs" / "generated"), *extra],
                cwd=target_repo, text=True, capture_output=True, check=False,
                timeout=180,
            )

        advised = generate()

        table_phrases = ("Dimension table", "State-space upper bound",
                         "read/write matrix", "Dense rows and columns",
                         "Invariant coverage")
        under_has_table = all(phrase in under.stdout for phrase in table_phrases)
        # CD-01: the descriptor makes NO suggestions -- no suggested move, no
        # recommendations, no projected gains, on either side.
        no_suggestions = not any(
            banned in stream
            for stream in (under.stdout, over.stdout)
            for banned in ("SUGGESTED MOVE", "RECOMMENDATION", "recommendation:",
                           "[PROJECTED]")
        )
        measured_facts_only = "[MEASURED]" in under.stdout
        over_names_dimensions = "dominant dimensions" in over.stdout.lower()
        # The over-threshold model produces a warning-bearing REPORT, not a
        # failure: a WARNING that names the target and states the fact.
        over_warns_with_facts = (
            "WARNING:" in over.stdout and "recommendation:" not in over.stdout
        )

        # Generation advises (prints the warnings) and proceeds -- it never
        # refuses, and there is no over-budget override flag to honor.
        advisory_ok = (
            "ADVISORY WARNINGS" in advised.stderr
            and "Proceeding with case generation" in advised.stderr
            and "REFUSING to generate cases" not in advised.stderr
        )

        return {
            "accepted": (
                under.returncode == 0
                and over.returncode == 0
                and under_has_table
                and no_suggestions
                and measured_facts_only
                and over_names_dimensions
                and over_warns_with_facts
                and advisory_ok
            ),
            "under_budget_exit_code": under.returncode,
            "over_budget_exit_code": over.returncode,
            "prints_dimension_table": under_has_table,
            "descriptor_makes_no_suggestions": no_suggestions,
            "reports_measured_facts": measured_facts_only,
            "over_budget_names_dominant_dimensions": over_names_dimensions,
            "over_budget_warns_with_facts": over_warns_with_facts,
            "generation_advises_not_refused": advisory_ok,
            "stderr": under.stderr + over.stderr,
        }


# --------------------------------------------------------------------------
# REMOVED 2026-08-04 (owner direction): AnalyzeArchitectureAdapter, and the two
# fixture models (ArchCut, ArchBlob) it ran `tla-spec-dev analyze architecture`
# against. The command is gone; an adapter for an action the model no longer
# declares is dead surface of exactly the kind the effect oracle exists to
# report. See the tombstone in TlaSpecDevCli.tla and
# references/architecture_advice.md.
#
# One thing the adapter checked survives the removal and is now a written rule
# rather than an executed one: the blob fixture asserted that a model which
# does not decompose is reported as NOT MEASURABLE rather than as a
# one-component partition with zero violations. "Refuse rather than certify
# what you could not see" is the single doctrine that came through this epic
# intact, and it is the first requirement any replacement must meet.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# MF-014: corpus diagnostics and hard case caps
# --------------------------------------------------------------------------

CORPUS_FIXTURE_CASES = '''
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StateGraphInput:
    action: str
    source_node: str
    target_node: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StateGraphCase:
    name: str
    before: dict
    input: StateGraphInput
    output: Any
    after: dict
    labels: frozenset
    view: str = "external"
    layer: str = "external"


SOURCE_MODULE = "Fixture"
SOURCE_VIEW = "external"

CASES = [
    StateGraphCase(
        name="case_%04d_SubmitDuplicate" % i,
        before={"n": i % 7, "seen": True},
        input=StateGraphInput("SubmitDuplicate", str(1000 + i), str(2000 + i), {"client": "c%d" % i}),
        output={},
        after={"n": i % 7, "seen": True},
        labels=frozenset({"SubmitDuplicate", "duplicate_submission"}),
    )
    for i in range(__COUNT__)
] + [
    StateGraphCase(
        name="case_regression_promoted",
        before={"n": 0},
        input=StateGraphInput("SubmitOnce", "1", "2", {}),
        output={},
        after={"n": 1},
        labels=frozenset({"SubmitOnce", "regression:issue-41"}),
    )
]

CASES_BY_NAME = {c.name: c for c in CASES}
'''


def _write_corpus_fixture(target: Path, count: int, cap: int) -> tuple[Path, Path]:
    """A generated-package-shaped corpus with `count` cases of one action."""
    package = target / "generated" / "fixture_cases"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(
        "from .cases import CASES, CASES_BY_NAME, SOURCE_MODULE, SOURCE_VIEW\n", encoding="utf-8"
    )
    (package / "cases.py").write_text(
        CORPUS_FIXTURE_CASES.replace("__COUNT__", str(count)), encoding="utf-8"
    )
    manifest = target / "spec_manifest.yaml"
    manifest.write_text(
        f"module: Fixture\nbudgets:\n  max_external_cases_per_action: {cap}\n", encoding="utf-8"
    )
    return package, manifest


class AnalyzeCorpusAdapter:
    """`tla-spec-dev analyze corpus` gates a generated corpus against its caps.

    Runs the REAL command on both sides of the cap and asserts the model's
    central claim: over cap it REPORTS AND REFUSES, and the corpus is exactly
    as large afterwards as it was before. Nothing is dropped, filtered,
    sampled, or truncated to fit the budget -- so the same fixture that fails
    at cap 50 passes unchanged at cap 500, with every case still present.
    """

    action_name = "AnalyzeCorpus"

    def apply(self, target_repo: Path, *, spec_root: str = "specs") -> dict[str, object]:
        root = repo_root()
        target_repo = Path(target_repo)

        over_pkg, over_manifest = _write_corpus_fixture(target_repo / "over", count=200, cap=50)
        under_pkg, under_manifest = _write_corpus_fixture(target_repo / "under", count=200, cap=500)

        def cli(pkg: Path, manifest: Path) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                 "--spec-root", spec_root, "analyze", "corpus", str(pkg),
                 "--view", "external", "--manifest", str(manifest)],
                cwd=target_repo, text=True, capture_output=True, check=False, timeout=180,
            )

        over = cli(over_pkg, over_manifest)
        under = cli(under_pkg, under_manifest)

        def case_count(pkg: Path) -> int:
            import re
            return len(re.findall(r"StateGraphCase\(", (pkg / "cases.py").read_text(encoding="utf-8")))

        # The same 201-case corpus, before and after a FAILING gate run.
        corpus_intact = case_count(over_pkg) == case_count(under_pkg)

        reports_distribution = "Distribution per (action, label class)" in over.stdout
        reports_dominant = "Strata that DOMINATE the corpus" in over.stdout
        reports_starved = "Strata that are STARVED" in over.stdout
        reports_variance = "What VARIES across the redundant group" in over.stdout
        names_cause = "Likely cause:" in over.stdout
        # CD-04 (resolves VAL-13): the over-cap output states the finding and
        # asks the redesign question -- naming the descriptor and the
        # intuition doc as judgment inputs -- and never prescribes a move.
        asks_redesign_question = (
            "REDESIGN QUESTION" in over.stdout
            and "analyze complexity" in over.stdout
            and "references/complexity_intuition.md" in over.stdout
            and "Suggested move" not in over.stdout
            and "SUGGESTED MOVE" not in over.stdout
            and "RECOMMENDATION REQUIRING USER APPROVAL" not in over.stdout
            and "Apply the suggested" not in over.stdout
        )
        accept_path = (
            "ACCEPT PATH" in over.stdout
            and "source: negotiated" in over.stdout
            and "rationale:" in over.stdout
        )
        never_trims = (
            "Nothing was" in over.stdout
            and "trimmed" in over.stdout
            and "dropped, filtered, sampled, or truncated" in over.stdout
        )
        regression_retained = (
            "Named regression traces (always retained)" in over.stdout
            and "Named regression traces (always retained)" in under.stdout
        )
        no_trim_offered = "--distill" not in over.stdout and "--trim" not in over.stdout

        return {
            "accepted": (
                over.returncode == 1
                and under.returncode == 0
                and corpus_intact
                and reports_distribution
                and reports_dominant
                and reports_starved
                and reports_variance
                and names_cause
                and asks_redesign_question
                and accept_path
                and never_trims
                and regression_retained
                and no_trim_offered
            ),
            "over_cap_exit_code": over.returncode,
            "raised_cap_exit_code": under.returncode,
            "corpus_unchanged_by_failing_gate": corpus_intact,
            "reports_count_per_action_and_label_class": reports_distribution,
            "reports_dominant_strata": reports_dominant,
            "reports_starved_strata": reports_starved,
            "reports_what_varies_across_redundant_group": reports_variance,
            "names_representation_cause": names_cause,
            "asks_redesign_question_never_prescribes": asks_redesign_question,
            "cap_raise_accept_path_offered": accept_path,
            "never_offers_to_trim": never_trims and no_trim_offered,
            "regression_traces_retained": regression_retained,
            "stdout": over.stdout,
            "stderr": over.stderr + under.stderr,
        }


class RunEffectConformanceAdapter:
    """`tla-spec-dev run effect-conformance` diffs observed vs declared effects.

    Runs the REAL command over three fixture spec directories and asserts the
    model's central claim: an undeclared observed effect FAILS, and NOTHING
    suppresses that failure.

    The load-bearing assertion is
    `justification_does_not_change_the_verdict`: two fixtures identical except
    that one carries a recorded justification produce byte-identical verdicts.
    That is the inverse test the 2026-07-18 degeneracy audit required -- there
    is deliberately no fixture proving suppression works, because out-of-
    contract justifications are withdrawn and suppression no longer exists.
    """

    action_name = "RunEffectConformance"

    _DECLARED = """module: Demo
effects:
  components:
    C:
      ports:
        workspace:
          type: filesystem.write
          target: "**/workspace/**"
  actions:
    Act: [workspace]
"""

    def apply(self, target_repo: Path, *, spec_root: str = "specs") -> dict[str, object]:
        root = repo_root()
        target_repo = Path(target_repo)

        def fixture(name: str, body: str) -> Path:
            spec_dir = target_repo / name
            spec_dir.mkdir(parents=True, exist_ok=True)
            (spec_dir / "spec_manifest.yaml").write_text(body, encoding="utf-8")
            return spec_dir

        plain = fixture("plain", self._DECLARED)
        justified = fixture(
            "justified",
            self._DECLARED + "  justification: 'accepted by review; ports are aspirational'\n",
        )
        undeclared = fixture("undeclared", "module: Demo\n")

        def cli(spec_dir: Path, out: Path) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                 "--spec-root", spec_root, "run", "effect-conformance",
                 "--target", str(spec_dir), "--out", str(out)],
                cwd=target_repo, text=True, capture_output=True, check=False, timeout=180,
            )

        plain_out = target_repo / "plain.json"
        justified_out = target_repo / "justified.json"
        plain_run = cli(plain, plain_out)
        justified_run = cli(justified, justified_out)
        undeclared_run = cli(undeclared, target_repo / "undeclared.json")

        plain_report = json.loads(plain_out.read_text(encoding="utf-8"))
        justified_report = json.loads(justified_out.read_text(encoding="utf-8"))

        # The inverse test: identical outcome with and without a justification.
        same_verdict = (
            plain_report["verdict"] == justified_report["verdict"]
            and plain_report["ok"] == justified_report["ok"] is False
            and plain_run.returncode == justified_run.returncode == 1
        )
        # ...and the ignored key is surfaced rather than silently dropped.
        suppression_reported = justified_report["ignored_suppression_keys"] == ["effects.justification"]
        policy_recorded = "withdrawn" in plain_report["suppression_policy"]

        return {
            "accepted": bool(
                same_verdict
                and suppression_reported
                and policy_recorded
                and undeclared_run.returncode == 2
            ),
            "findings_exit_code": plain_run.returncode,
            "justified_exit_code": justified_run.returncode,
            "no_declarations_exit_code": undeclared_run.returncode,
            "justification_does_not_change_the_verdict": same_verdict,
            "suppression_attempt_reported_not_honored": suppression_reported,
            "suppression_policy_recorded_in_report": policy_recorded,
            "report_written_as_evidence": plain_out.is_file() and justified_out.is_file(),
            "stdout": plain_run.stdout + justified_run.stdout,
            "stderr": plain_run.stderr + justified_run.stderr + undeclared_run.stderr,
        }


# CA-04 removed RunKillTestAdapter with the RunKillTest action it conformed to.
# It drove `scripts/run_kill_test.py` over fixture spec trees and asserted the
# gate's central claims (below_floor fails, an incomplete catalog exits 2, no
# waiver is honored). The finding is RM-03-DF-05. The whole conformance surface
# went with the action: this file, case_adapters.toml, and
# tests/test_tla_spec_dev_kill_test_adapter.py in each spec tree.


class ComplexityLedgerCloseOutAdapter:
    """MF-019: prove the standing objective is a GATE on the shipped close path.

    Drives the real CLI (`scaffold -> open ticket -> close ticket`) against a
    throwaway repository, four times, and asserts the close-time behavior that
    eleven tickets of this epic performed by hand:

    * a filled ledger input closes, and the history entry records the complexity
      delta JOINTLY with its retention evidence and the refinement record;
    * an UNFILLED scaffolded template refuses the close -- the standing
      objective is a required step, not an optional one;
    * a complexity DECREASE with DEGRADED validated-refactor evidence is
      REJECTED -- the anti-gaming rule on the amended basis (CD-09,
      owner-approved 2026-07-22: TLC before/after, behavior tests, descriptor
      comparison license a decrease);
    * a validated decrease with the fuzzing-era members honestly recorded as
      `not_run` IS recorded -- the members are experimental since the
      2026-07-21 pivot and no longer gate (CD-09).
    """

    action_name = "CloseTicket"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-140",
        title: str = "CLI complexity ledger close-out",
    ) -> dict[str, object]:
        import json

        root = repo_root()
        setup = prepare_ticket_workflow(root, target_repo, spec_root=spec_root, ticket_id=ticket_id, title=title)
        plan_path = target_repo / spec_root / "desired_program_model" / "ticket_plan.yaml"

        def open_ticket(ticket: str) -> Path:
            if ticket != ticket_id and plan_path.exists():
                plan_path.write_text(
                    plan_path.read_text(encoding="utf-8")
                    + f'  - id: {ticket}\n    title: "ledger case"\n    status: next\n    depends_on: []\n',
                    encoding="utf-8",
                )
            run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket)
            return target_repo / spec_root / "tickets" / ticket / "results" / "complexity_ledger.yaml"

        def close(ticket: str):
            if plan_path.exists():
                plan_path.write_text(
                    plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1),
                    encoding="utf-8",
                )
            return run_cli(
                root, target_repo, "--spec-root", spec_root,
                "close", "ticket", ticket, "--summary", "closed from complexity-ledger adapter",
            )

        # 1. Filled ledger input -> the close is recorded.
        ledger_input = open_ticket(ticket_id)
        template_scaffolded = ledger_input.is_file() and "TODO" in ledger_input.read_text(encoding="utf-8")
        set_ticket_model(target_repo, spec_root, ticket_id, BASELINE_FIXTURE_MODEL)
        fill_complexity_ledger(target_repo, spec_root, ticket_id)
        good = close(ticket_id)

        history_root = target_repo / spec_root / ".history" / "desired-ticket-workflow"
        manifest_path = history_root / f"ticket-000-{ticket_id}" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        ledger_file = target_repo / spec_root / "results" / "complexity_ledger.json"

        # 2. The scaffolded template, left unfilled, must REFUSE the close.
        unfilled_ticket = f"{ticket_id}-UNFILLED"
        open_ticket(unfilled_ticket)
        unfilled = close(unfilled_ticket)

        # 3. A decrease with DEGRADED validated-refactor evidence must be
        # REJECTED (CD-09: the basis that licenses a decrease is TLC
        # before/after + behavior tests + descriptor comparison).
        degraded_ticket = f"{ticket_id}-DEGRADED"
        degraded_input = open_ticket(degraded_ticket)
        degraded_input.write_text(
            PASSING_COMPLEXITY_LEDGER.replace('status: "recorded"', 'status: "stale"', 1),
            encoding="utf-8",
        )
        # Shrink the model so the delta is a genuine decrease. Both trees, so
        # the current==desired equality gate still passes and the refusal under
        # test is the ledger's, not an earlier gate's.
        set_ticket_model(target_repo, spec_root, degraded_ticket, SHRUNK_FIXTURE_MODEL)
        degraded = close(degraded_ticket)

        # 4. CD-09: a VALIDATED decrease with the fuzzing-era members honestly
        # recorded as `not_run` closes -- the amended basis licenses it, and
        # the non-gating members stay recorded in the entry.
        validated_ticket = f"{ticket_id}-VALIDATED"
        validated_input = open_ticket(validated_ticket)
        validated_input.write_text(NOT_RUN_FUZZING_LEDGER, encoding="utf-8")
        set_ticket_model(target_repo, spec_root, validated_ticket, SHRUNK_FIXTURE_MODEL)
        validated = close(validated_ticket)
        validated_entry: dict[str, object] = {}
        if ledger_file.is_file():
            entries = json.loads(ledger_file.read_text(encoding="utf-8")).get("entries", [])
            for candidate in entries:
                if candidate.get("scope_id") == validated_ticket:
                    validated_entry = candidate

        return {
            "accepted": all(record.returncode == 0 for record in setup)
            and good.returncode == 0
            and template_scaffolded
            and unfilled.returncode != 0
            and degraded.returncode != 0
            and validated.returncode == 0,
            # 1. recorded, jointly
            "close_recorded": good.returncode == 0,
            "ledger_file_written": ledger_file.is_file(),
            "delta_recorded": manifest.get("complexity_delta") is not None,
            "retention_recorded": manifest.get("retention_evidence") is not None,
            "refinement_recorded": (manifest.get("refinement_record") or {}).get("outcome"),
            "delta_and_retention_in_same_entry": bool(
                manifest.get("complexity_delta") is not None
                and manifest.get("retention_evidence") is not None
            ),
            # 2. the template is a gate, not a suggestion
            "template_scaffolded_with_sentinels": template_scaffolded,
            "unfilled_template_refuses_close": unfilled.returncode != 0,
            "unfilled_names_refinement_and_narrative": (
                "refinement" in unfilled.stdout + unfilled.stderr
                and "narrative" in unfilled.stdout + unfilled.stderr
            ),
            # 3. anti-gaming on the amended basis (CD-09)
            "degraded_decrease_rejected": degraded.returncode != 0,
            "degraded_message_says_rejected": "REJECTED" in degraded.stdout + degraded.stderr,
            "degraded_message_names_the_basis": "validated-refactor" in degraded.stdout + degraded.stderr,
            # 4. the amended licensing (CD-09)
            "validated_decrease_recorded": validated.returncode == 0,
            "validated_delta_direction": (
                (validated_entry.get("delta") or {}).get("direction")
                if isinstance(validated_entry.get("delta"), dict)
                else None
            ),
            "fuzzing_members_recorded_not_run": bool(validated_entry)
            and all(
                (validated_entry.get("retention") or {}).get(name, {}).get("status") == "not_run"
                for name in ("kill_rate", "effect_conformance", "external_coverage")
            ),
            "validated_refactor_recorded_in_entry": bool(
                validated_entry.get("validated_refactor")
            ),
            "stdout": good.stdout + unfilled.stdout + degraded.stdout + validated.stdout,
            "stderr": good.stderr + unfilled.stderr + degraded.stderr + validated.stderr,
        }


# --------------------------------------------------------------------------
# RC-01 (MF-026 G-6): case generation, and the weakened close
# --------------------------------------------------------------------------

# A two-action model small enough that TLC explores it in well under a second,
# so the generation adapter measures the CLI path rather than a state space.
GENERATE_CASES_TLA = """--------------------------- MODULE GenProbe ---------------------------
EXTENDS Naturals

VARIABLES counter, flag

vars == << counter, flag >>

Init == counter = 0 /\\ flag = FALSE

Bump == counter < 2 /\\ counter' = counter + 1 /\\ UNCHANGED flag
Flip == flag' = ~flag /\\ UNCHANGED counter

Next == Bump \\/ Flip

TypeInvariant == counter \\in 0..2 /\\ flag \\in BOOLEAN

Spec == Init /\\ [][Next]_vars
=============================================================================
"""

GENERATE_CASES_CFG = """SPECIFICATION Spec

INVARIANTS
  TypeInvariant
"""


class GenerateCasesAdapter:
    """`tla-spec-dev generate cases` GENERATES the corpus a view implies.

    RC-01, closing MF-026's headline gap. Until this ticket case-module
    generation had no CLI subcommand, no model action and no declared port:
    `scripts/generate_cases_from_tlc_dump.py` and `scripts/case_modules.py`
    were reachable only by running the files, so an import-closure walk of
    `build_parser` never saw the java/TLC spawn, the metadir `rmtree` or the
    package writes -- and CM-01 and RP-03 both closed "zero model delta"
    against surface the model did not contain.

    Checks the three things the model now claims. The command is reachable from
    the shipped parser; it performs the declared effects (a package on disk,
    a per-action coverage record beside it, and the parameter-recovery audit);
    and it records no verdict, matching `GenerateCases` leaving every gate
    variable UNCHANGED.

    NO SILENT PASS when TLC is absent (MF-027). The corpus_process port is a
    java spawn, and an adapter that reports success on a machine where the
    spawn never happened is exactly the "unobservable read as clean" defect the
    effect oracle was changed to stop producing -- so a missing `tlc2` is
    reported as its own outcome and `accepted` is False.
    """

    action_name = "GenerateCases"

    def apply(self, target_repo: Path, *, spec_root: str = "specs") -> dict[str, object]:
        root = repo_root()
        target_repo = Path(target_repo)
        # RC-02 (MF-026 round-3 N-2): the probe generates INSIDE a `specs/`
        # tree, because that is the tree `spec_tree` and `spec_tree_delete`
        # declare and `generate cases` now refuses anything outside it. The
        # fixture moved; the effects asserted below did not.
        spec_dir = target_repo / "specs" / "genprobe"
        tla_path, cfg_path = _write_fixture(
            spec_dir, "GenProbe", GENERATE_CASES_TLA, GENERATE_CASES_CFG
        )

        tlc2 = shutil.which("tlc2")
        if tlc2 is None:
            return {
                "accepted": False,
                "verdict": "unobservable",
                "reason": (
                    "tlc2 is not on PATH, so the corpus_process spawn this action "
                    "declares never happened. Reported rather than passed: an oracle "
                    "that cannot see the boundary has no evidence about it (MF-027)."
                ),
            }

        out_root = target_repo / "specs" / "generated"
        package = out_root / "genprobe_cases"
        coverage_json = package / "case_module_coverage.json"
        result = subprocess.run(
            [
                sys.executable,
                str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                "--spec-root",
                spec_root,
                "generate",
                "cases",
                str(tla_path),
                str(cfg_path),
                "--out",
                str(out_root),
                "--package",
                "genprobe_cases",
                "--coverage-json",
                str(coverage_json),
            ],
            cwd=target_repo,
            text=True,
            capture_output=True,
            check=False,
        )

        # The undeclared-destination refusal: `--coverage-json` outside the
        # generated package is the same undeclared-write shape G-2 closed on
        # `--out`, and it is refused rather than relocated.
        stray = subprocess.run(
            [
                sys.executable,
                str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"),
                "--spec-root",
                spec_root,
                "generate",
                "cases",
                str(tla_path),
                str(cfg_path),
                "--out",
                str(out_root),
                "--package",
                "genprobe_cases",
                "--coverage-json",
                str(target_repo / "elsewhere.json"),
            ],
            cwd=target_repo,
            text=True,
            capture_output=True,
            check=False,
        )

        metadirs = sorted(str(p) for p in out_root.rglob(".tlc-metadir")) if out_root.exists() else []
        return {
            "accepted": (
                result.returncode == 0
                and (package / "cases.py").is_file()
                and (package / "case_coverage.json").is_file()
                and (package / "param_recovery_audit.md").is_file()
                and coverage_json.is_file()
                and not metadirs
                and stray.returncode != 0
            ),
            "exit_code": result.returncode,
            "package_written": (package / "cases.py").is_file(),
            "coverage_record_written": (package / "case_coverage.json").is_file(),
            "param_audit_written": (package / "param_recovery_audit.md").is_file(),
            "coverage_report_written": coverage_json.is_file(),
            "metadir_removed": not metadirs,
            "stray_coverage_json_refused": stray.returncode != 0,
            "stdout": result.stdout,
            "stderr": result.stderr + stray.stderr,
        }


class CloseTicketWeakenedAdapter:
    """`close ticket` under a GUARD-WEAKENING FLAG is a different state.

    RC-01, owner decision 2026-08-01. `CloseTicket` guards on the ticket having
    reached `TicketSpecUnitTestsPassed`, and TLC proves
    `ClosedTicketsPassedSpecUnitTests` over the whole reachable state space --
    while `--accept-new` and `--allow-open` exist specifically to get past that
    precondition. No modeled state recorded their use and no oracle in this
    toolchain could see the difference, because the kill test seeds faults per
    declared port and per invariant, i.e. only inside modeled boundaries.

    Drives the REAL close twice against throwaway repositories -- once through
    the guard, once around it with `--allow-open` -- and asserts the append-only
    history entry distinguishes them, naming the flag and what it bypassed. The
    weakened close still SUCCEEDS: the flags ship and have legitimate uses, and
    an adapter asserting a refusal the CLI does not perform would be the same
    false assurance this ticket exists to remove.
    """

    action_name = "CloseTicketWeakened"

    def apply(
        self,
        target_repo: Path,
        *,
        spec_root: str = "specs",
        ticket_id: str = "CLI-901",
        title: str = "CLI weakened close",
    ) -> dict[str, object]:
        root = repo_root()
        target_repo = Path(target_repo)

        def close(repo: Path, *extra: str) -> tuple[subprocess.CompletedProcess, dict]:
            repo.mkdir(parents=True, exist_ok=True)
            setup = prepare_ticket_workflow(
                root, repo, spec_root=spec_root, ticket_id=ticket_id, title=title
            )
            assert all(record.returncode == 0 for record in setup)
            run_cli(root, repo, "--spec-root", spec_root, "open", "ticket", ticket_id)
            fill_complexity_ledger(repo, spec_root, ticket_id)
            plan_path = repo / spec_root / "desired_program_model" / "ticket_plan.yaml"
            if not extra and plan_path.exists():
                plan_path.write_text(
                    plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1),
                    encoding="utf-8",
                )
            record = run_cli(
                root,
                repo,
                "--spec-root",
                spec_root,
                "close",
                "ticket",
                ticket_id,
                "--summary",
                "weakened-close adapter",
                *extra,
            )
            manifest_path = (
                repo
                / spec_root
                / ".history"
                / "desired-ticket-workflow"
                / f"ticket-000-{ticket_id}"
                / "manifest.json"
            )
            manifest = (
                json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.is_file()
                else {}
            )
            return record, manifest

        guarded, guarded_manifest = close(target_repo / "guarded")
        # `--allow-open` closes a ticket the plan still calls open: the
        # precondition is not met and the close happens anyway.
        weakened, weakened_manifest = close(target_repo / "weakened", "--allow-open")

        guarded_record = guarded_manifest.get("guard_weakening") or {}
        weakened_record = weakened_manifest.get("guard_weakening") or {}
        return {
            "accepted": (
                guarded.returncode == 0
                and weakened.returncode == 0
                and guarded_record.get("weakened") is False
                and guarded_record.get("model_action") == "CloseTicket"
                and weakened_record.get("weakened") is True
                and weakened_record.get("model_action") == "CloseTicketWeakened"
                and weakened_record.get("flags") == ["--allow-open"]
                and bool(weakened_record.get("bypassed"))
            ),
            "guarded_exit_code": guarded.returncode,
            "weakened_exit_code": weakened.returncode,
            "guarded_record": guarded_record,
            "weakened_record": weakened_record,
            "stdout": guarded.stdout + weakened.stdout,
            "stderr": guarded.stderr + weakened.stderr,
        }
