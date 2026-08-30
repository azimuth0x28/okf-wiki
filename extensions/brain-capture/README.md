# Brain Capture — browser extension for okf-wiki

MV3 extension that captures the active web page (or a text selection) into an
okf-wiki bundle's `_raw/` inbox, where the normal `/wiki-ingest` flow promotes
it into the bundle. Two capture routes:

1. **Native host (recommended).** A native-messaging host resolves your bundle
   through the okf-wiki Config Resolution Protocol (active `config`, `@name`
   profiles) and delegates to `okf-wiki capture` — the same contract as the CLI.
2. **Folder pick.** With no host installed, the popup writes the markdown file
   straight into a `_raw/` folder you pick once (File System Access API).

The fill/auto-form functionality of the upstream extension is intentionally
out of scope here — this port ships capture only.

## Layout

| Path | Purpose |
|---|---|
| `manifest.json` | MV3 manifest (neutral branding, no fixed extension key) |
| `popup.html` / `popup.css` / `popup.js` | Capture pane: host bundle select or folder pick + note |
| `background.js` | Context-menu capture (page / selection), badge feedback |
| `capture-page.js` | Injected page extractor (completion-value contract) |
| `capture-common.js` | Shared markdown shaping (one v0.2-shaped `_raw/` frontmatter for both routes) |
| `host/brain_capture_host.py` | Native-messaging host: 4-byte LE framing + JSON; `vaults` / `capture` messages |
| `host/install.sh` | Stages host into `~/.config/okf-wiki/brain-capture/` and registers it with Chrome / Chromium / Brave |
| `host/test_host.py` | Wire-protocol end-to-end test (no browser needed) |

## Quickstart

1. **Load the extension:** `chrome://extensions` → Developer mode → *Load
   unpacked* → select this directory. Copy the extension **ID** shown there.
2. **Folder-only mode works immediately:** open the popup, pick your bundle's
   `_raw/` folder, capture.
3. **Host mode:** run `host/install.sh <extension-id>`, then restart Chrome
   (⌘Q — native hosts attach at browser start). The popup then shows your
   bundles from the okf-wiki config; captures go through `okf-wiki capture`.

## Test without Chrome

```bash
uv run python extensions/brain-capture/host/test_host.py
```

Builds a throwaway bundle + XDG config, sends `vaults` and `capture` over the
real wire protocol, and asserts a valid `_raw/` page with
`type/generated/sources.resource` frontmatter appears.

## Manual browser smoke

The automated CI surface covers the wire protocol only; the popup/context-menu
flows are exercised manually in the browser (load unpacked → capture a page →
check `_raw/`).

## Logs

Host diagnostics: `~/.config/okf-wiki/brain-capture.log` (stdout is the
messaging wire, so everything else goes to this file).

> Derived from Ar9av/obsidian-wiki (MIT) — extension `brain`, reduced to the
> capture loop and re-pointed at the okf-wiki CLI.
