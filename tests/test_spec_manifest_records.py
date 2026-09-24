"""RC-01: the manifest's own records are checked against what they describe.

MF-026's coverage audit found three defects that no oracle in this toolchain
could ever have caught, because none of them is a behavior:

* **G-5** -- all three `spec_manifest.yaml` files stated "the model's 9
  variables and 15 actions live in TlaSpecDevCli.tla" beside models with
  different counts. AC-01 added `architecture_scan` and `AnalyzeArchitecture`
  and left the comment. The same defect class as EV-01-DF-03, which RP-05 was
  opened to repair -- and RP-05 repaired the instance, not the mechanism.
* **G-7** -- two comments in each manifest cited "the 2026-07-22 scope
  amendment" as their authority. No such amendment exists. A reader following
  the citation found nothing, and one of the two comments was about to become
  affirmatively FALSE when `GenerateCases` landed.
* **G-1** -- `AnalyzeArchitecture` had no row in `effects.actions` at all,
  while the manifest's own rule says an ABSENT row claims "unmapped" and the
  model states that each action's `@port` lines mirror its row.

None of the four oracles can see any of this: TLC checks the model against
itself, the corpus gate counts cases, the effect oracle diffs observed effects
against declarations, and the kill test seeds faults inside modeled boundaries.
A stale number in a comment is invisible to all four. So it is checked here,
against the module beside each manifest, which is the durable form of the check
RP-05 applied by hand to `architecture_components.yaml`.

These tests deliberately DERIVE the figures rather than restating them: a test
that hardcodes 11 and 18 goes stale the same way the comment did.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# `program_model` is the accepted baseline and is always present. `current` and
# `desired_program_model` exist ONLY while a spec workflow is open -- the
# workflow close prunes them into the sealed snapshot. Parametrizing over all
# three unconditionally made these tests pass during the epic and fail the
# moment it closed, which is a defect in the test rather than in the manifests.
# Skip the transient trees when they are absent; never skip the baseline.
MANIFEST_TREES = ("program_model", "current", "desired_program_model")
ALWAYS_PRESENT = "program_model"


def tree_paths(tree: str) -> tuple[Path, Path]:
    base = REPO_ROOT / "specs" / tree
    if tree != ALWAYS_PRESENT and not base.is_dir():
        pytest.skip(f"specs/{tree} is absent -- no spec workflow is open")
    return base / "TlaSpecDevCli.tla", base / "spec_manifest.yaml"


def block_after(text: str, header: str, indent: str) -> str:
    """The lines of a YAML block, stopping at the first line less indented."""
    start = text.index(header) + len(header)
    lines = []
    for line in text[start:].splitlines():
        if line.strip() and not line.startswith(indent):
            break
        lines.append(line)
    return "\n".join(lines)


def effects_action_rows(manifest_path: Path) -> set[str]:
    text = manifest_path.read_text(encoding="utf-8")
    assert "\n  actions:\n" in text, f"{manifest_path}: no effects.actions block"
    body = block_after(text, "\n  actions:\n", "    ")
    return set(re.findall(r"^    (\w+):", body, flags=re.MULTILINE))


def effects_action_ports(manifest_path: Path) -> dict[str, set[str]]:
    """``effects.actions`` as action -> declared port names.

    RC-02 (N-1). ``effects_action_rows`` above answers "is there a row", which
    is the question G-1 asked. It cannot see a port that is declared and then
    attached to nothing, which is the question N-1 asked, so the rows are
    parsed with their contents here.
    """
    text = manifest_path.read_text(encoding="utf-8")
    assert "\n  actions:\n" in text, f"{manifest_path}: no effects.actions block"
    body = block_after(text, "\n  actions:\n", "    ")
    rows: dict[str, set[str]] = {}
    for name, raw in re.findall(r"^    (\w+):\s*\[(.*?)\]\s*$", body, flags=re.MULTILINE):
        rows[name] = {port.strip() for port in raw.split(",") if port.strip()}
    return rows


def declared_ports(manifest_path: Path) -> set[str]:
    """Every port name under ``effects.components.<component>.ports``.

    EVERY component, which is what the docstring always said and what the
    schema always allowed. This read `block_after(text, "\\n      ports:\\n")`,
    which takes the FIRST match and stops -- so it described one component while
    the manifest's shape is `effects.components.<component>.ports`. It went
    unnoticed because there was exactly one component for the life of the file.
    Adding `SktPort` (SI-20, the skt model surface) made the first block the new
    one, and all fourteen of TlaSpecDevCliPort's ports read as UNDECLARED --
    reported as "action rows name ports that are not declared", which points at
    the rows rather than at the reader.

    A reader that answers about less than it claims is the defect this
    repository has spent the epic on, and it had one in its own checker.
    """
    text = manifest_path.read_text(encoding="utf-8")
    assert "\n      ports:\n" in text, f"{manifest_path}: no ports block"
    names: set[str] = set()
    cursor = 0
    header = "\n      ports:\n"
    while True:
        at = text.find(header, cursor)
        if at == -1:
            break
        body = block_after(text[at:], header, "        ")
        names |= set(re.findall(r"^        (\w+):$", body, flags=re.MULTILINE))
        cursor = at + len(header)
    return names


def annotated_ports(tla_path: Path) -> dict[str, set[str]]:
    """Each ``@command`` action mapped to the ports its ``@port`` lines name."""
    ports: dict[str, set[str]] = {}
    command: str | None = None
    pending: set[str] = set()
    for line in tla_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("\\*"):
            command_match = re.match(r"\\\* @command (\w+)", stripped)
            if command_match:
                command, pending = command_match.group(1), set()
                continue
            port_match = re.match(r"\\\* @port \w+\.(\w+)", stripped)
            if port_match and command is not None:
                pending.add(port_match.group(1))
            continue
        if stripped and command is not None:
            ports[command] = pending
            command, pending = None, set()
    if command is not None:
        ports[command] = pending
    return ports


def justification_rows(manifest_path: Path) -> set[str]:
    text = manifest_path.read_text(encoding="utf-8")
    assert "\njustification:\n" in text, f"{manifest_path}: no justification block"
    body = block_after(text, "\njustification:\n", "  ")
    return set(re.findall(r"^  (\w+):$", body, flags=re.MULTILINE))


def model_counts(tla_path: Path) -> tuple[int, int, int]:
    """(variables, Next disjuncts, @command actions) parsed from the module."""
    text = tla_path.read_text(encoding="utf-8")

    block = re.search(r"^VARIABLES\n(.*?)\n\nvars ==", text, re.S | re.M)
    assert block, f"{tla_path}: no VARIABLES block"
    variables = [line.strip().rstrip(",") for line in block.group(1).splitlines() if line.strip()]

    next_body = re.search(r"\nNext ==\n(.*?)\n\n", text, re.S)
    assert next_body, f"{tla_path}: no Next relation"
    disjuncts = next_body.group(1).count("\\/")

    commands = re.findall(r"^\\\* @command (\w+)", text, flags=re.MULTILINE)
    return len(variables), disjuncts, len(commands)


@pytest.mark.parametrize("tree", MANIFEST_TREES)
def test_the_manifest_states_the_counts_of_the_model_beside_it(tree: str) -> None:
    """G-5. Each manifest is checked against ITS OWN module, not a global figure.

    This distinction is the reason the check exists in this shape. The audit
    reported G-5 against all three manifests as though one model were being
    described three times, and that overstated it: `specs/program_model` is the
    ACCEPTED BASELINE, it predates AC-01, and its "9 variables and 15 actions"
    was correct for the module sitting beside it. Checking each tree against its
    own module states the true property and cannot be satisfied by copying one
    number into three files.
    """
    tla_path, manifest_path = tree_paths(tree)
    variables, disjuncts, commands = model_counts(tla_path)
    # The claim lives in a comment, so it wraps across lines. Strip the comment
    # markers and collapse whitespace before reading it -- a check that only
    # works when the sentence happens to fit on one line is not a check.
    manifest = re.sub(
        r"\s+", " ", re.sub(r"^\s*#\s?", "", manifest_path.read_text(encoding="utf-8"), flags=re.M)
    )

    claim = re.search(
        r"(\d+) variables and (\d+) (?:Next disjuncts|actions)", manifest
    )
    assert claim, f"{manifest_path}: no variable/action count recorded at all"
    assert int(claim.group(1)) == variables, (
        f"{manifest_path} claims {claim.group(1)} variables; "
        f"{tla_path.name} declares {variables}"
    )
    assert int(claim.group(2)) == disjuncts, (
        f"{manifest_path} claims {claim.group(2)} actions; "
        f"{tla_path.name}'s Next has {disjuncts} disjuncts"
    )
    # Stutter carries no @command annotation: it is the stuttering frame
    # condition, not an observable command.
    assert commands == disjuncts - 1


@pytest.mark.parametrize("tree", MANIFEST_TREES)
def test_no_manifest_cites_an_amendment_that_does_not_exist(tree: str) -> None:
    """G-7. A dated citation is a claim, and both of these resolved to nothing.

    The plan's rulings were folded into the PREDECESSOR plan on 2026-07-23 and
    restored into this epic's plan on 2026-08-01. Nothing was ever amended on
    2026-07-22, and two comments per manifest pointed there.
    """
    _, manifest_path = tree_paths(tree)
    manifest = re.sub(r"\s+", " ", manifest_path.read_text(encoding="utf-8"))
    # The two exact citations the audit named. `updated: "2026-07-22"` in the
    # accepted baseline is a date field, not a citation, and is left alone --
    # the defect is pointing a reader at an authority that is not there.
    offenders = [
        phrase
        for phrase in (
            "the 2026-07-22 scope amendment",
            "known_gaps, amended 2026-07-22",
        )
        if phrase in manifest
    ]
    assert offenders == [], (
        f"{manifest_path} cites an amendment that does not exist: {offenders}"
    )


@pytest.mark.parametrize("tree", MANIFEST_TREES)
def test_every_command_action_has_an_effects_row(tree: str) -> None:
    """G-1. An ABSENT row claims "unmapped"; only an EMPTY row claims "no effect".

    `AnalyzeArchitecture` -- this epic's one new action -- had neither, in all
    three manifests, and was the only non-stutter action without a row.
    """
    tla_path, manifest_path = tree_paths(tree)
    text = tla_path.read_text(encoding="utf-8")
    actions = set(re.findall(r"^\\\* @command (\w+)", text, flags=re.MULTILINE))

    rows = effects_action_rows(manifest_path)

    assert actions <= rows, f"{manifest_path}: actions with no effects row: {sorted(actions - rows)}"
    assert rows <= actions, f"{manifest_path}: effects rows that are not actions: {sorted(rows - actions)}"


@pytest.mark.parametrize("tree", MANIFEST_TREES)
def test_every_declared_port_is_attached_to_an_action(tree: str) -> None:
    """N-1. A declared port that no action row names is DEAD MODEL SURFACE.

    RC-01 declared `cli_download`, `cli_artifact_delete` and
    `cli_selftest_process` under `effects.components...ports` and attached none
    of them to an action, in all three trees. The manifest's own schema note
    calls that a hard failure, and it is not a cosmetic one:
    `scripts/effect_conformance.py` binds ports to actions strictly through
    `effects.actions` (`load_effect_declarations` fills `action_ports`;
    `declared_for_action` reads it), so a port absent from every row is
    declared for NOTHING and the effects it was written for stay undeclared on
    the path that performs them.

    `run effect-conformance` reports this as `DEAD MODEL SURFACE` -- but only
    over a corpus it has actually executed, and only for ports no case
    exercises. This check is the cheap, always-on half: it needs no corpus, no
    TLC run and no adapter, and it fails on the declaration itself.
    """
    _, manifest_path = tree_paths(tree)
    ports = declared_ports(manifest_path)
    rows = effects_action_ports(manifest_path)
    attached = set().union(*rows.values()) if rows else set()

    assert ports - attached == set(), (
        f"{manifest_path}: DEAD MODEL SURFACE -- declared but attached to no "
        f"effects.actions row: {sorted(ports - attached)}"
    )
    assert attached - ports == set(), (
        f"{manifest_path}: action rows name ports that are not declared: "
        f"{sorted(attached - ports)}"
    )


@pytest.mark.parametrize("tree", MANIFEST_TREES)
def test_each_actions_port_annotations_mirror_its_effects_row(tree: str) -> None:
    """N-1, the other half: the `@port` mirror rule, checked in BOTH directions.

    `TlaSpecDevCli.tla` states that each action's `@port` lines mirror its row
    in `effects.actions`. Round-2 G-1 broke that rule in one direction -- an
    action carrying annotations with no row. N-1 broke it in the other -- ports
    in the manifest that no annotation mirrors. A test that checks set equality
    per action cannot be satisfied by either.
    """
    tla_path, manifest_path = tree_paths(tree)
    annotated = annotated_ports(tla_path)
    rows = effects_action_ports(manifest_path)

    assert set(annotated) <= set(rows), (
        f"{manifest_path}: annotated actions with no effects row: "
        f"{sorted(set(annotated) - set(rows))}"
    )
    mismatched = {
        action: (sorted(annotated[action]), sorted(rows[action]))
        for action in sorted(annotated)
        if annotated[action] != rows[action]
    }
    assert mismatched == {}, (
        f"{tla_path.name} @port lines do not mirror {manifest_path.name} "
        f"effects.actions (action: (@port lines, manifest row)): {mismatched}"
    )


@pytest.mark.parametrize("tree", MANIFEST_TREES)
def test_every_variable_carries_a_justification_row(tree: str) -> None:
    """Found while closing G-5, and not one of the audit's nine.

    `architecture_scan` had NO row in `justification:` in any tree that has the
    variable. The manifest says `analyze complexity` reads that table and flags
    any variable with no linkage as dead weight, so the epic's own new variable
    has been reported as unjustified since AC-01 closed and nothing failed.
    """
    tla_path, manifest_path = tree_paths(tree)
    variables, _, _ = model_counts(tla_path)
    block = re.search(r"^VARIABLES\n(.*?)\n\nvars ==", tla_path.read_text(encoding="utf-8"), re.S | re.M)
    assert block
    declared = {line.strip().rstrip(",") for line in block.group(1).splitlines() if line.strip()}
    assert len(declared) == variables

    justified = justification_rows(manifest_path)
    assert declared <= justified, (
        f"{manifest_path}: variables with no justification row: {sorted(declared - justified)}"
    )
