# 待准入区

会话式 intake 的暂存区。这里的内容**不是知识**，不参与索引、不参与检索、不参与校验。

- 每次 intake 建一个子目录 `inbox/<id>/`，放原文、归一化草稿与抽取出的 frontmatter。
- 四态判定：`digested`（生成 draft PR）、`needs-review`（转人工）、`ignored`（记录原因）、`unsupported`（记录阻塞）。**抽取成功不等于自动准入**。
- 判定通过后由 Agent 在 `kb/<topic>` 分支开 PR；被拒绝的材料留在本目录或退回会话，不进 `knowledge/`。
- 本目录内容不设长期保留要求，可定期清理；长期留存的是 `sources/` 与 `knowledge/`。

对应 Issue 表单见 `.github/ISSUE_TEMPLATE/knowledge-intake.yml`，脚本入口见 `python scripts/intake.py`（add / status / promote / pr），状态记录在每个条目的 `metadata.json`。
