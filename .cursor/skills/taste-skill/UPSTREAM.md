# taste-skill (vendored reference)

## Source

| | |
|---|---|
| Repository | <https://github.com/leonxlnx/taste-skill> |
| Branch | `main` (default branch) |
| Commit | `ccbc15639c97057cbfcf32ecebc38ef716e4bb37` |
| Imported | 2026-09-11 |
| Licence | MIT, Copyright (c) 2026 Leonxlnx (see `LICENSE`) |

Upstream is vendored here so frontend work in this repository has a stable,
reviewable design reference that does not depend on network access and does not
silently change under us.

## What was imported

Documentation only. Everything under `skills/` in this directory is an
unmodified copy of the upstream `skills/` tree:

- `skills/llms.txt` - upstream's one-line index of every skill
- `skills/<name>/SKILL.md` - the 13 skill documents
- `skills/stitch-skill/DESIGN.md` - the one supporting document upstream ships

`LICENSE` is copied verbatim to preserve attribution as the MIT terms require.

## What was deliberately not imported, and why

| Upstream path | Reason |
|---|---|
| `skill.sh` | Executable shell script. It is only a lookup table mapping skill names to file paths, so it adds nothing an agent reading this directory needs, and vendoring executables into a repo that has no use for them is avoidable risk. |
| `scripts/*.mjs` | Node scripts that regenerate upstream's own README banner and sponsor images. Irrelevant to this project and executable. |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Tool configuration for a different agent platform. Copying it here would register a plugin this repository does not use. |
| `.github/` | Upstream's funding config and Copilot instructions. Project-level tool config that must not leak into this repository. |
| `assets/`, `examples/` | Binary images used by upstream's README (banner, sponsor logos, screenshots). Large, and carry no design guidance. |
| `README.md`, `CHANGELOG.md` | Mostly sponsor tables and release notes. The substance lives in the `SKILL.md` files. |
| `research/` | Essays on why LLMs truncate output. Interesting, but not frontend design guidance. |

### Safety review

Every imported file was read before import. All 15 imported files are plain
Markdown or plain text. They contain no scripts, no build configuration, no
network calls, no install hooks, and nothing that executes. The only shell
commands that appear anywhere in them are inside fenced code blocks in
`skills/taste-skill/SKILL.md` Appendix A, as `npm install` examples for design
systems this project does not use. Nothing in this directory runs.

## How this differs from how we apply it

Upstream guidance is not adopted wholesale. `PROJECT-NOTES.md` in this directory
records where this project deviates and why. Read both files together: upstream
states the general rule, `PROJECT-NOTES.md` states the local decision.

## Updating from upstream

The `skills/` subdirectory and `LICENSE` are the only vendored files. Nothing in
them is edited locally, so they can be replaced wholesale. Project-specific
content lives outside them and must survive the update.

```bash
git clone --depth 1 https://github.com/leonxlnx/taste-skill.git /tmp/taste-skill
cd /tmp/taste-skill && git rev-parse HEAD   # record this hash

# Replace only the vendored tree.
rm -rf <repo>/.cursor/skills/taste-skill/skills
mkdir -p <repo>/.cursor/skills/taste-skill/skills
cp /tmp/taste-skill/skills/llms.txt <repo>/.cursor/skills/taste-skill/skills/
for d in /tmp/taste-skill/skills/*/; do
  n=$(basename "$d")
  mkdir -p "<repo>/.cursor/skills/taste-skill/skills/$n"
  cp "$d"/*.md "<repo>/.cursor/skills/taste-skill/skills/$n/"
done
cp /tmp/taste-skill/LICENSE <repo>/.cursor/skills/taste-skill/LICENSE
```

Then, before committing:

1. Update the commit hash and import date in the table at the top of this file.
2. Re-read the diff of the `skills/` tree. Confirm it is still Markdown only. If
   upstream has started shipping scripts or configuration inside `skills/`, do
   not import those files, and add a row to the exclusion table above.
3. Re-read `PROJECT-NOTES.md` against the new upstream text. If upstream has
   changed a rule that `PROJECT-NOTES.md` overrides, either the override needs a
   fresh justification or it can be dropped.
4. Never edit anything under `skills/` or `LICENSE`. Local opinions belong in
   `PROJECT-NOTES.md`, so that the next update is a clean replace rather than a
   merge.
