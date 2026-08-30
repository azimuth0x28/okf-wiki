// Brain Capture popup — single capture pane.
// Two routes, host-first:
//   1. okf-wiki native host present → {type:"vaults"} fills the bundle select,
//      capture goes through the host (bundle Config Resolution Protocol, CLI `capture`).
//   2. No host → File System Access API folder pick, markdown written directly
//      into the picked _raw/ with the same v0.2-shaped frontmatter the CLI writes.
// Shared capture-page injection lives in capture-page.js (scripting.executeScript files).

const HOST_NAME = "com.okf_wiki.brain_capture";

import { buildFilename, buildMarkdown } from "./capture-common.js";

const IDB_NAME = "brain-capture-capture";
const IDB_STORE = "handles";
const IDB_KEY = "raw-folder";
// The saved handle is keyed by a fixed literal: renaming the key would orphan
// existing installs' stored handles.
const DB_NAME = IDB_NAME;

let hostAvailable = false;
let rawHandle = null;

const $ = (id) => document.getElementById(id);

function setStatus(text, cls = "") {
  const el = $("status");
  el.textContent = text;
  el.className = "status" + (cls ? " " + cls : "");
}

function setResult(text, cls = "") {
  const el = $("result");
  el.textContent = text;
  el.className = "hint" + (cls ? " " + cls : "");
}

// --- IndexedDB folder-handle persistence (FS route only) -------------------

function idbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(IDB_STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbGet(key) {
  const db = await idbOpen();
  return new Promise((resolve, reject) => {
    const req = db.transaction(IDB_STORE).objectStore(IDB_STORE).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbSet(key, value) {
  const db = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, "readwrite");
    tx.objectStore(IDB_STORE).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// --- Native host -------------------------------------------------------------

function sendHost(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(HOST_NAME, message, (resp) => {
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          resolve(resp || { ok: false, error: "empty host response" });
        }
      });
    } catch (err) {
      resolve({ ok: false, error: String(err) });
    }
  });
}

// --- Bundle select (host mode) ----------------------------------------------

async function loadBundles() {
  const resp = await sendHost({ type: "vaults" });
  if (!resp.ok || !Array.isArray(resp.bundles)) return false;

  const select = $("bundle");
  select.innerHTML = "";
  for (const b of resp.bundles) {
    const opt = document.createElement("option");
    opt.value = b.name || "";
    opt.textContent = b.exists ? b.label : `${b.label} (missing)`;
    opt.disabled = !b.exists;
    select.appendChild(opt);
  }
  hostAvailable = true;
  $("host-mode").hidden = false;
  $("folder-mode").hidden = true;
  setStatus("okf-wiki host connected", "ok");
  return true;
}

// --- FS fallback --------------------------------------------------------------

async function loadSavedFolder() {
  const handle = await idbGet(IDB_KEY);
  if (!handle) return false;
  const perm = await handle.queryPermission({ mode: "readwrite" });
  if (perm !== "granted") return false;
  rawHandle = handle;
  $("folder-name").textContent = handle.name;
  $("folder-mode").hidden = false;
  $("host-mode").hidden = true;
  setStatus("Folder mode — writes straight into the picked _raw/", "warn");
  return true;
}

async function chooseFolder() {
  try {
    const handle = await showDirectoryPicker({
      id: "okf-wiki-raw",
      mode: "readwrite",
      startIn: "documents",
    });
    await handle.requestPermission({ mode: "readwrite" });
    await idbSet(IDB_KEY, handle);
    rawHandle = handle;
    $("folder-name").textContent = handle.name;
    setStatus("Folder picked", "ok");
  } catch (err) {
    if (err && err.name !== "AbortError") {
      setStatus(String(err), "err");
    }
  }
}

// --- Capture ------------------------------------------------------------------

async function extractPage(tabId) {
  const [res] = await chrome.scripting.executeScript({
    target: { tabId },
    files: ["capture-page.js"],
  });
  return res ? res.result : null;
}

// Uniqueness contract (from source): getFileHandle(create:true) happily opens
// an existing file, so existence is probed WITHOUT create first; duplicates of
// the same page land as `<base>-2.md` … `<base>-100.md`, then a Date.now() name.
async function getUniqueFileHandle(dir, filename) {
  const free = async (name) => {
    try {
      await dir.getFileHandle(name);
      return false;
    } catch (err) {
      return true; // NotFoundError → name unused
    }
  };
  if (await free(filename)) {
    return { handle: await dir.getFileHandle(filename, { create: true }), name: filename };
  }
  const base = filename.replace(/\.md$/, "");
  for (let n = 2; n < 100; n++) {
    const candidate = `${base}-${n}.md`;
    if (await free(candidate)) {
      return { handle: await dir.getFileHandle(candidate, { create: true }), name: candidate };
    }
  }
  const fallback = `${base}-${Date.now()}.md`;
  return { handle: await dir.getFileHandle(fallback, { create: true }), name: fallback };
}

async function writeMarkdown(dir, filename, markdown) {
  const { handle, name } = await getUniqueFileHandle(dir, filename);
  const writable = await handle.createWritable();
  await writable.write(markdown);
  await writable.close();
  return name;
}

function filterBlocked(url) {
  return /^chrome|^chrome-extension|^about:/.test(url || "");
}

async function captureActiveTab(trigger, selectionText = "") {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || filterBlocked(tab.url)) {
    setResult("This page can't be captured (browser-internal URL).", "err");
    return;
  }
  const note = $("note").value.trim();
  const page = await extractPage(tab.id);
  if (!page) {
    setResult("Could not extract page content.", "err");
    return;
  }
  if (selectionText) page.selection = selectionText;

  const title = page.title || tab.title || "Web capture";
  if (hostAvailable) {
    const bundle = $("bundle").value;
    const resp = await sendHost({
      type: "capture",
      bundle,
      title,
      url: page.url || tab.url || "",
      description: page.description || "",
      selection: page.selection || "",
      text: page.text || "",
      note,
    });
    if (resp.ok && resp.path) {
      setResult(`Captured ${resp.path}`, "ok");
      $("note").value = "";
      return;
    }
    setResult(`Host capture failed: ${resp.error || "unknown error"}`, "err");
    return;
  }

  if (!rawHandle) {
    setResult("Pick a _raw/ folder first (or install the native host).", "warn");
    return;
  }
  const markdown = buildMarkdown(page, note);
  const filename = buildFilename(title);
  const written = await writeMarkdown(rawHandle, filename, markdown);
  setResult(`Captured ${written}`, "ok");
  $("note").value = "";
}

// --- Context-menu selection from background ----------------------------------

chrome.storage.local.get(["pendingSelection"], ({ pendingSelection }) => {
  if (pendingSelection) {
    chrome.storage.local.remove("pendingSelection");
    captureActiveTab("context-menu", pendingSelection);
  }
});

// --- Init ----------------------------------------------------------------------

(async function init() {
  $("choose-folder").addEventListener("click", chooseFolder);
  $("capture").addEventListener("click", () => captureActiveTab("popup"));

  const connected = await loadBundles();
  if (connected) return;

  const restored = await loadSavedFolder();
  if (restored) return;

  setStatus("No host found — pick a folder, or run host/install.sh", "warn");
  $("folder-mode").hidden = false;
})();
