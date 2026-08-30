// Brain Capture background service worker (ES module).
// Context-menu captures go host-first, then fall back to the saved folder
// handle; browser-internal pages get a badge prompt instead.

import { buildFilename, buildMarkdown } from "./capture-common.js";

const HOST_NAME = "com.okf_wiki.brain_capture";
const IDB_NAME = "brain-capture-capture";
const IDB_STORE = "handles";
const IDB_KEY = "raw-folder";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "brain-capture-page",
    title: "Capture page to _raw/",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "brain-capture-selection",
    title: "Capture selection to _raw/",
    contexts: ["selection"],
  });
});

function flashBadge(text, color = "#2563eb", title = "Brain Capture") {
  chrome.action.setBadgeBackgroundColor({ color });
  chrome.action.setBadgeText({ text });
  chrome.action.setTitle({ title });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 2400);
}

function blocked(url) {
  return /^chrome|^chrome-extension|^about:/.test(url || "");
}

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

async function extractPage(tabId) {
  const [res] = await chrome.scripting.executeScript({
    target: { tabId },
    files: ["capture-page.js"],
  });
  return res ? res.result : null;
}

// --- IndexedDB folder-handle persistence (FS fallback) ----------------------
// The store is shared per-origin: the popup writes the handle via idbSet, this
// worker only reads it.

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

// --- Capture ------------------------------------------------------------------

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || blocked(tab.url)) {
    flashBadge("popup", "#c08a2e", "Open the popup to capture this page");
    return;
  }

  const page = await extractPage(tab.id);
  if (!page) {
    flashBadge("fail", "#b3452f", "Could not extract page content");
    return;
  }
  if (info.selectionText) page.selection = info.selectionText;

  const title = page.title || tab.title || "Web capture";
  const hostResp = await sendHost({
    type: "capture",
    bundle: "",
    title,
    url: page.url || tab.url || "",
    description: page.description || "",
    selection: page.selection || "",
    text: page.text || "",
    note: "",
  });
  if (hostResp.ok && hostResp.path) {
    flashBadge("ok", "#3b8f5a", `Captured ${hostResp.path}`);
    return;
  }

  const handle = await idbGet(IDB_KEY);
  if (handle) {
    const perm = await handle.queryPermission({ mode: "readwrite" });
    if (perm === "granted") {
      const markdown = buildMarkdown(page, "");
      const written = await writeMarkdown(handle, buildFilename(title), markdown);
      flashBadge("ok", "#3b8f5a", `Captured ${written}`);
      return;
    }
  }

  flashBadge("setup", "#c08a2e", "No capture route: pick a folder in the popup or install the host");
});

