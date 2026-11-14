---
type: Metric Definition
title: 金标问题集与 hit rate@k
description: 检索评测基线的最小组成、hit rate@k 定义、以及除命中率外必须检查的行为
source_url: https://www.kunalganglani.com/blog/llm-knowledge-base-github-template
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

# 金标问题集与 hit rate@k

检索评测基线用于发现知识库变更后的静默退化：答案听起来仍然自信，但引用的来源已经不对。

## 金标问题集的最小组成

金标问题集是一组 25-50 条「永远应该能被回答」的问题，每条记录 `id`、问题文本、类别、期望来源路径、是否应当拒答。问题必须来自真实提问，不能按文档目录反推；按目录反推会让评测只覆盖已经写好的内容，测不出缺口。

## hit rate@k 的定义

hit rate@k 表示检索返回的前 k 个结果中，至少出现一个期望来源的问题占比，常用 k=5。分母是全部金标问题，分子是命中问题。拒答类问题不计入命中率，单独统计拒答率。

## 除命中率外必须检查的行为

除命中率外，还要检查引用格式与拒答行为。引用格式要求答案显式给出知识文件路径或链接；拒答行为要求检索为空时明确说明依据不足，而不是用模型自身知识补全。这两项与命中率一起构成回归门禁，缺一项就会出现「召回到了但答案不可核验」。

## 什么时候必须重跑基线

chunker、embedding 模型、prompt 或知识文件结构任一变更，都要在同一金标集上重跑并与上一版对比。指标下降视为回归，CI 至少告警，稳定后应改为阻断合并。知识库每周都在变，没有测试集的检索会静默退化。
