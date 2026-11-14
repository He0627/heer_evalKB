# heer_evalKB

面向 AI Agent 的评测知识库。**Git 是唯一事实源**：知识以 Markdown + YAML frontmatter 存放，所有变更经 PR 进入 main，机器查机械错误、人审判断。

初始化采用 **Docs-as-Code + PR 治理**（方案二）：目录即分类、frontmatter 即契约、CI 即门禁、PR 即审计记录。

## 快速开始

```bash
python scripts/build_index.py           # 重新生成 index.md / manifest.json
python scripts/validate.py --strict     # 跑全部校验门禁
python scripts/validate.py --freshness-report   # 列出已过复核期的 active 文件
```

两个脚本只用 Python 标准库，无需安装依赖。CI 在**所有分支的 push**和**针对 main 的 PR**上运行同一套 `--strict` 校验。

## 目录约定

| 路径 | 用途 | 能否手工改 |
| --- | --- | --- |
| `AGENTS.md` | 给 AI Agent 的仓库指令（单一事实源） | 需 PR + owner 评审 |
| `knowledge/schema.json` | frontmatter 契约，校验脚本读取它 | 需 PR + owner 评审 |
| `knowledge/**/*.md` | canonical 知识，一文件一主题 | 可改，走 PR |
| `knowledge/index.md` | 自动生成的导航索引 | **禁止手改** |
| `knowledge/manifest.json` | 自动生成的知识清单（含正文哈希） | **禁止手改** |
| `sources/` | 原始资料快照，**只增不改** | 只增 |
| `inbox/` | 待准入区，供会话式 intake 使用 | 可写，不进 canonical |
| `evals/golden_questions.json` | 检索评测基线（25 条起） | 需 PR + owner 评审 |
| `evals/expected_sources.json` | 允许作为证据引用的文件白名单 | 需 PR + owner 评审 |
| `scripts/` | 校验与索引生成脚本 | 需 PR + owner 评审 |
| `.github/` | PR 模板、CODEOWNERS、workflows | 需 PR + owner 评审 |
| `log.md` | append-only 变更史 | 只追加 |

## 知识文件的样子

```yaml
---
type: Metric Definition
title: 金标问题集与 hit rate@k
description: 检索评测基线的最小组成、hit rate@k 定义、三类必须检查的行为
source_url: https://example.com/docs/retrieval-eval
retrieved_at: 2026-11-14
owner: He0627
status: active
stale_after: 2027-05-14
canonical_id: evaluation/golden-set-and-hit-rate
tags: [eval, retrieval, baseline]
verified: true
verified_by: He0627
pii: none
acl: internal
---
```

字段的必填项、枚举值与格式规则以 `knowledge/schema.json` 为准。**每个 H2 章节必须能脱离上下文独立成立**——RAG 一次只给 Agent 一个片段，不会把相邻章节一起给它。

## 准入流程

1. 原始资料先进 `sources/` 或 `inbox/`，附出处与抓取时间。
2. 在 `kb/<topic>` 分支上创建知识文件，填齐 frontmatter。
3. 运行 `python scripts/build_index.py` 重建生成文件。
4. 开 PR，填完整 `pull_request_template.md`（含 plan、证据、风险与回滚）。
5. CI 跑四道门禁；CODEOWNERS 指定的 owner 做人工评审。
6. 合并进 main；**默认不自动合并**，由仓库所有者决定。

## 四道 CI 门禁

| 门禁 | 检查内容 | 失败后果 |
| --- | --- | --- |
| Schema / frontmatter | 必填字段、枚举、日期格式、`canonical_id`、标题结构 | 阻断合并 |
| 溯源 / 链接 / 密钥 | `source_url`、内部链接可达、token 与私钥扫描 | 阻断合并 |
| 生成文件 / 去重 | `index.md` / `manifest.json` 与内容一致、正文哈希去重 | 阻断合并 |
| 评测基线 | 金标问题 id 唯一、期望来源存在且在白名单内 | 阻断合并 |

第五道是**定时 freshness**：每周一生成过期知识报告写入 run summary 与 artifact，不静默改 main。

## 评测基线

`evals/golden_questions.json` 的每一条记录包含 `id`、`question`、`category`、`expected_sources`、`refusal_expected`。`refusal_expected: true` 的问题用于验证「检索为空时是否明确拒答」，不计算命中率。随知识增长把问题扩到 50 条，并在 chunker / embedding / prompt 变更时重跑对比。

## 边界与预留

- 本仓库**不提供语义检索**；量大之后应在此结构上叠加索引层，且必须明确「检索的是哪个 commit 的快照」。
- `llms.txt` 若需要，只能由 `scripts/build_index.py` 自动生成；手工维护的过期索引比没有更糟。
- `inbox/`、Issue 表单 `knowledge-intake.yml` 和 PR 模板里的 provenance 段落，是为后续「会话式 Intake → PR」流水线预留的接口。

## 参考实践

GitHub 官方 PR 工作流与 CODEOWNERS、`microsoft/discovery` 的 PR 治理、docs-as-code CI kit 的 required-check 实践、2026 年 LLM Knowledge Base GitHub Template 的 frontmatter 溯源与四道门禁、Google Cloud Open Knowledge Format v0.2 的信任信号、Anthropic Agent Skills 的渐进式披露。完整来源见选型报告 `GitHub知识库方案选型_报告_20261114.md`。
