# 原始资料快照

本目录存放知识文件的**来源原文**，只增不改，供溯源、复核与重建使用。

- 命名：`YYYYMMDD-<简短主题>.<原扩展名>`，例如 `20261114-retrieval-eval.html`。
- 每个 canonical 文件的 `source_url` 若指向这里，路径必须以 `sources/` 开头。
- 抓取时间写进知识文件的 `retrieved_at`，不要依赖文件系统时间。
- 大文件、扫描件、音视频可以放这里，但**不进入 canonical 区**：先归一化为 Markdown，表格另存 CSV/JSON，图片配等价文字。
- 含密钥或 PII 的原文不要提交；确需保留时先脱敏，并在知识文件里标 `pii: redacted`。

目录保持精简：只有已被 `knowledge/` 引用的原文才值得长期留存。
