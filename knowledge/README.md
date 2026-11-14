# canonical 知识区

本目录下的 `.md` 文件是唯一可被引用的知识。每个文件一个主题、一段 YAML frontmatter。

- 契约：`schema.json`（必填字段、枚举、格式规则）
- 导航：`index.md`（由 `scripts/build_index.py` 生成，禁止手改）
- 清单：`manifest.json`（由脚本生成，含每个文件的正文 SHA-256，禁止手改）
- 分类目录：`evaluation/`（评测指标与 rubric）、`methods/`（方法与工程约定）、后续按需扩展

新增分类目录时，在 `AGENTS.md` 的目录说明里同步登记。文件名即概念标识，不要在文件名里写日期或版本号。
