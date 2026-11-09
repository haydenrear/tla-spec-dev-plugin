"""A gate states its verdict as data, so nothing has to match on a sentence.

**41 of the instrument registry's 103 demonstration slots assert on literal
output strings.** `corpus_diagnostics.py` moved from *"Every component is within
cap"* to *"Every {scope} is within cap"* when the cap became per-action, and a
demonstration that had been correct for months began reporting a working
instrument broken. Nobody wrote anything false; the coupling was a sentence.

The prose stays -- the sentence a person reads when a gate refuses is some of
this project's best work, and `#301`'s remedy text is a finding in its own
right. What changes is that **no automated consumer reads it.**

Scope, stated honestly: converting `corpus-diagnostics` fixed exactly one
standing failure. The other instruments still red are red for reasons a schema
cannot touch -- two call a script `CA-04` deleted, two are DELIBERATELY red over
a standing `R-H1` violation and say so in the file, one asserts pytest counts.
**This change is preventive, not curative**: it decouples 41 slots from wording
so the next rename does not manufacture a failure, and it fixed one that
already had.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "spec-double-2"
if str(SKILL_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from verdict import SCHEMA_VERSION, VERDICTS, Verdict, read  # type: ignore  # noqa: E402

REGISTRY = REPO_ROOT / "examples" / "validation" / "instruments" / "instruments.toml"


def test_a_reason_must_be_a_code_and_not_a_sentence() -> None:
    """The one rule that keeps this from becoming the thing it replaced.

    A `reason` with spaces or capitals is a sentence wearing a field name, and
    it drifts exactly like the sentences this exists to remove.
    """
    Verdict("i", "pass", "within_cap")
    for bad in ("Over Cap", "over cap", "", " over_cap"):
        with pytest.raises(ValueError):
            Verdict("i", "fail", bad)
    with pytest.raises(ValueError):
        Verdict("i", "maybe", "over_cap")


def test_there_is_no_third_verdict() -> None:
    """`UNDECIDED` is deliberately absent, and that is an `SS-02` decision.

    A gate that could not measure something reports `fail` with a reason saying
    so. A third value invites a consumer to treat "could not measure" as a pass,
    which is the one direction `SS-02` says an absent input may never go.
    """
    assert VERDICTS == ("pass", "fail")


def test_an_unreadable_verdict_is_refused_not_defaulted(tmp_path) -> None:
    """A consumer that defaults turns a broken gate into a quiet pass."""
    bad = tmp_path / "v.json"
    bad.write_text('{"verdict": "pass"}', encoding="utf-8")
    with pytest.raises(ValueError):
        read(bad)
    bad.write_text('{"schema_version":1,"instrument":"i","verdict":"ok","reason":"r"}', encoding="utf-8")
    with pytest.raises(ValueError):
        read(bad)


def test_the_corpus_gate_states_its_verdict_as_data(tmp_path) -> None:
    """End to end through the real CLI, because a library nobody calls is not a fix."""
    # BS-08: the committed example corpus moved here from
    # examples/distributed_history/specs/generated/, which 76ef2758 ("removed
    # generated", 2026-09-14) deleted and gitignored. Restored byte-for-byte from
    # 76ef2758^ as a TEST fixture, outside any directory a generator writes.
    corpus = REPO_ROOT / "tests/fixtures/distributed_history_generated/testgraph/ecommerce_external_cases"
    out = tmp_path / "verdict.json"
    proc = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "corpus_diagnostics.py"),
         str(corpus), "--verdict-json", str(out)],
        cwd=REPO_ROOT, text=True, capture_output=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = read(out)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["verdict"] == "pass"
    assert payload["reason"] == "within_cap"
    assert payload["detail"]["cap_budget"] == "max_external_cases_per_action"
    # The reason must NOT be the sentence. If these ever converge, the coupling
    # is back.
    assert payload["reason"] not in proc.stdout


def test_a_slot_that_declares_a_reason_also_asks_for_one() -> None:
    """`expect_reason` without `--verdict-json {verdict}` can never be satisfied.

    The runner reports that case loudly rather than skipping it, and this makes
    the registry itself consistent: a declaration the argv cannot produce is a
    demonstration that would fail for a reason having nothing to do with the
    instrument.
    """
    registry = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for instrument in registry.get("instrument", []):
        for name in ("failing", "passing", "blind_spot"):
            slot = instrument.get(name)
            if not isinstance(slot, dict) or "expect_reason" not in slot:
                continue
            argv = " ".join(slot.get("argv", []))
            if "{verdict}" not in argv:
                offenders.append(f"{instrument['id']}/{name}")
    assert not offenders, (
        "these slots declare expect_reason but never pass `--verdict-json {verdict}`, "
        "so no verdict can be written: " + ", ".join(offenders)
    )


def test_no_instrument_still_points_at_the_pre_rename_corpus() -> None:
    """`E-06`'s rename orphaned this registry too, and nothing said so.

    `spec_unit` became `spec-unit` in `#313`. Two instruments kept the old path
    and reported themselves unable to demonstrate -- read for a year as "the
    instrument cannot fail" rather than "the argv is stale". **Fifth orphaned
    consumer of one rename**, after the driver defaults, `--dot`, the remedy
    text, the docs and a test's corpus path.
    """
    text = REGISTRY.read_text(encoding="utf-8")
    assert "specs/generated/spec_unit/" not in text, (
        "an instrument still cites the pre-#313 `spec_unit` directory; it will "
        "report MISS for a path error and be read as an instrument that cannot fail"
    )
