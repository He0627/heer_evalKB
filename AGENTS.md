# AGENTS.md

本仓库是**给 AI 读的评测知识库**，不是文档站点。以下命令与约束是 Agent 从代码里推不出来的，必须遵守。

## 目录与事实源

- `knowledge/` 是唯一 canonical 区；`sources/` 是不可变原文快照；`inbox/` 是待准入暂存区，**不参与检索**。
- `knowledge/schema.json` 是 frontmatter 契约；`knowledge/index.md` 与 `knowledge/manifest.json` 是生成文件。
- 回答问题时先读 `knowledge/index.md` 定位范围，再只读相关文件；不要一次读完全部知识文件。

## 必跑命令

```bash
python scripts/build_index.py
python scripts/validate.py --strict
```

改动任何 `knowledge/**/*.md` 后必须先跑 `build_index.py`，再跑 `validate.py --strict`。两个命令都只用标准库。

## 如何加一页（不超过 15 行）

1. 原文存 `sources/`，记下 URL 与抓取时间。
2. 在 `kb/<topic>` 分支上新建 `knowledge/<分类>/<短名>.md`。
3. 按 `schema.json` 填齐 frontmatter，`status` 默认 `draft`。
4. 正文一个 H1，每个 H2 自足、不含「如上所述」。
5. 跑 `build_index.py` 与 `validate.py --strict`。
6. 开 PR 填模板，等 owner 评审，不要自己合并。

## 禁止事项

- 禁止直接 push 到 main，禁止自行 merge PR。
- 禁止手工编辑 `knowledge/index.md`、`knowledge/manifest.json`、`knowledge/schema.json`。
- 禁止写入没有 `source_url` 或 `retrieved_at` 的 canonical 文件。
- 禁止把 PDF / HTML / 截图原件放进 `knowledge/`；先归一化为 Markdown，表格另存 CSV/JSON。
- 禁止提交 token、私钥或含 PII 的原文；`pii` 字段必须如实填写。
- 禁止覆盖已有知识：命中重复或冲突时，用 `supersedes` 建立版本链并交人裁决。

## 回答行为

- 引用知识时给出 `knowledge/` 下的路径；检索不到依据时明确说明依据不足，不要用自身知识补全。
- `status` 不是 `active` 或已过 `stale_after` 的文件，只能作为历史参考，不作为当前结论依据。

CLAUDE.md 若存在，应当只包含一行 `@AGENTS.md`，保持单一事实源。
