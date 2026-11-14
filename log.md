# 变更日志

本文件 append-only，记录 ingest / 变更 / lint。新条目追加在末尾，不修改历史行。

## [2026-11-14] init | Docs-as-Code 骨架

- 建立 frontmatter 契约 `knowledge/schema.json`、自动索引 `index.md` 与清单 `manifest.json`。
- 建立四道 CI 门禁、`--strict` 校验、所有分支 push 与针对 main 的 PR 触发。
- 建立 PR 模板、CODEOWNERS、Issue 准入表单与每周 freshness 报告。
- 落地 3 篇示例知识文件、25 条检索评测基线与期望来源白名单。
- 分支 `kb/init-docs-as-code`，基于 main 种子提交创建，默认不自动合并。

## [2026-11-14] intake | 会话式准入流水线

- 新增 `scripts/intake.py`（仅标准库）：add（URL/文件 → sources/ 不可变快照 + inbox/ 草稿，四态判定）、status、promote（digested → knowledge/ draft，自动重建索引并跑严格门禁）、pr（kb/intake-* 分支提交推送，输出 PR 链接，不合并）。
- 归一化覆盖 Markdown/HTML/CSV/TSV/JSON/TXT；PDF/Office/图片判 unsupported，先转格式再准入。
- 原文按字节 SHA-256 去重，重复快照复用；`promote` 门禁不过自动退回 needs-review。
- 本地全链路测试通过：add（4 类输入）、status、promote（strict 0 errors）、pr（建分支推送成功）。
- 分支 `kb/intake-pipeline`，基于 `kb/init-docs-as-code` 叠加，默认不自动合并。
