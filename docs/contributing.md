# Contributing

Thank you for improving okf-wiki. The framework is intentionally small:
markdown skills, a validation script, and a stdlib-only CLI.

## Adding a new skill

1. Create `.skills/<name>/SKILL.md` with the standard frontmatter (`name`,
   `description`) and the Derived-from footer when applicable.
2. Reference the canonical schema instead of re-deriving frontmatter mappings
   — see `okf-wiki` §Schema in `.skills/okf-wiki/SKILL.md`.
3. Re-run `bash setup.sh` so every agent picks the new skill up through its
   own symlinks.
4. Add a row to the skill catalog in `README.md`, `AGENTS.md`, and
   `docs/skills.md` — the three counts must stay equal to
   `ls .skills | wc -l`.

## Keeping docs in sync

`AGENTS.md` is the single source of truth for the catalog; `CLAUDE.md`,
`GEMINI.md`, and `.hermes.md` are symlinks to it. When you add a skill,
config variable, or CLI subcommand, update the matching `docs/` page
(`skills.md`, `configuration.md`, [cli.md](./cli.md)) rather than duplicating
content in `README.md`.

## Repo conventions

- Python package code lives in `okf_wiki/`; core is stdlib-only
  (extras `ast`, `graph`, `server` are optional).
- Comments appear only at contract/correctness boundaries.
- Markdown links inside the bundle are file-relative; absolute paths are
  reserved for cross-bundle import/export.
- Framework-facing docs stay platform-neutral ("format not platform").

## Tests

```bash
uv venv && uv pip install -e '.[server]' pytest
uv run pytest tests/ -q          # full suite (93+ tests)
bash scripts/validate.sh tests/fixtures/mini-bundle        # positive fixture → exit 0
bash scripts/validate.sh tests/fixtures/non-conformant     # negative → exit 1
bash scripts/roundtrip.sh tests/fixtures/mini-bundle       # frontmatter round-trip → exit 0
```

The CI in `.github/workflows/validate.yml` runs all of the above plus a
Docker build smoke test.

---

Derived from Ar9av/obsidian-wiki `docs/contributing.md` (MIT).
