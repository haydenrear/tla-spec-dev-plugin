"""`CA-06-DF-02`, consumed as an adapter conformance case (`CA-07`).

**The defect, filed by `CA-06` and confirmed by its reviewer.** The negative
corpus keyed each case's ``params`` by the TLA+ FORMAL parameter names, while
the positive corpus keys them by the names the module DECLARES in its own
action marker -- the names every shipped adapter reads. Over a full TLC state
graph the generator emits 11 negative cases for
``examples/distributed_history`` and all 11 died before asserting anything:
``KeyError: 'account'`` x7, ``KeyError: 'order'`` x4. The measured yield of
``--negative-cases`` on a real subject was zero cases EXECUTED.

**THIS FILE BUILDS AT TWO STATES, NOT THE WHOLE GRAPH, SO IT EMITS 9 AND NOT
11** -- ``KeyError: 'account'`` x7, ``KeyError: 'order'`` x2. Both figures are
real and they are not the same measurement; the 11 is the sealed pipeline run
in ``specs/results/scorecards/cut-the-apparatus/CA-07/`` and the 9 is what the
two commands in that directory's ``RESULTS.md`` reproduce. The two states are
enough because they reach all four negated actions and all four refusal
reasons; they are not enough to reproduce a count.

**The subject is real, not a fixture (`R1`).** Everything below is
``examples/distributed_history`` -- this repository's own worked example: its
``Internal.tla``, its ``Internal.cfg`` constants, the corpus already committed
under ``specs/generated/``, its ``case_adapters.toml`` mapping, and the adapter
classes that mapping names.

**Why a CONFORMANCE case and not a generator unit test.** The defect is a
disagreement between two artifacts -- what the corpus emits and what the
adapter reads -- and only one of them lives in ``scripts/``. A test of the
generator alone is green on either keying, because either keying is
self-consistent. That is how this survived three epics.

**WHAT THIS FILE DOES NOT COVER, found by the independent reviewer of PR #269
and stated here rather than in a document nobody reads next to the code.**
`CA-06-DF-02` has a SECOND face: the same key mismatch made
``negative_cases_for_corpus``'s soundness cross-check compare declared names
against formal ones, so it examined nothing on any model that declares a
marker. `CA-07` repaired that too -- and **NOTHING BELOW PROTECTS THE REPAIR.**
Every call here passes ``edges=[]``, so the cross-check loop is empty by
construction; the reviewer deleted the 11-line remap and this file still
reported 5 passed. Roughly a third of `CA-07`'s production delta is therefore
evidenced by a TRANSCRIPT and not by an executable check. Filed as
`CA-07-DF-05`. Covering it needs dump ``edges`` whose after-states carry a
populated action marker, which is the one thing two hand-written states cannot
supply without transcribing a third.

**The one transcribed input** is the pair of states the cases are built at:
TLC is the only thing that produces a state graph and a unit test may not run
it. Both are the model's own -- ``Internal.tla``'s ``InternalInit`` and the
state one ``CreateAccount`` later -- and
``test_the_states_carry_exactly_the_modules_variables`` fails if the module's
variables move underneath them. Nothing else here is typed rather than read:
the argument names on both sides come out of checked-in artifacts.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "spec-double-2"
sys.path.insert(0, str(ROOT))

from scripts.analyze_complexity import parse_cfg_constants  # noqa: E402
from scripts.generate_cases_from_tlc_dump import (  # noqa: E402
    GuardEvaluator,
    coerce_cfg_constant,
    extract_action_signatures,
    negative_cases_for_corpus,
    parse_tla_definitions,
    resolve_next_relation,
)
from scripts.infer_action_params import build_recipes, parse_variables  # noqa: E402

EXAMPLE = ROOT / "examples" / "distributed_history"
SPEC = EXAMPLE / "specs" / "program_model"
# E-06 (#313): this was hardcoded to "spec_unit" while the generator writes
# VIEW_OUTPUT_DIRS["internal"] == "spec-unit". The two drifted apart, the
# committed corpus was renamed to match the generator, and this line was the one
# consumer that still named the old spelling -- caught by set-comparing the
# suite against main, not by anything here. Derived from the generator now, so
# the next rename moves this with it instead of orphaning it.
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
try:
    from generate_cases_from_tlc_dump import VIEW_OUTPUT_DIRS  # type: ignore
finally:
    sys.path.pop(0)

# BS-08: the committed example corpus moved here from
# examples/distributed_history/specs/generated/, which 76ef2758 ("removed
# generated", 2026-09-14) deleted and gitignored. Restored byte-for-byte from
# 76ef2758^ as a TEST fixture, outside any directory a generator writes.
COMMITTED_CORPUS = ROOT / "tests" / "fixtures" / "distributed_history_generated" / VIEW_OUTPUT_DIRS["internal"]
FIXTURE_MODEL = ROOT / "examples" / "validation" / "ab" / "model"

# `Internal.tla:8-14` -- `InternalInit`, and the state one `CreateAccount`
# later. These are the only values in this file that were typed rather than
# read out of an artifact.
INITIAL = {
    "accounts": frozenset(),
    "carts": {"acct-1": ()},
    "orders": {
        order: {"account": "acct-1", "items": (), "status": "none"}
        for order in ("order-1", "order-2")
    },
    "outbox": frozenset(),
    "projections": {"order-1": "none", "order-2": "none"},
    "lastInternalAction": {"name": "Init", "params": ()},
}
WITH_AN_ACCOUNT = dict(INITIAL, accounts=frozenset({"acct-1"}))


def _example_module(dotted: str) -> ModuleType:
    """Import one module of the example by the name its own mapping uses.

    Loaded by path under a private name, which keeps THIS import off the
    ``specs`` name. The example root itself is still added to ``sys.path``,
    because that is what ``--import-root`` does and what ``adapters.py`` needs
    to reach ``ecommerce_backend``.

    **AND THAT INSERT DOES SHADOW THIS REPOSITORY'S ``specs/``, which an
    earlier version of this docstring claimed it could not.** Corrected on the
    independent review of PR #269, which confirmed that after this runs,
    ``import specs.program_model.adapters`` resolves to the example's file:
    the example ships ``specs/__init__.py`` and is therefore a REGULAR
    package, this repository's ``specs/`` has none and is a NAMESPACE package,
    and a regular package wins wherever it sits on the path. Nothing in the
    suite imports ``specs.*``, so nothing breaks today -- it is an
    ordering-dependent landmine for whoever adds the first such import.
    Declared rather than worked around, as `CA-07-DF-06`.
    """
    if str(EXAMPLE) not in sys.path:
        sys.path.insert(0, str(EXAMPLE))
    name = f"_ca07_{dotted.replace('.', '_')}"
    if name not in sys.modules:
        path = EXAMPLE.joinpath(*dotted.split(".")).with_suffix(".py")
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None, path
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _negative_corpus():
    """The negative pass on the real module, exactly as the CLI drives it.

    The CLI passes the text of the named ``.tla`` and nothing else
    (``generate_cases_from_tlc_dump.py``: ``tla_source=tla_path.read_text()``),
    so this does too rather than resolving an ``EXTENDS`` the CLI does not.
    """
    tla = (SPEC / "Internal.tla").read_text()
    return negative_cases_for_corpus(
        states={"1": INITIAL, "2": WITH_AN_ACCOUNT},
        edges=[],
        tla_source=tla,
        cfg_text=(SPEC / "Internal.cfg").read_text(),
        view="internal",
        action_metadata={},
        state_projector=_example_module("specs.program_model.tlc_projection").project_visible_state,
        dedupe="guard-reads",
        only_actions=(),
        param_recipes=build_recipes(tla),
        start_index=1,
    )


def _committed_argument_names() -> dict[str, frozenset[str]]:
    """The argument names the corpus ALREADY IN THIS REPOSITORY uses per action."""
    corpus = str(COMMITTED_CORPUS)
    if corpus not in sys.path:
        sys.path.insert(0, corpus)
    cases = importlib.import_module("ecommerce_internal_cases")
    return {case.input.action: frozenset(case.input.params) for case in cases.CASES}


def _shipped_adapters() -> dict[str, type]:
    """The adapter classes ``case_adapters.toml`` names, resolved as it names them."""
    mapping = tomllib.loads((SPEC / "case_adapters.toml").read_text())
    declared = {block["adapter"].split(":")[0] for block in mapping["adapters"].values()}
    assert declared == {"specs.program_model.adapters"}, declared
    module = _example_module("specs.program_model.adapters")
    return {
        action: getattr(module, block["adapter"].split(":")[1])
        for action, block in mapping["adapters"].items()
    }


def test_the_states_carry_exactly_the_modules_variables() -> None:
    """The drift guard on the only transcribed input in this file."""
    declared = set(parse_variables((SPEC / "Internal.tla").read_text()))
    for state in (INITIAL, WITH_AN_ACCOUNT):
        assert set(state) == declared


def test_the_negative_pass_reaches_every_action_the_model_lets_it_negate() -> None:
    """Without this, a keying assertion over an empty corpus would pass."""
    cases, report = _negative_corpus()
    assert report.negated == ("AddCartItem", "Checkout", "CreateAccount", "ProjectOrder")
    assert {case.edge.action for case in cases} == set(report.negated)


def test_the_negative_corpus_names_its_arguments_as_the_committed_corpus_does() -> None:
    """`CA-06-DF-02`: two corpora over one model must agree on one contract.

    Neither side of this comparison is written here. The left is what the
    generator emits; the right is the corpus checked in for the example (under
    ``tests/fixtures/distributed_history_generated/`` since BS-08), which every adapter in ``case_adapters.toml`` was
    written against.
    """
    cases, _ = _negative_corpus()
    emitted: dict[str, frozenset[str]] = {}
    for case in cases:
        emitted.setdefault(case.edge.action, frozenset(case.params))
    assert emitted == _committed_argument_names()


def test_the_shipped_adapters_execute_every_negative_case() -> None:
    """The defect as `CA-06`'s reviewer measured it: 11 dead before any assertion.

    This drives ``run``, the entry point the runner calls, so the case's own
    before-state is loaded into the store exactly as it is in a shipped run.
    """
    cases, _ = _negative_corpus()
    adapters = _shipped_adapters()
    failures: list[str] = []
    for case in cases:
        shim = SimpleNamespace(
            name=case.name,
            before=case.before,
            input=SimpleNamespace(action=case.edge.action, params=dict(case.params)),
        )
        try:
            adapters[case.edge.action]().run(shim)
        except Exception as error:  # noqa: BLE001 -- the failure IS the finding
            failures.append(
                f"{case.name} via {case.edge.action}: {type(error).__name__}: {error}"
            )
    assert not failures, "\n".join(failures)


def test_a_module_that_declares_no_action_marker_keeps_its_formal_names() -> None:
    """The constraint `CA-06` named, and why the sealed tables cannot move.

    ``QuotaLedger`` is the fixture whose kill tables this programme quotes
    throughout. It declares no action marker, so it declares no argument
    names, so there is nothing to re-key and its corpus is byte-identical
    either side of this change.

    Imported here rather than at module scope on purpose: with the fix backed
    out, the three cases above must fail ON THE DEFECT rather than the whole
    module failing to import.
    """
    from scripts.generate_cases_from_tlc_dump import declared_param_names

    tla = (FIXTURE_MODEL / "QuotaLedger.tla").read_text()
    cfg = (FIXTURE_MODEL / "QuotaLedger.cfg").read_text()
    definitions = parse_tla_definitions(tla)
    evaluator = GuardEvaluator(
        definitions,
        {name: coerce_cfg_constant(value) for name, value in parse_cfg_constants(cfg).items()},
        parse_variables(tla),
    )
    signatures, _ = extract_action_signatures(
        definitions, evaluator, resolve_next_relation(cfg, definitions)
    )
    assert signatures, "the fixture must still yield signatures, or this proves nothing"
    for name, signature in signatures.items():
        assert declared_param_names(signature.body, signature.params, "internal") == {}, name
