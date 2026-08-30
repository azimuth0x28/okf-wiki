---
category: skills
title: "Ghost Sync Flow"
summary: "The five-step ghost-writer procedure for syncing a legacy bundle after a schema revision."
tags: [ghost-writer, workflow, migration]
by: ghost-writer/0.3
timestamp: 2026-08-28T16:00:00Z
lifecycle: draft
sources:
  - "https://ghost-writer.example/docs/sync-flow"
---

# Ghost Sync Flow

The sync flow reconciles a bundle with a revised header schema:

1. Snapshot the bundle tree and hash every page.
2. Parse each legacy header block and collect the observed key sets.
3. Diff the observed key sets against the target schema.
4. Re-emit every page whose header changed, in canonical order.
5. Re-run the hash pass and report pages whose body changed unexpectedly.

Step 4 is where [Ghost Canonicalization](../concepts/ghost-canonicalization.md)
is enforced; step 1 is what makes the whole flow reversible.
