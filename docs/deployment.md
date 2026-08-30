# Deployment

Run your bundle as a memory service: a single container exposes it to remote
agents over HTTP and MCP. The container does no LLM work — it is a thin,
deterministic front end over the same `okf_wiki` modules the CLI uses.

## Run it

```bash
WIKI_API_KEY=change-me docker compose up -d
curl -s localhost:8080/health     # → {"ok":true,"bundle":"/bundle"}
```

`Dockerfile` builds `python:3.12-slim` with git, installs `okf-wiki[server]`,
runs as a non-root user, mounts `/bundle` (the `OKF_BUNDLE_PATH` the Config
Resolution Protocol picks up), and healthchecks `/health`. Build with a real
version in CI via `--build-arg VERSION=$(git describe --tags)`.

## Configuration

| Env | Meaning |
|---|---|
| `OKF_BUNDLE_PATH` | bundle root inside the container (`/bundle` default) |
| `WIKI_API_KEY` | required bearer key; boot refuses without it |
| `WIKI_ALLOW_ANONYMOUS=1` | open access — local development only |
| `WIKI_PORT` | listen port (default 8080) |

`docker-compose.yml` keeps the bundle in the named volume `okf-bundle:/bundle`
so writes survive container restarts.

## Connect an agent (MCP)

The server exposes four MCP tools — `memory_search`, `memory_read`,
`memory_write` (writes land in `_raw/` via the capture contract),
`memory_context_pack` — on the streamable HTTP endpoint at `/mcp`. Point an
MCP-capable agent at `http://host:8080/mcp` with the same bearer key.

## REST

All data endpoints require `Authorization: Bearer $WIKI_API_KEY`;
`/health` is open.

```bash
# search the graph
curl -s -H "Authorization: Bearer $KEY" "localhost:8080/v1/search?q=rate+limiting&limit=5"

# read a page
curl -s -H "Authorization: Bearer $KEY" localhost:8080/v1/pages/concepts/okf-bundle.md

# write a memo (always _raw/, v0.2 frontmatter — full-page authoring stays with skills/sync)
curl -s -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"title":"api demo memo","content":"finding text","tags":["demo"]}' \
  localhost:8080/v1/pages

# context pack for another agent
curl -s -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"topic":"session clustering","budget":1500}' \
  localhost:8080/v1/context-pack
```

Path traversal is refused (`400`); the API key is compared in constant time.

## Backups

The bundle is plain markdown — back up the volume or bind-mount directory with
any file-level tool (`tar`, restic, rsync). `okf-wiki sync` commits bundle
changes to git; the container image includes git for exactly that.

## What this is not

A multi-tenant SaaS. One process serves one bundle with one API key; run one
container per bundle. There is no user management, no TLS termination — put it
behind your own reverse proxy if you expose it.

---

Derived from Ar9av/obsidian-wiki `docs/deployment.md` (MIT).
