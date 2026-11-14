## Goal

<!-- 这条变更要解决什么问题？为什么值得进 canonical 知识库？ -->

## Scope (paths)

<!-- 列出新增/修改/删除的文件路径。一个 PR 只处理一个主题。 -->

## Steps

1.
2.
3.

## Success criteria (verifiable)

<!-- 可执行的验证步骤，例如 `python scripts/validate.py --strict` 输出。 -->

## Source and provenance

- 来源 URL 或 `sources/` 路径：
- 抓取时间 `retrieved_at`：
- 是否由会话 intake 生成：是 / 否
- 原文快照是否已存入 `sources/`：是 / 否

## Risks and rollback

<!-- 冲突、过期、误引风险；回滚方式（git revert <sha>）。 -->

## Evidence

- CI run：
- 去重检查结果：
- 评测基线是否受影响：是 / 否

## Checklist

- [ ] 单个 PR 只涉及一个主题
- [ ] frontmatter 通过 `schema.json` 契约，含 `source_url` / `retrieved_at` / `owner` / `status` / `stale_after`
- [ ] 每个 H2 章节脱离上下文仍成立，无「如上所述」类指代
- [ ] 表格有表头与单位，图片有等价文字
- [ ] 运行过 `python scripts/build_index.py`，`index.md` / `manifest.json` 已同步
- [ ] 运行过 `python scripts/validate.py --strict` 且通过
- [ ] 无密钥 / PII 泄漏
- [ ] 相关 golden questions 已更新（如影响检索基线）
