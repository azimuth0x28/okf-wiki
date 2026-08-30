# Browser Extension

**Brain Capture** is a Chrome MV3 extension that saves the page you are
reading into your okf-wiki bundle's `_raw/` directory, ready for promotion via
`/wiki-ingest`. This port is capture-only — form-filling from the source
project is out of scope.

## Install

**Folder mode (no host needed):**

1. Open `chrome://extensions`, enable **Developer mode**, click **Load
   unpacked**, pick `extensions/brain-capture/`.
2. Click the toolbar icon, choose your bundle's `_raw/` folder. The choice is
   remembered (IndexedDB).
3. Click **Capture** — the page lands in `_raw/` as markdown with v0.2-shaped
   frontmatter.

**Host mode (capture straight through the `okf-wiki` CLI):**

```bash
bash extensions/brain-capture/host/install.sh <extension-id>
```

`<extension-id>` is the ID shown on `chrome://extensions` after loading the
unpacked folder (the build intentionally ships without a fixed key, so you
register your own). The script stages a private copy of the host plus the
`okf_wiki` package under `~/.config/okf-wiki/brain-capture/` and registers
`com.okf_wiki.brain_capture` for Chrome, Chrome Canary, Chromium, and Brave
(existing profiles only). Restart the browser (⌘Q / full quit) so the
native-messaging manifest is picked up.

The popup then lists your bundle profiles from the Config Resolution Protocol
(active config first, named profiles with `@name`), flags stale ones, and
captures through `okf-wiki capture` — the same contract the CLI and the API
use.

## Capture

- **Popup**: current tab is extracted (chrome chrome, nav/footer/aside/forms
  removed; `article`/`main` preferred), a note can be added, and the page is
  written to `_raw/` — through the host when connected, otherwise directly to
  the picked folder.
- **Context menu**: right-click anywhere ("Capture page") or on a selection
  ("Capture selection") without opening the popup.

Captures follow the `wiki-capture --quick` contract: title, tags
`[web-capture, raw-ingest]`, description, `generated`, `status: draft`,
`provenance`, `sources` with the URL as `resource`. Promotion into real bundle
pages happens via `/wiki-ingest`.

## Security model

- Folder mode keeps everything in the sandboxed File System Access API; the
  extension only writes `.md` files into the folder you picked.
- Host mode speaks Chrome native messaging (4-byte length-prefixed JSON on
  stdio) with the single registered host; the manifest pins the extension ID.
- The host resolves bundles through the same config resolution as the CLI and
  shells out to `okf-wiki capture` — it holds no bundle logic of its own.

## Why the host is staged outside the repo

On macOS, `~/Documents` is TCC-protected: a Chrome-launched host inherits
Chrome's sandbox context and cannot traverse your checkout, which surfaces as
an opaque "Native host has exited". Staging a private copy under
`~/.config/okf-wiki/brain-capture/` with baked `PATH`/`PYTHONPATH`/`HOME`
avoids both the TCC trap and minimal-PATH issues. Re-run `install.sh` after
updating the repo.

## Cost

Zero. Capture is extraction and file writing; no LLM, no network calls.

## Troubleshooting

- **"Native host has exited"** → run `install.sh`, then fully restart the
  browser.
- **Folder pick greyed out** → re-grant the permission from the popup.
- **Diagnostics** → `~/.config/okf-wiki/brain-capture.log` (stdout is reserved
  for the wire protocol).
- **Test the wire without a browser**:
  `uv run python extensions/brain-capture/host/test_host.py` — end-to-end:
  vaults listing plus a real capture into a temp bundle.

The browser flow itself is verified manually; CI covers the wire protocol.

---

Derived from Ar9av/obsidian-wiki `docs/browser-extension.md` (MIT).
