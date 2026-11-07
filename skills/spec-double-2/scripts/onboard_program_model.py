#!/usr/bin/env python3
"""Scaffold the first whole-program TLA+ model for an existing repository.

This is the project-onboarding path. It creates ``specs/program_model`` as the
accepted baseline and intentionally does not create ``specs/current`` or
``specs/desired_program_model``. Those directories are for later ticket work
after a program model already exists.

The baseline is a *three-module* model with both executable views wired up:

- ``Core.tla``: shared constants and helper operators.
- ``Internal.tla`` / ``Internal.cfg``: fine-grained program state. Generates
  spec-unit cases, executed through the spec-unit adapters in ``adapters.py``
  and mapped by ``case_adapters.toml``.
- ``External.tla`` / ``External.cfg``: publicly observable behavior. Generates
  Test Graph cases, executed through the Test Graph adapters in ``adapters.py``
  and mapped by ``testgraph_bindings.yml``.

Both views are mandatory. A baseline with only one module cannot generate Test
Graph cases, so the project can never be validated against its public surface.
See ``references/testgraph_adapters.md``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from budgets import budgets_block  # noqa: E402


# The accepted baseline is not complete until every one of these exists. This
# list is the executable form of the checklist in SKILL.md; keep them in sync.
# The minimum baseline (2026-09-14): a model, its cfg, and the manifest. That is
# everything TLC, `analyze complexity` and the implementation brief -- the
# validated products -- read. It used to be thirteen files, and an agent that
# did not produce all thirteen was told the baseline was "not complete".
REQUIRED_BASELINE_FILES = (
    "Core.tla",
    "Internal.tla",
    "Internal.cfg",
    "spec_manifest.yaml",
)

# The rest of the accepted shape: the External view, generated-case adapters,
# effect providers and Test Graph bindings. `scaffold project --full` emits
# them; nothing requires them. Add them when the project wants generated cases
# or its public surface driven through a test_graph.
OPTIONAL_BASELINE_FILES = (
    "External.tla",
    "External.cfg",
    "actions.yml",
    "adapters.py",
    "providers.py",
    "effect_provider_usage.yaml",
    "case_adapters.toml",
    "testgraph_bindings.yml",
    "tlc_projection.py",
)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "program_model"


def _module_name(value: str) -> str:
    direct = re.sub(r"[^a-zA-Z0-9]+", "", value)
    if direct and direct[0].isalpha() and any(ch.isupper() for ch in direct[1:]):
        return direct
    candidate = "".join(part.capitalize() for part in re.split(r"[^a-zA-Z0-9]+", value) if part)
    if not candidate:
        return "ProgramModel"
    if candidate[0].isdigit():
        return f"Program{candidate}"
    return candidate


def write_file(path: Path, content: str, *, force: bool, dry_run: bool) -> bool:
    if path.exists() and not force:
        return False
    if dry_run:
        print(f"would write {path}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")
    return True


def _resolve_spec_root(repo_root: Path, spec_root: Path) -> Path:
    return spec_root if spec_root.is_absolute() else repo_root / spec_root


def _display_spec_root(repo_root: Path, spec_root: Path) -> str:
    if spec_root.is_absolute():
        try:
            return spec_root.relative_to(repo_root).as_posix()
        except ValueError:
            return spec_root.as_posix()
    return spec_root.as_posix()


def core_tla() -> str:
    return """------------------------------- MODULE Core -------------------------------
\\* Shared constants and helper operators for the whole-program model.
\\* Internal.tla and External.tla both EXTEND this module, so anything both
\\* views need to agree on belongs here.
\\*
\\* SCAFFOLD: replace the placeholder domain below with this repository's real
\\* resources. Completion target: examples/distributed_history/specs/program_model/
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
  Actors,
  Records

RecordStatus == {"none", "accepted"}
ProjectionStatus == {"none", "published"}

SeqToSet(seq) == {seq[i] : i \\in 1..Len(seq)}

=============================================================================
"""


def internal_tla() -> str:
    return """----------------------------- MODULE Internal -----------------------------
\\* INTERNAL VIEW: fine-grained program/component state.
\\*
\\* Actions here generate spec-unit cases. They are executed by the spec-unit
\\* adapters in adapters.py, mapped by case_adapters.toml.
\\*
\\* SCAFFOLD: replace these placeholder actions with the repository's real
\\* internal transitions.
EXTENDS Core

VARIABLES owners, records, outbox, projections, lastInternalAction

InternalVars == <<owners, records, outbox, projections, lastInternalAction>>

InternalInit ==
  /\\ owners = {}
  /\\ records = [r \\in Records |-> [owner |-> CHOOSE a \\in Actors : TRUE, status |-> "none"]]
  /\\ outbox = {}
  /\\ projections = [r \\in Records |-> "none"]
  /\\ lastInternalAction = [name |-> "Init", params |-> <<>>]

\\* @action RegisterActor
\\* @layer internal
\\* @controllability unit_direct
RegisterActor(a) ==
  /\\ a \\in Actors
  /\\ a \\notin owners
  /\\ owners' = owners \\cup {a}
  /\\ UNCHANGED <<records, outbox, projections>>
  /\\ lastInternalAction' = [name |-> "RegisterActor", params |-> [actor |-> a]]

\\* @action AcceptRecord
\\* @layer internal
\\* @controllability unit_direct
AcceptRecord(a, r) ==
  /\\ a \\in owners
  /\\ r \\in Records
  /\\ records[r].status = "none"
  /\\ records' = [records EXCEPT ![r] = [owner |-> a, status |-> "accepted"]]
  /\\ outbox' = outbox \\cup {r}
  /\\ UNCHANGED <<owners, projections>>
  /\\ lastInternalAction' = [name |-> "AcceptRecord", params |-> [actor |-> a, record |-> r]]

\\* @action PublishRecord
\\* @layer internal
\\* @controllability unit_direct
PublishRecord(r) ==
  /\\ r \\in outbox
  /\\ projections' = [projections EXCEPT ![r] = "published"]
  /\\ outbox' = outbox \\ {r}
  /\\ UNCHANGED <<owners, records>>
  /\\ lastInternalAction' = [name |-> "PublishRecord", params |-> [record |-> r]]

InternalNext ==
  \\/ \\E a \\in Actors : RegisterActor(a)
  \\/ \\E a \\in Actors, r \\in Records : AcceptRecord(a, r)
  \\/ \\E r \\in Records : PublishRecord(r)

\\* @invariant InternalInvariant
InternalInvariant ==
  /\\ owners \\subseteq Actors
  /\\ outbox \\subseteq Records
  /\\ \\A r \\in outbox : records[r].status = "accepted"
  /\\ \\A r \\in Records :
       projections[r] = "published" => records[r].status = "accepted"

InternalSpec == InternalInit /\\ [][InternalNext]_InternalVars

=============================================================================
"""


def internal_cfg() -> str:
    return """SPECIFICATION InternalSpec
INVARIANT InternalInvariant

\\* The bounded model is intentionally terminating: once every actor is
\\* registered and every record is accepted and published, no action is enabled.
\\* That is exhaustion of the finite model, not a bug.
CHECK_DEADLOCK FALSE

CONSTANTS
  Actors = {"actor-1", "actor-2"}
  Records = {"record-1", "record-2"}
"""


def external_tla() -> str:
    return """----------------------------- MODULE External -----------------------------
\\* EXTERNAL VIEW: the behavior a test harness can drive or observe from
\\* outside the program. This is a projection of the internal semantics, not an
\\* independent business model.
\\*
\\* Actions here generate Test Graph cases. They are executed by the Test Graph
\\* adapters in adapters.py, mapped by testgraph_bindings.yml.
\\*
\\* External does NOT mean distributed. For an HTTP service it is requests. For
\\* a CLI it is command invocations plus filesystem assertions. For a library it
\\* is the public API surface and the files/streams it produces. Model whatever
\\* a caller can actually see.
\\*
\\* SCAFFOLD: replace these placeholder submissions with this repository's real
\\* public surface, including negative/duplicate cases. See
\\* references/edge-cases.md for choosing boundary cases.
EXTENDS Internal

CONSTANTS Clients

VARIABLES responses, lastExternalAction

ExternalVars == <<InternalVars, responses, lastExternalAction>>

ExternalInit ==
  /\\ InternalInit
  /\\ responses = [c \\in Clients |-> [status |-> 0, body |-> <<>>]]
  /\\ lastExternalAction = [name |-> "Init", params |-> <<>>]

MarkExternal(actionName, params) ==
  lastExternalAction' = [name |-> actionName, params |-> params]

\\* @action SubmitRegisterActor
\\* @layer external
\\* @controllability e2e_direct
SubmitRegisterActor(c, a) ==
  /\\ c \\in Clients
  /\\ RegisterActor(a)
  /\\ responses' = [responses EXCEPT ![c] = [status |-> 201, body |-> [actor |-> a]]]
  /\\ MarkExternal("SubmitRegisterActor", [client |-> c, actor |-> a])

\\* @action SubmitDuplicateRegisterActor
\\* @layer external
\\* @controllability e2e_direct
SubmitDuplicateRegisterActor(c, a) ==
  /\\ c \\in Clients
  /\\ a \\in owners
  /\\ UNCHANGED InternalVars
  /\\ responses' = [responses EXCEPT ![c] = [status |-> 200, body |-> [actor |-> a, idempotent |-> TRUE]]]
  /\\ MarkExternal("SubmitDuplicateRegisterActor", [client |-> c, actor |-> a])

\\* @action SubmitAcceptRecord
\\* @layer external
\\* @controllability e2e_direct
SubmitAcceptRecord(c, a, r) ==
  /\\ c \\in Clients
  /\\ AcceptRecord(a, r)
  /\\ responses' = [responses EXCEPT ![c] = [status |-> 202, body |-> [record |-> r, status |-> "accepted"]]]
  /\\ MarkExternal("SubmitAcceptRecord", [client |-> c, actor |-> a, record |-> r])

\\* @action SubmitAcceptRecordUnknownActor
\\* @layer external
\\* @controllability e2e_direct
SubmitAcceptRecordUnknownActor(c, a, r) ==
  /\\ c \\in Clients
  /\\ a \\in Actors
  /\\ a \\notin owners
  /\\ r \\in Records
  /\\ UNCHANGED InternalVars
  /\\ responses' = [responses EXCEPT ![c] = [status |-> 404, body |-> [error |-> "actor_not_found"]]]
  /\\ MarkExternal("SubmitAcceptRecordUnknownActor", [client |-> c, actor |-> a, record |-> r])

\\* @action SubmitDuplicateAcceptRecord
\\* @layer external
\\* @controllability e2e_direct
SubmitDuplicateAcceptRecord(c, a, r) ==
  /\\ c \\in Clients
  /\\ a \\in owners
  /\\ r \\in Records
  /\\ records[r].status # "none"
  /\\ UNCHANGED InternalVars
  /\\ responses' = [responses EXCEPT ![c] = [status |-> 409, body |-> [error |-> "record_exists"]]]
  /\\ MarkExternal("SubmitDuplicateAcceptRecord", [client |-> c, actor |-> a, record |-> r])

\\* @action RunPublishWorker
\\* @layer external
\\* @controllability e2e_direct
RunPublishWorker(c) ==
  /\\ c \\in Clients
  /\\ outbox # {}
  /\\ projections' = [r \\in Records |-> IF r \\in outbox THEN "published" ELSE projections[r]]
  /\\ outbox' = {}
  /\\ UNCHANGED <<owners, records>>
  /\\ lastInternalAction' = [name |-> "PublishAllOutbox", params |-> [records |-> outbox]]
  /\\ UNCHANGED responses
  /\\ MarkExternal("RunPublishWorker", [client |-> c, pending |-> Cardinality(outbox)])

\\* @action RunPublishWorkerNoop
\\* @layer external
\\* @controllability e2e_direct
RunPublishWorkerNoop(c) ==
  /\\ c \\in Clients
  /\\ outbox = {}
  /\\ UNCHANGED InternalVars
  /\\ UNCHANGED responses
  /\\ MarkExternal("RunPublishWorkerNoop", [client |-> c, pending |-> 0])

\\* @action HiddenInternalProgress
\\* @layer internal
\\* @controllability hidden
HiddenInternalProgress ==
  /\\ InternalNext
  /\\ UNCHANGED <<responses, lastExternalAction>>

ExternalNext ==
  \\/ \\E c \\in Clients, a \\in Actors : SubmitRegisterActor(c, a)
  \\/ \\E c \\in Clients, a \\in Actors : SubmitDuplicateRegisterActor(c, a)
  \\/ \\E c \\in Clients, a \\in Actors, r \\in Records : SubmitAcceptRecord(c, a, r)
  \\/ \\E c \\in Clients, a \\in Actors, r \\in Records : SubmitAcceptRecordUnknownActor(c, a, r)
  \\/ \\E c \\in Clients, a \\in Actors, r \\in Records : SubmitDuplicateAcceptRecord(c, a, r)
  \\/ \\E c \\in Clients : RunPublishWorker(c)
  \\/ \\E c \\in Clients : RunPublishWorkerNoop(c)
  \\/ HiddenInternalProgress

\\* @invariant ExternalInvariant
ExternalInvariant ==
  /\\ InternalInvariant
  /\\ \\A c \\in Clients :
       responses[c].status \\in {0, 200, 201, 202, 404, 409}

Spec == ExternalInit /\\ [][ExternalNext]_ExternalVars
Invariant == ExternalInvariant

=============================================================================
"""


def external_cfg() -> str:
    return """SPECIFICATION Spec
INVARIANT Invariant

\\* See Internal.cfg: the bounded model is intentionally terminating.
CHECK_DEADLOCK FALSE

CONSTANTS
  Clients = {"client-1"}
  Actors = {"actor-1", "actor-2"}
  Records = {"record-1", "record-2"}
"""


def actions_yml() -> str:
    return """# Which view each action belongs to, and what it generates.
#
#   layer: internal  -> spec-unit cases  (case_adapters.toml)
#   layer: external  -> Test Graph cases (testgraph_bindings.yml)
#   controllability: hidden -> generates nothing; internal progress the harness
#                              cannot drive directly.
#   effect_ports: typed semantic ports required while this case executes.
#
# SCAFFOLD: keep this in sync with Internal.tla / External.tla.
actions:
  RegisterActor:
    layer: internal
    controllability: unit_direct
    generates:
      - spec_unit
    effect_ports: []
  AcceptRecord:
    layer: internal
    controllability: unit_direct
    generates:
      - spec_unit
    effect_ports: []
  PublishRecord:
    layer: internal
    controllability: unit_direct
    generates:
      - spec_unit
    effect_ports: []
  SubmitRegisterActor:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  SubmitDuplicateRegisterActor:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  SubmitAcceptRecord:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  SubmitAcceptRecordUnknownActor:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  SubmitDuplicateAcceptRecord:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  RunPublishWorker:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  RunPublishWorkerNoop:
    layer: external
    controllability: e2e_direct
    generates:
      - testgraph
    effect_ports: []
  HiddenInternalProgress:
    layer: internal
    controllability: hidden
    generates: []
    effect_ports: []
"""


def case_adapters_toml() -> str:
    return """# ADAPTER MODULES ARE NAMED BARE, AND THAT IS LOAD-BEARING.
#
# A binding written `specs.program_model.adapters:X` is resolved from the
# PROJECT ROOT, so it means the accepted baseline's adapters no matter which
# view is selected. `open ticket` copies these files verbatim into
# `specs/tickets/<id>/{current,desired}`, so a ticket that edits its own
# `adapters.py` runs GREEN WITHOUT EVER EXECUTING IT -- the corpus is the
# ticket's and the adapters are the baseline's.
#
# A bare `adapters:X` resolves against the SELECTED spec directory, which both
# loaders put on the import path (`default_import_roots_for` adds the spec dir;
# `enforce_external_channels` adds the bindings file's own directory). So the
# view executes its own adapters, which is the only reading under which a
# ticket-local adapter change is validated at all.
#
# ONE CONDITION, because it is easy to lose: `default_import_roots_for` is
# skipped entirely when `--import-root` is passed explicitly. A caller that
# states its own roots must include the spec directory among them, or a bare
# name stops resolving. The default path needs nothing.
#
# Found by a ticket agent in examples/agent_integration round 001, filed as its
# own DEF-001 against the epic it was working, with the reproduction that names
# this scaffold: *"consider the same in the tla-spec-dev ticket scaffold so
# seeded bindings never point at another view."*
#
# SPEC-UNIT ADAPTERS (internal view).
#
# Maps each Internal.tla action to the adapter that drives the real internal
# boundary for a generated spec-unit case. Run with:
#
#   tla-spec-dev run spec-unit-tests
#
# Every action in Internal.tla with `generates: [spec_unit]` needs an entry.
# To supply a concrete representative for a generated semantic effect port,
# uncomment and adapt this project-owned binding:
#
# [effect_providers.ExampleEffectPort]
# provider = "providers:effect_provider"

[adapters.RegisterActor]
adapter = "adapters:RegisterActorInternalAdapter"
kind = "program-internal"

[adapters.AcceptRecord]
adapter = "adapters:AcceptRecordInternalAdapter"
kind = "program-internal"

[adapters.PublishRecord]
adapter = "adapters:PublishRecordInternalAdapter"
kind = "program-internal"
"""


def providers_py() -> str:
    return '''"""Project-owned semantic effect provider.

Generated cases select the abstract effect outcome. Providers choose concrete
representatives and bind repository-owned implementations for one case and one
deterministic fuzz iteration. Read references/effect_providers.md.

SCAFFOLD: implement one provider against the generated port Protocols before
enabling its mapping tables. The framework ships no domain implementations.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

from spec_double_compiler.runtime import EffectProviderContext


class ProjectEffectProvider:
    @contextmanager
    def bind(self, context: EffectProviderContext) -> Iterator[Any | None]:
        # SCAFFOLD: acquire the repository-owned implementation selected by
        # context.port_name and context.case. Use context.derived_seed for
        # deterministic representatives. Yield the generated-port
        # implementation, or None only when this scope installs and restores
        # its own bounded integration.
        raise NotImplementedError(
            f"SCAFFOLD: bind generated port {context.port_name}"
        )
        yield None


effect_provider = ProjectEffectProvider()
'''


def effect_provider_usage_yml() -> str:
    return """# Local, reviewable evidence about agent-authored providers.
version: 1
providers: []
# - port: ExampleEffectPort
#   provider: providers:effect_provider
#   binding_style: explicit_injection  # explicit_injection | self_installed | external_fixture | other
#   state_scope: execution_point
#   fuzz_dimensions: []
#   assertions: []
#   cleanup: context_manager
#   bypass_limits: []
"""


def testgraph_bindings_yml() -> str:
    return """# Adapter modules are named BARE here for the same reason they are in
# case_adapters.toml: a view-qualified `specs.program_model.adapters:X`
# resolves from the project root, so a ticket copy of this file silently drives
# the accepted baseline's adapters instead of its own. `enforce_external_channels`
# puts this file's own directory on the import path, so a bare name means "the
# adapters beside these bindings", which is the only reading that makes a
# ticket-local adapter change observable.
#
# TEST GRAPH ADAPTERS (external view).
#
# Maps each External.tla action to the adapter that drives the real public
# surface, plus the projector/assertion that compare deployed state back to the
# model. Read references/testgraph_adapters.md before editing this file.
#
#   channel             -> HOW the program is driven: http/cli/fs/queue/k8s
#   adapter             -> drives the public action (HTTP call, CLI run, ...)
#   projector           -> observes real state, projected into the TLA shape
#   expected_projection -> expected state, usually a projection of case.after
#   assertion           -> compares the two and writes per-case evidence
#
# Every action in External.tla with `generates: [testgraph]` needs an entry.
# Test Graph nodes are end-to-end External-view executions only. TLC runs and
# spec-unit runs are direct tla-spec-dev commands, never graph nodes.
#
# MF-015 external channel enforcement. Both the runner and the exporter refuse
# to proceed unless:
#   * every binding below declares a `channel`;
#   * no adapter/projector/expected_projection/assertion module imports
#     `external.production_package`, directly or via a first-party helper --
#     an adapter that imports the program under test is running it in-process
#     and is a spec-unit adapter however it is labelled; and
#   * `external.port_bindings` names each port double or real, with at least
#     one real. All-doubles is a spec-unit run, never a Test Graph node.
# Replace the placeholders below with this program's real values.
external:
  production_package: REPLACE_ME_program_package
  port_bindings:
    REPLACE_ME_Port: real
  # Uncomment to drive a transport beyond the base five. Explicit and visible,
  # per-program -- it widens the accepted set, it never excuses a binding that
  # declares no channel.
  # additional_channels: [grpc]

actions:
  SubmitRegisterActor:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:RegisterActorExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
  SubmitDuplicateRegisterActor:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:RegisterActorExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
  SubmitAcceptRecord:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:AcceptRecordExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
  SubmitAcceptRecordUnknownActor:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:AcceptRecordExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
  SubmitDuplicateAcceptRecord:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:AcceptRecordExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
  RunPublishWorker:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:PublishWorkerExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
  RunPublishWorkerNoop:
    view: external
    channel: http
    layer: external
    controllability: e2e_direct
    kind: program-external
    adapter: adapters:PublishWorkerExternalAdapter
    projector: adapters:ProgramStateProjector
    expected_projection: adapters:ExpectedProgramProjection
    assertion: adapters:ProjectedStateAssertion
"""


def adapters_py(module: str) -> str:
    return f'''"""Adapters for the {module} program model.

This file carries BOTH executable views. Neither is optional:

- Spec-unit adapters (internal view) drive real internal boundaries for cases
  generated from Internal.tla. Mapped by ``case_adapters.toml``.
- Test Graph adapters (external view) drive the real public surface for cases
  generated from External.tla, then project observed state back into the model
  shape so it can be compared with the generated expected state. Mapped by
  ``testgraph_bindings.yml``.

Read ``references/testgraph_adapters.md`` for the hook order and the
projected-state assertion contract. The worked reference implementation is
``examples/distributed_history/specs/program_model/adapters.py``.

SCAFFOLD: every ``apply``/``observe`` below raises NotImplementedError. Replace
each one with a call into this repository's real boundary. The class names here
must stay in sync with ``case_adapters.toml`` and ``testgraph_bindings.yml``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spec_double_compiler.runtime import CaseRunResult


def _state(value: Any) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


# ---------------------------------------------------------------------------
# Spec-unit adapters (internal view) -> case_adapters.toml
#
# Hook order per batch: setup_all -> (run per case) -> teardown_all.
# `run` materializes case.before, applies one internal action, and returns the
# observed output plus the resulting state in the model's shape.
# ---------------------------------------------------------------------------


class _InternalAdapter:
    def setup_all(self, context: Any) -> None:
        """Suite-wide internal setup: open a store, clear shared tables."""

    def teardown_all(self, context: Any) -> None:
        """Suite-wide internal teardown."""

    def run(self, case: Any, work_dir: Path | None = None) -> CaseRunResult:
        store = self.load(case.before)
        output = self.apply(store, case.input.params)
        return CaseRunResult(output=output, after=self.snapshot(store))

    def load(self, before: dict[str, Any]) -> Any:
        """Materialize the generated `before` state in the real component."""
        raise NotImplementedError(
            "load the TLA `before` state into this repository's internal component"
        )

    def snapshot(self, store: Any) -> dict[str, Any]:
        """Observe the real component and return it in the Internal.tla shape."""
        raise NotImplementedError(
            "project this repository's internal state back into the Internal.tla shape"
        )

    def apply(self, store: Any, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class RegisterActorInternalAdapter(_InternalAdapter):
    def apply(self, store: Any, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("call the real RegisterActor boundary")


class AcceptRecordInternalAdapter(_InternalAdapter):
    def apply(self, store: Any, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("call the real AcceptRecord boundary")


class PublishRecordInternalAdapter(_InternalAdapter):
    def apply(self, store: Any, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("call the real PublishRecord boundary")


# ---------------------------------------------------------------------------
# Test Graph adapters (external view) -> testgraph_bindings.yml
#
# Hook order per batch:
#   setup_all -> for each case: setup -> run -> projected-state assertion ->
#   teardown -> ... -> teardown_all
#
# `setup` must establish the abstract pre-state before each case. That is what
# makes leftover residue from a previous case visible instead of silently
# passing.
# ---------------------------------------------------------------------------


class _ExternalAdapter:
    def setup_all(self, context: Any) -> None:
        """Suite-wide external setup: start/await the app, reset shared state.

        For an HTTP service: wait for health, reset the deployment.
        For a CLI: create the workspace root.
        """

    def teardown_all(self, context: Any) -> None:
        """Suite-wide external teardown."""

    def setup(self, context: Any) -> None:
        """Load `context.case.before` into the real system before each case."""
        raise NotImplementedError(
            "materialize the TLA `before` state on the real public surface "
            "(debug/admin endpoint, fixture files, seeded DB, ...)"
        )

    def teardown(self, context: Any) -> None:
        """Clear per-case state so the next case starts from its own `before`."""

    def run(self, case: Any, work_dir: Path | None = None) -> CaseRunResult:
        return CaseRunResult(output=self.apply(case.input.params))

    def apply(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class RegisterActorExternalAdapter(_ExternalAdapter):
    def apply(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("drive the real public RegisterActor surface")


class AcceptRecordExternalAdapter(_ExternalAdapter):
    def apply(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("drive the real public AcceptRecord surface")


class PublishWorkerExternalAdapter(_ExternalAdapter):
    def apply(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("drive the real public publish-worker surface")


# ---------------------------------------------------------------------------
# Projected-state assertion (external view)
#
# expected = ExpectedProgramProjection.expected_state(context)  (from case.after)
# actual   = ProgramStateProjector.observe(context)             (from real system)
# compare  = ProjectedStateAssertion.assert_state(context)
# ---------------------------------------------------------------------------


class ExpectedProgramProjection:
    def expected_state(self, context: Any) -> dict[str, Any]:
        return _visible_projection(context.case.after)


class ProgramStateProjector:
    def observe(self, context: Any) -> dict[str, Any]:
        raise NotImplementedError(
            "observe the real system's externally visible state and pass it "
            "through _visible_projection so it can be compared with case.after"
        )


class ProjectedStateAssertion:
    def assert_state(self, context: Any) -> None:
        expected = _state(context.expected)
        actual = _state(context.actual)
        artifact = context.work_dir / "program-state.json"
        payload = {{
            "case": context.case.name,
            "action": context.case.input.action,
            "params": dict(context.case.input.params),
            "expected_program_state": expected,
            "actual_projected_program_state": actual,
            "adapter_result": _case_result_payload(context.result),
            "matched": actual == expected,
        }}
        artifact.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
        if actual != expected:
            raise AssertionError(
                f"projected program state mismatch for {{context.case.name}}; wrote {{artifact}}"
            )


def _visible_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Keep only what a caller can actually observe.

    Both the expected projection and the live projector go through this, so the
    two sides are always compared in the same shape. Drop internal bookkeeping
    the public surface does not expose.
    """
    return {{
        "owners": sorted(state.get("owners", [])),
        "records": dict(state.get("records", {{}})),
        "projections": dict(state.get("projections", {{}})),
    }}


def _case_result_payload(result: CaseRunResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {{
        "output": result.output,
        "after": result.after,
        "semantic_output": result.semantic_output,
    }}
'''


def tlc_projection_py(module: str) -> str:
    return f'''"""Project raw TLC states into the shapes the generated cases use.

`project_visible_state` turns a TLC state into the externally observable
projection. `project_adapter_output` derives the output a correct adapter run
should produce for a given action, so generated cases carry an expected output
as well as an expected state.

SCAFFOLD: mirror the placeholder responses in External.tla. Reference:
examples/distributed_history/specs/program_model/tlc_projection.py
"""

from __future__ import annotations

from typing import Any


def project_visible_state(state: dict[str, Any]) -> dict[str, Any]:
    owners = sorted(str(owner) for owner in _as_list(state.get("owners", [])))
    records = {{
        str(record_id): {{
            "owner": str(_as_dict(record)["owner"]),
            "status": str(_as_dict(record)["status"]),
        }}
        for record_id, record in _as_dict(state.get("records", {{}})).items()
        if _as_dict(record).get("status") != "none"
    }}
    projections = {{
        str(record_id): str(status)
        for record_id, status in _as_dict(state.get("projections", {{}})).items()
        if status != "none"
    }}
    return {{
        "owners": owners,
        "records": dict(sorted(records.items())),
        "projections": dict(sorted(projections.items())),
    }}


def project_adapter_output(
    *,
    after: dict[str, Any],
    projected_before: dict[str, Any],
    action: str,
    params: dict[str, Any],
    view: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    if view == "external":
        response = _response_for(after, params)
        return {{"status": int(response["status"]), "body": _plain(response["body"])}}
    if action == "RegisterActor":
        return {{"status": 201, "body": {{"actor": params["actor"]}}}}
    if action == "AcceptRecord":
        return {{"status": 202, "body": {{"record": params["record"], "status": "accepted"}}}}
    if action == "PublishRecord":
        return {{"status": 200, "body": {{"processed": 1}}}}
    raise ValueError(f"no adapter output projection for {{view}} action {{action}}")


def _response_for(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    response_key = params.get("client")
    responses = _as_dict(state.get("responses", {{}}))
    if response_key not in responses:
        raise ValueError(f"response for {{response_key!r}} not found in TLC state")
    response = _as_dict(responses[response_key])
    if "status" not in response or "body" not in response:
        raise ValueError(f"malformed TLC response for {{response_key!r}}: {{response!r}}")
    return response


def _as_dict(value: Any) -> dict[Any, Any]:
    if isinstance(value, dict):
        return value
    raise TypeError(f"expected TLC mapping, got {{value!r}}")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=repr)
    return [value]


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {{str(key): _plain(inner) for key, inner in sorted(value.items(), key=lambda item: str(item[0]))}}
    if isinstance(value, tuple):
        return [_plain(inner) for inner in value]
    if isinstance(value, (set, frozenset)):
        return [_plain(inner) for inner in sorted(value, key=repr)]
    return value
'''


def tlc_command(model_dir: str, view: str) -> str:
    """The TLC command an onboarded project runs, from its repository root.

    BS-07 (#143 SF-041): this used to emit ``scripts/run_tlc.sh <tla> <cfg>``,
    a path relative to the SKILL's root that does not exist in the project, so
    each project wrote its own runner (``python3 scripts/run_project_tlc.py``)
    whose preflight then refused the ``python3`` stock macOS puts on PATH.
    ``tlc2`` is the launcher skill-manager installs onto PATH, it needs no
    Python, and ``-metadir`` keeps TLC's states/ scratch out of the model dir.
    """
    return f'(cd {model_dir} && tlc2 -metadir "$(mktemp -d)" -config {view}.cfg {view}.tla)'


def manifest(module: str, package: str, spec_root_text: str = "specs", full: bool = False) -> str:
    internal_tlc = tlc_command(f"{spec_root_text}/program_model", "Internal")
    external_tlc = tlc_command(f"{spec_root_text}/program_model", "External")
    if full:
        next_steps = f"""      - Replace the scaffolded Core/Internal/External semantics with this repository's real whole-program behavior.
      - Keep actions.yml in sync with Internal.tla and External.tla.
      - Implement the spec-unit adapters in adapters.py and map them in case_adapters.toml.
      - Implement the Test Graph adapters, projector, and assertion in adapters.py and map them in testgraph_bindings.yml.
      - Run TLC on the internal view - {internal_tlc}
      - Run TLC on the external view - {external_tlc}
      - Budgets carry documented defaults; adjust one only when analyze complexity warns on it, and note why."""
        views = """views:
  internal:
    module: Internal.tla
    config: Internal.cfg
    spec: InternalSpec
    generates: spec_unit
    adapter_mapping: case_adapters.toml
  external:
    module: External.tla
    config: External.cfg
    spec: Spec
    generates: testgraph
    adapter_mapping: testgraph_bindings.yml"""
    else:
        next_steps = f"""      - Replace the scaffolded Core/Internal semantics with this repository's real state, actions and invariants.
      - Run TLC - {internal_tlc}
      - Budgets carry documented defaults; adjust one only when analyze complexity warns on it, and note why.
      - Optional later - tla-spec-dev scaffold project --full adds the External view, adapters and providers."""
        views = """views:
  internal:
    module: Internal.tla
    config: Internal.cfg
    spec: InternalSpec
    generates: spec_unit"""
    # Hoisted rather than nested: a triple-quoted string inside this f-string
    # needs PEP 701 (Python 3.12), and the CLI shim runs whatever `python3`
    # is first on PATH -- 3.9 on stock macOS, where the whole CLI failed to
    # import with "f-string: expecting '}'".
    external_invariant = "\n  - ExternalInvariant" if full else ""
    projection = "\n  projection: tlc_projection.py" if full else ""
    return f"""module: {module}
package: {package}

status:
  workflow: project_onboarding
  model_role: accepted_program_model
  relation_to_current: none_until_ticket_workflow_starts
  relation_to_desired_program_model: none_until_ticket_workflow_starts
  updated: null
  onboarding:
    status: scaffolded
    next:
{next_steps}

# Per-program complexity and case budgets. These are advisory thresholds read
# by analyze complexity (which warns with facts and never blocks) and by the
# EXPERIMENTAL fuzzing surface (case generation, the adapter runner, the
# mutation kill test). Defaults come from references/modular_fuzzing.md and
# need no agreement before modeling; when you change one, record a one-line
# rationale. Doctrine: SKILL.md "Complexity Budgets Are Advisory".
{budgets_block()}
# Optional dead-weight audit (advisory): add a justification: table linking
# every declared variable to what depends on it. Schema: one mapping per
# variable with at least one NON-EMPTY list among invariants/effects/
# kill_tests. Prose strings are not linkage -- a prose-only entry leaves the
# variable flagged DEAD WEIGHT. Example:
#   justification:
#     orders:
#       invariants: [SafetyInv]
#       effects: [order_submitted]
#       kill_tests: [test_order_cap]

{views}

state:
  {module}State:
    fields:
      owners:
        type: frozenset[ActorId]
        tla: owners
      records:
        type: dict[RecordId, RecordEntry]
        tla: records
      outbox:
        type: frozenset[RecordId]
        tla: outbox
      projections:
        type: dict[RecordId, str]
        tla: projections

types:
  ActorId:
    python: str
    source: Actors
  RecordId:
    python: str
    source: Records
  ClientId:
    python: str
    source: Clients

commands:
  RegisterActor:
    action: RegisterActor
    fields:
      actor:
        type: ActorId
        tla: a
  AcceptRecord:
    action: AcceptRecord
    fields:
      actor:
        type: ActorId
        tla: a
      record:
        type: RecordId
        tla: r
  PublishRecord:
    action: PublishRecord
    fields:
      record:
        type: RecordId
        tla: r

results:
  RegisterActorResult:
    fields:
      status:
        type: int
      body:
        type: dict
  AcceptRecordResult:
    fields:
      status:
        type: int
      body:
        type: dict
  PublishRecordResult:
    fields:
      status:
        type: int
      body:
        type: dict

ports:
  {module}Port:
    methods:
      register_actor:
        command: RegisterActor
        result: RegisterActorResult
      accept_record:
        command: AcceptRecord
        result: AcceptRecordResult
      publish_record:
        command: PublishRecord
        result: PublishRecordResult
      snapshot:
        result: {module}State

invariants:
  - InternalInvariant{external_invariant}

finite_model:
  Actors:
    values:
      - actor-1
      - actor-2
  Records:
    values:
      - record-1
      - record-2
  Clients:
    values:
      - client-1

case_codegen:
  style: explicit_transition_cases
  generation_status: planned{projection}
"""


def readme(module: str, spec_root_text: str = "specs", full: bool = False) -> str:
    shape = "the full shape" if full else "the minimum"
    full_section = f"""
## The optional layer (`--full`)

| File | Purpose |
| --- | --- |
| `External.tla` / `External.cfg` | external view: what a harness can drive and observe |
| `actions.yml` | per-action layer, controllability, and what it generates |
| `adapters.py` | spec-unit adapters and Test Graph adapters/projector/assertion |
| `providers.py` | agent-authored effect providers for generated ports |
| `effect_provider_usage.yaml` | provider scope, assertions, cleanup, bypass limits |
| `case_adapters.toml` | internal action -> spec-unit adapter |
| `testgraph_bindings.yml` | external action -> Test Graph adapter |
| `tlc_projection.py` | TLC state -> generated-case shapes |

These generate and run cases from the model. They are worth having when the
project wants its public surface driven end to end; they are not required for
the model to be a baseline. The working example of the full shape is
`examples/distributed_history/specs/program_model/`.
""" if full else """
## Adding the optional layer later

`tla-spec-dev scaffold project --full` adds the External view, generated-case
adapters, effect providers and Test Graph bindings. None of it is required.
Add it when the project wants cases generated from the model and run against
real adapters; `references/testgraph_adapters.md` describes that layer.
"""
    internal_tlc = tlc_command(f"{spec_root_text}/program_model", "Internal")
    return f"""# Program Model

Accepted whole-program TLA+ model for this repository. It is the semantic
baseline for future ticket workflows. This scaffold is {shape}: placeholders
to replace with the repository's real state, actions and invariants.

## The baseline

| File | Purpose |
| --- | --- |
| `Core.tla` | shared constants and helper operators |
| `Internal.tla` / `Internal.cfg` | the program state machine and its finite model |
| `spec_manifest.yaml` | ports, invariants, finite model, budgets, onboarding status |

A baseline is done when TLC passes on `Internal.tla` and the model names the
real state, actions and invariants of this program. Keep it small: model the
boundary that matters for the ticket at hand, not every subsystem.
{full_section}
## Validate

```bash
{internal_tlc}
tla-spec-dev --spec-root {spec_root_text} analyze complexity {spec_root_text}/program_model/Internal.tla {spec_root_text}/program_model/Internal.cfg
```

Budgets in `spec_manifest.yaml` carry documented defaults. Nothing needs
agreeing before you model; change a value only if `analyze complexity` warns
on it, and note why.

Use `{spec_root_text}/current` and `{spec_root_text}/desired_program_model` only after this
baseline exists and a later ticket needs a planned destination. First onboarding
should not create those directories.
"""


def onboarding_test(module: str, spec_root_text: str = "specs") -> str:
    return f'''"""The accepted baseline carries a model, its cfg and the manifest.

This test fails while the minimum is absent. The optional layer (External view,
adapters, providers, bindings) is added by `scaffold project --full` and is not
checked here. A single module was once treated as invalid; it is not, so the project would
have no validation of its public surface.
"""

from pathlib import Path

import pytest


SPEC_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_BASELINE_FILES = [
    "Core.tla",
    "Internal.tla",
    "Internal.cfg",
    "spec_manifest.yaml",
]


@pytest.mark.parametrize("name", REQUIRED_BASELINE_FILES)
def test_baseline_file_exists(name: str) -> None:
    assert (SPEC_ROOT / name).exists(), (
        f"{{name}} is missing from the accepted program model. "
        "See references/testgraph_adapters.md and "
        "examples/distributed_history/specs/program_model/."
    )


def test_external_view_is_modeled() -> None:
    external = (SPEC_ROOT / "External.tla").read_text(encoding="utf-8")
    assert "EXTENDS Internal" in external, (
        "External.tla must project the internal semantics, not redefine them."
    )


def test_testgraph_bindings_cover_external_actions() -> None:
    bindings = (SPEC_ROOT / "testgraph_bindings.yml").read_text(encoding="utf-8")
    for hook in ("adapter:", "projector:", "expected_projection:", "assertion:"):
        assert hook in bindings, f"testgraph_bindings.yml is missing {{hook}}"
'''


def spec_unit_adapter_test(module: str, spec_root_text: str = "specs") -> str:
    return f'''"""Example spec-unit adapter test for the {module} program model.

Runs the generated internal cases through the spec-unit adapters in
`adapters.py`, mapped by `case_adapters.toml`.

The external counterpart is NOT a pytest test: External-view cases run as Test
Graph nodes. See `testgraph_bindings.yml` and
`references/testgraph_adapters.md`.

Reference implementation:
examples/distributed_history/specs/program_model/tests/test_ecommerce_adapters.py

SCAFFOLD: this is skipped until the adapters in adapters.py are implemented and
generated cases exist. Remove the skip once both are real.
"""

import subprocess
import sys
from pathlib import Path

import pytest


SPEC_DIR = Path(__file__).resolve().parents[1]
SPEC_ROOT = SPEC_DIR.parent


def _repo_root() -> Path:
    """Find the repository root by SEARCH, not by counting `..`.

    Counting is off by one inside a ticket workspace. `SPEC_ROOT.parent` is
    correct at `specs/current/tests` (`specs` -> repo root) and WRONG at
    `specs/tickets/<id>/current/tests`, where it resolves to `specs/tickets`.
    The batch runner was then invoked with `--import-root specs/tickets`, and
    the adapter module every entry in `case_adapters.toml` names was
    unimportable -- so no ticket-local corpus could import its own adapters,
    in every repository using this scaffold.

    Searching upward for the nearest ancestor that is a repository root works
    at BOTH depths, which is the property counting cannot have.
    """
    markers = (".git", "pyproject.toml", "Cargo.toml", "go.mod", "package.json")
    for candidate in [SPEC_DIR, *SPEC_DIR.parents]:
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    # No marker found: fall back to the historical guess rather than raising at
    # import time, and let the run fail with its own error instead of this one.
    return SPEC_ROOT.parent


REPO_ROOT = _repo_root()

CASES_DIR = SPEC_ROOT / "generated" / "spec-unit" / "{_slug(module)}_internal_cases"


def _runner_script() -> Path | None:
    # The runner must be invoked as a script by absolute path, not as
    # `-m scripts.run_generated_case_adapters`: the module name resolves only
    # inside the toolchain repository, and once [effect_providers.*] is
    # configured the runner's import layout requires direct-script mode.
    try:
        import spec_double_compiler
    except ImportError:
        return None
    candidate = (
        Path(spec_double_compiler.__file__).resolve().parents[1]
        / "scripts"
        / "run_generated_case_adapters.py"
    )
    return candidate if candidate.is_file() else None


@pytest.mark.skipif(
    not CASES_DIR.exists(),
    reason="no generated spec-unit cases yet; generate them from Internal.tla first",
)
def test_internal_adapters_run_in_batch(tmp_path: Path) -> None:
    runner = _runner_script()
    if runner is None:
        pytest.skip("spec_double_compiler runtime not importable; set PYTHONPATH to the tla-spec-dev checkout")
    command = [
        sys.executable,
        str(runner),
        str(CASES_DIR),
        "--mapping",
        str(SPEC_DIR / "case_adapters.toml"),
        "--spec-dir",
        str(SPEC_DIR),
        "--view",
        "internal",
        "--batch",
        "--work-dir",
        str(tmp_path / "internal-work"),
        "--import-root",
        str(REPO_ROOT),
    ]
    subprocess.run(command, check=True, cwd=REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
'''


def testgraph_reminder(repo_root: Path, spec_root_text: str) -> str:
    return f"""
note: no test_graph project in {repo_root}. The External view
({spec_root_text}/program_model/External.tla) generates Test Graph cases, and without a
test_graph project they have nowhere to run. Optional: scaffold one with the
test-graph skill when you want the public surface driven end to end
(references/testgraph_adapters.md).
"""


def has_test_graph(repo_root: Path) -> bool:
    """A test_graph project exists if a test_graph dir with a build file is present."""
    candidate = repo_root / "test_graph"
    if not candidate.is_dir():
        return False
    return any(
        (candidate / marker).exists()
        for marker in ("build.gradle.kts", "build.gradle", "settings.gradle.kts", "settings.gradle")
    )


def missing_baseline_files(program_dir: Path) -> list[str]:
    """Return the required baseline files that are absent from program_dir."""
    return [name for name in REQUIRED_BASELINE_FILES if not (program_dir / name).exists()]


def missing_optional_baseline_files(program_dir: Path) -> list[str]:
    """Return the optional (``--full``) baseline files absent from program_dir."""
    return [name for name in OPTIONAL_BASELINE_FILES if not (program_dir / name).exists()]


def scaffold(
    repo_root: Path,
    name: str | None,
    force: bool,
    dry_run: bool,
    spec_root: Path = Path("specs"),
    full: bool = False,
) -> list[Path]:
    """Scaffold the accepted baseline.

    Default: the minimum -- Core/Internal model, cfg, manifest, README and one
    smoke test. ``full=True`` adds the External view, the generated-case
    adapters, effect providers, Test Graph bindings and the TLC projection.
    """
    module = _module_name(name or repo_root.name)
    package = f"{_slug(module)}_program_cases"
    resolved_spec_root = _resolve_spec_root(repo_root, spec_root)
    spec_root_text = _display_spec_root(repo_root, spec_root)
    program_dir = resolved_spec_root / "program_model"

    files = [
        (program_dir / "README.md", readme(module, spec_root_text, full=full)),
        (program_dir / "__init__.py", ""),
        (program_dir / "Core.tla", core_tla()),
        (program_dir / "Internal.tla", internal_tla()),
        (program_dir / "Internal.cfg", internal_cfg()),
        (program_dir / "spec_manifest.yaml", manifest(module, package, spec_root_text, full=full)),
        (program_dir / "tests" / "test_program_model_onboarding.py", onboarding_test(module, spec_root_text)),
    ]
    if full:
        files += [
            (program_dir / "External.tla", external_tla()),
            (program_dir / "External.cfg", external_cfg()),
            (program_dir / "actions.yml", actions_yml()),
            (program_dir / "adapters.py", adapters_py(module)),
            (program_dir / "providers.py", providers_py()),
            (program_dir / "effect_provider_usage.yaml", effect_provider_usage_yml()),
            (program_dir / "case_adapters.toml", case_adapters_toml()),
            (program_dir / "testgraph_bindings.yml", testgraph_bindings_yml()),
            (program_dir / "tlc_projection.py", tlc_projection_py(module)),
            (program_dir / "tests" / "test_spec_unit_adapters.py", spec_unit_adapter_test(module, spec_root_text)),
        ]

    written: list[Path] = []
    for path, content in files:
        if write_file(path, content, force=force, dry_run=dry_run):
            written.append(path)

    if full and not has_test_graph(repo_root):
        print(testgraph_reminder(repo_root, spec_root_text))

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root to scaffold into.")
    parser.add_argument("--spec-root", type=Path, default=Path("specs"), help="Spec root under the repository.")
    parser.add_argument("--name", help="Program/module name. Defaults to the repository directory name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing program-model files.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned writes without changing files.")
    parser.add_argument("--full", action="store_true", help="Also emit the External view, adapters, providers, bindings and projection.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    written = scaffold(repo_root, args.name, args.force, args.dry_run, args.spec_root, full=args.full)
    print(f"scaffolded program model files: {len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
