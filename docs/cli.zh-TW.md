# CLI 參考（繁體中文）

`okf-wiki` 是代理技能的確定性對應物：所有不變操作（lint 平價、capture、圖譜匯出、
會話聚類）都以同一條程式碼路徑執行，有無代理皆同。

```bash
uv venv && uv pip install -e '.[server]' && uv run okf-wiki --help
```

所有 bundle 命令皆可位置式傳入路徑，或經由 Config Resolution Protocol 解析
（含 `@name` 覆寫，如 `okf-wiki lint @work`）。

## 設定與檢查

- `okf-wiki list` — 具名設定檔與作用中標記
- `okf-wiki info [--name demo]` — 版本、設定來源、路徑
- `okf-wiki doctor <bundle>` — 驗證設定解析、bundle 存在、`index.md` 的 `okf_version`

## 查詢與 lint

- `okf-wiki lint <bundle>` — `scripts/validate.sh` 的精確移植（E1–E4/W 警告，
  結束碼 0/1/2）；CI 斷言兩者平價
- `okf-wiki query "<question>" --top 2` — 關鍵字排序（標題 ×3、標籤 ×2、描述 ×1）
  並輸出 file-relative 引用與摘要

## 上下文包

- `okf-wiki context-pack --topic "rate limiting" --budget 1500` — 為另一代理編製
  有預算上限的上下文（排名頁面、摘要、每頁 provenance 行）；唯讀。

## 會話主題圖

- `okf-wiki sessions-build [--full] [--mutual] [--half-life 60]` — 建圖並輸出
  `graph.html`；sidecar 位於 `~/.config/okf-wiki/session-graph/`
- `okf-wiki sessions-query "rate limiting api"` — 相似度、聚類提升、書籤加權、時間衰減
- `okf-wiki sessions-show <id> --pretty` — 聚類與鄰居
- `okf-wiki sessions-clusters --unnamed` — 待命名聚類
- `okf-wiki sessions-name --from -`（stdin JSON）— 命名；透過穩定詞彙鍵在重建後保留

## 捕獲與同步

- `okf-wiki capture <bundle> --title ... --tags ... --note ...` — 寫入 v0.2 格式的
  `_raw/` 頁面（`wiki-capture --quick` 合約）；`/wiki-ingest` 負責晉升
- `okf-wiki sync <bundle> [--push]` — 恰好一次常規提交
- `okf-wiki sync-setup <bundle>` — post-commit 自動同步鉤子

## 圖譜匯出

- `okf-wiki graph <bundle> --out /tmp/graph` — graph.json / graph.graphml /
  cypher.txt / postgres.sql / graph.html 五種格式，全部位元組級確定性
- `okf-wiki graph-query <bundle> <tokens>` — 依關鍵字過濾節點

## 程式碼智能

- `okf-wiki ast-extract <path> --pretty` — 結構符號與邊
- `okf-wiki code-understand [--backend builtin|codegraph]` — 代理的焦點圖

## 信任帳本

- `okf-wiki trust-check <page>` — 顯示信任等級（verified > human > machine）
- `okf-wiki trust-record <page> --by human:evgeniy --note ...` — 追加 `verified` 條目

## 底層命令

- `okf-wiki cache-check` / `cache-update [--dry-run]` / `cache-hash` /
  `batch-plan` — `.manifest.json` 完整性、NEW/MODIFIED 增量、確定性摘要、
  有序 ingest 計劃

## 記憶服務

- `WIKI_API_KEY=... okf-wiki server [--port 8080]` — HTTP + MCP 前端（詳見
  [deployment](./deployment.md)）：開放 `/health`、持鑰保護的 `/v1/*` 與 `/mcp`。

---

Derived from Ar9av/obsidian-wiki `docs/cli.zh-TW.md` (MIT).
