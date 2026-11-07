"""BS-02 (#188): the ledger readers read a CONSUMER's ledger, with real counts.

One regression per covered issue -- #161, #162, #163, #164, #165 and #143's
SF-010 item. The fixtures are the ledger shapes the meta-harness issues
(DEF-440..444) reported: a column-0 list (what PyYAML's `safe_dump` emits),
nested `surface:` sub-keys, the §4.1 tokens plus `UNDECIDED`, and a ledger at
a path outside this repository's hardcoded backlog list.

The failure mode every issue shares is a confident wrong answer -- most often a
silent 0 -- so every test below asserts a real, non-zero count.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import disposition as D  # noqa: E402
from scripts import improvement_ledger as L  # noqa: E402

SCRIPTS = ROOT / "skills" / "spec-double-2" / "scripts"
DISPOSITION = SCRIPTS / "disposition.py"
IMPROVEMENT_LEDGER = SCRIPTS / "improvement_ledger.py"
BUG_ATTRIBUTION = ROOT / "skills" / "spec-double-2" / "references" / "bug_attribution.md"

#: (id, channel, skill_change) -- seven rows: the three §4.1 tokens CA-02 did not
#: have, two UNDECIDED channels, one CA-02 token, and ONE genuinely
#: off-vocabulary `reading` (the §2 mistake #164 describes), so the advisory
#: has exactly one honest row to report.
ROWS = [
    ("DEF-200", "test-graph", "UNDECIDED"),
    ("DEF-201", "test-graph", "UNDECIDED"),
    ("DEF-202", "tlc", "UNDECIDED"),
    ("DEF-203", "cross-implementation", "UNDECIDED"),
    ("DEF-204", "UNDECIDED", "'proposed(spec-double-2, #188)'"),
    ("DEF-205", "UNDECIDED", "UNDECIDED"),
    ("DEF-206", "reading", "none"),
]


def ledger_text(indent: str, *, planted_duplicate: str | None = None) -> str:
    """A findings ledger whose list starts at `indent` ("" = column 0).

    Every row carries a nested `surface:` mapping, whose sub-keys sit exactly
    where the old pattern looked for row keys in the column-0 layout.
    """
    k = indent + "  "
    lines = ["findings:"]
    for rid, channel, skill_change in ROWS:
        lines += [
            f"{indent}- id: {rid}",
            f"{k}found_by: MH-48",
            f"{k}channel: {channel}",
            f"{k}disposition: carried",
            f"{k}disposition_ticket: '#97'",
            f"{k}skill_change: {skill_change}",
            f"{k}surface:",
            f"{k}  production:",
            f"{k}  - specs/desired_program_model/deferred_findings.yaml",
            f"{k}  tla: []",
            f"{k}  adapters: []",
            f"{k}  test_graph: []",
        ]
        if planted_duplicate == rid:
            lines.append(f"{k}found_by: MH-49")
    return "\n".join(lines) + "\n"


def run(script: pathlib.Path, *args: str, cwd: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], cwd=str(cwd),
                          capture_output=True, text=True)


# -- #161: CHANNELS lags §4.1; UNDECIDED reported as drift -------------------


def test_161_disposition_channels_accept_section_4_1_tokens_and_undecided():
    off = D.off_vocabulary_channels([{"id": r, "channel": c} for r, c, _ in ROWS])
    # Before the fix: 6 rows (2 test-graph, tlc, cross-implementation, 2 UNDECIDED)
    # plus the real one. After: exactly the real one.
    assert off == [("DEF-206", "reading")]


def test_161_disposition_advisory_prints_one_row_not_seven(tmp_path):
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(ledger_text("  "), encoding="utf-8")  # nested: isolates #161 from #162
    done = run(DISPOSITION, "--ledger", str(ledger), "--all", cwd=tmp_path)
    assert "0 of 7 findings" in done.stdout, done.stdout + done.stderr
    assert "ADVISORY (not a clause): 1 row(s)" in done.stdout, done.stdout
    assert "DEF-206: 'reading'" in done.stdout


# -- #162: duplicate_keys assumes a 2-space list ----------------------------


@pytest.mark.parametrize("indent", ["", "  "], ids=["column-0", "nested"])
def test_162_disposition_reads_both_layouts_with_no_false_duplicates(indent):
    assert D.duplicate_keys(ledger_text(indent)) == []


@pytest.mark.parametrize("indent", ["", "  "], ids=["column-0", "nested"])
def test_162_disposition_names_a_planted_duplicate_precisely(indent):
    dups = D.duplicate_keys(ledger_text(indent, planted_duplicate="DEF-203"))
    assert [(rid, key, len(ns)) for rid, key, ns in dups] == [("DEF-203", "found_by", 2)]


def test_162_column_0_ledger_loads_seven_rows_and_improvement_ledger_reads_them(tmp_path):
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(ledger_text(""), encoding="utf-8")
    rows, faults = D.read_rows(ledger)
    assert len(rows) == 7 and faults == []
    done = run(DISPOSITION, "--ledger", str(ledger), "--all", cwd=tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "REFUSING" not in done.stderr
    assert "0 of 7 findings" in done.stdout
    records = L.read_backlog(ledger, (), problems := [])
    assert len(records) == 7, problems


# -- #143 SF-010: nested `surface:` sub-keys read as duplicate row keys -----


def test_143_sf010_disposition_nested_surface_keys_are_not_row_keys(tmp_path):
    text = ledger_text("")
    reported = {key for _, key, _ in D.duplicate_keys(text)}
    assert not reported & {"production", "tla", "adapters", "test_graph"}
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(text, encoding="utf-8")
    rows = D.load(ledger)  # raised SystemExit (STRUCTURAL) before the fix
    assert len(rows) == 7
    assert all(set(r["surface"]) == {"production", "tla", "adapters", "test_graph"} for r in rows)


# -- #163: improvement_ledger reads only this repo's hardcoded backlogs ------


def consumer_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """A consumer repository: the live ledger is the only record it has."""
    root = tmp_path / "consumer"
    live = root / D.LEDGER
    live.parent.mkdir(parents=True)
    live.write_text(ledger_text("  "), encoding="utf-8")  # nested: isolates #163
    return root


def test_163_improvement_ledger_default_reads_the_consumer_live_ledger(tmp_path):
    root = consumer_repo(tmp_path)
    done = run(IMPROVEMENT_LEDGER, "--repo-root", str(root), cwd=root)
    assert done.returncode == 0, done.stderr
    assert "improvement ledger -- 7 record(s) across 1 file(s)" in done.stdout, done.stdout


def test_163_improvement_ledger_reads_an_explicit_ledger_outside_the_defaults(tmp_path):
    root = consumer_repo(tmp_path)
    elsewhere = tmp_path / "elsewhere" / "findings.yaml"
    elsewhere.parent.mkdir()
    elsewhere.write_text(ledger_text("  "), encoding="utf-8")
    done = run(IMPROVEMENT_LEDGER, "--repo-root", str(root), "--ledger", str(elsewhere), cwd=root)
    assert done.returncode == 0, done.stderr
    assert "improvement ledger -- 7 record(s) across 1 file(s)" in done.stdout, done.stdout
    # `--ledger` replaces the defaults, it does not add to them.
    assert D.LEDGER not in done.stdout


# -- #164: §4.1 says "Nine tokens" over ten rows; §2 names `reading` a channel


def section_4_1() -> str:
    text = BUG_ATTRIBUTION.read_text(encoding="utf-8")
    return text.split("### 4.1 ", 1)[1].split("\n### ", 1)[0]


def test_164_bug_attribution_token_count_matches_its_table_and_disposition():
    sec = section_4_1()
    tokens = re.findall(r"^\| `([a-z-]+)` \| \*\*(?:automated|hand|reading)\*\* \|", sec, re.M)
    assert len(tokens) == 10
    words = {9: "Nine", 10: "Ten", 11: "Eleven"}
    assert f"**{words[len(tokens)]} tokens.**" in sec
    assert "reading" not in tokens
    # The instrument's vocabulary and the page's are the same set (#161 + #164).
    assert set(tokens) == D.CHANNELS


def test_164_bug_attribution_section_2_does_not_name_reading_as_a_channel():
    text = BUG_ATTRIBUTION.read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "channel is `reading`" not in flat
    assert "`channel` may be `reading`" not in flat
    assert "**`reading` is a CLASS, not a token**" in section_4_1()


# -- #165: no UNDECIDED in the skill_change grammar --------------------------


def test_165_improvement_ledger_parses_undecided_on_its_own():
    parsed = L.parse_skill_change("UNDECIDED")
    assert parsed.verb == "undecided"
    assert not parsed.terminal
    assert parsed != L.parse_skill_change(None) and parsed != L.parse_skill_change("none")


def test_165_improvement_ledger_counts_undecided_apart_from_unparseable(tmp_path):
    root = consumer_repo(tmp_path)
    done = run(IMPROVEMENT_LEDGER, "--repo-root", str(root), cwd=root)
    out = done.stdout
    assert re.search(r"skill_change UNDECIDED \(asked, open\) \.+ 5$", out, re.M), out
    assert re.search(r"skill_change present but unparseable \.+ 0$", out, re.M), out
    assert re.search(r"no skill_change field at all \.+ 0$", out, re.M), out


def test_165_bug_attribution_grammar_spells_undecided():
    text = BUG_ATTRIBUTION.read_text(encoding="utf-8")
    assert re.search(r"^skill_change: none \|.*\| UNDECIDED$", text, re.M)
    assert "| `UNDECIDED` |" in text.split("### 2a.", 1)[1].split("\n### ", 1)[0]
