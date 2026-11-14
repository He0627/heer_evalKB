# heer_evalKB

面向 AI Agent 的评测知识库。知识以 Markdown + YAML frontmatter 存放，Git 是唯一事实源。

> 仓库初始化中：完整的 Docs-as-Code 骨架（目录约定、frontmatter 契约、校验脚本、CI 门禁、PR 模板、评测基线）位于 `kb/init-docs-as-code` 分支。合并该分支后，本文件会被完整版 README 取代。

## 三条原则

- Git 是唯一事实源，禁止绕过 PR 直接改 main。
- 每个 canonical 知识文件必须带溯源、状态与责任人元数据。
- 机器查机械错误，人审判断；required checks 必须阻断合并。
