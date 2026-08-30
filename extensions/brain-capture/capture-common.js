// Shared capture helpers: one markdown shape for both the popup and the
// background service worker (imported as ES modules).

export function slugify(title) {
  const slug = String(title || "")
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 72);
  return slug || "web-capture";
}

export function yq(s) {
  // YAML double-quoted scalar: escape backslash and quote; fold newlines.
  return JSON.stringify(String(s ?? ""));
}

export function buildFilename(title) {
  return `${new Date().toISOString().slice(0, 10)}-${slugify(title)}.md`;
}

export function buildMarkdown(page, note) {
  const now = new Date().toISOString();
  const desc = (page.description || "").replace(/\s+/g, " ").trim().slice(0, 200);
  const noteText = (note || "").trim();
  const parts = [];
  parts.push("---");
  parts.push(`title: ${yq(page.title || "Web capture")}`);
  parts.push("type: Concept");
  parts.push("tags: [web-capture, raw-ingest]");
  if (desc) parts.push(`description: ${yq(desc)}`);
  parts.push("generated:");
  parts.push('  by: "brain-capture/0.1.0"');
  parts.push(`  at: ${now}`);
  parts.push("status: draft");
  parts.push("tier: supporting");
  parts.push("base_confidence: 0.75");
  parts.push("provenance:");
  parts.push(`  extracted: ${noteText ? 0.75 : 0.9}`);
  parts.push(`  inferred: ${noteText ? 0.25 : 0.1}`);
  parts.push(`lifecycle_changed: ${now.slice(0, 10)}`);
  parts.push("sources:");
  parts.push(`  - resource: ${yq(page.url || "unknown")}`);
  parts.push("---");
  parts.push("");
  parts.push(`# ${page.title || "Web capture"}`);
  parts.push("");
  if (desc) {
    parts.push(`> ${desc}`);
    parts.push("");
  }
  parts.push(`- Source: ${page.url || "unknown"}`);
  parts.push(`- Captured: ${now}`);
  parts.push("");
  if (noteText) {
    parts.push("## Capture Note");
    parts.push("");
    parts.push(noteText);
    parts.push("");
  }
  if (page.selection) {
    parts.push("## Selection");
    parts.push("");
    parts.push(page.selection);
    parts.push("");
  }
  if (page.text) {
    parts.push("## Page Content");
    parts.push("");
    parts.push(page.text);
    parts.push("");
  }
  return parts.join("\n");
}
