"""The agent-integration harness has to be trustworthy without spending an agent.

`examples/agent_integration/` dispatches real Claude sessions: a full run costs
real money and up to ninety minutes, so it cannot be a suite test. What CAN be a
suite test is every property the harness's conclusions rest on, and those are
the properties that, if they silently broke, would make a run report a clean
result over a measurement that never happened.

Three of them matter most:

* **the ask must not leak the answer.** A role's `ask` names no flag, file or
  verb; what the agent has to discover is the measurement. An ask that drifts
  into naming `tla-spec-dev --spec-root specs open ticket` has measured the
  agent's reading comprehension, not the toolchain's ergonomics.
* **the done_check must not be reachable from the ask.** An agent that can infer
  the predicate can satisfy the predicate.
* **binding a home must remove the OTHER homes.** `runtime_requirements.md` is
  explicit that this is the part hand-exporting forgets, and this harness
  hand-exports on purpose (see its README). A launch that merely prepends leaves
  the operator's wrappers reachable, and a wrapper resolved from the wrong home
  is a different toolchain wearing the right name.
"""

from __future__ import annotations

import importlib.util
import os
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "agent_integration"
HARNESS = EXAMPLE / "run_agent_integration.py"
ROLES = EXAMPLE / "roles.toml"


def _harness():
    spec = importlib.util.spec_from_file_location("agent_integration_harness", HARNESS)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _roles() -> list[dict]:
    return tomllib.loads(ROLES.read_text(encoding="utf-8"))["role"]


def test_both_seats_are_declared() -> None:
    """Two roles, not two runs of one thing. A missing seat is a silent halving."""
    ids = {r["id"] for r in _roles()}
    assert ids == {"epic", "ticket"}, f"expected both seats, got {sorted(ids)}"


#: Things an ask must never contain. Every one of these is either the answer or
#: half of it: a verb the agent is supposed to find, a path it is supposed to
#: discover, or a flag whose absence is itself a measured failure mode.
LEAKS = (
    "tla-spec-dev",
    "--spec-root",
    "--actions-metadata",
    "ticket_plan.yaml",
    "specs/program_model",
    "specs/desired_program_model",
    "specs/.history",
    "scaffold",
    "SELF-IMPROVEMENT-MATRIX",
)


@pytest.mark.parametrize("role", _roles(), ids=lambda r: r["id"])
def test_the_ask_does_not_name_what_the_agent_must_discover(role: dict) -> None:
    ask = role["ask"].lower()
    leaked = [token for token in LEAKS if token.lower() in ask]
    assert not leaked, (
        f"role {role['id']}'s ask names {leaked}, which is what it is supposed to "
        "measure the agent finding. An ask that supplies the answer has measured "
        "nothing."
    )


@pytest.mark.parametrize("role", _roles(), ids=lambda r: r["id"])
def test_the_done_check_is_not_reachable_from_the_ask(role: dict) -> None:
    """An agent that knows the check can satisfy the check without doing the work.

    Compared on the check's PATH-LIKE tokens rather than on whole lines: the
    predicate is shell, and an accidental shared word like `test` or `find`
    proves nothing either way.
    """
    ask = role["ask"].lower()
    paths = {
        token.strip("'\"")
        for token in role["done_check"].split()
        if "/" in token and not token.startswith("-")
    }
    assert paths, (
        f"role {role['id']}'s done_check names no path-like token, so this "
        "comparison has nothing to compare and would pass whatever the ask "
        "said. Four other tests in this file carry a non-vacuity guard; this "
        "is that guard."
    )
    leaked = sorted(p for p in paths if p.lower() in ask)
    assert not leaked, f"role {role['id']}'s ask reveals its own done_check: {leaked}"


@pytest.mark.parametrize("role", _roles(), ids=lambda r: r["id"])
def test_every_role_prices_its_prediction_before_the_round(role: dict) -> None:
    """A prediction recorded after the fact is not a prediction.

    This is the PRICE record kind: declared before, measured after. The field is
    required so a round cannot quietly become a description of whatever happened.
    """
    assert role.get("predicts", "").strip(), f"role {role['id']} predicts nothing"


def test_binding_a_home_removes_every_other_home_from_path(monkeypatch) -> None:
    """The part hand-exporting forgets, asserted rather than trusted."""
    harness = _harness()
    other = "/Users/somebody/.skill-manager/bin/cli"
    monkeypatch.setenv("PATH", os.pathsep.join([other, "/usr/bin", "/bin"]))
    home = Path("/tmp/a-home/.skill-manager")

    env, note = harness.bind_home_env(home)
    parts = env["PATH"].split(os.pathsep)

    assert parts[0] == str(home / "bin" / "cli"), "this home's bin must come first"
    assert other not in parts, (
        "another home's bin survived the bind. `runtime_requirements.md` calls "
        "this exact omission out: prepending is not enough, the other homes have "
        "to go, or a wrapper resolves from the wrong home."
    )
    assert env["SKILL_MANAGER_HOME"] == str(home)
    assert "Not logged in" in note, "the launch note must carry the finding it stands on"


def test_a_failed_call_is_a_defect_only_when_it_invoked_the_toolchain() -> None:
    """Classified by the EXECUTABLE, and tested on the input that actually broke it.

    The first classifier matched `skill-manager` and `test_graph` as substrings
    anywhere in the command, and on this repository's own committed evidence it
    was **75% wrong**: three of four "toolchain" errors were
    `E=.skill-manager/skills/...; cat $E/a; cat $E/b` -- a failed `cat` whose
    PATH contained the token.

    The old test passed anyway, because its negative input was
    `cat a.md; cat b.md; cat missing.md` -- a cat chain with no toolchain-shaped
    path in it. **The failing input was in the repository as committed evidence
    and was not used.** Both are here now, and the second is the one that
    matters.
    """
    harness = _harness()

    assert harness.classify_error(
        {"input": {"command": "tla-spec-dev --spec-root specs close ticket X"}}
    ) == "toolchain"
    assert harness.classify_error(
        {"input": {"command": "cat a.md; cat b.md; cat missing.md"}}
    ) == "shell"

    # THE REAL ONE: reading a skill's files is not running the skill.
    reading_a_skill = {
        "input": {
            "command": (
                "cd /tmp/ws/project\n"
                "S=.skill-manager/skills/spec-double-compiler\n"
                "cat $S/references/typical_workflow.md; echo ======; "
                "ls -R $S/examples/distributed_history/specs/program_model/ | head -60"
            )
        }
    }
    assert harness.classify_error(reading_a_skill) == "shell", (
        "a failed `cat` of a skill's own files was counted as invoking the "
        "toolchain -- this is the input that made the headline number 75% wrong"
    )

    # And RUNNING a script that belongs to another installed unit is.
    running_a_skill_script = {
        "input": {
            "command": "python3 .skill-manager/skills/test-graph/scripts/new-uv-node.py a.b action"
        }
    }
    assert harness.classify_error(running_a_skill_script) == "toolchain"


def test_the_classifier_reads_an_input_that_the_harvest_already_trimmed() -> None:
    """Re-classifying committed evidence must not silently report it clean.

    `_trim` turns a long input dict into JSON TEXT before it reaches
    `RESULT.json`. A classifier handed text instead of a mapping finds no
    command, no executable, and answers `shell` -- so every long command in
    every past round would re-read as clean. That is a false PASS in the one
    direction this instrument may never fail in (`SS-02`).
    """
    harness = _harness()
    trimmed = {"input": '{"command": "tla-spec-dev --spec-root specs close ticket X"}'}
    assert harness.classify_error(trimmed) == "toolchain"

    not_even_json = {"input": "tla-spec-dev close ticket X\n... [900 more chars]"}
    assert harness.classify_error(not_even_json) == "toolchain"


def test_the_committed_evidence_reclassifies_the_way_the_record_says() -> None:
    """The numbers in the write-ups have a source, and this is it.

    Round 001's report said "0 real refusals, 4 classified, all its own shell".
    Two of those were wrong in opposite directions -- the count of classified
    errors was inflated by three `cat` chains, and the claim of zero REAL
    refusals was contradicted by `new-uv-node.py` in the same run. This asserts
    the corrected reading against the committed evidence so the next write-up
    cannot drift from it silently.
    """
    import json

    harness = _harness()
    result = json.loads(
        (
            REPO_ROOT
            / "examples/agent_integration/evidence/runs/round-001/RESULT.json"
        ).read_text()
    )
    counts = {"toolchain": 0, "shell": 0}
    for role in ("epic", "ticket"):
        for err in result["roles"][role]["harvest"]["tool_errors"]:
            counts[harness.classify_error(err)] += 1

    assert counts == {"toolchain": 2, "shell": 5}, (
        f"round 001 re-classifies as {counts}; the record says 2 toolchain / 5 "
        "shell. Either the classifier changed or the record is stale, and both "
        "are things a reader has to be told."
    )


def test_the_attribution_probe_is_silent_on_an_empty_transcript() -> None:
    """No attribution found in nothing is absence of evidence, not evidence of it.

    The probe answers a yes/no about SHAPE. It must say `no` for an empty run --
    a probe that reports `any_attribution_shape` for a transcript with no
    content would turn every failed dispatch into a passing E-09 check.
    """
    harness = _harness()
    empty = harness.attribution_probe({"narration": "", "final": {}})
    assert empty["any_attribution_shape"] is False

    named = harness.attribution_probe(
        {"narration": "this sat under UNMODELED/yaml-parser", "final": {}}
    )
    assert named["named_unmodeled_bin"] == ["UNMODELED/yaml-parser"]

    action = harness.attribution_probe(
        {"narration": "", "final": {"result": "the regression is inside TlaSpecDevCli.CloseTicket"}}
    )
    assert "TlaSpecDevCli.CloseTicket" in action["action_shaped_mentions"]


def test_the_harvest_pairs_an_error_back_to_the_call_that_made_it(tmp_path) -> None:
    """The agent's summary is not evidence; the pairing is.

    A tool_result carries only a `tool_use_id`, so an unpaired harvest reports
    "something failed" with no command -- which is unactionable, and worse,
    indistinguishable from a harness that lost the call.
    """
    harness = _harness()
    stream = tmp_path / "stream.jsonl"
    stream.write_text(
        "\n".join(
            [
                '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t1",'
                '"name":"Bash","input":{"command":"tla-spec-dev close ticket X"}}]}}',
                '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1",'
                '"is_error":true,"content":"ERROR: ticket X is already closed"}]}}',
                '{"type":"result","subtype":"success","num_turns":2,"total_cost_usd":0.5,'
                '"result":"done"}',
            ]
        ),
        encoding="utf-8",
    )
    got = harness.harvest(stream)
    assert got["tool_error_count"] == 1
    assert got["toolchain_error_count"] == 1
    only = got["tool_errors"][0]
    assert only["tool"] == "Bash"
    assert "close ticket X" in str(only["input"])
    assert "already closed" in str(only["error"])
    assert got["final"]["total_cost_usd"] == 0.5


def test_a_missing_stream_is_reported_as_unparsed_not_as_zero_errors(tmp_path) -> None:
    """Zero errors and no transcript must not look the same.

    This project has shipped that exact false pass before: `blind_dispatch.check`
    returned PASS for an empty file and for `Error: Invalid API key` alike, and
    the fix was to refuse a subject that is not a report. A dispatch that never
    started has no errors, and calling that a clean run is the same mistake.
    """
    harness = _harness()
    got = harness.harvest(tmp_path / "nothing.jsonl")
    assert got["parsed"] is False
    assert "tool_error_count" not in got


def _git(cwd: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo_with_the_plan_on_another_branch(tmp_path: Path) -> Path:
    """A repository shaped the way `git-epic-workflow` actually leaves one.

    The epic agent works on `epic/<slug>` in its own worktree. The default
    branch carries the accepted baseline and NOT the plan.
    """
    repo = tmp_path / "project"
    (repo / "specs" / "program_model").mkdir(parents=True)
    (repo / "specs" / "program_model" / "Core.tla").write_text("---- MODULE Core ----\n====\n")
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@t.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baseline")

    _git(repo, "checkout", "-q", "-b", "epic/shortlink-spec")
    plan = repo / "specs" / "desired_program_model"
    plan.mkdir(parents=True)
    (plan / "ticket_plan.yaml").write_text(
        "version: 1\ntickets:\n  - id: SL-1\n    status: open\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "plan")
    _git(repo, "checkout", "-q", "main")
    return repo


def test_the_epic_check_looks_on_every_branch_not_just_this_one(tmp_path) -> None:
    """H-01. Round 1 called a complete plan a FAIL because it was on another ref.

    The epic agent produced a validating `ticket_plan.yaml`, three tickets, an
    epic branch and a worktree -- everything `git-epic-workflow` asks for -- and
    this check reported FAIL because it looked only at the working directory.

    **A measurement taken on the wrong fixture is not a refutation; it is a void
    run**, which is the same conclusion round 2 reached about `T1`, and the
    harness owns the error both times. So this asserts the check asks the
    question the workflow answers.
    """
    import subprocess

    repo = _repo_with_the_plan_on_another_branch(tmp_path)
    epic = next(r for r in _roles() if r["id"] == "epic")
    proc = subprocess.run(
        ["bash", "-c", epic["done_check"].strip()], cwd=repo, text=True, capture_output=True
    )
    assert proc.returncode == 0, (
        "the plan is on `epic/shortlink-spec` and the check could not see it:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
    assert "epic/shortlink-spec" in proc.stdout, (
        "the check must SAY where it found the plan; a bare exit 0 leaves a "
        "reader unable to tell a real pass from a check that stopped looking"
    )


def test_the_check_still_fails_when_nothing_was_planned(tmp_path) -> None:
    """Guard the guard: branch-awareness must not turn the check into a pass.

    Widening a predicate is how a green stops meaning anything. This is the
    negative control for the fix above, and it is the reason the fix is
    trustworthy at all.
    """
    import subprocess

    repo = tmp_path / "bare"
    (repo / "specs" / "program_model").mkdir(parents=True)
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@t.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "nothing planned")

    for role in _roles():
        proc = subprocess.run(
            ["bash", "-c", role["done_check"].strip()], cwd=repo, text=True, capture_output=True
        )
        assert proc.returncode != 0, (
            f"role {role['id']}'s done_check passed on a repository where no agent "
            f"did anything:\n{proc.stdout}"
        )


def test_the_ticket_worktree_branches_from_wherever_the_plan_is(tmp_path) -> None:
    """The other half of H-01: a ticket agent must be handed the plan.

    Round 1 branched the ticket worktree from `main` while the plan sat on
    `epic/shortlink-spec`. Any refusal the ticket agent then hit would have been
    the harness's doing, and would have been recorded against the toolchain.
    """
    harness = _harness()
    repo = _repo_with_the_plan_on_another_branch(tmp_path)
    assert harness._ref_carrying_the_plan(repo) == "epic/shortlink-spec"


def test_no_plan_anywhere_falls_back_rather_than_crashing(tmp_path) -> None:
    """A round where the epic seat produced nothing must still measure the ticket seat.

    Returning HEAD keeps the ticket agent's own behaviour as the thing being
    observed. Raising here would convert a finding about the epic seat into a
    harness crash that reports neither.
    """
    harness = _harness()
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@t.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "empty")
    assert harness._ref_carrying_the_plan(repo) == "HEAD"


def test_cleanup_removes_the_home_clones_and_nothing_the_agents_wrote(tmp_path) -> None:
    """Two 700MB clones per run, and nothing in the evidence refers to them.

    Left behind, a weekly round costs a gigabyte and a half of disk. Removed
    carelessly, it costs the run. So the cleanup is asserted on both halves at
    once: every `.skill-manager` under the run root goes, and everything else
    stays exactly where the agents left it.
    """
    harness = _harness()
    (tmp_path / "project" / ".skill-manager" / "bin").mkdir(parents=True)
    (tmp_path / "ticket-worktree" / ".skill-manager").mkdir(parents=True)
    (tmp_path / "project" / "shortlink.py").write_text("# the agent's work\n")
    (tmp_path / "project" / "specs").mkdir()

    removed = harness._drop_home_clones(tmp_path)

    assert len(removed) == 2, f"expected both homes, removed {removed}"
    assert not (tmp_path / "project" / ".skill-manager").exists()
    assert not (tmp_path / "ticket-worktree" / ".skill-manager").exists()
    assert (tmp_path / "project" / "shortlink.py").is_file(), "the agent's work was deleted"
    assert (tmp_path / "project" / "specs").is_dir(), "the agent's spec tree was deleted"


def test_cleanup_will_not_follow_a_symlink_out_of_the_run(tmp_path) -> None:
    """A cleanup that can wander is worse than the disk it saves.

    `rglob` cannot leave the root on its own, but a `.skill-manager` SYMLINK
    inside the workspace pointing at the operator's real home is a plausible
    accident — a copied worktree, a hand-made shortcut — and `rmtree` through it
    would take the home this machine works from.
    """
    harness = _harness()
    outside = tmp_path / "outside" / ".skill-manager"
    (outside / "skills").mkdir(parents=True)
    run_root = tmp_path / "run"
    (run_root / "project").mkdir(parents=True)
    (run_root / "project" / ".skill-manager").symlink_to(outside, target_is_directory=True)

    removed = harness._drop_home_clones(run_root)

    # ASSERTED ON THE RETURN VALUE, not just on the survivor. `shutil.rmtree`
    # refuses a symlink and `ignore_errors=True` swallows that refusal, so
    # `outside` survives whether or not the guard exists -- checking only that
    # it survived is a test that passes vacuously, which is the shape this
    # repository has been caught by three times. The guard's observable effect
    # is that the link is SKIPPED rather than attempted.
    assert removed == [], f"the cleanup tried to remove a home outside the run: {removed}"
    assert outside.is_dir(), "the cleanup followed a symlink out of the run root"
    assert (outside / "skills").is_dir()


#: The scaffold placeholders the epic `done_check` refuses. Kept here AND in
#: `roles.toml`, with `test_the_scaffold_still_emits_the_placeholders_the_check_refuses`
#: asserting the scaffold still emits them -- so a rename in
#: `new_ticket_workflow.ticket_plan()` fails a test rather than quietly turning
#: the predicate back into one that accepts a template.
SCAFFOLD_PLACEHOLDERS = (
    "ReplaceWithDesiredAction",
    "replace_with_state_field",
    "Replace with implementation surfaces",
)


def test_the_scaffold_still_emits_the_placeholders_the_check_refuses() -> None:
    """Derived from the scaffold, not retyped from memory of it.

    If `ticket_plan()` renames a placeholder, the epic predicate stops rejecting
    templates and starts passing on two scaffold verbs again -- silently, and in
    exactly the way it already did once. This is the guard on that.
    """
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    try:
        from scripts.new_ticket_workflow import ticket_plan  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    template = ticket_plan("SL-1", "A title", "Shortlink")
    missing = [p for p in SCAFFOLD_PLACEHOLDERS if p not in template]
    assert not missing, (
        f"the scaffold no longer emits {missing}, so the epic done_check's "
        "template rejection is now partly inert. Update both this list and "
        "examples/agent_integration/roles.toml."
    )

    epic = next(r for r in _roles() if r["id"] == "epic")
    absent = [p for p in SCAFFOLD_PLACEHOLDERS if p not in epic["done_check"]]
    assert not absent, f"the epic done_check does not refuse {absent}"


def test_the_epic_check_refuses_a_plan_that_is_still_the_scaffold_template(tmp_path) -> None:
    """Two scaffold verbs and zero thought used to be a PASS.

    `tla-spec-dev scaffold workflow` emits a `ticket_plan.yaml` that already
    contains `tickets:` and `- id: <ticket>`, so the first version of this
    predicate -- a grep for a list item -- returned exit 0 on a plan that was
    100% placeholders. **That was the epic seat's only pass/fail signal**, and
    the role's own `predicts` field says the thing worth watching is whether the
    agent finds the plan half at all.

    The template is generated here rather than pasted, so this control tracks
    the scaffold instead of a snapshot of it.
    """
    import subprocess
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    try:
        from scripts.new_ticket_workflow import ticket_plan  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    repo = tmp_path / "scaffolded"
    (repo / "specs" / "program_model").mkdir(parents=True)
    plan_dir = repo / "specs" / "desired_program_model"
    plan_dir.mkdir(parents=True)
    (plan_dir / "ticket_plan.yaml").write_text(
        ticket_plan("SL-1", "Reserve a short code", "Shortlink"), encoding="utf-8"
    )
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "t@t.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "scaffold only")

    epic = next(r for r in _roles() if r["id"] == "epic")
    proc = subprocess.run(
        ["bash", "-c", epic["done_check"].strip()], cwd=repo, text=True, capture_output=True
    )
    assert proc.returncode != 0, (
        "the epic done_check PASSED on the shipped scaffold template -- the seat "
        f"has no pass/fail signal:\n{proc.stdout}"
    )
    assert "placeholder" in proc.stdout, (
        "the check refused without saying why; a reader cannot tell a template "
        f"rejection from a missing file:\n{proc.stdout}"
    )


#: State-bearing concepts that would each need real machinery in the fixture --
#: a field, a parameter, a comparison. Narrow on purpose: this is a guard on one
#: demonstrated failure, not a general docstring checker, and it says so.
FIXTURE_CONCEPTS = ("expir", "ttl", "clock", "deadline", "timestamp", "timeout")

#: Everything after this marker is the fixture explaining its own history, and
#: it necessarily names the concept it got wrong.
FIXTURE_CORRECTION_MARKER = "THIS DOCSTRING IS PART OF THE MEASUREMENT"


def test_the_fixture_docstring_promises_nothing_the_fixture_lacks() -> None:
    """The fixture's description IS part of the experiment, and it lied once.

    `shortlink.py` opened *"A link shortener with expiry and a reservation
    window ... a reservation must be claimed before it expires."* **There is no
    expiry in that file** -- no timestamp, no clock, no deadline check. The epic
    agent of round 001 read it, believed it, and built a three-ticket epic
    around implementing "the reservation window the module docstring promises."

    The example exists to see whether an agent finds the trace-only `release`
    property WITHOUT being told where to look. A docstring naming a property the
    program does not have is not a neutral fixture; it is a different
    experiment, run by accident -- and nothing else in the harness can see it.
    `done_check` asks only whether a plan file exists, and `fixture_still_green`
    passes because the agent never touched the module.
    """
    source = (
        REPO_ROOT / "examples/agent_integration/fixture/shortlink.py"
    ).read_text(encoding="utf-8")
    marker = source.find(FIXTURE_CORRECTION_MARKER)
    assert marker > 0, (
        "the fixture's correction marker is gone, so this test cannot tell a "
        "promise from an explanation of a past promise"
    )
    promise, explanation = source[:marker], source[marker:]

    body_start = source.find('"""', source.find('"""') + 3) + 3
    code = source[body_start:].lower()

    leaked = [c for c in FIXTURE_CONCEPTS if c in promise.lower() and c not in code]
    assert not leaked, (
        f"the fixture's opening description names {leaked}, and the code "
        "implements none of it. That is the round-001 defect exactly: the "
        "docstring is what an agent reads first, so it steers the measurement."
    )
    # Non-vacuity: the guard must be looking at a real description, and the
    # explanation below the marker must still be there to be excluded.
    assert len(promise) > 200, "the fixture's description is gone; nothing is guarded"
    assert any(c in explanation.lower() for c in FIXTURE_CONCEPTS), (
        "the record of what went wrong has been edited out of the fixture, and "
        "with it the only reason this test is here"
    )


def test_the_record_does_not_leak_what_the_gitignore_excludes_transcripts_for() -> None:
    """The file that travels must not carry what the file that stays was excluded for.

    `.gitignore` excludes `stream.jsonl` because it *"carries the operator's
    absolute paths, session ids and home layout"*. `RESULT.json` carried the
    same thing — ten occurrences of `/Users/<operator>/` in round 001 across
    `workspace_root`, `home`, `cwd`, `claude_bin` and `preflight.source_home`.
    A stated reason that the neighbouring file violates is not a partial reason;
    it is an untrue one.
    """
    harness = _harness()
    committed = sorted(
        (REPO_ROOT / "examples/agent_integration/evidence/runs").glob("*/RESULT.json")
    )
    assert committed, "no committed RESULT.json to check"
    home = str(Path.home())
    for path in committed:
        text = path.read_text(encoding="utf-8")
        assert home not in text, (
            f"{path.relative_to(REPO_ROOT)} embeds the operator's home path, "
            "which is the reason `.gitignore` gives for excluding the transcripts"
        )
    # Non-vacuity: the redactor must actually be doing something, or these files
    # could be clean because nothing ever wrote a path into them.
    assert harness._redact({"p": f"{home}/x"}) == {"p": "~/x"}


def test_a_timeout_takes_the_whole_process_tree() -> None:
    """`proc.kill()` kills `claude` and nothing it spawned.

    TLC's JVM, a gradle daemon, the fixture's HTTP server: all reparented, all
    still running after the harness prints `timeout`. **The next round then
    inherits a machine the last one did not clean up**, which is a measurement
    of the previous round wearing this one's run id.

    Asserted on a real process tree rather than by reading: a shell that spawns
    a child which outlives it, killed through the group, and the grandchild must
    be gone.
    """
    import os
    import signal
    import subprocess as sp
    import time

    harness = _harness()
    marker = Path(os.environ.get("TMPDIR", "/tmp")) / f"kill-tree-probe-{os.getpid()}"
    marker.unlink(missing_ok=True)
    # The grandchild writes the marker only if it is still alive after the kill.
    child = sp.Popen(
        ["bash", "-c", f"(sleep 2; touch {marker}) & sleep 30"],
        start_new_session=True,
        stdout=sp.DEVNULL,
        stderr=sp.DEVNULL,
    )
    try:
        time.sleep(0.3)
        harness._kill_tree(child)
        time.sleep(3)
        assert not marker.exists(), (
            "a grandchild of the killed process survived and kept working; a "
            "timed-out round leaves its JVMs and servers behind"
        )
    finally:
        marker.unlink(missing_ok=True)
        try:
            os.killpg(os.getpgid(child.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass


def test_the_stream_shape_fields_do_not_claim_to_be_turn_counts(tmp_path) -> None:
    """Round 001 carried two turn counts in one file, disagreeing by 50%.

    `assistant_turns: 118` sat beside the result event's `num_turns: 77`,
    because the stream emits one `assistant` event per content BLOCK. Distinct
    message ids give 28 — a third number. None is wrong; they count different
    things, and only one of them is a turn.

    So nothing in the harvest is named for turns any more. `final.num_turns` is
    the agent's own count and is authoritative when a result event exists; these
    two describe raw stream shape, which is what a reader has when it does not.
    """
    harness = _harness()
    stream = tmp_path / "stream.jsonl"
    stream.write_text(
        "\n".join(
            [
                '{"type":"assistant","message":{"id":"m1","content":[{"type":"text","text":"a"}]}}',
                '{"type":"assistant","message":{"id":"m1","content":[{"type":"tool_use","id":"t1",'
                '"name":"Bash","input":{"command":"true"}}]}}',
                '{"type":"assistant","message":{"id":"m2","content":[{"type":"text","text":"b"}]}}',
                '{"type":"result","subtype":"success","num_turns":2,"result":"done"}',
            ]
        ),
        encoding="utf-8",
    )
    got = harness.harvest(stream)
    assert "assistant_turns" not in got, "a field named for turns is back"
    assert got["assistant_events"] == 3, "the raw event count is what it says"
    assert got["assistant_messages"] == 2, "two distinct message ids"
    assert got["final"]["num_turns"] == 2, "the agent's own count is preserved"


def test_prose_inside_a_heredoc_is_not_read_as_a_command() -> None:
    """Round 002 flagged a seat's error as `toolchain` for text it was WRITING.

    The ticket agent ran `cat > deferred_findings.yaml <<'YAML'` and one line of
    the body began `.skill-manager/bin/cli/tla-spec-dev runs a bare python3 from
    PATH` -- prose recording a finding it had just made. Split on newlines, that
    line's first token sat in the executable position, and the classifier read
    documentation of a defect as a defect. The seat's real count for that round
    is **zero**.

    Second time the same instrument over-claimed: first `skill-manager` matched
    as a substring anywhere, and when that was narrowed to the executable,
    heredoc text still reached the executable position. **Both times it reported
    a defect where there was a description of one**, which is the failure mode
    this whole harness exists to police in others.
    """
    harness = _harness()
    writing_it_down = (
        "cd /tmp/x\n"
        "cat > findings.yaml <<'YAML'\n"
        "  .skill-manager/bin/cli/tla-spec-dev runs a bare python3 from PATH\n"
        "  tla-spec-dev --spec-root specs close ticket X\n"
        "YAML\n"
    )
    assert harness.classify_error({"input": {"command": writing_it_down}}) == "shell", (
        "a heredoc body was read as shell; the instrument counted the agent's "
        "own notes about a defect as an occurrence of it"
    )
    # And the same text OUTSIDE a heredoc is still an invocation.
    assert harness.classify_error(
        {"input": {"command": "tla-spec-dev --spec-root specs close ticket X"}}
    ) == "toolchain"


# --------------------------------------------------------------------------
# The eval suite's own configuration.
#
# `evals/` (SI-10; it was `examples/agent_integration/eval-plugin/`) replaced most of this harness with
# `claude plugin eval`, and the four defects that followed were all the same
# shape: a contract the library was ASSUMED to honour, with no receipt. Each
# one made a run report an agent failure that was the suite's own setup, which
# is the exact direction this project says an instrument may not fail in.
#
# These pin the four. They read configuration, cost nothing, and go red if a
# later edit walks any of them back.
# --------------------------------------------------------------------------

# SI-10 moved the suite out of `examples/agent_integration/eval-plugin`, which
# was a thin symlinked plugin built because `claude plugin eval` refuses a
# plugin directory over 20,000 entries. It carried ONE skill's surface by name,
# and the nesting made that a bug: there are six skills now, and the shim could
# only ever have shown one of them. The suite is the plugin's own `evals/`, and
# `evals/run.sh` stages a view of the checkout small enough for the CLI to
# accept. Every pin below is unchanged except for where it looks.
EVAL_SUITE = REPO_ROOT / "evals"
# RECURSIVE, because cases are `evals/<skill>/<case>/` now -- one directory per
# nested skill. A non-recursive scan would silently pin nothing, which is the
# failure shape these tests exist to catch.
EVAL_CASES = sorted(c.parent for c in EVAL_SUITE.rglob("case.yaml"))
EVAL_CASE = EVAL_SUITE / "spec-double-2" / "scaffold-a-program-model"
PLACE = EVAL_SUITE / "lib" / "place.sh"
VERIFY = EVAL_SUITE / "lib" / "verify.sh"


def _eval_case_text(case=None) -> str:
    return ((case or EVAL_CASE) / "case.yaml").read_text(encoding="utf-8")


def test_the_fixture_is_placed_by_a_hook_and_not_by_scaffold_script() -> None:
    """The fixture is placed by a hook, and that is still the right mechanism.

    The reason was RE-MEASURED in SI-14 on 2.1.276 and the old wording here --
    "accepted by the case loader and never executed" -- is now only half true.
    Corrected, with the probes in `references/plugin_evals.md`:

      * top-level `scaffold_script:` with an inline body: accepted and silently
        ignored, exactly as measured on 2.1.261 (a body of `exit 3` scored 1.00);
      * `context.scaffold_script:` with an inline body: refused at load, because
        the value is read as a PATH;
      * `context.scaffold_script: ./scaffold.sh` under `--scaffold`: RUNS, as
        the operator, outside the sandbox, with network.

    The hook is still what places fixtures here, because `--scaffold` is OFF BY
    DEFAULT -- a suite depending on it runs unscaffolded, and scores, for anyone
    who forgets the flag -- and because one hook dispatching on `EVAL_CASE`
    serves every case. A case scored 0 on an EMPTY repository once already, and
    that read as "the agent could not build a spec".
    """
    hooks = EVAL_SUITE / "hooks" / "hooks.json"
    assert hooks.is_file(), "the fixture has no placement mechanism at all"

    import json

    session_start = json.loads(hooks.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    commands = [
        h["command"]
        for entry in session_start
        for h in entry["hooks"]
        if h.get("type") == "command"
    ]
    assert any("place.sh" in c for c in commands), (
        f"no SessionStart hook places a fixture; commands were {commands}"
    )

    # And nobody may quietly re-add the inert key and believe it does the work.
    for line in _eval_case_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("scaffold_script:"), (
            "case.yaml declares scaffold_script:, which the CLI accepts and "
            "never runs -- the fixture would silently not be placed"
        )


def test_every_gated_tool_the_case_declares_is_granted_in_the_documented_run() -> None:
    """A tool in `allowed_tools:` is still refused unless `--allow-tools` grants it.

    `--allow-tools Bash` alone produced `not granted (missing --allow-tools
    grant, or a malformed entry): Write, Edit` and a score of 0: the agent
    could read the program and could not write one line of the spec. The
    summary line said nothing; only the per-case notes did.
    """
    import re

    declared = re.search(r"allowed_tools:\s*\[([^\]]*)\]", _eval_case_text())
    assert declared, "the case declares no allowed_tools"
    tools = {t.strip() for t in declared.group(1).split(",") if t.strip()}
    gated = tools & {"Bash", "Write", "Edit", "WebFetch"}

    readme = (EVAL_SUITE / "README.md").read_text(encoding="utf-8")
    grant = re.search(r"--allow-tools ([A-Za-z ]+)", readme)
    assert grant, "the README documents no --allow-tools grant"
    granted = set(grant.group(1).split())

    missing = sorted(gated - granted)
    assert not missing, (
        f"the case declares {sorted(gated)} but the documented run grants "
        f"{sorted(granted)}; {missing} would be refused and the run would "
        "score 0 for a reason that is not the agent's"
    )


def test_no_grader_scores_an_artefact_any_scratch_file_would_satisfy() -> None:
    """The first artefact grader globbed `specs/program_model/*.tla`.

    A run that spent its whole budget on toolchain archaeology left behind
    `Probe.tla` -- `Next == x' = (x + 1) % 3`, a counter mod 3 with nothing to
    do with the fixture -- and the case reported 0.50, as though half the work
    had been done.
    """
    import re

    for grader in sorted(g for c in EVAL_CASES for g in (c / "graders").glob("*.md")):
        text = grader.read_text(encoding="utf-8")
        if "type: file_exists" not in text:
            continue
        path = re.search(r"^path:\s*\"?([^\"\n]+)\"?", text, re.M)
        assert path, f"{grader.name}: a file_exists grader with no path"
        assert not path.group(1).strip().endswith("*.tla"), (
            f"{grader.name} globs *.tla, which a scratch probe satisfies"
        )


def test_the_llm_grader_does_not_claim_to_read_files_it_cannot_see() -> None:
    """The `llm` grader sees the final response and nothing else.

    Measured with a probe case whose hook wrote `banana` into SECRET.txt and
    whose criterion was "score 1 only if SECRET.txt contains banana":

        never mentioned the file            FAIL FAIL FAIL
        READ the file, did not quote it     FAIL FAIL FAIL
        quoted its contents in the reply    PASS PASS PASS

    The grader used to end "Score the artefacts: an action in the `.tla` files,
    not a claim in the response." That instruction could never be followed, so
    what it scored was the claim while reading as artefact evidence -- SS-02
    with the grader itself as the absent input.
    """
    for grader in sorted(g for c in EVAL_CASES for g in (c / "graders").glob("*.md")):
        text = grader.read_text(encoding="utf-8")
        if "type: llm" not in text:
            continue
        assert "CANNOT SEE THE WORKSPACE" in text, (
            f"{grader.name}: an llm grader that does not say what it can see "
            "will drift back into being written as though it reads the tree"
        )
        # AND THE DISCLAIMER MUST NOT SIT ABOVE AN INSTRUCTION THAT CONTRADICTS
        # IT. A blind review pointed out that the check above pins a magic
        # string: a grader could carry that sentence and still end "score the
        # artefacts in the .tla files", which is the exact defect. So the
        # instruction itself is checked too.
        lowered = text.lower()
        for forbidden in (
            "score the artefacts",
            "in the `.tla` files",
            "inspect the workspace",
            "read the files",
            "look at the file",
        ):
            assert forbidden not in lowered, (
                f"{grader.name} tells the judge to {forbidden!r}, which it "
                "cannot do -- the judge sees the final response and nothing "
                "else, so that instruction silently becomes 'score the claim'"
            )


# --------------------------------------------------------------------------
# The verdict discipline.
#
# The case scored 1.00 while `tla-spec-dev scaffold project` failed with exit 1
# on all three attempts, and the manifest its artefact grader accepted as proof
# the pipeline had run was typed by the agent's own Write tool. A probe scored
# that same grader green on `placeholder: true`.
#
# The repair is a `Stop` hook that runs the real check and writes verdict paths
# the graders read. These pin the three properties that make it sound.
# --------------------------------------------------------------------------



def test_the_case_verifies_after_the_run_and_not_only_before_it() -> None:
    """A fixture hook alone grades what the agent SAYS about what it did."""
    import json

    hooks = json.loads((EVAL_SUITE / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    stop = hooks["hooks"].get("Stop") or []
    commands = [
        h["command"] for entry in stop for h in entry["hooks"] if h.get("type") == "command"
    ]
    assert any("verify.sh" in c for c in commands), (
        f"no Stop hook runs the verifier; Stop commands were {commands}"
    )
    assert VERIFY.is_file() and os.access(VERIFY, os.X_OK), (
        "verify.sh is missing or not executable, so the hook would do nothing "
        "and every verdict grader would fail for a reason that is not the run's"
    )


def test_the_verifier_clears_its_verdicts_before_it_writes_any() -> None:
    """The agent has Write and can create any filename it can guess.

    Measured: an agent told to write `VERIFIED.txt` itself scored FAIL once the
    hook erased it before checking. If the clear ever moves after the first
    write, a forged file survives and the grader reads the forgery.
    """
    # CODE ONLY. The first version used `text.find("rm -rf")`, which finds the
    # first mention anywhere -- so a comment saying "rm -rf" above the real
    # clear would let the clear move below the first write with this still
    # green. A blind review found that; the lines are stripped of comments now.
    text = VERIFY.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in text.splitlines()
        if not line.lstrip().startswith("#")
    )
    clear = code.find('rm -rf "$VD"')
    assert clear != -1, "verify.sh never clears the verdict directory in code"
    first_write = min(
        (i for i in (code.find('"$VD/'), code.find("cp \"$v\" \"$VD/")) if i != -1),
        default=-1,
    )
    assert first_write != -1, "verify.sh writes no verdict at all"
    assert clear < first_write, (
        "verify.sh writes into the verdict directory before clearing it, so a "
        "file the agent forged under that name survives into the grading"
    )
    assert text.rstrip().endswith("exit 0"), (
        "verify.sh must exit 0 unconditionally: a Stop hook that fails non-zero "
        "can push the session onward, and a verifier that changes the run it "
        "measures is not a verifier"
    )


def test_a_forged_workspace_earns_no_verdict(tmp_path) -> None:
    """THE CONTROL, EXECUTED. The false-positive direction, which is the one
    that matters -- a verifier that misses a real model wastes a run, and one
    that blesses a forgery invalidates every number the suite reports.

    The forgery is the exact shape that scored green before: a one-line
    manifest, plus every verdict path pre-planted under the name the graders
    read.
    """
    import subprocess

    model = tmp_path / "specs" / "program_model"
    model.mkdir(parents=True)
    (model / "spec_manifest.yaml").write_text("placeholder: true\n", encoding="utf-8")
    verdicts = tmp_path / ".eval"
    verdicts.mkdir()
    for name in ("parses", "checks", "manifest"):
        (verdicts / name).write_text("forged\n", encoding="utf-8")

    # EVAL_CASE, WITHOUT WHICH THIS CONTROL VERIFIES NOTHING.
    #
    # The first version omitted it. `verify.sh` dispatches on `EVAL_CASE`, so
    # the run fell to the `""` arm, logged "EVAL_CASE unset; nothing verified",
    # and the forged files vanished only because of the unconditional clear.
    # The manifest recogniser this test exists to exercise never executed.
    # Mutation-proved by a blind review: gutting that recogniser so
    # `placeholder: true` earns a verdict left this test GREEN.
    subprocess.run(
        ["sh", str(VERIFY)],
        cwd=tmp_path,
        env={**os.environ, "EVAL_CASE": "scaffold-a-program-model"},
        check=False,
        timeout=900,
    )

    # `toolchain` is not a verdict about the WORK -- it records that java and
    # the tla2tools jar resolved, so that a missing artefact verdict can be told
    # apart from an artefact that was never checked. No grader reads it, and the
    # pin below enforces that every grader reads something else.
    diagnostic = {"verify.log", "toolchain", "UNDECIDED-toolchain"}
    # The verifier emits this diagnostic when Linux lacks sandbox-exec. Keep
    # testing every scored verdict path on that host, including the forgeries.
    import shutil
    if shutil.which("sandbox-exec") is None:
        assert "sandbox-exec was unavailable" in (verdicts / "UNDECIDED-unconfined").read_text()
        diagnostic.add("UNDECIDED-unconfined")
    survived = sorted(p.name for p in verdicts.iterdir() if p.name not in diagnostic)
    assert not survived, (
        f"forged verdicts survived the verifier: {survived}. Every one of these "
        "is a grader scoring green on a workspace that holds no model."
    )


def test_no_grader_reads_a_path_the_agent_can_simply_write(tmp_path) -> None:
    """Every artefact grader has to read a verdict, not an artefact.

    `file_exists` cannot look inside a file -- `contains:` is rejected as an
    unknown key -- so a grader pointed at the work itself asks only whether a
    name exists, and the agent chooses the names.
    """
    import re

    for grader in sorted(g for c in EVAL_CASES for g in (c / "graders").glob("*.md")):
        text = grader.read_text(encoding="utf-8")
        if "type: file_exists" not in text:
            continue
        path = re.search(r"^path:\s*\"?([^\"\n]+)\"?", text, re.M)
        assert path, f"{grader.name}: a file_exists grader with no path"
        target = path.group(1).strip()
        assert target.startswith(".eval/"), (
            f"{grader.name} grades {target}, which the agent can create with "
            "Write. Point it at a verdict the Stop hook writes."
        )


def test_every_regex_grader_compiles_where_the_grader_actually_runs() -> None:
    """A `regex` grader is evaluated by the CLI's own JavaScript engine.

    Measured, at $1.34: `start-from-the-spec-not-the-source` scored 0.67 with

        grader threw: Invalid regular expression: unrecognized character after (?

    because the pattern opened with `(?s)`. Python accepts that inline flag;
    JavaScript has never had it. So the pattern was valid everywhere it was
    tested and invalid in the only place it runs.

    A grader that THROWS is worse than one that fails: it scores 0 against the
    agent while the fault is entirely the suite's, which is the direction this
    file exists to make impossible. `[\\s\\S]` spans newlines in both engines
    and is what to use instead.
    """
    import re

    unsupported = ("(?s)", "(?i)", "(?m)", "(?x)", "(?P<", "(?<=", "(?<!")
    checked = 0
    for grader in sorted(g for c in EVAL_CASES for g in (c / "graders").glob("*.md")):
        text = grader.read_text(encoding="utf-8")
        if "type: regex" not in text:
            continue
        pattern = re.search(r"^pattern:\s*'(.*)'\s*$", text, re.M)
        assert pattern, f"{grader.name}: a regex grader with no single-quoted pattern"
        body = pattern.group(1)
        checked += 1
        for token in unsupported:
            assert token not in body, (
                f"{grader.name} uses {token}, which Python accepts and the CLI's "
                "JavaScript engine rejects at grading time -- the grader throws, "
                "and the run scores 0 for a reason that is not the agent's"
            )
        re.compile(body)
    assert checked, "no regex graders were checked, so this pin asserts nothing"


# --------------------------------------------------------------------------
# Two cases, one plugin, and the CLI the run actually executes.
# --------------------------------------------------------------------------


def test_every_case_declares_which_case_it_is() -> None:
    """Hooks belong to the PLUGIN, not to a case.

    `lib/place.sh` and `lib/verify.sh` dispatch on `EVAL_CASE`, which a case
    can set because `execution.env` allows `EVAL_*` and refuses everything else
    -- "only EVAL_* keys can be set from case.yaml. Anything else must come
    from the operator's shell." A case that forgets it gets no fixture, and an
    empty workspace reads as an agent who could not work.
    """
    import re

    for case in EVAL_CASES:
        text = _eval_case_text(case)
        declared = re.search(r"^\s*EVAL_CASE:\s*(\S+)", text, re.M)
        assert declared, f"{case.name}/case.yaml sets no EVAL_CASE under execution.env"
        assert declared.group(1).strip() == case.name, (
            f"{case.name}/case.yaml declares EVAL_CASE={declared.group(1)}, which "
            "does not match its directory, so the hooks would place and verify "
            "some other case's fixture"
        )


def test_the_hooks_handle_every_case_that_exists() -> None:
    """Conservation, for the dispatch table.

    A case added without an arm in both scripts is a case whose fixture is
    never placed and whose work is never verified -- and both failures look
    exactly like an agent who did nothing.
    """
    place = PLACE.read_text(encoding="utf-8")
    verify = VERIFY.read_text(encoding="utf-8")
    for case in EVAL_CASES:
        assert f"{case.name})" in place, f"lib/place.sh has no arm for {case.name}"
        assert f"{case.name})" in verify, f"lib/verify.sh has no arm for {case.name}"


def test_the_run_executes_this_checkout_and_not_an_installed_copy() -> None:
    """Measured: a run's `which -a tla-spec-dev` returned only
    `~/.skill-manager/bin/cli/tla-spec-dev`, three times. The plugin's skill
    directory loaded correctly and the branch under review was never executed.

    A plugin `bin/` does not reach the eval's PATH, and `execution.env` refuses
    `PATH`. What works is a shim inside the checkout that the operator
    prepends -- so the shim has to exist, has to run this tree, and has to
    REFUSE rather than fall through, because a shim that quietly defers to the
    installed CLI reintroduces the bug invisibly.
    """
    shim = EVAL_SUITE / "bin" / "tla-spec-dev"
    assert shim.is_file() and os.access(shim, os.X_OK), (
        "no executable bin/tla-spec-dev shim: the run would grade whichever "
        "copy the operator happens to have installed"
    )
    text = shim.read_text(encoding="utf-8")
    assert "exec python3" in text and "scripts/tla_spec_dev.py" in text, (
        "the shim does not exec this checkout's CLI"
    )
    assert "exit 127" in text, (
        "the shim falls through when the checkout is missing, which silently "
        "restores the defect it exists to prevent"
    )
    # The README has to SHOW the prepend, whether it writes the directory out
    # or binds it to a variable first. Checking for one literal spelling made
    # this fail on a README that documented it correctly through `$BIN` -- a
    # pin that asserts a phrasing rather than a property.
    readme = (EVAL_SUITE / "README.md").read_text(encoding="utf-8")
    assert "evals/bin" in readme, (
        "the README never names the shim directory, so a reader has no way to "
        "know the run needs it"
    )
    # And it has to be in the COMMAND, not only in the prose beside it. The
    # first version of this check passed a README whose runnable block had lost
    # the prepend, because a bullet further down still mentioned it -- an
    # assertion satisfied by discussion of the thing rather than the thing.
    blocks = [
        b for b in readme.split("```")
        if "claude plugin eval" in b and "--allow-tools" in b
    ]
    assert blocks, "the README documents no runnable command"
    assert any("PATH=" in b for b in blocks), (
        "the README's runnable command does not prepend the shim directory, so "
        "following it exactly grades the installed CLI"
    )


def test_the_shim_refuses_when_there_is_no_checkout(tmp_path) -> None:
    """THE REFUSAL, EXECUTED -- the property above, run rather than grepped."""
    import shutil, subprocess

    fake = tmp_path / "a" / "b" / "c" / "bin"
    fake.mkdir(parents=True)
    shutil.copy2(EVAL_SUITE / "bin" / "tla-spec-dev", fake / "tla-spec-dev")
    done = subprocess.run(
        ["sh", str(fake / "tla-spec-dev"), "--version"],
        capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 127, (
        f"the shim ran something instead of refusing (rc={done.returncode}, "
        f"out={done.stdout!r})"
    )
    assert "refusing to fall through" in done.stderr


def test_no_grader_scores_the_toolchain_marker() -> None:
    """`.eval/toolchain` says the ENVIRONMENT was able to look, not that the
    work was good. A workspace holding nothing but a forged manifest still
    earns it, so a grader pointed at it would score green on an empty run.
    """
    for case in EVAL_CASES:
        for grader in sorted((case / "graders").glob("*.md")):
            text = grader.read_text(encoding="utf-8")
            assert ".eval/toolchain" not in text, (
                f"{case.name}/{grader.name} grades the toolchain marker, which "
                "a forged workspace also earns"
            )


def test_the_seeded_fault_still_anchors_to_the_program() -> None:
    """`catch-the-drift` seeds its fault by replacing one exact line.

    A blind review found the hole: reflow that line -- double quotes to single,
    a formatter's whim -- and the seed fails AFTER the workspace has been
    copied and committed. The case then runs on an UNFAULTED program, and an
    agent that does nothing at all scores 0.80, because the weight-2 grader
    passes for free.

    `place.sh` now exits 2 (blocking; 1 is advisory and let the session start)
    and re-checks the behaviour after seeding. This is the cheap half: it says
    so at suite time rather than at $1.32 a run.
    """
    import re

    place = PLACE.read_text(encoding="utf-8")
    anchor = re.search(r"^find = '(.+)'$", place, re.M)
    assert anchor, "lib/place.sh no longer carries a `find = '...'` anchor line"

    domain = (
        REPO_ROOT / "examples" / "distributed_history" / "ecommerce_backend" / "domain.py"
    ).read_text(encoding="utf-8")
    hits = domain.count(anchor.group(1))
    assert hits == 1, (
        f"the seed anchor appears {hits} times in ecommerce_backend/domain.py, "
        "expected exactly 1. At 0 the fault is never seeded and catch-the-drift "
        "passes for free; above 1 the replacement is ambiguous."
    )


def test_a_config_that_asserts_nothing_earns_no_tlc_verdict(tmp_path) -> None:
    """THE STUB CONTROL, EXECUTED.

    A blind review built a six-line module and a `.cfg` naming only
    `SPECIFICATION Spec`. TLC printed "Model checking completed. No error has
    been found" -- it had nothing to check -- and the grader that calls itself
    "the one a confident report cannot move" went green on a model of nothing.
    """
    import subprocess

    model = tmp_path / "specs" / "program_model"
    model.mkdir(parents=True)
    (model / "Triv.tla").write_text(
        "---- MODULE Triv ----\nVARIABLE x\nInit == x = 0\nNext == x' = x\n"
        "Spec == Init /\\ [][Next]_x\n====\n",
        encoding="utf-8",
    )
    (model / "Triv.cfg").write_text("SPECIFICATION Spec\n", encoding="utf-8")
    (model / "spec_manifest.yaml").write_text(
        "module: Triv\nports: []\ninvariants: []\ncodegen: {}\n", encoding="utf-8"
    )

    subprocess.run(
        ["sh", str(VERIFY)],
        cwd=tmp_path,
        env={**os.environ, "EVAL_CASE": "scaffold-a-program-model"},
        check=False,
        timeout=900,
    )

    verdicts = tmp_path / ".eval"
    log = (verdicts / "verify.log").read_text(encoding="utf-8") if verdicts.is_dir() else ""
    if "V2 skipped: no java or jar" in log:
        pytest.skip("no java or tla2tools jar here, so this control cannot look")
    assert not (verdicts / "checks").exists(), (
        "TLC earned a verdict on a config declaring no INVARIANT and no "
        "PROPERTY, so the run asserted nothing and the grader said it passed"
    )


def test_agent_code_cannot_write_a_verdict_after_the_hook_exits(tmp_path) -> None:
    """THE RESIDUAL HOLE, CLOSED AND PINNED.

    `verify.sh` used to say, in its own header, that a process spawned to write
    a verdict AFTER it exits "would still win. Nothing here defends against
    that." That was true, and it was demonstrated rather than argued: five lines
    appended to `ecommerce_backend/domain.py` -- the file `catch-the-drift` asks
    the agent to repair -- spawning

        Popen([...], start_new_session=True)   # sleep 4, then write .eval/behaviour

    produced a `behaviour` verdict four seconds after the hook exited, on a
    workspace where the program was never repaired. The hook had refused
    correctly ("create_account did not persist") and the refusal was overwritten
    by the thing it refused, before the graders read the path.

    A Stop hook runs OUTSIDE the sandbox that constrains the agent's Bash tool,
    so whatever the hook executes runs with the hook's privileges. Killing the
    process group does not close it -- the payload starts a new session to
    escape exactly that. Denying writes does, and it holds for descendants,
    which inherit the profile.

    This test is the reason to believe that: it runs the attack.
    """
    import shutil, subprocess, time

    if not shutil.which("sandbox-exec"):
        pytest.skip("no sandbox-exec here, so the confinement this pins cannot be applied")

    workspace = tmp_path / "ws"
    workspace.mkdir()
    placed = subprocess.run(
        ["sh", str(PLACE)],
        cwd=workspace,
        env={**os.environ, "EVAL_CASE": "catch-the-drift"},
        capture_output=True, text=True, timeout=600,
    )
    assert placed.returncode == 0, f"place.sh refused: {placed.stderr[-400:]}"

    domain = workspace / "ecommerce_backend" / "domain.py"
    domain.write_text(
        domain.read_text(encoding="utf-8")
        + "\n"
        "import subprocess as _sp, sys as _sys, os as _os\n"
        "_PAYLOAD = (\n"
        '    "import time, os\\n"\n'
        '    "time.sleep(4)\\n"\n'
        '    "os.makedirs(\'.eval\', exist_ok=True)\\n"\n'
        '    "open(\'.eval/behaviour\', \'w\').write(\'forged after the hook exited\')\\n"\n'
        ")\n"
        "_sp.Popen([_sys.executable, '-c', _PAYLOAD], cwd=_os.getcwd(), start_new_session=True)\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["sh", str(VERIFY)],
        cwd=workspace,
        env={**os.environ, "EVAL_CASE": "catch-the-drift"},
        check=False, timeout=900,
    )

    verdicts = workspace / ".eval"
    assert not (verdicts / "behaviour").exists(), (
        "the hook published a behaviour verdict for an unrepaired program"
    )

    # Past the payload's sleep, which is when it would land.
    time.sleep(7)
    assert not (verdicts / "behaviour").exists(), (
        "agent-authored code wrote a verdict after the hook exited: the weight-2 "
        "grader is now green on a program that was never repaired, and the "
        "verifier's own log records the refusal it overwrote"
    )


def test_the_verdict_deny_survives_a_symlinked_workspace(tmp_path) -> None:
    """macOS resolves paths before matching a sandbox profile.

    A profile naming `/tmp/ws/.eval` does not deny a write to
    `/private/tmp/ws/.eval`, and **a deny that never applies looks exactly like
    a deny that worked** -- an allowed write prints nothing either. The first
    version of `noverdict.sb` was wired with the logical path and the forged
    file appeared; the failure was visible only by checking the artefact.

    This runs the deny through a symlink, which is the shape that exposed it.
    """
    import shutil, subprocess

    sandbox = shutil.which("sandbox-exec")
    if not sandbox:
        pytest.skip("no sandbox-exec here")

    real = tmp_path / "real"
    (real / ".eval").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real)

    profile = EVAL_SUITE / "lib" / "checks" / "noverdict.sb"
    assert profile.is_file(), "the verdict-denying profile is missing"

    # The profile is given the RESOLVED path, as verify.sh gives it (`pwd -P`).
    resolved = real.resolve()
    for reached_by, target in (("physical", resolved), ("symlink", link)):
        done = subprocess.run(
            [sandbox, "-D", f"VERDICTS={resolved}/.eval", "-f", str(profile),
             "python3", "-c", f"open('{target}/.eval/forged','w').write('x')"],
            capture_output=True, text=True, timeout=300,
        )
        assert done.returncode != 0, f"the write succeeded when reached by its {reached_by} path"
        assert not (real / ".eval" / "forged").exists(), (
            f"a verdict was forged through the {reached_by} path: the profile "
            "is not covering the directory the graders read"
        )
