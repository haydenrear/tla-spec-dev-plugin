# Isolation for graphs an agent reruns and repairs

Read this before a graph is handed to a regression agent with fix rights
(`skt regress run --fix`, skt `references/regression-agent.md`), and when
authoring a graph that will be.

A regression agent is a small model that runs a graph, makes small fixes and
runs it again until it passes. It may run one graph five times in an hour,
unattended, with its shell commands approved automatically. Whatever the graph
touches gets touched that often, by an agent that is trying things. So the rule
is:

**A graph an agent may repair touches nothing that anyone else is using.**
`skt regress run --fix` is refused without `--isolated "<statement>"`, and the
statement is the caller's claim that this rule holds. This page is how to make
the claim true.

## What has to be private

Go through the graph's nodes by their declared `side_effects`. `skt regress run
--dry-run` prints the ones the node sources declare.

| the graph touches | private means |
| --- | --- |
| `fs:tmp`, `net:local`, `process:*` only | nothing more to do; say "local temp and loopback only" |
| a Kubernetes cluster | **a cluster of its own**, not a namespace in a shared one: a k3d cluster created for the run, reached through its own kubeconfig |
| an environment repository (`SideEffect.environment`) | an environment id of its own (below) |
| a database, queue or bucket | an instance or a uniquely named schema/prefix created for the run |
| `net:external` (a registry, an API, a cloud account) | a scratch account or project, or the node is not handed to the agent |
| a shared host resource: a fixed port, a fixed output directory, a global install | the graph is not isolatable as written; fix that first (`graph-architecture-review.md`) |

A separate namespace in a shared cluster is not enough for an agent with fix
rights. Cluster-scoped objects (CRDs, cluster roles, node resources, admission
webhooks) are shared, and a repair attempt is exactly the kind of run that
reinstalls them.

## Environment repositories: the run gets its own environment

The environment id is `<graph>__<branch>__<target>__<backend>`
(`environment-repositories.md`, *Lifecycle*), and `<branch>` comes from
`TEST_GRAPH_FEATURE_BRANCH`. `skt regress` sets that to `regress-<id>` for the
agent, so a node using the contract provisions a new environment, and with the
local k3d template a new cluster, instead of reusing the feature branch's.

That covers only nodes that use the contract. The shipped
`monitoring.cluster.*` standard nodes do not: their CLI owns one cluster
lifecycle on the host. A graph containing them is run report-only, or against a
host nobody else is using.

## A cluster the graph does not provision itself

Create it before the run and hand the agent its kubeconfig:

```bash
k3d cluster create regress-<id> --kubeconfig-update-default=false
k3d kubeconfig write regress-<id> --output "$PWD/.regress-<id>.kubeconfig"
skt regress run <id> <graph>... --fix \
    --isolated "k3d cluster regress-<id>, created for this run" \
    --env KUBECONFIG="$PWD/.regress-<id>.kubeconfig"
k3d cluster delete regress-<id>          # after `skt regress close`
```

Nodes must take the cluster from `KUBECONFIG` (or from an upstream node's
published `KUBECONFIG`/`KUBECONTEXT` outputs). A node that names a context or
reads `~/.kube/config` directly cannot be pointed at a private cluster and will
reach the shared one.

## When it cannot be isolated

Run it report-only: drop `--fix`. The agent then runs the graph, retries an
environment failure once by resume, attributes every red and reports what a fix
would need. Nothing is edited and nothing is rerun in a loop.
