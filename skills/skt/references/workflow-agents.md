# Workflow subagents

From the consumer checkout, `skt agent list` lists the plugin’s roles.
`skt agent run regress <id> <graphs...>` shares the run state, options and
exit codes of `skt regress run`. Use `skt regress new` or `adopt` first.

For review, pass `--base` and `--head` and repeat `--evidence FILE` for the
ticket, wave or regression evidence to include. The CLI resolves both commits
and supplies the diff and evidence text to the reviewer. Only supply inputs
appropriate for the selected provider. A missing file becomes a coverage gap.
The ACP reviewer requests the meta-harness read-only tool list. A compatible
text-only backend receives the same inputs directly. A review uses a temporary
working directory. Its JSON report records the revisions, execution ID,
findings, gaps and evidence location. Exit 0 means clean, 1 means findings,
2 indicates invalid input and 3 indicates an incomplete review.

## Configuration

Place `skt-agents.toml` at the consumer checkout root. Each role uses its named
profile by default, and `--profile` selects a different one for a single run.

```toml
[roles]
regress = "graph-runner"
review = "independent"

[profiles.graph-runner]
model = "CLAUDE_haiku"
transport = "acp"
skill_home = ".skill-manager"
timeout = 7200

[profiles.independent]
model = "CUSTOM_reviewer"
transport = "http"
harness_config = "meta-harness.toml"
```

Use the complete model ID routed by meta-harness. The upstream config defines
the provider prefix, downstream agent command or HTTP service and credentials.
Select a running **meta-harness server** with `--base-url` for ACP. Text-only review uses a private server so skt can verify the actual provider transport before sending the diff. A private server
loads `--harness-config`. Keep backend credentials in the server environment.
Set `transport` to the selected route's type. A text-only provider supports
diff review. Regress needs an ACP agent capable of running the graph and
writing reports. The installed bundle in `skill_home` is passed through the
episode’s `SKILL_MANAGER_HOME`. Profile paths resolve against the project root.

Command-line values override profile settings, environment fallbacks and bundled
defaults in that order. Environment fallbacks are `META_HARNESS_BIN`, `MH_CONFIG`,
`SKT_REGRESS_MODEL` and `SKT_REVIEW_MODEL`. Use `--dry-run` to write the
episode request and `settings.json` with the source of each setting.
The review attempt lives under the Git common directory in `skt-agent/review/`.
Regression attempts keep their existing `skt-regress/<id>/attempt-N` location.

## Adding a role

Register a role command in `skills/skt/src/skt/agents.py`. Its entry point
parses role inputs and the common execution options, resolves a profile, builds
the brief and calls the shared episode transport. Use the result reader to
decide the domain outcome and retain the attempt and evidence reference. Test
through `skt agent run` with a stub binary. Existing upstream provider routes
work across roles that meet their capability requirements.

For a private server, skt reads the actual provider table and checks the longest
matching model prefix before dispatch. For an existing server, the published
model list gives provider IDs and prefixes. It omits transport capabilities.
Select an ACP route configured by that server’s operator for remote regress.
Remote ACP review sends its read-only tool requirement with the episode and
meta-harness refuses a provider that cannot enforce it.
