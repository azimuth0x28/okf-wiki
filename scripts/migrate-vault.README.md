# migrate-vault.sh

Deterministic, idempotent Obsidian vault → OKF v0.2 bundle migration pipeline.

**The original vault is never modified.** Migration writes to a new directory;
the backup is belt-and-braces.

## Usage

```bash
# Full migration
bash scripts/migrate-vault.sh /path/to/obsidian-vault

# Dry run: inventory + transform plan, zero writes (beyond backup)
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
6. **Service files** — `hot.md→_cache/`, index.md regeneration, log.md update, Obsidian artifacts→`_archives/obsidian/`; `.git/` is excluded from the migrated bundle
7. **Verify** — `validate.sh` + wikilink audit + edge comparison (non-zero exit on failure)

## Idempotency

Re-running on an already-migrated bundle produces zero changes to knowledge pages
**and** service files: `log.md`, `index.md`, and `_archives/migration-report.md`
are left untouched when nothing was transformed, so the output bundle is
byte-identical to its input. All transformers detect already-OKF fields (`type`,
`generated`, `description`, `status`, `stale_after`) and skip. A fresh backup and
output directory are still created on every run.

## Dependencies

- **bash** (POSIX)
- **python3** (stdlib only, no PyYAML) — for YAML-safe frontmatter transforms

## Wikilink Conversion Rules

| Legacy form | Converted form |
|---|---|
| `[[path/to/page]]` | `[path/to/page](./path/to/page.md)` |
| `[[path/to/page\|display]]` | `[display](./path/to/page.md)` |
| `[[page#section]]` | `[page#section](./page.md#section)` (fragment re-appended after resolution) |
| `[[BareTitle]]` (matched) | `[BareTitle](./relative/path.md)` |
| `[[BareTitle]]` (unmatched) | `BareTitle` (plain text) |
| `[[path/to/future]]` (no file) | `[path/to/future](./path/to/future.md)` (forward-ref) |

Spaces in targets are percent-encoded (`my page.md` → `my%20page.md`) so the
emitted links are valid markdown.

## Known Limitations

- **`generated.by` is hardcoded** to `okf-wiki/0.1.0` — there is no producer
  manifest/config wiring yet.
- **Malformed YAML frontmatter** is only detected as "missing frontmatter"
  (the page lands in `_staging/migration-review/`); there is no `yaml.safe_load`
  sanity check, so subtly-broken YAML may pass through verbatim.
- **`![[embed]]` embeds are mangled** — they are treated as regular wikilinks.
- **Wikilinks inside code fences are converted** — the converter does not track
  fenced-code context.
- **`stale_after` for timezone-naive `updated` values** is computed against the
  local timezone before UTC conversion.

## Related

- `wiki-import` skill — imports OKF bundles (redirects Obsidian vaults here)
- `validate.sh` — OKF v0.2 conformance checker
- `.skills/okf-wiki/SKILL.md` — canonical frontmatter mapping