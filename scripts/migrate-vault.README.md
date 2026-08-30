# migrate-vault.sh

Deterministic, idempotent Obsidian vault → OKF v0.2 bundle migration pipeline.

**The original vault is never modified.** Migration writes to a new directory;
the backup is belt-and-braces.

## Usage

```bash
# Full migration
bash scripts/migrate-vault.sh /path/to/obsidian-vault

# Dry run: inventory + transform plan, zero writes
bash scripts/migrate-vault.sh --dry-run /path/to/obsidian-vault
```

## Output

| Path | Purpose |
|---|---|
| `<vault>.bak-<ts>/` | Backup of the original vault |
| `<vault>.migrated-<ts>/` | The migrated OKF v0.2 bundle |

## Pipeline

1. **Backup** — `cp -a` the vault to a timestamped sibling directory
2. **Inventory** — classify files (knowledge pages, Obsidian artifacts, out-of-scope)
3. **Frontmatter transform** — `category→type`, `created→generated`, `lifecycle→status`, `summary→description`, `sources→v0.2 list`, `stale_after` computation
4. **Wikilink conversion** — `[[path|display]]→[display](./path.md)`, unmatched bare-titles→plain text, forward-refs preserved
5. **v0.1→v0.2 upgrade** — `timestamp→generated`, `# Citations→sources` frontmatter
6. **Service files** — `hot.md→_cache/`, index.md regeneration, log.md update, Obsidian artifacts→`_archives/obsidian/`
7. **Verify** — `validate.sh` + wikilink audit + edge comparison

## Idempotency

Re-running on an already-migrated bundle produces zero changes to knowledge pages.
All transformers detect already-OKF fields (`type`, `generated`, `description`,
`status`, `stale_after`) and skip.

## Dependencies

- **bash** (POSIX)
- **python3** (stdlib only, no PyYAML) — for YAML-safe frontmatter transforms

## Wikilink Conversion Rules

| Legacy form | Converted form |
|---|---|
| `[[path/to/page]]` | `[path/to/page](./path/to/page.md)` |
| `[[path/to/page\|display]]` | `[display](./path/to/page.md)` |
| `[[BareTitle]]` (matched) | `[BareTitle](./relative/path.md)` |
| `[[BareTitle]]` (unmatched) | `BareTitle` (plain text) |
| `[[path/to/future]]` (no file) | `[path/to/future](./path/to/future.md)` (forward-ref) |

## Related

- `wiki-import` skill — imports OKF bundles (redirects Obsidian vaults here)
- `validate.sh` — OKF v0.2 conformance checker
- `.skills/okf-wiki/SKILL.md` — canonical frontmatter mapping