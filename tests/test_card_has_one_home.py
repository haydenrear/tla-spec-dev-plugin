"""SM-06: `references/eval_scorecard.md` is the ONE home for the card, executed.

## Why a check and not a convention

The card's dimensions, anchors and scoring rules were stated in seven other live
places. Nothing compared any of them to the card, and two of them had already
gone wrong in a way that was read forward for weeks: `PORTS-AS-ADAPTERS-EPIC.md`
restated the baseline table, its D5 row credited the control with a 4 that went
to the treatment, and its D1 row credited one arm with a 3 that both arms got --
**contradicting section 5 of the same document**. Both survived a change to the
instrument and were corrected by hand, mid-epic.

`declaration_executability_rule`: a pointer nothing executes will drift. That
applies to this rule as much as to the ones it replaces, so *"nothing but the
card states a dimension, an anchor or a scoring rule"* is executed here rather
than written down and hoped for.

**The gap mutant that justifies it, measured before anything was deleted.** Four
copies were made to DISAGREE with the card at `6aac1ec` and the whole repository
was asked whether it noticed:

| mutant | the copy | verdict |
|---|---|---|
| M1 | `README.md`'s dimension table, D3 and D4 swapped | **UNCAUGHT** |
| M2 | scoring rule 7 inverted in a judge's evidence packet | **UNCAUGHT** |
| M3 | scoring rules 2 and 7 inverted in every scaffolded card | **UNCAUGHT** |
| M4 | an anchor edited inside a sealed `scorecard.md` (**control**) | CAUGHT |

The full 1378-test suite, `demonstrate.py`, `score_tools check`, `audit` and
`serve` were all green on M1, M2 and M3. M4 -- the control -- went red on three
surfaces, so the green above is a fact about the copies and not about a broken
harness (R2). Run and record:
`specs/results/scorecards/subtract-to-measure/SM-06/run_dup_mutants.py`,
`dup-mutants.json`.

## What counts as a statement of the card, and where it comes from

**Every needle is derived from the card at run time.** Nothing in this file
spells a dimension name, an anchor or a scoring rule: a checker carrying its own
copy of the thing it de-duplicates is the joke that writes itself, and a
hardcoded list is the shape rejected at `EVAL-RERUN-DF-01` and again at
`ARM_MODULE_PREFIXES`. Change the card and the needles change with it.

Three kinds, all parsed by `score_tools.load_rubric`:

1. **A dimension** -- a `D<n>` key immediately followed by *any* of the five
   titles. Adjacency is required, so `"D2 = 2 on 27 of 27 cards"` beside the word
   "complexity" is a citation of a score and not a statement of the bar. Citing
   scores is what this repository is for. **Any** title rather than the key's own
   is deliberate: a copy that got the pairing WRONG is the copy that has already
   done damage here, and a per-key needle would be blind to precisely that.
2. **An anchor** -- the opening clause of one of the anchor texts, six words or
   more.
3. **A scoring rule** -- the bolded lead sentence of a numbered rule, four words
   or more.

Anchors and rules are matched on **content words**: lowercased, punctuation and
markdown stripped, a short stoplist removed. That is what lets a copy which
swapped a comma for an "and" and shouted one word in capitals still match the
rule it came from -- which is how M2's copy is found, and a literal match does
not find it. (The example is not reproduced here for the obvious reason: this
file may not state a scoring rule either, and the rule it applies to itself is
the rule it applies to everything else.)

**WHAT THIS CANNOT SEE, stated rather than discovered later.**

- **A paraphrase escapes.** README stated rule 2 in its own words, sharing no
  content-word run with the card's wording of it, and no tightening of this
  matcher will find that without matching ordinary English as well. Every copy
  that was a paraphrase was found by reading and deleted by hand; the next one
  will not be found by this. `test_the_blind_spots_are_declared_and_still_real`
  keeps that admission honest by demonstrating the miss.
- **One scoring rule is not watched at all.** Its lead sentence is three words,
  short enough that matching it would flag any sentence on the same subject. It
  is dropped rather than matched loosely, so a restatement of that one rule
  escapes. Which rule it is comes out of the card, not out of this file:
  `card_needles(...)["dropped_rules"]` names it.

## The one legitimate second copy, and what it costs to have one

A copy is exempt only when **something executes a comparison of it against the
card**, so a disagreement is loud rather than silent. That is the same bargain a
scaffolded `scorecard.md` strikes, and the reason M4 was the only mutant caught.

The exemption is **earned by demonstration, not declared**:
`test_the_guarded_copies_are_really_guarded` makes each guarded copy disagree and
asserts the refusal arrives. An entry in `GUARDED` with no demonstration behind
it is the thing this file exists to prevent, so adding one costs a test.

## Scope, stated rather than assumed

One principle, five instances: **a record of what was true when it was written
is not a live declaration, and rewriting a record to satisfy a checker is the
opposite of the point.** (The same reasoning `tests/test_source_citations.py`
gives for its own scope.) So out of scope are the card itself; `specs/.history/`;
records under `specs/results/`; the sealed `PREDICTIONS-*.md`, which
`check_prediction_seal.py` reads as written; and `deferred_findings.yaml`, whose
findings quote the text they are findings about -- the two wrong rows above
survive verbatim there on purpose, because a finding that deletes its own
subject is not a finding.

`.py` files under `specs/results/` are **in** scope. They are generators, not
records: `measure/build_evidence_packets.py` writes into the packet a judge is
handed, which is where a stale copy of a scoring rule does the most damage, and
it was M2.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "spec-double-2"
CARD = SKILL_ROOT / "references/eval_scorecard.md"
SCORE_TOOLS = REPO_ROOT / "examples/validation/scorecards/score_tools.py"

#: Repo-relative prefixes whose card statements are records, not declarations.
OUT_OF_SCOPE = {
    "skills/spec-double-2/references/eval_scorecard.md": "the card itself",
    "specs/.history/": "append-only close records",
    "examples/validation/PREDICTIONS": "sealed pre-dispatch predictions; "
                                       "check_prediction_seal.py reads them as written",
    "specs/desired_program_model/deferred_findings.yaml": "findings quote the text they "
                                                          "are findings about",
}

#: Under `specs/results/`, records are out and generators are in.
RESULTS = "specs/results/"
GENERATOR_SUFFIX = ".py"

#: A restatement something executes a comparison for. The value names the
#: comparison; `test_the_guarded_copies_are_really_guarded` demonstrates each.
GUARDED = {
    "examples/validation/scorecards/score_tools.py":
        "score_tools.NAMES is compared to the card's parsed dimension titles on every "
        "load_rubric() call, which raises RubricError on disagreement",
    "tests/test_score_tools.py":
        "the served-digest fixtures assert `text.count(old) == 1` against the card "
        "before using each fragment, so a fragment that stops matching fails there",
    # RM-03. The frozen version 3 bar is a WHOLE second copy of the card, and it
    # exists because the card's own change rule demands one: "keep the old
    # anchors" and "freeze the rubric file before you edit it". THE TWO RULES ARE
    # IN TENSION AND THIS ENTRY IS WHERE THEY MEET. It earns its exemption the
    # same way the others do -- something runs a comparison, and the comparison
    # is the one that matters for a frozen bar: it must still digest to the
    # anchors digest versions 1 to 3 declare, or it has stopped being the bar it
    # claims to freeze.
    "examples/validation/scorecards/rubric_v3_frozen.md":
        "load_rubric() parses it as scorecard version 3 and its anchors digest is "
        "compared to the sha256:eeccf4576bc6fd85 that the card's own version history "
        "declares for versions 1, 2 and 3",
    # CL-03. The same tension, one version later. The change rule says FREEZE THE
    # RUBRIC FILE BEFORE YOU EDIT IT, and CL-03's version 5 bump is the first one
    # that had to, because it is the first whose SERVED digest moves. The
    # exemption is earned the same way: something runs the comparison, and for a
    # frozen bar it is the only comparison that matters -- this file must still
    # parse as version 4 and still digest to the anchors AND served digests the
    # card's own version history declares for version 4, or it has stopped being
    # the bar it claims to freeze and the version 4 arm of CL-03's re-score is
    # not a version 4 arm.
    "examples/validation/scorecards/rubric_v4_frozen.md":
        "load_rubric() parses it as scorecard version 4 and both of its digests are "
        "compared to the row the card's own version history declares for version 4 -- "
        "sha256:f73b4d82638f09df anchors and sha256:a213a36770ccab09 served -- in "
        "tests/test_score_tools.py::test_the_frozen_v4_bar_is_still_the_v4_bar",
}

TEXTY = (".md", ".py", ".toml", ".yaml", ".yml", ".txt", ".tla", ".json", ".sh")
# Per-checkout AGENT HOMES, which `wt new` creates and .gitignore excludes. They
# hold real copies of the card and of the instruments -- a whole installed
# skill-manager tree -- and they are NOT this repository. Scanning them made
# this tripwire and the thermometer scan report 2 failures in every ticket
# worktree while an archive of the same commit was clean (RD-01-DF-02), so
# "the suite is green" was never true where every ticket agent works.
#
# Pruned by NAME rather than by asking git, deliberately: `demonstrate.py` runs
# this tripwire in a staged copy with no repository around it, where
# `git check-ignore` decides nothing and the failing demonstration would pass
# for the wrong reason.
AGENT_HOMES = {".skill-manager", ".claude", ".codex", ".gemini"}

# Build output is the same argument one directory over: `test_graph` writes
# whole plugin trees as fixtures under `test_graph/build/validation-reports/`,
# which carry real copies of the card. Running the test graphs and then this
# tripwire reported the card "stated outside its one home" at a path that is a
# fixture of itself (SI-27). Nothing tracked lives under a `build/`.
BUILD_OUTPUT = {"build"}

PRUNE = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache",
         ".mypy_cache"} | AGENT_HOMES | BUILD_OUTPUT

STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "be", "and", "or", "of",
             "to", "in", "on", "it", "its", "that", "this", "by", "as"}

MIN_ANCHOR_WORDS = 6
MIN_RULE_WORDS = 4


def _load_score_tools():
    spec = importlib.util.spec_from_file_location("sm06_score_tools", SCORE_TOOLS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def st():
    return _load_score_tools()


@pytest.fixture(scope="module")
def rubric(st):
    return st.load_rubric(CARD)


def _flat(text: str) -> str:
    """Whitespace-insensitive, so a reflowed copy is still a copy."""
    return " ".join(text.split())


def _content(text: str) -> str:
    """Content words only: no markdown, no punctuation, no stopwords.

    This is what makes a copy that reworded its connectives still a copy. `>=`
    and `:` survive because `file:line` and `score >= 2` are the substance of a
    rule rather than its punctuation.
    """
    text = re.sub(r"[^0-9a-z:\u2265<>=]+", " ", text.lower())
    return " ".join(w for w in text.split() if w not in STOPWORDS)


def _lead(rule: str) -> str:
    m = re.match(r"\s*\*\*(.+?)\*\*", rule)
    return m.group(1).strip() if m else ""


def card_needles(rubric: dict) -> dict:
    """Everything the card says, parsed out of the card. Nothing is spelled here."""
    anchors, rules = [], []
    titles = [_flat(d["name"]) for d in rubric["dimensions"].values()]
    # ANY key next to ANY title, not each key next to its own. A swapped table --
    # M1's shape, and the shape both wrong rows in PORTS-AS-ADAPTERS-EPIC.md had
    # -- pairs a key with the WRONG title, so a per-key needle would miss exactly
    # the copy that has already gone wrong here.
    dimensions = re.compile(
        r"\b(D[1-5])\b[^\w]{0,6}(" + "|".join(re.escape(t) for t in titles) + r")", re.I)
    for key, dim in rubric["dimensions"].items():
        for score, anchor in dim["anchors"].items():
            clause = re.split(r"[.;]", _flat(anchor))[0].strip(" *")
            if len(clause.split()) >= MIN_ANCHOR_WORDS:
                anchors.append((f"{key} anchor {score}", _content(clause)))
    dropped = []
    for i, rule in enumerate(rubric["scoring_rules"], 1):
        lead = _flat(_lead(rule)).strip(" .")
        if len(lead.split()) >= MIN_RULE_WORDS:
            rules.append((f"rule {i}", _content(lead)))
        else:
            dropped.append(f"rule {i}")
    return {"dimensions": dimensions, "anchors": anchors, "rules": rules,
            "dropped_rules": dropped}


def restatements(rel: str, text: str, needles: dict) -> list[str]:
    """Lines of `rel` that state a dimension, an anchor or a scoring rule."""
    found = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = _flat(raw)
        if not line:
            continue
        content = _content(line)
        for m in needles["dimensions"].finditer(line):
            found.append(f"{rel}:{i}: states dimension {m.group(1)} -- {line[:120]}")
        for label, needle in needles["anchors"]:
            if needle in content:
                found.append(f"{rel}:{i}: states {label} -- {line[:120]}")
        for label, needle in needles["rules"]:
            if needle in content:
                found.append(f"{rel}:{i}: states scoring {label} -- {line[:120]}")
    return found


def in_scope(rel: str) -> bool:
    if not rel.endswith(TEXTY):
        return False
    if any(rel == k or rel.startswith(k) for k in OUT_OF_SCOPE):
        return False
    if rel.startswith(RESULTS) and not rel.endswith(GENERATOR_SUFFIX):
        return False
    return True


def scanned_files() -> list[str]:
    """Walk the tree rather than asking git.

    `demonstrate.py` runs a tripwire in a STAGED copy with no repository around
    it, and `git ls-files` there returns nothing -- which would make the failing
    demonstration below pass for the wrong reason.

    Symlinks are not followed, and that is load-bearing rather than tidy.
    `examples/agent_integration/eval-plugin/skills/spec-double-compiler` is a
    symlink to this repository's own skill directory -- the eval plugin carries
    the skill surface by reference so it cannot drift (E-14) -- so following it
    reported `references/eval_scorecard.md`, THE CARD'S ONE HOME, as a
    restatement of itself at a second path. A symlink is a second NAME, never a
    second statement: it cannot hold different bytes, so nothing hides behind
    this skip.
    """
    out = []
    stack = [REPO_ROOT]
    while stack:
        d = stack.pop()
        for child in sorted(d.iterdir()):
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name not in PRUNE:
                    stack.append(child)
                continue
            rel = str(child.relative_to(REPO_ROOT))
            if in_scope(rel):
                out.append(rel)
    return out


@pytest.fixture(scope="module")
def offenders(rubric):
    needles = card_needles(rubric)
    out: dict[str, list[str]] = {}
    for rel in scanned_files():
        try:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = restatements(rel, text, needles)
        if hits:
            out[rel] = hits
    return out


def test_only_the_card_states_a_dimension_an_anchor_or_a_scoring_rule(offenders):
    """THE RULE, EXECUTED. This is the failing input M1, M2 and M3 could not find.

    A failure here is not a style complaint. It means a second statement of the
    bar exists that nothing compares to the bar, which is how the two wrong rows
    in `PORTS-AS-ADAPTERS-EPIC.md` survived an instrument change.

    The fix is a POINTER, never a corrected copy: link
    `references/eval_scorecard.md`, and for results link
    `specs/results/scorecards/SELF-IMPROVEMENT.md`.
    """
    unguarded = {k: v for k, v in offenders.items() if k not in GUARDED}
    lines = [line for v in unguarded.values() for line in v]
    assert not lines, (
        "the card is stated outside references/eval_scorecard.md:\n  "
        + "\n  ".join(lines)
        + "\n\nReplace the copy with a pointer. If the copy is load-bearing it has to be "
          "compared to the card by something that runs -- add it to GUARDED and "
          "demonstrate the comparison, as score_tools.NAMES does."
    )


def test_every_guarded_entry_still_restates_something(offenders):
    """A GUARDED entry that no longer restates anything is a stale exemption.

    It costs nothing to leave behind and it silently pre-authorises the next copy
    that lands in the same file, which is exactly how a whitelist rots. Delete
    the entry when the copy goes.
    """
    stale = sorted(k for k in GUARDED if k not in offenders)
    assert not stale, (
        f"GUARDED exempts {stale}, which no longer restate the card. Remove the entry: "
        "an exemption nobody needs is an exemption nobody re-reads."
    )


def test_the_guarded_copies_are_really_guarded(st):
    """The exemptions, earned rather than asserted.

    `score_tools.NAMES` may spell the dimension titles ONLY because `load_rubric`
    refuses when it and the card disagree. Make them disagree and the refusal has
    to arrive -- otherwise `NAMES` is an ordinary stale copy wearing a
    justification.
    """
    assert st.load_rubric(CARD), "the card must parse before the guard means anything"

    original = dict(st.NAMES)
    # A dimension the CURRENT card still scores. `NAMES` keeps an entry for every
    # dimension ever scored -- 73 sealed cards carry all five and R-H4 says they
    # are never edited -- so the guard can only be demonstrated on a key the
    # current file actually contains.
    victim = sorted(st.scored_dims(st.load_rubric(CARD)["card_version"]))[0]
    st.NAMES[victim] = original[victim] + " (SM-06 made this disagree)"
    try:
        with pytest.raises(st.RubricError, match="the dimension key has drifted"):
            st.load_rubric(CARD)
    finally:
        st.NAMES.clear()
        st.NAMES.update(original)
    assert st.load_rubric(CARD)["dimensions"], "the guard must pass once the copy agrees"

    # The second guarded copy: every fragment `tests/test_score_tools.py` holds
    # is asserted to occur exactly once in the card before it is used, so a
    # fragment that stops matching fails there rather than rotting quietly.
    # The third guarded copy: the frozen version 3 bar. It is a second statement
    # of the card ON PURPOSE, because the change rule cannot be followed without
    # one, and what keeps it from being an ordinary stale copy is that it still
    # has to BE the bar it froze.
    frozen = st.load_rubric(REPO_ROOT / "examples/validation/scorecards/rubric_v3_frozen.md")
    assert frozen["card_version"] == 3, frozen["card_version"]
    declared = {v["version"]: v["anchors_digest"] for v in st.load_rubric(CARD)["versions"]}
    assert frozen["anchors_digest"] == declared[3] == declared[2] == declared[1], (
        "the frozen version 3 rubric no longer digests to the anchors the card's "
        "version history declares for versions 1 to 3. It has stopped being the bar "
        "it claims to freeze, and every re-score run against it measured something "
        "nobody can name.")
    assert set(frozen["dimensions"]) == {"D1", "D2", "D3", "D4", "D5"}

    fixtures = (REPO_ROOT / "tests/test_score_tools.py").read_text(encoding="utf-8")
    assert "assert text.count(old) == 1" in fixtures, (
        "tests/test_score_tools.py is exempted because it compares its fragments to the "
        "card; that comparison is gone, so the exemption is no longer earned"
    )


def test_a_disagreeing_copy_of_a_scoring_rule_is_caught(rubric, tmp_path):
    """R1: the demonstrated FAILING input, on the mutant shape that was UNCAUGHT.

    M2 inverted scoring rule 7 inside a judge's evidence packet and nothing in
    the repository went red. The same inversion is applied here to a throwaway
    file, and the matcher has to find it.
    """
    needles = card_needles(rubric)
    label, _ = needles["rules"][0]
    lead = _flat(_lead(rubric["scoring_rules"][0])).strip(" .")
    fake = f"The rules that make a score hard to game:\n\n- **{lead}** -- optional.\n"
    hits = restatements("CHARTER.md", fake, needles)
    assert hits, f"a disagreeing restatement of scoring {label} was not detected"
    assert any("scoring rule" in h for h in hits)


def test_a_disagreeing_copy_of_the_dimension_table_is_caught(rubric):
    """The M1 shape: a charter's restated dimension table with two rows swapped."""
    needles = card_needles(rubric)
    dims = rubric["dimensions"]
    a, b = sorted(dims)[:2]
    swapped = (f"| **{a}** | {dims[b]['name']} | ... |\n"
               f"| **{b}** | {dims[a]['name']} | ... |\n")
    hits = restatements("CHARTER.md", swapped, needles)
    assert len(hits) >= 2, f"a swapped dimension table was not detected: {hits}"


def test_a_score_citation_is_not_a_statement_of_the_card(rubric):
    """The false positive that would make this check unusable, ruled out.

    "D2 = 2 on 27 of 27 cards ever written" is what this repository is FOR. A
    checker that flags it would be turned off within a week, and a checker that
    is off catches nothing.
    """
    needles = card_needles(rubric)
    citation = ("D2 = 2 on 27 of 27 cards ever written, and the question is whether the "
                "card can measure complexity at all. Score the removal on D2 anchor 3.\n")
    assert not restatements("CHARTER.md", citation, needles)


def test_the_check_is_not_vacuous_on_the_card_itself(rubric):
    """A scanner that matches nothing anywhere proves nothing (R2).

    The needles must still find the card's own statements in the card. If this
    fails, the parse or the matcher broke and every green above is meaningless.
    """
    needles = card_needles(rubric)
    hits = restatements("skills/spec-double-2/references/eval_scorecard.md", CARD.read_text(encoding="utf-8"),
                        needles)
    kinds = set()
    for h in hits:
        if "states dimension" in h:
            kinds.add("dimension")
        elif "states scoring rule" in h:
            kinds.add("rule")
        elif "states D" in h:
            kinds.add("anchor")
    assert {"dimension", "anchor", "rule"} <= kinds, (
        f"the matcher does not find all three kinds in the card itself; found {kinds}")


def test_the_blind_spots_are_declared_and_still_real(rubric):
    """R2 again, pointed at this instrument: say what it cannot see, and be right.

    Rule 6's lead is too short to match on and is dropped. If the card ever gives
    it a longer lead this test fails, which is the prompt to delete the blind-spot
    paragraph in the docstring above rather than let it become false.
    """
    needles = card_needles(rubric)
    assert needles["dropped_rules"], (
        "no scoring rule is dropped for a short lead any more -- the declared blind spot "
        "in this file's docstring is now false and must be removed")

    # And the paraphrase blind spot, demonstrated rather than asserted: rule 2
    # reworded the way README worded it is NOT found.
    paraphrase = "- **Any score >= 2 without a `file:line` citation is capped at 1.**\n"
    assert not [h for h in restatements("X.md", paraphrase, needles) if "rule 2" in h], (
        "the paraphrase blind spot is no longer real; update the docstring")
