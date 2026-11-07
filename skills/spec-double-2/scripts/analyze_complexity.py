#!/usr/bin/env python3
"""The complexity DESCRIPTOR for a constrained-profile TLA+ spec + cfg.

A factual pass-through for TLA+ complexity: it measures the model and reports
what is there, so an agent has numbers to reason from **before** TLC ever
runs. Facts, not judgment -- it never suggests an architectural move (CD-01;
the earlier suggested-move machinery was confidently wrong on standard TLA+
and was removed; suggestions may return later, earned from real-app
observations).

What it emits:

* the per-variable domain cardinality table -- domain sources merge
  PER-VARIABLE in a documented order (``TypeInvariant``, then ``TypeOK``, then
  the cfg-configured invariants, each resolved transitively; first source that
  resolves wins -- CD-05, VAL-17), parsed conjunct-wise so membership
  conjuncts may wrap across lines (CD-05, VAL-16), with operator-defined sets
  expanded through the EXTENDS hierarchy (CD-05, VAL-06) and the ``.cfg``
  constants applied. The exact coverage contract is
  references/architecture_tractability.md, "What The Domain Resolver Can And
  Cannot See";
* the state-space upper bound (the product of those cardinalities) and the
  dominant dimensions -- or an EXPLICIT "unknown" when no variable domain
  could be resolved, never a silent 1;
* the variables x actions read/write matrix -- ACTIONS ARE THE MEMBERS OF THE
  NEXT-STATE RELATION (the ``Next``/``ExternalNext`` disjuncts named by the
  cfg's ``NEXT`` or reached through ``SPECIFICATION``'s ``[][Next]_vars``),
  with every called operator's body expanded transitively so a prime inside a
  helper is attributed to the top-level action that calls it (CD-06, VAL-07 /
  VAL-12). Helper operators are NOT actions and get no column;
* a graph-modularity score over that matrix, the near-decomposable variable
  clusters, and the candidate port-crossing actions;
* dense rows (god-state variables touched by most actions) and dense columns
  (actions touching most variables);
* variables no configured invariant reads -- with invariant aliasing and
  composition (``INVARIANT Inv`` with ``Inv == RealInv``) resolved
  transitively;
* variables with no justification linkage, flagged as dead weight, when the
  manifest carries a ``justification:`` table; and
* **advisory complexity warnings** read against the thresholds in
  :mod:`scripts.budgets` (the MF-012 helper). Each threshold breach becomes a
  WARNING that names the component/variable/action and states the measured
  fact. It NEVER drives a nonzero exit and NEVER blocks promotion (MF-036;
  references/architecture_tractability.md, "Advisory, Not Blocking"). The scan
  exits nonzero only when it *cannot analyze* the model at all -- an unresolved
  module hierarchy (MF-030 fail-closed) or a usage error -- which is a
  different thing from "this model is complex".
* **self-configured fitness functions** (CD-03): when the project's agent has
  written rules over the descriptor's facts (``fitness_functions:`` in the
  manifest or a sibling ``fitness_functions.yaml``), each rule whose condition
  does not hold FIRES and is surfaced here so future agents are notified.
  There are NO built-in rules and firings are advisory -- they report, never
  block, and never change the exit code. See
  :mod:`scripts.fitness_functions` and ``references/fitness_functions.md``.

Two standing cautions are wired into the output rather than left to prose,
because both have already cost this repository real work (see MF-020):

1. **The distinct-state count is blind to deleted self-loops.** Removing an
   idempotent re-fire transition returns to an already-known state, so
   distinct states and depth do not move and a distinct-state gate sees
   nothing. ``--tlc-report``/``--baseline-tlc`` compare TLC runs and raise a
   RED FLAG when generated states drop at constant distinct states and depth.
2. **Projected reductions are unverified until the transition diff is read.**
   Every number in the output is tagged MEASURED or PROJECTED, and no
   projected figure is ever presented as a finding.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spec_paths import EvidencePathError, resolve_evidence_out  # noqa: E402

# Exit codes.
EXIT_PASS = 0
# MF-036: this is the "I could not analyze this model" exit, NOT "this model is
# complex". A complex model now exits EXIT_PASS with advisory warnings; only an
# unresolvable module hierarchy (MF-030 fail-closed) reaches here. The old name
# is retained for import compatibility.
EXIT_ANALYSIS_ERROR = 1
EXIT_BUDGET_EXCEEDED = EXIT_ANALYSIS_ERROR
EXIT_USAGE = 2


# --------------------------------------------------------------------------
# TLA+ / cfg parsing (the constrained profile in references/tla_profile.md)
# --------------------------------------------------------------------------

_DEF_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]*)\))?\s*==\s*(.*)$")
_TERMINATOR_RE = re.compile(r"^====+\s*$")


def strip_comments(text: str) -> str:
    """Remove TLA+ line comments and block comments."""
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.DOTALL)
    out = []
    for line in text.splitlines():
        idx = line.find("\\*")
        out.append(line if idx < 0 else line[:idx])
    return "\n".join(out)


def parse_declaration_block(text: str, keyword: str) -> list[str]:
    """Parse a ``VARIABLES``/``CONSTANTS`` declaration into a name list."""
    # NOTE: horizontal whitespace only. `\s*` under re.MULTILINE would let `^`
    # anchor on an earlier blank line and swallow the newlines in between,
    # putting match.start() before the declaration.
    pattern = re.compile(rf"^[ \t]*{keyword}S?\b(.*)$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return []
    lines = text[match.start() :].splitlines()
    collected: list[str] = []
    first = re.sub(rf"^[ \t]*{keyword}S?\b", "", lines[0])
    buffer = [first]
    def _still_open() -> bool:
        """Is the declaration syntactically unfinished?

        TLA+ separates declared names with commas, so content ending in a comma
        PROMISES another name. A blank line cannot be the end of the block while
        that promise is outstanding.

        This is what a wrapped comment looks like after `strip_comments`:

            CONSTANTS
              Orchestrator,    \\* the control-plane principal that
                               \\* OWNS the kickoff streams
              TracerConfigured,\\* ...
              Branched         \\* ...

        The continuation line is pure comment, so stripping it leaves a blank
        line in the MIDDLE of the declaration. Breaking there silently dropped
        every name below it -- and the caller then reported the loss as
        "<config>.cfg assigns CONSTANT X, which <module>.tla does not declare",
        blaming a correct config for a declaration the parser had given up on.
        """
        tail = " ".join(buffer).rstrip()
        return tail.endswith(",")

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            if _still_open():
                continue
            if collected or any(part.strip() for part in buffer):
                break
            continue
        # A new definition or declaration ends the block.
        if _DEF_RE.match(stripped) or _TERMINATOR_RE.match(stripped):
            break
        if re.match(r"^(VARIABLE|CONSTANT|ASSUME|EXTENDS|LOCAL)", stripped):
            break
        buffer.append(stripped)
    joined = " ".join(buffer)
    for chunk in joined.split(","):
        name = chunk.strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            collected.append(name)
    return collected


@dataclass
class Definition:
    name: str
    params: list[str]
    body: str


def parse_definitions(text: str) -> list[Definition]:
    """Split a module body into top-level ``Name == body`` definitions."""
    lines = text.splitlines()
    defs: list[Definition] = []
    current: Definition | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal current, body_lines
        if current is not None:
            current.body = "\n".join(body_lines)
            defs.append(current)
        current = None
        body_lines = []

    for line in lines:
        if _TERMINATOR_RE.match(line.strip()):
            flush()
            continue
        match = _DEF_RE.match(line)
        # Only a definition when it starts at column 0 (top level).
        if match and not line[:1].isspace():
            flush()
            params = [p.strip() for p in (match.group(2) or "").split(",") if p.strip()]
            current = Definition(name=match.group(1), params=params, body="")
            body_lines = [match.group(3)]
        elif current is not None:
            body_lines.append(line)
    flush()
    return defs


# --------------------------------------------------------------------------
# EXTENDS resolution (MF-030)
# --------------------------------------------------------------------------
#
# The analyzer used to read one .tla file and stop. On a decomposed model --
# the architecture SKILL.md mandates -- that scores only the declarations
# literally present in that file and silently drops everything reached through
# EXTENDS. The error is NEVER conservative: missing variables always shrink the
# product bound, so the gate fails toward PASS. MF-023 measured `External`
# reporting bound = 1 over 2 of its 9 variables for exactly this reason.
#
# The resolver below follows EXTENDS through the module hierarchy and unions
# the declarations the analyzer reads (VARIABLES, CONSTANTS, and the top-level
# definitions that carry TypeInvariant, Init, and the actions) into a single
# resolved view. What it does and does NOT handle is declared explicitly, and
# every construct it cannot model FAILS CLOSED with a named error rather than
# under-reporting -- see references/architecture_tractability.md, "No
# Degenerate Escapes": when you cannot resolve something, write the failure,
# not a smaller number.
#
# HANDLED:
#   * EXTENDS of one or more sibling modules, transitively, deduped, with the
#     extending module's own declarations overriding inherited names.
#   * EXTENDS of the standard TLA+ library modules below, which declare no
#     VARIABLES/CONSTANTS the bound reads and are skipped rather than resolved.
#
# NOT HANDLED -- each fails closed with a named error:
#   * INSTANCE / named instantiation (`Foo == INSTANCE M`) and unnamed
#     instantiation (`INSTANCE M`);
#   * substitution (`... WITH x <- y`) -- only ever appears with INSTANCE;
#   * parameterized instantiation (`I(x) == INSTANCE M WITH ...`);
#   * LOCAL definitions and LOCAL INSTANCE -- the analyzer cannot tell which
#     LOCAL names an extending module sees;
#   * an EXTENDS naming a non-standard module whose .tla file is not found.

# Standard TLA+ library modules. Extending these contributes operators (`+`,
# `Cardinality`, `Append`, ...) but declares no VARIABLES and no CONSTANTS the
# static bound reads, so they are skipped rather than resolved to a file.
# Anything NOT on this list must resolve to a real file or the analyzer fails
# closed -- silently skipping an unknown module would under-report the bound.
STANDARD_MODULES = frozenset(
    {
        "Naturals",
        "Integers",
        "Reals",
        "Sequences",
        "FiniteSets",
        "Bags",
        "TLC",
        "Json",
    }
)

_EXTENDS_RE = re.compile(r"(?m)^[ \t]*EXTENDS\b(.*)$")
_INSTANCE_RE = re.compile(r"(?<![A-Za-z0-9_])INSTANCE(?![A-Za-z0-9_])")
_LOCAL_RE = re.compile(r"(?m)^[ \t]*LOCAL(?![A-Za-z0-9_])")


class ModuleResolutionError(Exception):
    """The analyzer cannot faithfully resolve the EXTENDS hierarchy.

    Raised instead of returning a bound so the complexity gate FAILS CLOSED. An
    unresolved or unsupported hierarchy that returned a number would return a
    smaller one -- missing declarations only ever shrink the product -- which is
    the original MF-030 defect wearing a new hat. See
    references/architecture_tractability.md, "No Degenerate Escapes".
    """


class UnresolvedExtendsError(ModuleResolutionError):
    """An EXTENDS names a non-standard module whose ``.tla`` file was not found."""


class UnsupportedModuleConstructError(ModuleResolutionError):
    """A construct this static resolver does not model appears in the hierarchy.

    INSTANCE, substitution (``WITH``), parameterized instantiation, or LOCAL.
    Each changes which declarations are in scope in ways the resolver does not
    compute, so it refuses rather than under-report.
    """


def parse_extends(text: str) -> list[str]:
    """Names in every ``EXTENDS`` clause of a (comment-stripped) module."""
    names: list[str] = []
    for match in _EXTENDS_RE.finditer(text):
        for chunk in match.group(1).split(","):
            name = chunk.strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                names.append(name)
    return names


@dataclass
class ResolvedModule:
    """The union of declarations across an EXTENDS hierarchy.

    ``variables``/``constants``/``defs`` are base-first: an extended module's
    declarations precede the extending module's, and a name the extending
    module redefines overrides the inherited one.
    """

    root: str
    variables: list[str]
    constants: list[str]
    defs: list["Definition"]
    modules: list[str]
    extended_files: list[Path]


def resolve_module(
    tla_path: Path,
    *,
    search_path: Sequence[Path] | None = None,
    _seen: set[Path] | None = None,
) -> ResolvedModule:
    """Follow ``EXTENDS`` and union the declarations the analyzer reads.

    Raises :class:`ModuleResolutionError` (fails closed) on any construct it
    cannot model, rather than returning an under-reported view.

    ``search_path`` is the module search path, in precedence order, for
    ``EXTENDS`` targets that do not sit beside the extending module -- a case
    module in ``specs/case_modules/`` extending a view in
    ``specs/program_model/`` (EV-02-DF-02). The extending module's own directory
    is always searched first, so a default of ``None`` is exactly the old
    behavior. Callers that also run TLC must pass the SAME path they give SANY,
    or the scan and the corpus can describe different files.
    """
    seen = _seen if _seen is not None else set()
    resolved_path = tla_path.resolve()
    if resolved_path in seen:
        raise ModuleResolutionError(
            f"cyclic EXTENDS detected at {resolved_path.name}; the module "
            "hierarchy is not a tree"
        )
    seen.add(resolved_path)

    text = strip_comments(resolved_path.read_text(encoding="utf-8"))
    module_match = re.search(r"MODULE\s+([A-Za-z0-9_]+)", text)
    module_name = module_match.group(1) if module_match else resolved_path.stem

    # Fail closed on constructs whose scoping this static resolver does not model.
    if _INSTANCE_RE.search(text):
        raise UnsupportedModuleConstructError(
            f"module {module_name} ({resolved_path.name}) uses INSTANCE "
            "(module instantiation / substitution WITH / parameterized "
            "instantiation). The complexity analyzer does not model which "
            "declarations this brings into scope and FAILS CLOSED rather than "
            "under-report the bound."
        )
    if _LOCAL_RE.search(text):
        raise UnsupportedModuleConstructError(
            f"module {module_name} ({resolved_path.name}) uses LOCAL. The "
            "analyzer cannot tell which LOCAL declarations an extending module "
            "sees and FAILS CLOSED rather than under-report the bound."
        )

    variables: list[str] = []
    constants: list[str] = []
    defs_by_name: dict[str, Definition] = {}
    modules: list[str] = []
    extended_files: list[Path] = []

    def merge(dst: list[str], names: Iterable[str]) -> None:
        for name in names:
            if name not in dst:
                dst.append(name)

    for extended in parse_extends(text):
        if extended in STANDARD_MODULES:
            continue
        lookup = [resolved_path.parent, *(Path(p) for p in (search_path or ()))]
        candidate = next(
            (
                directory / f"{extended}.tla"
                for directory in lookup
                if (directory / f"{extended}.tla").is_file()
            ),
            None,
        )
        if candidate is None:
            where = (
                str(resolved_path.parent)
                if len(lookup) == 1
                else "any of " + ", ".join(str(directory) for directory in lookup)
            )
            raise UnresolvedExtendsError(
                f"module {module_name} ({resolved_path.name}) EXTENDS "
                f"{extended}, but {extended}.tla was not found in "
                f"{where}. The analyzer cannot union "
                "declarations from a module it cannot read and FAILS CLOSED "
                "rather than under-report the bound. If the module it extends "
                "lives in another directory, put that directory on the module "
                "search path (--module-path for case generation). If it is a "
                "library module with no VARIABLES, add it to STANDARD_MODULES "
                "once verified."
            )
        sub = resolve_module(candidate, search_path=search_path, _seen=seen)
        merge(variables, sub.variables)
        merge(constants, sub.constants)
        for definition in sub.defs:
            defs_by_name[definition.name] = definition
        merge(modules, sub.modules)
        extended_files.append(candidate)
        extended_files.extend(sub.extended_files)

    # The extending module's own declarations extend and override the inherited
    # set (TLA+ forbids redefinition, so override is only reached on collision).
    merge(variables, parse_declaration_block(text, "VARIABLE"))
    merge(constants, parse_declaration_block(text, "CONSTANT"))
    for definition in parse_definitions(text):
        defs_by_name[definition.name] = definition
    merge(modules, [module_name])

    return ResolvedModule(
        root=module_name,
        variables=variables,
        constants=constants,
        defs=list(defs_by_name.values()),
        modules=modules,
        extended_files=extended_files,
    )


def parse_cfg_constants(cfg_text: str) -> dict[str, Any]:
    """Parse ``CONSTANTS`` assignments from a TLC ``.cfg``.

    Returns a mapping of constant name to either a ``list`` (set value) or a
    string (model value).
    """
    text = strip_comments(cfg_text)
    constants: dict[str, Any] = {}
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("CONSTANT"):
            in_block = True
            line = re.sub(r"^CONSTANTS?\s*", "", line, flags=re.IGNORECASE).strip()
            if not line:
                continue
        elif line.split(None, 1)[0] in CFG_SECTION_KEYWORDS or re.match(
            r"^[A-Z_]+$", line
        ):
            # RP-04: the same keyword set that terminates an INVARIANT block
            # terminates a CONSTANTS block. The ad-hoc prefix tuple this
            # replaces missed ACTION_CONSTRAINT, ALIAS, POSTCONDITION and
            # CHECK_DEADLOCK when they carried a value on the same line. The
            # comparison is case-SENSITIVE on purpose: TLC's keywords are
            # uppercase, and matching case-insensitively would make a constant
            # named `Alias` or `View` close the block.
            in_block = False
            continue
        if not in_block:
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:<-|=)\s*(.+)$", line)
        if not match:
            continue
        name, value = match.group(1), match.group(2).strip()
        set_match = re.fullmatch(r"\{(.*)\}", value)
        if set_match:
            inner = set_match.group(1).strip()
            members = [m.strip() for m in inner.split(",") if m.strip()] if inner else []
            constants[name] = members
        else:
            constants[name] = value
    return constants


# --------------------------------------------------------------------------
# Read/write extraction
# --------------------------------------------------------------------------

_UNCHANGED_TUPLE_RE = re.compile(r"UNCHANGED\s*<<(.*?)>>", re.DOTALL)
_UNCHANGED_NAME_RE = re.compile(r"UNCHANGED\s+([A-Za-z_][A-Za-z0-9_]*)")


def strip_unchanged(body: str) -> str:
    """Remove ``UNCHANGED`` clauses -- they are neither reads nor writes."""
    body = _UNCHANGED_TUPLE_RE.sub(" ", body)
    body = _UNCHANGED_NAME_RE.sub(" ", body)
    return body


def strip_frame_conditions(body: str, variables: Iterable[str]) -> str:
    """Remove explicit ``v' = v`` frame-condition conjuncts (MF-036).

    ``v' = v`` says the action leaves ``v`` UNCHANGED -- it is the written-out
    form of ``UNCHANGED v`` and is neither a read nor a write of ``v``. Counting
    it as a touch inflates the R/W matrix: every variable an action leaves alone
    then shows as coupled to it, over-reporting the god-state. A probe's
    5-variable / 10-command CLI (each command touching only two variables, the
    rest pinned with ``v' = v``) reported a fully-coupled 10/10 component that
    was almost entirely frame conditions.

    Only an EXACT frame condition is removed: the right-hand side must be the
    bare variable, ending at a conjunction/disjunction boundary or the end of
    the body. ``v' = v + 1`` and ``v' = v \\cup {x}`` genuinely read the old
    value of ``v`` and are left intact, so a real write-that-reads is never
    silenced.
    """
    for name in variables:
        escaped = re.escape(name)
        body = re.sub(
            rf"(?<![A-Za-z0-9_]){escaped}'\s*=\s*{escaped}(?=\s*(?:/\\|\\/|$))",
            " ",
            body,
        )
    return body


def references(body: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_'])", body) is not None


def primed_references(body: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}'", body) is not None


@dataclass
class Action:
    name: str
    reads: set[str] = field(default_factory=set)
    writes: set[str] = field(default_factory=set)
    body: str = ""

    @property
    def touched(self) -> set[str]:
        return self.reads | self.writes


def extract_actions(defs: Sequence[Definition], variables: Sequence[str]) -> list[Action]:
    """FALLBACK action heuristic: any top-level definition priming a variable.

    This is the pre-CD-06 attribution and it is WRONG on composed actions --
    it lists helper operators as actions and drops wrappers whose writes all
    happen inside called operators (VAL-07 / VAL-12). :func:`analyze` uses it
    only when no next-state relation can be found via the cfg's ``NEXT`` or
    ``SPECIFICATION`` entries, and says so in the output. The correct
    attribution is :func:`extract_next_actions`.
    """
    actions: list[Action] = []
    for definition in defs:
        # MF-036: strip BOTH forms of "leaves it alone" -- the UNCHANGED clause
        # and the explicit ``v' = v`` frame condition -- before reads/writes are
        # extracted, so a variable an action does not touch is not counted as
        # coupled to it.
        body = strip_frame_conditions(strip_unchanged(definition.body), variables)
        writes = {v for v in variables if primed_references(body, v)}
        if not writes:
            continue
        reads = {v for v in variables if references(body, v)}
        actions.append(Action(name=definition.name, reads=reads, writes=writes, body=body))
    return actions


# --------------------------------------------------------------------------
# Action attribution to the next-state relation (CD-06: VAL-07 / VAL-12)
# --------------------------------------------------------------------------
#
# The matrix used to call every definition that syntactically primes a
# variable an "action". Both directions of that are wrong on standard TLA+
# composition:
#
#   * VAL-07: a wrapper action that primes a variable only through a helper
#     operator (taskq's ``MarkCli(cmd, task, exit)`` doing the ``lastCli'``
#     assignment) VANISHED from the matrix -- 9 CLI actions collapsed to 4
#     columns.
#   * VAL-12: the inverse -- helper operators (``MarkExternal``) were listed
#     AS actions, while composed actions whose writes happen entirely through
#     called operators or UNCHANGED (``RunFulfillmentWorker``,
#     ``RunFulfillmentWorkerNoop``, ``HiddenInternalProgress``) got NO column.
#
# Dense-row fractions, dense columns, action_count, per-component action
# counts -- and every fitness fact derived from them -- were computed over
# that partially wrong action set.
#
# The fix: the ACTION SET IS THE SET OF TOP-LEVEL DISJUNCTS of the next-state
# relation (the definition the cfg names via ``NEXT``, or the ``[][Next]_vars``
# box-action inside the definition ``SPECIFICATION`` names). Each disjunct's
# reads/writes are computed over its TRANSITIVELY RESOLVED body -- the CD-01/F1
# resolution machinery extended by CD-05 -- with ``UNCHANGED`` clauses and
# exact frame conditions stripped per definition body BEFORE expansion, so an
# ``UNCHANGED InternalVars`` never drags the variable-tuple definition in as a
# phantom read. Helpers are reachable only through expansion and are never
# columns of their own.
#
# Coverage contract (static, like the rest of this analyzer):
#   * disjuncts are split at top-level ``\/`` -- nesting inside (), [], {},
#     and << >> is respected; indentation-scoped bullet nesting is not parsed;
#   * leading ``\E`` / ``\A`` quantifier prefixes are stripped (repeatedly);
#   * a disjunct that reduces to ``Name`` or ``Name(args)`` where ``Name`` is
#     a definition becomes the action ``Name``;
#   * any other disjunct shape is kept as an INLINE action named
#     ``<Next>[k]`` over the disjunct text itself -- never silently dropped.

_BOX_ACTION_RE = re.compile(r"\[\]\s*\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]_")
_QUANTIFIER_PREFIX_RE = re.compile(r"^\\(?:EE|AA|E|A)\s+[^:]*:\s*", re.DOTALL)
_STRING_LITERAL_RE = re.compile(r'"[^"\n]*"')


def _parse_cfg_named_entry(cfg_text: str, keyword: str) -> str | None:
    """The identifier a cfg assigns to ``keyword`` (``NEXT``/``SPECIFICATION``/``INIT``).

    Handles both ``KEYWORD Name`` on one line and the name on the following
    line.
    """
    text = strip_comments(cfg_text)
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        line = raw.strip()
        match = re.match(rf"^{keyword}\b\s*(.*)$", line, flags=re.IGNORECASE)
        if not match:
            continue
        rest = match.group(1).strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", rest):
            return rest
        for follow in lines[index + 1 :]:
            follow = follow.strip()
            if not follow:
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", follow):
                return follow
            break
    return None


def find_next_relation(cfg_text: str, defs_by_name: dict[str, Definition]) -> str | None:
    """The definition name of the next-state relation, or None.

    ``NEXT Name`` wins; otherwise ``SPECIFICATION Spec`` is followed to the
    ``[][Next]_vars`` box-action -- first in ``Spec``'s immediate body, then in
    its transitively resolved body (a ``Spec == RealSpec`` alias still
    resolves). Returns None when neither names a definition that exists, and
    the caller falls back to the primes heuristic AND SAYS SO -- attribution is
    never silently degraded.
    """
    next_name = _parse_cfg_named_entry(cfg_text, "NEXT")
    if next_name and next_name in defs_by_name:
        return next_name
    spec_name = _parse_cfg_named_entry(cfg_text, "SPECIFICATION")
    if spec_name and spec_name in defs_by_name:
        for text in (
            defs_by_name[spec_name].body,
            resolve_definition_body(spec_name, defs_by_name),
        ):
            for match in _BOX_ACTION_RE.finditer(text):
                if match.group(1) in defs_by_name:
                    return match.group(1)
    return None


def split_top_level_disjuncts(body: str) -> list[str]:
    """Split a next-state relation body at top-level ``\\/`` boundaries.

    Depth-aware for ``()``, ``[]``, ``{}``, and ``<< >>`` so a disjunction
    inside an argument list or set is not torn apart.
    """
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    index = 0
    length = len(body)
    while index < length:
        pair = body[index : index + 2]
        char = body[index]
        if pair == "<<":
            depth += 1
            current.append(pair)
            index += 2
            continue
        if pair == ">>":
            depth -= 1
            current.append(pair)
            index += 2
            continue
        if pair == "\\/" and depth == 0:
            parts.append("".join(current))
            current = []
            index += 2
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        current.append(char)
        index += 1
    parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def _strip_quantifier_prefixes(chunk: str) -> str:
    """Remove leading ``\\E x \\in S :`` / ``\\A ...`` prefixes, repeatedly."""
    while True:
        match = _QUANTIFIER_PREFIX_RE.match(chunk)
        if not match:
            return chunk.strip()
        chunk = chunk[match.end() :].strip()


def _resolved_reads_writes(
    body: str,
    defs_by_name: dict[str, Definition],
    variables: Sequence[str],
    *,
    _seen: set[str] | None = None,
) -> tuple[set[str], set[str], str]:
    """Reads/writes of ``body`` with every called operator expanded transitively.

    Each definition body is stripped of ``UNCHANGED`` clauses, exact frame
    conditions, and STRING LITERALS before its tokens are scanned, so (a) a
    variable-tuple name under ``UNCHANGED`` (``UNCHANGED InternalVars``) is
    neither counted as a touch nor expanded into phantom reads of every
    variable in the tuple, and (b) a string that happens to spell an operator
    name (``result' = CommandResult(TRUE, NoReason, "RecordBudgets")``) is
    data, not a call -- it must not expand that operator into the caller.
    """
    seen = _seen if _seen is not None else set()
    reads: set[str] = set()
    writes: set[str] = set()
    resolved_parts: list[str] = []
    stack = [body]
    while stack:
        text = strip_frame_conditions(strip_unchanged(stack.pop()), variables)
        text = _STRING_LITERAL_RE.sub(" ", text)
        resolved_parts.append(text)
        for variable in variables:
            if primed_references(text, variable):
                writes.add(variable)
            if references(text, variable):
                reads.add(variable)
        for token in sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))):
            if token in defs_by_name and token not in seen:
                seen.add(token)
                stack.append(defs_by_name[token].body)
    return reads, writes, "\n".join(resolved_parts)


def extract_next_actions(
    next_name: str, defs_by_name: dict[str, Definition], variables: Sequence[str]
) -> list[Action]:
    """The action set: one Action per top-level disjunct of ``next_name``.

    A disjunct that is a plain (possibly quantified) reference to a defined
    operator becomes that operator, with reads/writes attributed through its
    transitively resolved body. Any other disjunct shape becomes an inline
    action named ``<next_name>[k]`` -- present in the matrix, never dropped.
    An action appearing in several disjuncts gets one column.
    """
    actions: list[Action] = []
    named: set[str] = set()
    for index, chunk in enumerate(split_top_level_disjuncts(defs_by_name[next_name].body), 1):
        stripped = _strip_quantifier_prefixes(chunk)
        call = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?", stripped, flags=re.DOTALL
        )
        if call and call.group(1) in defs_by_name:
            name = call.group(1)
            if name in named:
                continue
            named.add(name)
            reads, writes, resolved = _resolved_reads_writes(
                defs_by_name[name].body, defs_by_name, variables, _seen={name}
            )
        else:
            name = f"{next_name}[{index}]"
            reads, writes, resolved = _resolved_reads_writes(
                chunk, defs_by_name, variables, _seen={next_name}
            )
        actions.append(Action(name=name, reads=reads, writes=writes, body=resolved))
    return actions


# --------------------------------------------------------------------------
# Domain cardinality inference
# --------------------------------------------------------------------------


@dataclass
class Dimension:
    variable: str
    expression: str | None
    cardinality: int | None
    note: str = ""
    source: str | None = None

    @property
    def bounded(self) -> bool:
        return self.cardinality is not None and self.cardinality > 0


_FUNCTION_SET_RE = re.compile(r"\[(.+?)\s*->\s*(.+)\]", flags=re.DOTALL)


def _set_size(
    expr: str,
    constants: dict[str, Any],
    defs: dict[str, "Definition"] | None = None,
    _seen: set[str] | None = None,
) -> int | None:
    """Resolve the cardinality of a set-valued expression.

    Resolves, in order: ``BOOLEAN``; set literals ``{...}``; integer ranges
    ``a..b``; function sets ``[S -> T]`` (``|T| ^ |S|`` when both sides
    resolve); unions of resolvable parts; names bound to a set in the TLC cfg;
    and -- CD-05 (VAL-06) -- names defined as zero-parameter operators anywhere
    in the EXTENDS hierarchy, expanded transitively (the same definition map
    CD-01/F1's ``resolve_definition_body`` walks) with a cycle guard.
    Anything else is an explicit ``None`` (UNKNOWN), never a guess.
    """
    expr = expr.strip()
    if expr == "BOOLEAN":
        return 2
    literal = re.fullmatch(r"\{(.*)\}", expr, flags=re.DOTALL)
    if literal:
        inner = literal.group(1).strip()
        if not inner:
            return 0
        return len([m for m in inner.split(",") if m.strip()])
    rng = re.fullmatch(r"(-?\d+)\s*\.\.\s*(-?\d+)", expr)
    if rng:
        low, high = int(rng.group(1)), int(rng.group(2))
        return max(0, high - low + 1)
    # Function set [S -> T]: |T|^|S| -- same formula infer_dimensions applies
    # at the top level of a membership conjunct; checked before the union split
    # so a `\cup` inside S or T is not torn apart.
    function = _FUNCTION_SET_RE.fullmatch(expr)
    if function:
        domain_size = _set_size(function.group(1), constants, defs, _seen)
        range_size = _set_size(function.group(2), constants, defs, _seen)
        if domain_size is not None and range_size is not None:
            return range_size**domain_size
        return None
    # Union of resolvable parts.
    if "\\cup" in expr:
        total = 0
        for part in expr.split("\\cup"):
            size = _set_size(part, constants, defs, _seen)
            if size is None:
                return None
            total += size
        return total
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
        value = constants.get(expr)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, str):
            return 1
        # CD-05 (VAL-06): an operator-defined set (`TaskStatus == {...}`,
        # possibly in an EXTENDS-ed module) -- expand the definition body and
        # recurse, guarding against definition cycles.
        if defs is not None and expr in defs and not defs[expr].params:
            seen = _seen if _seen is not None else set()
            if expr in seen:
                return None
            seen.add(expr)
            return _set_size(defs[expr].body, constants, defs, seen)
        return None
    return None


_BOOLEAN_CONNECTIVE_RE = re.compile(r"/\\|\\/")


def _split_conjuncts(body: str) -> list[str]:
    """Split one definition body into conjunct/disjunct chunks.

    CD-05 (VAL-16): the old membership regex captured to end-of-line, so a
    `x \\in {...}` conjunct wrapped across lines silently resolved unknown.
    Splitting on the boolean connectives instead respects TLA+ conjunction
    structure: each chunk is one conjunct with its continuation lines attached,
    so a domain expression may span as many lines as it likes.
    """
    return [c.strip() for c in _BOOLEAN_CONNECTIVE_RE.split(body) if c.strip()]


def resolve_constraint_chunks(
    name: str, defs_by_name: dict[str, "Definition"], _seen: set[str] | None = None
) -> list[str]:
    """Conjunct chunks of ``name``'s body plus, transitively, of every
    definition it references.

    The companion to :func:`resolve_definition_body` for domain inference:
    aliased/composed invariants (``Inv == RealInv``) still contribute their
    real membership conjuncts, but each definition's body is split SEPARATELY,
    so a chunk never bleeds across a definition boundary the way a capture
    over the concatenated resolved text would.
    """
    seen = _seen if _seen is not None else set()
    if name in seen or name not in defs_by_name:
        return []
    seen.add(name)
    body = defs_by_name[name].body
    chunks = _split_conjuncts(body)
    for token in sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body))):
        if token not in seen and token in defs_by_name:
            chunks.extend(resolve_constraint_chunks(token, defs_by_name, seen))
    return chunks


UNRESOLVED_SOURCE_LABEL = "any type invariant or configured invariant"


def _constraint_for(
    variable: str,
    chunk: str,
    constants: dict[str, Any],
    defs: dict[str, "Definition"] | None,
) -> tuple[str, int | None, str] | None:
    """(expression, cardinality, note) if ``chunk`` constrains ``variable``."""
    subset = re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(variable)}\s*\\subseteq\s*(.+)\Z",
        chunk,
        flags=re.DOTALL,
    )
    if subset:
        raw = subset.group(1).strip()
        base = _set_size(raw, constants, defs)
        if base is not None:
            return (f"SUBSET {raw}", 2**base, f"powerset of {base} elements")
        return (f"SUBSET {raw}", None, "")
    member = re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(variable)}\s*\\in\s*(.+)\Z",
        chunk,
        flags=re.DOTALL,
    )
    if member:
        raw = member.group(1).strip()
        function = _FUNCTION_SET_RE.fullmatch(raw)
        if function:
            domain_size = _set_size(function.group(1), constants, defs)
            range_size = _set_size(function.group(2), constants, defs)
            if domain_size is not None and range_size is not None:
                return (
                    raw,
                    range_size**domain_size,
                    f"{range_size}^{domain_size} total functions",
                )
            return (raw, None, "")
        return (raw, _set_size(raw, constants, defs), "")
    return None


def infer_dimensions(
    domain_sources: Sequence[tuple[str, Sequence[str]]],
    variables: Sequence[str],
    constants: dict[str, Any],
    defs: dict[str, "Definition"] | None = None,
) -> list[Dimension]:
    """Derive a per-variable domain cardinality from the ordered domain sources.

    ``domain_sources`` is an ordered list of ``(label, conjunct-chunks)`` pairs
    -- ``TypeInvariant`` first, then ``TypeOK``, then the configured cfg
    invariants (each resolved transitively). CD-05 (VAL-17): sources MERGE
    per-variable -- for each variable the first source (in that order) whose
    constraint resolves to a cardinality wins, so a multi-view layout whose
    views necessarily use different invariant names still resolves every
    variable. A variable constrained only in a form the resolver cannot size
    keeps its expression with an unknown cardinality; a variable no source
    constrains is reported unknown and excluded from the product, rather than
    silently assigned a convenient number (CD-01, F3).
    """
    dimensions: list[Dimension] = []
    source_labels = [label for label, _ in domain_sources]
    unresolved_label = (
        " / ".join(source_labels) if source_labels else UNRESOLVED_SOURCE_LABEL
    )
    for variable in variables:
        expression: str | None = None
        cardinality: int | None = None
        note = ""
        source: str | None = None
        for label, chunks in domain_sources:
            found = None
            for chunk in chunks:
                candidate = _constraint_for(variable, chunk, constants, defs)
                if candidate is None:
                    continue
                if found is None:
                    found = candidate
                if candidate[1] is not None:
                    found = candidate
                    break
            if found is None:
                continue
            if found[1] is not None:
                expression, cardinality, note = found
                source = label
                break
            if expression is None:
                # Remember the first constraining-but-unresolvable source in
                # case no later source resolves the variable either.
                expression, cardinality, note = found
                source = label
        if cardinality is None:
            if expression is not None:
                note = note or (
                    "domain found but not resolvable -- excluded from the bound "
                    "(explicit UNKNOWN)"
                )
            elif not note:
                note = f"unconstrained by {unresolved_label} -- excluded from the bound"
        dimensions.append(
            Dimension(
                variable=variable,
                expression=expression,
                cardinality=cardinality,
                note=note,
                source=source,
            )
        )
    return dimensions


def state_space_bound(dimensions: Iterable[Dimension]) -> int | None:
    """Product of the bounded dimensions, or ``None`` when there are none.

    CD-01 (F3): with no resolvable domain the old code returned a silent 1 --
    a meaningless headline number. ``None`` means UNKNOWN and is rendered as
    such, never as 1.

    CM-01-DF-03: the product is over the *bounded* dimensions only. When some
    variable has no resolvable domain the number returned is a product over a
    SUBSET of the declared representation -- see ``bound_completeness`` for the
    fact that says so, and read it before comparing this number to anything.
    """
    bounded = [d for d in dimensions if d.bounded]
    if not bounded:
        return None
    bound = 1
    for dimension in bounded:
        bound *= int(dimension.cardinality or 1)
    return bound


@dataclass
class BoundCompleteness:
    """How much of the declared representation the state-space bound covers.

    CM-01-DF-03. The bound is a product over the variables whose domain the
    resolver could size. When it could not size all of them the product is over
    a SUBSET, and the number it yields is a LOWER BOUND on the
    declared-representation bound, not the bound itself. Every consumer that
    compares the bound to something must read this first, because the two
    comparisons are not symmetric:

    * incomplete bound > cap  -- SOUND. Every unresolved variable has at least
      one value, so the complete bound is >= this one; over the cap stays over
      the cap.
    * incomplete bound <= cap -- UNSOUND, and this is the defect. The nine
      unresolved variables of the shipped example carry the whole model; the
      surviving factor of 4 said "0.0% of 1,000,000, within cap" for a model
      TLC measures at 49,386 distinct states.

    ``complete`` is deliberately a boolean over the product's own definition --
    the product is over every declared variable or it is not. Partial
    resolution IS a spectrum, and the spectrum is published as ``resolved`` /
    ``total`` plus the per-variable notes in the dimension table; it is not
    collapsed into a "mostly complete" verdict, because no threshold on that
    ratio would be a measurement either.
    """

    resolved: int
    total: int
    unresolved: list[str]

    @property
    def complete(self) -> bool:
        return self.total > 0 and not self.unresolved

    @property
    def known(self) -> bool:
        """True when a bound could be computed at all (>= 1 variable sized)."""
        return self.resolved > 0

    def comparable_to_cap(self, bound: int | None, cap: int) -> bool | None:
        """``bound <= cap``, or ``None`` when that claim cannot be made.

        Returns ``False`` for an incomplete bound that already exceeds the cap:
        that claim is sound in the direction it is made. Returns ``None`` for an
        incomplete bound at or under the cap -- "within cap" is exactly the
        sentence this class exists to refuse.
        """
        if bound is None or not isinstance(cap, int) or cap <= 0:
            return None
        if bound > cap:
            return False
        if not self.complete:
            return None
        return True

    def caveat(self) -> str:
        """One sentence naming the incompleteness, or '' when complete."""
        if self.complete:
            return ""
        if not self.known:
            return (
                "no variable domain resolved, so there is no bound to compare"
            )
        return (
            f"product over {self.resolved} of {self.total} declared variables "
            f"({len(self.unresolved)} unresolved: {', '.join(self.unresolved)}) "
            "-- a LOWER BOUND on the declared-representation bound, not the bound"
        )


def bound_completeness(dimensions: Sequence[Dimension]) -> BoundCompleteness:
    """Measure how much of the declared representation the bound covers."""
    unresolved = [d.variable for d in dimensions if not d.bounded]
    return BoundCompleteness(
        resolved=sum(1 for d in dimensions if d.bounded),
        total=len(dimensions),
        unresolved=unresolved,
    )


# --------------------------------------------------------------------------
# Modularity over the R/W matrix
# --------------------------------------------------------------------------


def interaction_graph(actions: Sequence[Action], variables: Sequence[str]) -> dict[tuple[str, str], int]:
    """Weight each variable pair by the number of actions touching both."""
    weights: dict[tuple[str, str], int] = {}
    for action in actions:
        touched = sorted(action.touched & set(variables))
        for i, left in enumerate(touched):
            for right in touched[i + 1 :]:
                key = (left, right)
                weights[key] = weights.get(key, 0) + 1
    return weights


def modularity(partition: Sequence[set[str]], weights: dict[tuple[str, str], int]) -> float:
    """Newman-Girvan modularity Q of a partition of the weighted graph."""
    total = sum(weights.values())
    if total == 0:
        return 0.0
    degree: dict[str, int] = {}
    for (left, right), weight in weights.items():
        degree[left] = degree.get(left, 0) + weight
        degree[right] = degree.get(right, 0) + weight
    score = 0.0
    for community in partition:
        internal = sum(
            weight
            for (left, right), weight in weights.items()
            if left in community and right in community
        )
        attached = sum(degree.get(node, 0) for node in community)
        score += internal / total - (attached / (2 * total)) ** 2
    return score


def greedy_communities(
    variables: Sequence[str], weights: dict[tuple[str, str], int]
) -> tuple[list[set[str]], float]:
    """Greedy agglomerative modularity maximization (CNM-style).

    Deterministic: ties break on sorted community keys, so the same model
    always yields the same recommendation. ``weights`` is the positive-integer
    graph emitted by :func:`interaction_graph`.
    """
    partition: list[set[str]] = [{v} for v in variables]
    best_q = modularity(partition, weights)
    if not weights:
        return partition, best_q

    # For two communities A and B, recomputing modularity for the complete
    # candidate partition is unnecessary. With m equal to the total edge
    # weight, e(A, B) the weight crossing between them, and d(A)/d(B) their
    # weighted degrees, the exact modularity delta is:
    #
    #   e(A, B) / m - d(A) * d(B) / (2 * m**2)
    #
    # The previous implementation rebuilt every candidate partition and then
    # rescanned every edge once per community. On dense 123-variable models
    # this turned the mandatory close-ticket ledger into billions of Python
    # membership checks. Rebuild the community crossing weights once per
    # accepted merge instead. The nested i/j scan and strict epsilon comparison
    # stay unchanged, preserving deterministic tie order.
    total = sum(weights.values())
    degree: dict[str, int] = {variable: 0 for variable in variables}
    for (left, right), weight in weights.items():
        degree[left] = degree.get(left, 0) + weight
        degree[right] = degree.get(right, 0) + weight

    improved = True
    while improved and len(partition) > 1:
        improved = False
        best_pair: tuple[int, int] | None = None
        best_gain = 0.0

        community_by_variable = {
            variable: index
            for index, community in enumerate(partition)
            for variable in community
        }
        attached = [
            sum(degree.get(variable, 0) for variable in community)
            for community in partition
        ]
        crossing: dict[tuple[int, int], int] = {}
        for (left, right), weight in weights.items():
            left_index = community_by_variable[left]
            right_index = community_by_variable[right]
            if left_index == right_index:
                continue
            pair = (min(left_index, right_index), max(left_index, right_index))
            crossing[pair] = crossing.get(pair, 0) + weight

        for i in range(len(partition)):
            for j in range(i + 1, len(partition)):
                cross_weight = crossing.get((i, j), 0)
                if cross_weight == 0:
                    continue
                gain = cross_weight / total - (attached[i] * attached[j]) / (
                    2 * total * total
                )
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_pair = (i, j)
        if best_pair is not None:
            i, j = best_pair
            merged = partition[i] | partition[j]
            partition = [c for k, c in enumerate(partition) if k not in (i, j)]
            partition.append(merged)
            best_q += best_gain
            improved = True
    partition.sort(key=lambda c: (-len(c), sorted(c)))
    # Report the descriptor's canonical modularity calculation rather than an
    # accumulated floating-point delta.
    return partition, modularity(partition, weights)


def crossing_actions(
    partition: Sequence[set[str]], actions: Sequence[Action]
) -> dict[str, list[str]]:
    """Actions that touch more than one community are candidate ports."""
    crossings: dict[str, list[str]] = {}
    for action in actions:
        hit = [
            index
            for index, community in enumerate(partition)
            if action.touched & community
        ]
        if len(hit) > 1:
            crossings[action.name] = [f"C{index + 1}" for index in hit]
    return crossings


# --------------------------------------------------------------------------
# Invariant resolution and invariant-read analysis
# --------------------------------------------------------------------------


def resolve_definition_body(
    name: str, defs_by_name: dict[str, "Definition"], _seen: set[str] | None = None
) -> str:
    """The body of ``name`` with every referenced definition expanded, transitively.

    CD-01 (F1): ``INVARIANT Inv`` with ``Inv == RealInv`` is standard TLA+ --
    invariant aliasing and composition. Reading only the immediate body of the
    cfg-named invariant sees a one-token alias with no variable names in it, so
    every variable was judged "read by no invariant". This helper follows every
    definition reference in the body (and onward, with a cycle guard) so the
    resolved text contains the variables the invariant actually reads.
    """
    seen = _seen if _seen is not None else set()
    if name in seen or name not in defs_by_name:
        return ""
    seen.add(name)
    body = defs_by_name[name].body
    parts = [body]
    for token in sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body))):
        if token not in seen and token in defs_by_name:
            parts.append(resolve_definition_body(token, defs_by_name, seen))
    return "\n".join(parts)


def invariant_unread_variables(
    variables: Sequence[str], invariant_bodies: dict[str, str]
) -> list[str]:
    """Variables no configured invariant reads -- a fact, not a recommendation.

    ``invariant_bodies`` must be TRANSITIVELY RESOLVED bodies (see
    :func:`resolve_definition_body`) or aliased/composed invariants will make
    every variable appear unread (the F1 defect).
    """
    read_by_invariant: set[str] = set()
    for body in invariant_bodies.values():
        for variable in variables:
            if references(body, variable):
                read_by_invariant.add(variable)
    return [v for v in variables if v not in read_by_invariant]


def dense_rows_and_columns(
    variables: Sequence[str], actions: Sequence[Action]
) -> tuple[dict[str, int], list[str]]:
    """Dense rows (god-state variables) and dense columns of the R/W matrix.

    A dense row is a variable touched by more than half the actions -- the
    god-state signature. A dense column is an action touching more than half
    the variables. Both are measured facts of the matrix, reported as part of
    the descriptor.
    """
    action_count = {v: 0 for v in variables}
    for action in actions:
        for variable in action.touched:
            if variable in action_count:
                action_count[variable] += 1
    dense_rows = {
        v: action_count[v]
        for v in sorted(variables, key=lambda v: (-action_count[v], v))
        if actions and action_count[v] > len(actions) / 2
    }
    dense_cols = sorted(
        a.name for a in actions if variables and len(a.touched) > len(variables) / 2
    )
    return dense_rows, dense_cols


# --------------------------------------------------------------------------
# TLC report comparison (the self-loop blindness check)
# --------------------------------------------------------------------------


@dataclass
class TlcReport:
    generated: int | None = None
    distinct: int | None = None
    depth: int | None = None

    @property
    def complete(self) -> bool:
        return None not in (self.generated, self.distinct, self.depth)


def parse_tlc_report(text: str) -> TlcReport:
    report = TlcReport()
    counts = re.search(r"([\d,]+)\s+states generated,\s*([\d,]+)\s+distinct states found", text)
    if counts:
        report.generated = int(counts.group(1).replace(",", ""))
        report.distinct = int(counts.group(2).replace(",", ""))
    depth = re.search(r"depth of the complete state graph search is\s+(\d+)", text)
    if depth:
        report.depth = int(depth.group(1))
    return report


def compare_tlc_reports(baseline: TlcReport, current: TlcReport) -> list[dict[str, str]]:
    """Detect the failure mode a distinct-state gate cannot see.

    A generated-states drop at constant distinct states and constant depth
    means transitions were removed without removing any state -- typically a
    deleted self-loop, i.e. a real behavior change wearing the costume of a
    re-representation. That is a RED FLAG, never a win.
    """
    findings: list[dict[str, str]] = []
    if not (baseline.complete and current.complete):
        findings.append(
            {
                "level": "NOTE",
                "message": "TLC reports incomplete; comparison skipped.",
            }
        )
        return findings
    same_states = baseline.distinct == current.distinct and baseline.depth == current.depth
    if current.generated < baseline.generated and same_states:
        findings.append(
            {
                "level": "RED FLAG",
                "message": (
                    f"generated states dropped {baseline.generated} -> {current.generated} "
                    f"while distinct states ({current.distinct}) and depth ({current.depth}) "
                    "are unchanged. A distinct-state gate is STRUCTURALLY BLIND to this: "
                    "removing a self-loop returns to an already-known state. Inspect the "
                    "transition-level diff before recording any reduction -- an idempotent "
                    "re-fire transition may have been deleted (behavior change), not "
                    "re-represented. See MF-020."
                ),
            }
        )
    elif current.generated < baseline.generated:
        findings.append(
            {
                "level": "INFO",
                "message": (
                    f"generated states {baseline.generated} -> {current.generated} with "
                    f"distinct {baseline.distinct} -> {current.distinct} and depth "
                    f"{baseline.depth} -> {current.depth}. State-level change accompanies the "
                    "transition-level change; still confirm against the transition diff."
                ),
            }
        )
    else:
        findings.append(
            {
                "level": "OK",
                "message": (
                    f"generated {baseline.generated} -> {current.generated}, distinct "
                    f"{baseline.distinct} -> {current.distinct}, depth {baseline.depth} -> "
                    f"{current.depth}. No self-loop-deletion signature."
                ),
            }
        )
    return findings


# --------------------------------------------------------------------------
# Analysis assembly
# --------------------------------------------------------------------------


@dataclass
class Advisory:
    """One advisory complexity finding: what and where it is.

    MF-036: complexity is a scanner, not a gate
    (references/architecture_tractability.md, "Advisory, Not Blocking"). Each
    Advisory is a WARNING that NEVER blocks promotion. ``finding`` names the
    component / variable / action and the measured threshold breach -- a fact.
    CD-01 removed the ``recommendation`` field with the rest of the
    suggested-move machinery: the descriptor states facts and the owner
    decides what, if anything, to do about them.
    """

    kind: str
    finding: str


@dataclass
class Analysis:
    module: str
    tla_path: Path
    cfg_path: Path
    manifest_path: Path | None
    constants: dict[str, Any]
    variables: list[str]
    dimensions: list[Dimension]
    actions: list[Action]
    bound: int | None
    bound_source: str | None
    unbounded: list[str]
    communities: list[set[str]]
    modularity_score: float
    crossings: dict[str, list[str]]
    dense_rows: dict[str, int]
    dense_columns: list[str]
    unread_by_invariant: list[str]
    unjustified: list[str] | None
    budgets: dict[str, Any]
    warnings: list[Advisory]
    tlc_findings: list[dict[str, str]]
    # CD-06: how the action set was determined -- the next-state relation's
    # disjuncts (correct) or the primes-heuristic fallback (stated honestly).
    action_attribution: str = ""
    # CD-03: the project's self-configured fitness functions, evaluated over
    # this descriptor. None when the project configured nothing -- there are NO
    # built-in rules. Firings are advisory: they are surfaced in the report and
    # NEVER change the exit code or block promotion.
    fitness: Any = None

    @property
    def completeness(self) -> BoundCompleteness:
        """CM-01-DF-03: how much of the representation ``bound`` is a product over.

        Derived from the dimension table rather than stored, so it cannot fall
        out of step with the bound and so EVERY holder of an ``Analysis`` has
        it -- there is no way to read the bound from this object without the
        fact that qualifies it being one attribute away.
        """
        return bound_completeness(self.dimensions)

    @property
    def violations(self) -> list[str]:
        """The advisory finding strings.

        Retained under this name so the complexity ledger (out of MF-036's
        scope) keeps recording the findings. Since MF-036 these are WARNINGS,
        not gate violations -- they are recorded as evidence, never enforced.
        """
        return [w.finding for w in self.warnings]

    @property
    def gate_passed(self) -> bool:
        """True when the scan raised no complexity warnings.

        MF-036: complexity is advisory -- this value NEVER gates promotion. A
        False result means "the scan raised warnings the owner should read", not
        "the build fails". The name and the ledger field are kept for
        continuity with the pre-reframe ledger schema.
        """
        return not self.warnings


def load_justification(manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(manifest, dict):
        return None
    table = manifest.get("justification")
    return table if isinstance(table, dict) else None


def unjustified_variables(
    variables: Sequence[str], table: dict[str, Any] | None
) -> list[str] | None:
    """Variables with no invariant, effect, or kill-test linkage."""
    if table is None:
        return None
    flagged: list[str] = []
    for variable in variables:
        entry = table.get(variable)
        if not isinstance(entry, dict):
            flagged.append(variable)
            continue
        linked = False
        for key in ("invariants", "effects", "kill_tests"):
            value = entry.get(key)
            if isinstance(value, (list, tuple)) and any(str(v).strip() for v in value):
                linked = True
        if not linked:
            flagged.append(variable)
    return flagged


def analyze(
    tla_path: Path,
    cfg_path: Path,
    manifest_path: Path | None,
    *,
    baseline_tlc: Path | None = None,
    current_tlc: Path | None = None,
    warn_stream: Any = None,
    search_path: Sequence[Path] | None = None,
) -> Analysis:
    from scripts.budgets import DEFAULT_BUDGETS, load_budgets

    cfg_text = cfg_path.read_text(encoding="utf-8")

    # MF-030: follow EXTENDS and union declarations across the module hierarchy.
    # On a single-file spec that extends only standard library modules this is
    # identical to reading the one file; on a decomposed model it recovers the
    # variables, TypeInvariant, and actions the extended modules contribute.
    # resolve_module raises ModuleResolutionError (fails closed) on any
    # construct it cannot model -- callers must not swallow it into a bound.
    resolved = resolve_module(tla_path, search_path=search_path)
    module = resolved.root
    variables = resolved.variables
    constants = parse_cfg_constants(cfg_text)
    defs = resolved.defs
    by_name = {d.name: d for d in defs}

    # CD-06 (VAL-07 / VAL-12): the action set is the set of top-level disjuncts
    # of the next-state relation, with called-operator bodies expanded
    # transitively so primes inside helpers are attributed to the top-level
    # action. Helpers are not actions. Only when no next-state relation can be
    # found does the scan fall back to the primes heuristic -- and it says so.
    next_name = find_next_relation(cfg_text, by_name)
    if next_name is not None:
        actions = extract_next_actions(next_name, by_name, variables)
        action_attribution = (
            f"top-level disjuncts of the next-state relation {next_name}, "
            "called-operator bodies expanded transitively; helpers are not actions"
        )
    else:
        actions = extract_actions(defs, variables)
        action_attribution = (
            "FALLBACK primes heuristic (every definition priming a variable) -- "
            "no next-state relation found via cfg NEXT or SPECIFICATION; helper "
            "operators may be listed as actions and composed actions may be missing"
        )

    # CD-01 (F1): resolve invariant aliasing/composition transitively. The cfg
    # may configure `INVARIANT Inv` with `Inv == RealInv` -- reading only the
    # immediate alias body sees no variable names at all.
    invariant_names = parse_cfg_invariants(cfg_text)
    invariant_bodies = {
        name: resolve_definition_body(name, by_name)
        for name in invariant_names
        if name in by_name
    }

    # CD-01 (F3) / CD-05 (VAL-17): the per-variable domain sources, in a
    # documented precedence order -- TypeInvariant, then TypeOK, then the
    # configured cfg invariants (each resolved transitively; it may itself
    # compose). CD-05 replaced first-named-definition-wins with a per-variable
    # MERGE: for each variable the first source in this order that resolves a
    # domain wins, so a multi-view layout (where TLA+ forbids redefining
    # TypeInvariant per view) still resolves every view's variables. When
    # nothing resolves a domain, the bound is reported UNKNOWN -- never a
    # silent 1.
    domain_sources: list[tuple[str, list[str]]] = []
    if "TypeInvariant" in by_name:
        domain_sources.append(
            ("TypeInvariant", resolve_constraint_chunks("TypeInvariant", by_name))
        )
    if "TypeOK" in by_name:
        domain_sources.append(("TypeOK", resolve_constraint_chunks("TypeOK", by_name)))
    cfg_invariant_chunks: list[str] = []
    for name in invariant_names:
        if name in ("TypeInvariant", "TypeOK") or name not in by_name:
            continue
        cfg_invariant_chunks.extend(resolve_constraint_chunks(name, by_name))
    if cfg_invariant_chunks:
        domain_sources.append(
            ("the configured invariants (resolved transitively)", cfg_invariant_chunks)
        )

    dimensions = infer_dimensions(domain_sources, variables, constants, defs=by_name)
    bound = state_space_bound(dimensions)
    contributing: list[str] = []
    for label, _ in domain_sources:
        if any(d.source == label and d.bounded for d in dimensions):
            contributing.append(label)
    bound_source = " + ".join(contributing) if bound is not None and contributing else None
    unbounded = [d.variable for d in dimensions if not d.bounded]

    weights = interaction_graph(actions, variables)
    communities, score = greedy_communities(variables, weights)
    crossings = crossing_actions(communities, actions)
    dense_rows, dense_columns = dense_rows_and_columns(variables, actions)

    unread = invariant_unread_variables(variables, invariant_bodies)

    manifest: dict[str, Any] | None = None
    if manifest_path and manifest_path.is_file():
        try:
            from scripts.extract_spec_manifest import load_manifest

            manifest = load_manifest(manifest_path)
        except Exception:
            manifest = None
    unjustified = unjustified_variables(variables, load_justification(manifest))

    budget_stream = warn_stream if warn_stream is not None else sys.stderr
    if manifest_path is None:
        # CD-02-DF-01: no --manifest was given and no spec_manifest.yaml sits
        # next to the spec. Say what happened -- never leak a sentinel path
        # into the warning.
        print(
            "warning: no manifest supplied (no --manifest and no "
            "spec_manifest.yaml next to the spec); using documented default "
            "budgets (references/modular_fuzzing.md)",
            file=budget_stream,
        )
        budgets = dict(DEFAULT_BUDGETS)
    else:
        budgets = load_budgets(manifest_path, warn=True, stream=budget_stream)

    # MF-036: each threshold breach is an ADVISORY warning that names the
    # component/variable/action and states the measured fact. None of these
    # block promotion, refuse case generation, or drive a nonzero exit -- they
    # are findings for the owner, per references/architecture_tractability.md,
    # "Advisory, Not Blocking". The only nonzero exit is for a model the scan
    # CANNOT analyze (ModuleResolutionError / usage), handled in the CLI.
    warnings: list[Advisory] = []
    # MF-022: the static bound is a Cartesian over-approximation of the
    # DECLARED representation -- it ignores every action guard, so it counts
    # combinations the program can never occupy. It is therefore compared
    # against max_state_space_bound (a TLC-capacity ceiling), NOT against
    # max_distinct_states, which caps ACTUAL reachable states measured by TLC
    # after the fact. Comparing the two is a category error: on this
    # repository the bound over-approximated reachable states by ~400x, on a
    # model that was 17x under its own reachable-state budget.
    #
    # CM-01-DF-03: the comparison is only made in the direction it is sound.
    # A bound that is a product over a SUBSET of the declared variables is a
    # LOWER bound, so "over the cap" still holds (every unresolved variable has
    # at least one value) but "within the cap" says nothing at all. The old
    # code made both claims; the second one reported the shipped example's
    # bound = 4 over 1 of 10 variables as 0.0% of 1,000,000, within cap.
    completeness = bound_completeness(dimensions)
    if bound is not None and bound > budgets["max_state_space_bound"]:
        qualifier = (
            ""
            if completeness.complete
            else (
                f" (and that is a LOWER bound: product over "
                f"{completeness.resolved} of {completeness.total} declared "
                f"variables, so the complete bound is at least this large)"
            )
        )
        warnings.append(
            Advisory(
                kind="state_space_bound",
                finding=(
                    f"state-space upper bound {bound:,} exceeds max_state_space_bound "
                    f"{budgets['max_state_space_bound']:,}{qualifier}"
                ),
            )
        )
    elif bound is not None and not completeness.complete:
        warnings.append(
            Advisory(
                kind="state_space_bound_partial",
                finding=(
                    f"state-space upper bound {bound:,} is INCOMPLETE and CANNOT be "
                    f"compared against max_state_space_bound "
                    f"{budgets['max_state_space_bound']:,}: {completeness.caveat()}. "
                    "Percent-of-cap over an incomplete bound is not a measurement, "
                    "so this scan reports the cap comparison as unknown rather than "
                    "as within cap"
                ),
            )
        )
    if bound is None:
        warnings.append(
            Advisory(
                kind="state_space_bound_unknown",
                finding=(
                    "state-space upper bound UNKNOWN: no variable domain could be "
                    "resolved from a TypeInvariant/TypeOK or from the configured "
                    "invariants, so the bound cannot be compared against "
                    "max_state_space_bound"
                ),
            )
        )
    for index, community in enumerate(communities, start=1):
        if len(community) > budgets["max_component_variables"]:
            members = ", ".join(sorted(community))
            warnings.append(
                Advisory(
                    kind="component_variables",
                    finding=(
                        f"component C{index} has {len(community)} variables "
                        f"({members}), exceeding max_component_variables "
                        f"{budgets['max_component_variables']}"
                    ),
                )
            )
    for index, community in enumerate(communities, start=1):
        touching = [a.name for a in actions if a.touched & community]
        if len(touching) > budgets["max_component_actions"]:
            warnings.append(
                Advisory(
                    kind="component_actions",
                    finding=(
                        f"component C{index} is touched by {len(touching)} actions "
                        f"({', '.join(touching)}), exceeding max_component_actions "
                        f"{budgets['max_component_actions']}"
                    ),
                )
            )

    tlc_findings: list[dict[str, str]] = []
    if current_tlc is not None and current_tlc.is_file():
        current_report = parse_tlc_report(current_tlc.read_text(encoding="utf-8"))
        if baseline_tlc is not None and baseline_tlc.is_file():
            baseline_report = parse_tlc_report(baseline_tlc.read_text(encoding="utf-8"))
            tlc_findings = compare_tlc_reports(baseline_report, current_report)
        elif current_report.complete:
            tlc_findings = [
                {
                    "level": "INFO",
                    "message": (
                        f"TLC measured {current_report.generated} generated / "
                        f"{current_report.distinct} distinct / depth {current_report.depth}. "
                        "Pass --baseline-tlc to check for the self-loop-deletion signature."
                    ),
                }
            ]
        # MF-022: max_distinct_states caps ACTUAL reachable states, so it can
        # only be checked once TLC has measured them (--tlc-report). This is the
        # comparison the budget was always for; before MF-022 it was applied
        # to the static over-approximation instead.
        if current_report.complete and current_report.distinct is not None:
            if current_report.distinct > budgets["max_distinct_states"]:
                warnings.append(
                    Advisory(
                        kind="distinct_states",
                        finding=(
                            f"TLC-measured {current_report.distinct:,} distinct reachable "
                            f"states exceeds max_distinct_states "
                            f"{budgets['max_distinct_states']:,}"
                        ),
                    )
                )
            else:
                tlc_findings.append(
                    {
                        "level": "INFO",
                        "message": (
                            f"TLC-measured {current_report.distinct:,} distinct reachable "
                            f"states is within max_distinct_states "
                            f"{budgets['max_distinct_states']:,}."
                        ),
                    }
                )

    analysis = Analysis(
        module=module,
        tla_path=tla_path,
        cfg_path=cfg_path,
        manifest_path=manifest_path,
        constants=constants,
        variables=variables,
        dimensions=dimensions,
        actions=actions,
        bound=bound,
        bound_source=bound_source,
        unbounded=unbounded,
        communities=communities,
        modularity_score=score,
        crossings=crossings,
        dense_rows=dense_rows,
        dense_columns=dense_columns,
        unread_by_invariant=unread,
        unjustified=unjustified,
        budgets=budgets,
        warnings=warnings,
        tlc_findings=tlc_findings,
        action_attribution=action_attribution,
    )

    # CD-03: evaluate the project's self-configured fitness functions over the
    # published descriptor facts. Rules persist with the project -- in the
    # manifest under `fitness_functions:` and/or in a sibling
    # fitness_functions.yaml next to the spec. No rules configured -> None ->
    # no fitness section in either renderer (there are NO built-in rules).
    # Advisory: firings are surfaced for future agents, never affect the exit
    # code, and even a broken rules file only yields advisory config errors.
    from scripts.fitness_functions import run_fitness

    analysis.fitness = run_fitness(manifest, tla_path.parent, descriptor_payload(analysis))
    return analysis


#: The TLC config keywords that open a section. CM-01-DF-02: a bare keyword
#: line is what CLOSES an INVARIANT block, and it is the ONLY honest way to
#: recognise one -- no regex over the same input can tell the keyword
#: `CONSTANTS` from an invariant that happens to be named `CONSTANTS`, because
#: the two are the same characters. TLC resolves the ambiguity the same way:
#: these words are reserved, so a definition cannot be called one.
CFG_SECTION_KEYWORDS = frozenset(
    {
        "SPECIFICATION",
        "INIT",
        "NEXT",
        "INVARIANT",
        "INVARIANTS",
        "PROPERTY",
        "PROPERTIES",
        "CONSTANT",
        "CONSTANTS",
        "CONSTRAINT",
        "CONSTRAINTS",
        "ACTION_CONSTRAINT",
        "ACTION_CONSTRAINTS",
        "SYMMETRY",
        "VIEW",
        "ALIAS",
        "POSTCONDITION",
        "CHECK_DEADLOCK",
    }
)


def parse_cfg_invariants(cfg_text: str) -> list[str]:
    """The invariant names an INVARIANT/INVARIANTS block configures.

    CM-01-DF-02: the old block terminator tested ``re.match("^[A-Z]+\\b") and
    not re.fullmatch(identifier)``, and every all-caps keyword ALSO fullmatches
    the identifier pattern -- so the guard never fired on a bare keyword line
    and `INVARIANT Invariant` followed by `CONSTANTS` yielded
    ``['Invariant', 'CONSTANTS']``. Harmless for the caller that only looks the
    name up in a definition table (a keyword resolves to nothing and is
    skipped); NOT harmless for a caller that treats an unresolvable invariant
    name as a finding, which is how it manufactured a model-pair mismatch on
    the shipped example. Recognise the keyword instead.

    BS-07 (#155, #159): TLC's config reader is TOKEN-based, not line-based --
    ``INVARIANTS A B C``, ``INVARIANT A B`` and a block whose continuation
    lines carry several names each are all legal, and TLC checks every name.
    The line-based reader this replaces appended the whole remainder of the
    keyword line as ONE name (``'TypeOK Bounded'``, which the model-pair check
    then reported as an undefined invariant and the close-time complexity
    ledger skipped on) and dropped a continuation line holding more than one
    name. Every reader of a cfg's invariants goes through this function
    (`spec_evolution.validate_model_pair` included), so there is one parser.
    """
    names: list[str] = []
    in_block = False
    for token in strip_comments(cfg_text).split():
        if token in ("INVARIANT", "INVARIANTS"):
            in_block = True
            continue
        if token in CFG_SECTION_KEYWORDS:
            # Any other section keyword ENDS the invariant block, whether or
            # not it carries a value. Case-SENSITIVE: TLC's keywords are
            # uppercase, and an invariant legitimately named `Alias` or
            # `View` must not be swallowed by this branch.
            in_block = False
            continue
        if in_block:
            if _CFG_IDENTIFIER.fullmatch(token):
                names.append(token)
            else:
                in_block = False
    return names


_CFG_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _table(rows: Sequence[Sequence[str]], headers: Sequence[str]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(lines)


def render_text(analysis: Analysis) -> str:
    out: list[str] = []
    add = out.append

    add(f"analyze complexity -- {analysis.module} (complexity descriptor)")
    add(f"  spec:     {analysis.tla_path}")
    add(f"  config:   {analysis.cfg_path}")
    add(f"  manifest: {analysis.manifest_path or '(none)'}")
    add("")
    add("This is a DESCRIPTOR: every figure below is [MEASURED] -- parsed from this")
    add("spec + cfg. It states facts about the model and makes no suggestions.")
    add("")

    add("[MEASURED] Dimension table")
    rows = [
        (
            d.variable,
            d.expression or "(unconstrained)",
            f"{d.cardinality:,}" if d.bounded else "unknown",
            d.source or "-",
            d.note,
        )
        for d in analysis.dimensions
    ]
    add(_table(rows, ("variable", "domain", "cardinality", "source", "note")))
    add("  (domain sources merge per-variable: TypeInvariant, then TypeOK, then the")
    add("  configured invariants -- first source that resolves wins. What the resolver")
    add("  can and cannot see: references/architecture_tractability.md,")
    add("  'What The Domain Resolver Can And Cannot See'.)")
    add("")

    add("[MEASURED] State-space upper bound")
    if analysis.bound is None:
        add("  bound = UNKNOWN -- no variable domain could be resolved from a")
        add("  TypeInvariant/TypeOK or from the configured invariants. This is an")
        add("  explicit unknown, not a small model. (Resolver coverage:")
        add("  references/architecture_tractability.md, 'What The Domain Resolver")
        add("  Can And Cannot See'.)")
    else:
        completeness = analysis.completeness
        label = "COMPLETE" if completeness.complete else "INCOMPLETE"
        add(
            f"  bound = {analysis.bound:,}  [{label}: product over "
            f"{completeness.resolved} of {completeness.total} declared variables; "
            f"domains from {analysis.bound_source}]"
        )
        if not completeness.complete:
            # CM-01-DF-03: the exclusions below were always printed; what was
            # missing is the consequence of them, said next to the number and
            # published as a fact the JSON and the ledger read too.
            add(
                "  this number is a LOWER BOUND on the declared-representation bound,"
            )
            add(
                "  not the bound: it cannot be read as a percent of "
                "max_state_space_bound, and"
            )
            add("  'within cap' is NOT a claim this scan can make about it.")
    if analysis.unbounded:
        add(f"  excluded (no resolvable domain): {', '.join(analysis.unbounded)}")
    dominant = sorted(
        (d for d in analysis.dimensions if d.bounded),
        key=lambda d: -(d.cardinality or 0),
    )[:3]
    if dominant and analysis.bound is not None and analysis.bound > 1:
        add("  dominant dimensions:")
        for d in dominant:
            share = math.log(d.cardinality or 1) / math.log(analysis.bound) * 100
            add(f"    {d.variable}: {d.cardinality:,} ({share:.1f}% of the bound in log space)")
    add("")

    add("[MEASURED] Variables x actions read/write matrix")
    if analysis.action_attribution:
        add(f"  (actions = {analysis.action_attribution})")
    header = ["variable"] + [a.name for a in analysis.actions]
    matrix_rows = []
    for variable in analysis.variables:
        row = [variable]
        for action in analysis.actions:
            read = variable in action.reads
            write = variable in action.writes
            row.append("rw" if read and write else "w" if write else "r" if read else ".")
        matrix_rows.append(row)
    add(_table(matrix_rows, header))
    add("")

    add("[MEASURED] Near-decomposability")
    add(f"  graph modularity Q = {analysis.modularity_score:.3f} over the variable interaction graph")
    add(f"  (weight of an edge = number of actions touching both variables)")
    for index, community in enumerate(analysis.communities, start=1):
        touching = [a.name for a in analysis.actions if a.touched & community]
        add(f"  C{index}: {', '.join(sorted(community))}  ({len(community)} variables, {len(touching)} actions)")
    if analysis.crossings:
        add("  candidate port-crossing actions:")
        for name, where in sorted(analysis.crossings.items()):
            add(f"    {name} crosses {', '.join(where)}")
    else:
        add("  no port-crossing actions (single component, or fully independent components)")
    add("")

    add("[MEASURED] Dense rows and columns of the R/W matrix")
    if analysis.dense_rows:
        add("  dense rows (god-state signature -- variable touched by more than half the actions):")
        for variable, count in analysis.dense_rows.items():
            add(f"    {variable} touched by {count}/{len(analysis.actions)} actions")
    else:
        add("  no dense rows (no variable is touched by more than half the actions)")
    if analysis.dense_columns:
        add("  dense columns (action touching more than half the variables):")
        for name in analysis.dense_columns:
            add(f"    {name}")
    else:
        add("  no dense columns (no action touches more than half the variables)")
    add("")

    add("[MEASURED] Invariant coverage (aliased/composed invariants resolved transitively)")
    if analysis.unread_by_invariant:
        add("  variables no configured invariant reads:")
        for variable in analysis.unread_by_invariant:
            add(f"    {variable}")
    else:
        add("  every variable is read by at least one configured invariant.")
    add("")

    add("[MEASURED] Justification linkage")
    if analysis.unjustified is None:
        add("  no justification: table in the manifest -- dead-weight analysis skipped.")
        add("  Add one to make every variable's right to exist auditable")
        add("  (references/architecture_tractability.md, 'Grow The Model By Evidence').")
    elif analysis.unjustified:
        add("  DEAD WEIGHT -- variables with no invariant, effect, or kill-test linkage:")
        for variable in analysis.unjustified:
            add(f"    {variable}")
    else:
        add("  every variable has a recorded justification linkage.")
    add("")

    if analysis.tlc_findings:
        add("[MEASURED] TLC transition-level diagnostics")
        for finding in analysis.tlc_findings:
            add(f"  {finding['level']}: {finding['message']}")
        add("")

    add("  A poor score is not a verdict. Some components score badly and still need to")
    add("  exist in that form -- performance paths, protocol-mandated shapes, irreducible")
    add("  domain complexity. This output is evidence for the owner, not a decision.")
    add("  Before recording ANY complexity reduction as a result: read the transition-level")
    add("  diff. A generated-states drop at constant distinct states is a RED FLAG (a")
    add("  deleted self-loop), not a win -- the distinct-state gate cannot see it.")
    add("")

    add("[MEASURED] Complexity thresholds (advisory -- warnings only)")
    add(f"  source: {analysis.manifest_path or 'documented defaults'}")
    for key in (
        "max_state_space_bound",
        "max_distinct_states",
        "max_component_variables",
        "max_component_actions",
    ):
        add(f"    {key}: {analysis.budgets[key]:,}")
    add("  max_state_space_bound compares against the STATIC declared-representation bound above.")
    add("  max_distinct_states compares against ACTUAL reachable states and is checked only once")
    add("  TLC has measured them (--tlc-report); the two are not interchangeable.")
    add("")
    if not analysis.warnings:
        add("  No complexity warnings -- every metric is within its advisory threshold.")
    else:
        add("  COMPLEXITY WARNINGS -- these are FINDINGS. They do NOT block promotion,")
        add("  do NOT refuse case generation, and do NOT change the exit code. Complexity is a")
        add("  scanner, not a gate (references/architecture_tractability.md, 'Advisory, Not")
        add("  Blocking'). The owner decides, with the user, whether to act on each one.")
        for warning in analysis.warnings:
            add("")
            add(f"  WARNING: {warning.finding}")
    add("")

    # CD-03: the project's self-configured fitness functions. The section only
    # exists when the project configured rules (or a rules source is broken) --
    # there are NO built-in rules. Firings are notifications for future agents,
    # never blocks: the exit code is unchanged by any number of firings.
    if analysis.fitness is not None:
        fitness = analysis.fitness
        add("[CONFIGURED] Fitness functions (self-configured; advisory -- report, never block)")
        add(f"  sources: {', '.join(fitness.sources) or '(none)'}")
        for error in fitness.errors:
            add(f"  CONFIG ERROR: {error}")
        for result in fitness.results:
            if result.status == "holds":
                add(f"  holds: {result.name}")
            else:
                add(f"  {result.status.upper()}: {result.name} -- {result.detail}")
                if result.description:
                    add(f"    ({result.description})")
        if fitness.fired:
            add("")
            add("  A FIRED fitness function is a NOTIFICATION to this project's future")
            add("  agents: a condition the project's agent declared it wants to hold does")
            add("  not hold on this scan. It does NOT block promotion and does NOT change")
            add("  the exit code -- read it, judge it, and decide with the owner.")
        add("")

    add("  `analyze complexity` exits 0 whenever it can analyze the model -- a complex model")
    add("  is a finding, not a failure. It exits nonzero ONLY when the model cannot be")
    add("  analyzed at all (e.g. an unresolved module hierarchy); that is 'I could not")
    add("  measure this', which is distinct from 'this is complex'.")
    return "\n".join(out) + "\n"


def descriptor_payload(analysis: Analysis) -> dict[str, Any]:
    """The descriptor as a plain dict -- the JSON payload shape.

    Also the fact source for CD-03 fitness functions: rules are evaluated over
    exactly the facts this payload publishes, nothing private.
    """
    payload: dict[str, Any] = {
        "module": analysis.module,
        "spec": str(analysis.tla_path),
        "cfg": str(analysis.cfg_path),
        "manifest": str(analysis.manifest_path) if analysis.manifest_path else None,
        "measured": {
            "dimensions": [
                {
                    "variable": d.variable,
                    "domain": d.expression,
                    "cardinality": d.cardinality,
                    "source": d.source,
                    "note": d.note,
                }
                for d in analysis.dimensions
            ],
            "state_space_upper_bound": analysis.bound,
            "state_space_bound_known": analysis.bound is not None,
            "state_space_bound_source": analysis.bound_source,
            # CM-01-DF-03: completeness travels with the number, in the same
            # payload the ledger and the CD-03 fitness rules read. A rule or a
            # ledger entry that quotes state_space_upper_bound without this is
            # quoting a product over a subset of the representation.
            "state_space_bound_complete": analysis.completeness.complete,
            "state_space_bound_resolved_variables": analysis.completeness.resolved,
            "state_space_bound_total_variables": analysis.completeness.total,
            "state_space_bound_caveat": analysis.completeness.caveat() or None,
            "state_space_bound_within_cap": analysis.completeness.comparable_to_cap(
                analysis.bound, analysis.budgets["max_state_space_bound"]
            ),
            "unbounded_variables": analysis.unbounded,
            "actions": [
                {"name": a.name, "reads": sorted(a.reads), "writes": sorted(a.writes)}
                for a in analysis.actions
            ],
            "action_attribution": analysis.action_attribution,
            "modularity": analysis.modularity_score,
            "components": [sorted(c) for c in analysis.communities],
            "port_crossing_actions": analysis.crossings,
            "dense_rows": analysis.dense_rows,
            "dense_columns": analysis.dense_columns,
            "unread_by_invariant": analysis.unread_by_invariant,
            "unjustified_variables": analysis.unjustified,
            "tlc_findings": analysis.tlc_findings,
        },
        "budgets": {
            key: analysis.budgets[key]
            for key in (
                "max_state_space_bound",
                "max_distinct_states",
                "max_component_variables",
                "max_component_actions",
            )
        },
        "advisory": {
            "blocks_promotion": False,
            "clean": analysis.gate_passed,
            "warnings": [
                {
                    "kind": warning.kind,
                    "finding": warning.finding,
                }
                for warning in analysis.warnings
            ],
        },
    }
    # CD-03: self-configured fitness functions. None when the project has no
    # rules configured (there are no built-in rules). Advisory only.
    if analysis.fitness is None:
        payload["fitness"] = None
    else:
        payload["fitness"] = {
            "blocks_promotion": False,
            "sources": analysis.fitness.sources,
            "config_errors": analysis.fitness.errors,
            "fired": [r.name for r in analysis.fitness.fired],
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "detail": r.detail,
                    "description": r.description,
                }
                for r in analysis.fitness.results
            ],
        }
    return payload


def render_json(analysis: Analysis) -> str:
    return json.dumps(descriptor_payload(analysis), indent=2, sort_keys=False) + "\n"


# --------------------------------------------------------------------------
# Advisory report helper used by case generation
# --------------------------------------------------------------------------


def gate_report(
    tla_path: Path,
    cfg_path: Path,
    manifest_path: Path | None,
    *,
    search_path: Sequence[Path] | None = None,
) -> tuple[bool, str]:
    """Advisory complexity report for case generation. Returns ``(clean, message)``.

    MF-036: this is a scanner, not a gate. ``clean`` is True when the scan
    raised no complexity warnings; a False value means the caller should print
    the warnings, NOT that it should refuse. Case generation is expected to
    proceed either way (references/architecture_tractability.md, "Advisory, Not
    Blocking"). The one thing that is not a mere finding is a model the scan
    cannot analyze at all (MF-030 fail-closed): that is reported as ``clean =
    False`` with a "could not be resolved" message so the caller can surface it,
    but even then the caller proceeds -- TLC may handle a model the static
    scanner cannot.
    """
    try:
        analysis = analyze(tla_path, cfg_path, manifest_path, search_path=search_path)
    except ModuleResolutionError as exc:
        return False, (
            "complexity scan could not analyze this model -- the module "
            "hierarchy could not be resolved:\n"
            f"  {exc}\n"
            "This is an 'I could not measure this' note, not a promotion block; "
            "case generation still proceeds."
        )
    if analysis.gate_passed:
        # CM-01-DF-03: gate_passed is only reachable here with a COMPLETE bound
        # at or under the cap -- an incomplete bound raises the
        # state_space_bound_partial advisory, so this sentence can no longer be
        # printed over a product taken across a subset of the variables.
        return True, (
            f"complexity scan clean: state-space upper bound {analysis.bound:,} "
            f"(complete: all {analysis.completeness.total} declared variables "
            f"resolved) within max_state_space_bound "
            f"{analysis.budgets['max_state_space_bound']:,}, and "
            "every component within its advisory thresholds"
        )
    lines = [
        "complexity scan -- ADVISORY WARNINGS (these do NOT block case generation):",
        "",
    ]
    for warning in analysis.warnings:
        lines.append(f"  WARNING: {warning.finding}")
    lines.append("")
    lines.append("Dominant dimensions:")
    dominant = sorted(
        (d for d in analysis.dimensions if d.bounded), key=lambda d: -(d.cardinality or 0)
    )[:5]
    for d in dominant:
        lines.append(f"  {d.variable}: {d.cardinality:,}  ({d.expression})")
    lines.append("")
    lines.append("Run `tla-spec-dev analyze complexity <spec> <cfg>` for the full descriptor.")
    return False, "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def default_cfg_for(tla_path: Path) -> Path:
    candidate = tla_path.with_suffix(".cfg")
    if candidate.is_file():
        return candidate
    return tla_path.parent / "MC.cfg"


def default_manifest_for(tla_path: Path) -> Path | None:
    candidate = tla_path.parent / "spec_manifest.yaml"
    return candidate if candidate.is_file() else None


def run(args: argparse.Namespace) -> int:
    tla_path = Path(args.tla).resolve()
    if not tla_path.is_file():
        print(f"ERROR: spec not found: {tla_path}", file=sys.stderr)
        return EXIT_USAGE
    cfg_path = Path(args.cfg).resolve() if args.cfg else default_cfg_for(tla_path)
    if not cfg_path.is_file():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        return EXIT_USAGE
    manifest_path = Path(args.manifest).resolve() if args.manifest else default_manifest_for(tla_path)

    try:
        analysis = analyze(
            tla_path,
            cfg_path,
            manifest_path,
            baseline_tlc=Path(args.baseline_tlc).resolve() if args.baseline_tlc else None,
            current_tlc=Path(args.tlc_report).resolve() if args.tlc_report else None,
        )
    except ModuleResolutionError as exc:
        # MF-030 / MF-036: a hierarchy the analyzer CANNOT resolve is the one
        # genuine error -- "I could not measure this model" -- so it fails closed
        # nonzero rather than emit an under-reported number. This is distinct
        # from "this model is complex", which is now advisory and exits 0.
        print(
            "ERROR: complexity analysis could not analyze this model -- the module "
            f"hierarchy could not be resolved:\n  {exc}",
            file=sys.stderr,
        )
        return EXIT_ANALYSIS_ERROR

    rendered = render_json(analysis) if args.format == "json" else render_text(analysis)
    sys.stdout.write(rendered)
    if args.out:
        # RC-01 (MF-026 G-3): the write is constrained to the surface the
        # `evidence_report` port declares. It used to take a bare string.
        try:
            out_path = resolve_evidence_out(args.out)
        except EvidencePathError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return EXIT_USAGE
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        print(f"wrote evidence: {out_path}", file=sys.stderr)
    # MF-036: a complex model is a finding, not a failure. Once the model could
    # be analyzed, the command exits 0 regardless of how many advisory warnings
    # the scan raised -- complexity never blocks promotion.
    return EXIT_PASS


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("tla", help="TLA+ module to analyze.")
    parser.add_argument("cfg", nargs="?", help="TLC config. Defaults to <module>.cfg or MC.cfg.")
    parser.add_argument("--manifest", help="spec_manifest.yaml carrying budgets: and justification:.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    parser.add_argument(
        "--out",
        help=(
            "Also write the report here. RC-01: the path MUST resolve under a "
            "`results/` directory -- that is the surface the `evidence_report` "
            "effect port declares, and a write anywhere else is undeclared."
        ),
    )
    parser.add_argument("--tlc-report", help="TLC output for this model, for transition-level diagnostics.")
    parser.add_argument("--baseline-tlc", help="Baseline TLC output to compare against (self-loop check).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="analyze_complexity",
        description="Static complexity analysis and budget gate for a constrained-profile TLA+ spec.",
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
