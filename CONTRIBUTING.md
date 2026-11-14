# 贡献与准入规范

本仓库把知识当代码管：**机器查机械错误，人审判断**。所有变更经 PR 进入 main。

## 状态机

| 状态 | 含义 | 能否作为默认答案依据 |
| --- | --- | --- |
| `draft` | 待评审、内容未核定 | 否 |
| `active` | 已核验、当前有效 | 是 |
| `deprecated` | 已废弃但保留供追溯 | 否 |
| `superseded` | 已被新版替代，见 `supersedes` | 否 |

旧版本**不物理删除**：保留版本链，供审计与「历史上某时点的口径」查询。新版本通过 `supersedes: [旧 canonical_id]` 指向旧文件。

## frontmatter 字段

必填字段与枚举见 `knowledge/schema.json`。几个容易填错的地方：

- `source_url`：公开来源写完整 http(s) URL；内部资料写 `sources/` 下的快照路径。**不要写「整理自网络」**。
- `retrieved_at`：抓取当天，不是编写当天。
- `stale_after`：建议不超过 6 个月。到期的 `active` 文件会出现在每周 freshness 报告。
- `canonical_id`：相对 `knowledge/` 的路径去掉 `.md`；缺省时脚本按路径推导。
- `tags`：最多 4 个，用于快速过滤，不要堆砌关键词。

YAML 支持子集：标量、引号字符串、`[a, b]` 行内列表、`- item` 块列表、布尔值。**不支持**嵌套对象、多行块、锚点与行尾注释，详见 `scripts/README.md`。

## 写作要求

- 一文件一主题；文件名可 grep，不用 `final_v2` 之类。
- 恰好一个 H1，标题层级不跳级，H2 标题互不重复。
- **每个 H2 章节脱离上下文仍成立**：首句点明本节讲什么，关键约束在每一节重复写，不要写「见上一节」。
- 表格要有表头、类型与单位；图片必须配等价文字；Mermaid 优于 PNG。
- 标题不要随意改名——重命名会让所有引用锚点失效。

## 去重与冲突

- 脚本对规范化正文做 SHA-256 去重，完全相同的正文会阻断合并。
- 近重内容（同一事实的不同表述）由人工判断：合并为一条 canonical，其余建立 `supersedes` 关系。
- 两份文件给出相互矛盾的结论时，不要静默改其中一份；在 PR 里写明冲突、裁决依据，必要时先把两份都标为 `draft`。

## 评测基线维护

新增或改写知识文件时，检查 `evals/golden_questions.json`：

- 至少为该主题补一条真实提问（不是按目录反推的假问题）。
- `expected_sources` 指向的路径必须存在，且已登记在 `evals/expected_sources.json` 白名单里。
- `refusal_expected: true` 的问题 `expected_sources` 必须为空。
- chunker、embedding 模型或 prompt 变更时，在同一金标集上重跑并对比上一版指标。

## PR 要求

- 一个 PR 只处理一个主题，便于 review 与回滚。
- 填完整 `.github/pull_request_template.md`，尤其是 Source and provenance 与 Risks and rollback。
- 本地先跑 `python scripts/build_index.py` 和 `python scripts/validate.py --strict`；CI 会再跑一次。
- required checks 全绿 + owner 批准后才能合并；**默认不自动合并**。

## 一次性仓库设置（需管理员）

**CI workflow 文件存在 ≠ 门禁生效。** 部署了校验但没有把它设为 required check，等于演戏：CI 红了仍然可以合并。请管理员在 GitHub 上完成：

1. `Settings → Branches → Add branch ruleset`（或 Branch protection rule），目标分支 `main`。
2. 勾选 `Require a pull request before merging`，至少 1 个审批；结合 `CODEOWNERS` 勾选 `Require review from Code Owners`。
3. 勾选 `Require status checks to pass`，添加来自 `validate` job 的两个检查：`Verify generated files are current` 与 `Validate with strict gates`。
4. 勾选 `Require conversation resolution`，禁止 force push 与分支删除。
5. 验收：故意提交一个漏填 `source_url` 的测试 PR，确认两个检查变红、Merge 按钮被禁用，然后关闭该 PR。

`freshness.yml` 是每周定时任务，只产出报告与 run summary，不设门禁，也不会自动改 main。

## 分支命名

`kb/<topic>`，基于最新 main 创建。合并后清理分支。
