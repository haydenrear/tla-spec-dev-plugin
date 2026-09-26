SI-28 review fix — `cached_report` rejects a cache of the wrong schema

WHAT WAS WRONG
--------------
`cached_report` (skills/skt/src/skt/check.py) compared only `checked_at`
against the TTL and never compared the cached `schema` against
`SCHEMA_VERSION`, so a record written by an OLDER skt was served as
CACHE_FRESH carrying whatever fields that older schema happened to have.

For SI-28 specifically: a v6 record has no `cli.floor` and no `cli-floor`
notification, so a home with a warm cache showed NO floor warning for up to a
full TTL (900 s). A check that does not fire is the exact defect this ticket
exists to catch.

It was never SI-28's problem alone. EVERY schema bump before this one had the
same hole, and every future one would have. The predicate is therefore the
schema NUMBER and nothing about the floor — this code does not know or care
which fields changed.

THE FIX
-------
A cache whose `schema` differs from `SCHEMA_VERSION` takes the path that
already existed for an absent file: CACHE_MISSING, REPORTED and NOT REPAIRED.
`--cached` stays one state-file read with no I/O, because PostToolUse runs it
on every tool call; the next live pass rewrites the cache at the current
schema anyway.

A non-dict record is folded into the same branch: it is the same predicate —
"this is not a record this code can read" — and `raw.get` on a JSON list would
otherwise be an AttributeError inside a SessionStart hook.

Added beyond the letter of the instruction, and easy to strike: a
`cache_reason` key on the returned dict. It is NOT rendered and changes no
text surface; without it, `--cached --json` cannot tell a REJECTED cache from
an absent one, which is the first thing anybody debugging this wants.


=======================================================================
CONTROL — the same v6 record against the PRE-FIX code (HEAD 3c5a7c7c)
=======================================================================
A fix that cannot be shown to change anything is not a fix, so the pre-fix
check.py was extracted with `git show 3c5a7c7c:skills/skt/src/skt/check.py`
and run against the same home and the same cache file:

  cache_state: fresh
  cli-floor notifications served: 0

The v6 record is served as CURRENT and the floor warning is silently absent.
That is the bug, reproduced.


=======================================================================
ARM A — a v6 cache is REJECTED, so the floor cannot be hidden
=======================================================================
Home: scratch home whose CLI pin reports 0.28.1. Declared floor: 0.28.2.

Step 1, a live pass writes a current-schema cache:
  cache schema: 7
  cli-floor in cache: True

Step 2, the cache is rewritten as a v6 record — byte-identical except the
schema, with the `cli-floor` notification and `cli.floor` REMOVED exactly as a
genuine v6 record would lack them, so a served cache would show no warning:

  $ SKILL_MANAGER_HOME=<home> python3.12 skills/skt/src/skt/cli.py check --cached
  skt check: no cached result (cache missing) — refresh with: skt check
  EXIT=0

  cache_state : missing
  cache_reason: cached at schema 6, this skt reads 7

And the consequence that matters — the SessionStart hook sees a non-fresh
cache state, refreshes live, and the floor warning reaches the session:

  $ SKILL_MANAGER_HOME=<home> bash hooks/skt-session-start.sh
  cli-floor lines printed: 1
  HOOK_EXIT=0


=======================================================================
ARM B — a current-schema cache is served FRESH, and nothing extra happens
=======================================================================
  cache_state                 : fresh
  cli-floor served from cache : 1
  EXIT                        : 10   (skt's notify code; the floor rode the cache)
  cache file rewritten        : no — reported, not repaired
  wall                        : 0.056s, no network, no subprocess

The unit test pins the no-I/O half harder than a stopwatch can: it monkeypatches
`_remote_tip` to raise, and asserts the state file is byte-identical afterwards.


=======================================================================
TESTS
=======================================================================
skills/skt/tests/test_check.py

  test_a_cache_of_the_wrong_schema_is_not_served
      Both arms in one test, because a rejection that rejects everything is
      worthless: the SAME record is served fresh at the current schema and
      refused one below it, so the schema is demonstrably what decides.
      NON-VACUITY: asserts the written record really is at SCHEMA_VERSION and
      really carries `checked_units == ["alpha"]` BEFORE the refusal arm — a
      corrupt file would be refused too, and would prove nothing.
      Also asserts: no network on the cached path (`_remote_tip` raises), the
      state file is not rewritten, `cache_reason` names the current schema,
      and `run(cached=True)` exits 0 so a hook cannot mistake a wrong-shaped
      record for news.

  test_a_cache_that_is_not_a_record_does_not_raise
      `[1,2,3]`, `"a string"`, `42`, `null` — all CACHE_MISSING, no raise.

Scope: this change alone. The exit code is untouched, `bootstrap-floor.toml`
stays, and SI-28-DF-01/DF-02 stand as filed.

Note for the reviewer, since it looks like an omission: `status.py` reads
`cache/skt-check.json` DIRECTLY (lines 47 and 69) rather than through
`cached_report`, and deliberately tolerates older schemas — it degrades to
printing one fewer line. Nothing there changed, and the existing schema-4 and
schema-5 tolerance tests in tests/test_status.py still pass unmodified. The
two readers want different things: `status` renders orientation from whatever
it finds; `cached_report` serves the notification contract, where a
wrong-shaped record is not an answer.


=======================================================================
WHAT THE GRAPHS CAUGHT THAT THE UNIT SUITE DID NOT
=======================================================================
The first `--only sktSurface --only sktHooks` run after this fix came back
ERRORED on BOTH graphs. `skt.hook-contract` failed all ten of its dedup
assertions (five per interpreter, 3.11 and 3.13) and `skt.ticket-roundtrip`
was skipped behind it.

The hooks were fine. `test_graph/sources/skt_hook_contract.py` wrote
`"schema": 2` as a LITERAL into the fixture cache it hands the PostToolUse
hook. This fix correctly refuses a record at a schema this skt does not read,
so `check --cached` answered CACHE_MISSING, the hook had no notifications to
inject, and every injection assertion failed at once.

That literal was a latent coupling to a number that moves, and it had already
survived five schema bumps by luck: 2 was simply never compared to anything.
The fixture now reads `SCHEMA_VERSION` from the source under test — exactly
what its sibling `test_graph/support/cached_no_spawn_probe.py` already did —
so the next bump needs no edit here and a stale literal cannot come back.

This is worth recording rather than quietly fixing, for two reasons:

  1. The unit suite passed throughout (352 passed, 3 skipped, 0 failed). The
     coupling lived in a fixture no unit test reads, so only the graph could
     see it. That is the graph earning its keep.

  2. It is the same defect class as the ticket itself, one layer down: a
     hardcoded copy of a fact that lives somewhere else, which stays silently
     wrong until something finally compares the two.

After the fixture fix, both graphs are green from their own fresh summaries:

  PASSED  sktSurface   nodes=5  assertions=318  non-passing=0
  PASSED  sktHooks     nodes=3  assertions=167  non-passing=0
