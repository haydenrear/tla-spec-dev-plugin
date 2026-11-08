# Addressing a bundled skill: what works, what breaks, what is a known bug

Bundling changes a skill's **identity**, not its contents. Everything that
addresses it by the old identity has to be rewritten. This page is the complete
list, with the evidence, because two of these fail at a distance and one of them
is a genuine skill-manager bug you should know about rather than design around.

Everything below was measured on a live home with **skill-manager 0.23.0** and
the `skt` plugin at 0.5.0. Each verdict shows the command that produced it, so
re-measure rather than trust the page against a newer CLI:

```bash
skill-manager --version                       # what these verdicts are about
skill-manager show <contained-skill>          # "unit not found" is fact 1
skill-manager unit validate <a-unit-dir>      # the import validator (install --dry-run does NOT validate)
```

## The one sentence

**A plugin is a unit; the skills inside it are not.** `skill-manager list` has
no row for a contained skill, `skill-manager show <contained>` answers `unit not
found`, and the only name that resolves is the plugin's:

```console
$ skill-manager show skt
PLUGIN  skt@0.5.0  (sha 7432617, source git)
path:        /Users/hayde/.skill-manager/plugins/skt
contained skills (2):
  - skt
  - unit-authoring

$ skill-manager show unit-authoring
unit not found: unit-authoring
```

Note also what the plugin's version is *not*: the contained skills carry their
own `[skill] version` (`skt` 0.3.1, `unit-authoring` 0.1.0) and nothing outside
the bundle reads them. The plugin's version is the only one consumers, `skt
check` and `units.lock.toml` see. Bump it — `scripts/release.sh` — or a change
is invisible to every notification path.

## Outbound edges keep working

A bundled skill referencing units **outside** the bundle is fine, and this is
the direction that matters most in practice:

- `skill_references` in a contained skill's `skill-manager.toml` are unioned
  into the plugin's install plan with attribution (`needed by: my-plugin /
  alpha-skill`) and installed transitively.
- `skill-imports` in a contained skill's markdown naming an installed unit
  (`unit: skill-manager`, `unit: git-issue-workflow`) validate normally.

Bundling a skill does not cut it off from the rest of the store.

## Inbound edges break, in three different ways

### 1. `skill-imports: unit: <bundled-skill>` — fails validation, loudly

The validator resolves `unit:` against **installed units**, and a contained
skill is not one. Measured:

```console
$ cat SKILL.md   # an unrelated skill importing a now-bundled one
skill-imports:
  - unit: unit-authoring
    path: SKILL.md

$ skill-manager unit validate .
markdown skill-import violations (1) — fix these references:
✗   - importer-demo (skill): SKILL.md
✗     skill-imports[0] references missing unit `unit-authoring`; install it or fix the `unit` value
```

`unit-authoring` **is** installed — inside `skt` — and the validator still calls
it missing, because "installed unit" means a row in the lock file.

**The rewrite**, verified clean: address the plugin, and make the path relative
to the plugin root.

```yaml
skill-imports:
  - unit: tla-spec-dev
    path: skills/unit-authoring/SKILL.md
    reason: …
```

A wrong path inside a real unit is caught just as explicitly
(`references missing path 'references/nope.md' in unit 'skt'`), so there is no
silent-success failure mode here.

**When it bites:** install, sync and `unit validate` check every markdown file under
the unit root being operated on. An already-installed importer keeps working
until someone syncs *it*; then that sync fails until the frontmatter is fixed.
So the cost lands on the importing unit's next release, possibly weeks later and
on someone else's machine. Grep for importers before you bundle — `verify.sh`
does it inside the bundle, and `migration.md` § 2 has the wider sweep.

### 2. `$SKILL_MANAGER_HOME/skills/<unit>/…` in shell — breaks on disk

Nothing to do with imports: the bytes move to
`$SKILL_MANAGER_HOME/plugins/<plugin>/skills/<unit>/`, so a hardcoded path stops
existing. It fails at **source time**, in a script that may be mid-fan-out.

This pattern is live today: `git-integration-repo`'s `integration-lib.sh`
reaches `git-issue-workflow`'s `lib.sh` exactly that way, and this skill's
`plugin-repo-lib.sh` reaches `integration-lib.sh` the same way — with a
`plugins/*/skills/` rung added, which is the fix:

```bash
for c in ${PIN:+"$PIN/lib.sh"} \
         "$H/skills/<unit>/scripts/lib.sh" \
         "$H"/plugins/*/skills/<unit>/scripts/lib.sh; do
  [ -f "$c" ] && { LIB="$c"; break; }
done
```

`unit_dir <name>` in `scripts/plugin-repo-lib.sh` is that search, once. Prose
counts too: a `SKILL.md` telling an agent to run a path is an instruction that
will fail, and no validator checks prose.

### 3. `skill_references = ["github:owner/<bundled-skill-repo>"]` — silently duplicates

A git coord still resolves: the repo is still there, so the referencing unit
installs a **second, standalone copy** of a skill that is also inside a bundle.
Two copies, two store paths, two versions, and `skt` change-manages them
separately — the exact incoherence the bundle was built to prevent. Not an
error, which is what makes it the nastiest of the three. Point the reference at
the plugin repo's coord instead.

## The known bug: a bundle cannot import its own siblings before it is installed

Two contained skills of the same bundle, one importing the other. Both spellings
fail `unit validate`:

```console
$ # alpha imports beta by bare name
✗ skill-imports[0] references missing unit `beta`; install it or fix the `unit` value

$ # alpha imports beta through the bundle itself
$ #   unit: demo-bundle / path: skills/beta/SKILL.md
✗ skill-imports[0] references missing unit `demo-bundle`; install it or fix the `unit` value
```

The second one is the *documented correct form* and it still fails, because the
bundle is not in the lock file at the moment it is being validated. Its own
name cannot resolve to itself.

And the validators disagree with each other: **`skill-manager install
file://<that same bundle> --yes` succeeds**, self-import and all. So the bundle
installs, works, and then answers `unit validate` with a violation.

What to do about it:

- **Use the self-referential form** (`unit: <plugin>`, `path:
  skills/<sibling>/…`). It is the one that is correct once installed, it is what
  `install` accepts, and it is what a future fix will make valid everywhere.
- **Expect `unit validate` to complain** on a bundle that is not currently
  installed, and do not "fix" it by deleting the import — that loses a real
  semantic edge to satisfy a validator with a scoping bug.
- **Or keep intra-bundle edges in prose** (`see skills/beta/SKILL.md`, relative
  and un-validated) when the import is documentation rather than a dependency
  another tool needs to walk. `skt`'s own contained skills do exactly this: they
  cross-reference each other in prose and declare no sibling `skill-imports`.

`install --dry-run` does not run this validation at all (only `unit
validate`, and the real `install`/`sync`), so a dry-run install is not evidence
that a bundle's imports are sound. `unit validate` exits non-zero on a
violation. The `publish --dry-run` it replaces (skill-manager 0.28.2 and
earlier) **prints the violations while exiting 0** — on those versions read its
output; do not gate CI on its exit code.

## Summary table

| Edge | After bundling | Fix |
|---|---|---|
| bundled skill → outside unit (`skill_references`) | works, unioned into the plugin's plan | — |
| bundled skill → outside unit (`skill-imports`) | works | — |
| outside unit → bundled skill (`skill-imports`) | **fails validation** on validate/sync | `unit: <plugin>`, `path: skills/<skill>/…` |
| outside unit → bundled skill (git coord reference) | installs a duplicate standalone copy | point at the plugin repo's coord |
| any script → bundled skill by store path | **breaks at source time** | add a `plugins/*/skills/` rung; `unit_dir` |
| bundled skill → sibling in the same bundle | `unit validate` fails; `install` accepts | self-referential form, or prose |
| agent invoking the skill | `<plugin>:<skill>` | update prose and docs |
