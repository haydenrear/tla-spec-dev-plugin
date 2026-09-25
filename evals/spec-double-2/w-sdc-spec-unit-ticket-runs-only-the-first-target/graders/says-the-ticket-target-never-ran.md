---
type: regex
pattern: '(?:[Oo]nly|[Jj]ust)\s+(?:the\s+)?(?:one|1|first|project|specs/current)|[Nn]ever (?:ran|executed|reached|got)|did\s*n.?t (?:run|execute|reach)|[Ss]econd target[^\n]{0,40}(?:not|never)|(?:one|a single|only one)[^\n]{0,20}running[^\n]{0,10}line|1 of 2|one of (?:the )?two'
weight: 3
---

THE BEHAVIOUR. Two targets are printed, and exactly **one** `running` line
follows. The agent has to notice that the listing is not the execution.

`spec_unit_target_dirs` (`skills/spec-double-2/scripts/tla_spec_dev.py:288`)
returns both paths for `--ticket`:

    if args.ticket:
        return unique_paths([project_current, ticket_model_dir(specs_dir / "tickets" / args.ticket)])

and both are printed before anything runs. The execution loop
(`tla_spec_dev.py:457`) then returns on the first failure:

    for label, command, env in commands:
        print(f"running {label}: ...")
        result = subprocess.run(command, cwd=repo_root, env=env)
        if result.returncode != 0:
            return result.returncode

So the ticket's command was built and never reached.

Any spelling of "the ticket's target did not run" passes: naming the count,
naming the single `running` line, or saying the loop returned early.

OBSERVED, NOT INFERRED. SI-21 worktree at `ac5f7491`, 2026-09-25:
`--ticket SI-17` → one `running` line, `9 failed, 47 passed`, rc=1.

Reads the FINAL RESPONSE only.
