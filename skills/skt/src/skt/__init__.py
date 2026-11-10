"""skt — skill-lifecycle CLI for skill-manager homes.

The subcommands live in `skt.status`, `skt.check`, `skt.sync`, `skt.ticket`
and `skt.publish`. What is re-exported HERE is the part other code is meant
to import rather than shell out to: the typed surface over this home's
artifact graph, in the same shape `skt.wt` exports the worktree lifecycle —
so that `from skt import stale, build` reads the way `from skt.wt import
wt_new` does, and a caller never has to know which module a name lives in.

`skt.wt` is not re-exported here. It shells out to `scripts/wt`, so importing
it costs a subprocess-capable environment that `skt status` does not need, and
`skt.ticket` is the one module that wants it.
"""

from .artifacts import (
    EXIT_UNRESOLVED_ANCESTOR,
    UnresolvedAncestor,
    Artifact,
    ArtifactError,
    ArtifactOutput,
    ArtifactsUnsupported,
    BuildRefused,
    BuildResult,
    BuildStep,
    CliUnavailable,
    HomeNotFound,
    ProbeTimeout,
    StaleReason,
    StaleSurvey,
    UnknownArtifact,
    build,
    list_artifacts,
    resolve_ids,
    stale,
)

__version__ = "0.8.2"

__all__ = [
    "Artifact",
    "ArtifactError",
    "ArtifactOutput",
    "ArtifactsUnsupported",
    "BuildRefused",
    "BuildResult",
    "BuildStep",
    "CliUnavailable",
    "HomeNotFound",
    "ProbeTimeout",
    "StaleReason",
    "StaleSurvey",
    "UnknownArtifact",
    "UnresolvedAncestor",
    "EXIT_UNRESOLVED_ANCESTOR",
    "build",
    "list_artifacts",
    "resolve_ids",
    "stale",
    "__version__",
]
