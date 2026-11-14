# 变更日志

本文件 append-only，记录 ingest / 变更 / lint。新条目追加在末尾，不修改历史行。

## [2026-11-14] init | Docs-as-Code 骨架

- 建立 frontmatter 契约 `knowledge/schema.json`、自动索引 `index.md` 与清单 `manifest.json`。
- 建立四道 CI 门禁、`--strict` 校验、所有分支 push 与针对 main 的 PR 触发。
- 建立 PR 模板、CODEOWNERS、Issue 准入表单与每周 freshness 报告。
- 落地 3 篇示例知识文件、25 条检索评测基线与期望来源白名单。
- 分支 `kb/init-docs-as-code`，基于 main 种子提交创建，默认不自动合并。
