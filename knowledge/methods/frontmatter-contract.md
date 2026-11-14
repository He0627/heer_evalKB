---
type: Method
title: 用 frontmatter 做检索前的元数据过滤
description: 一概念一文件、必填 type、状态与时效字段如何让废弃文档进不了检索候选集
source_url: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
retrieved_at: 2026-11-14
owner: He0627
status: active
stale_after: 2027-05-14
canonical_id: methods/frontmatter-contract
tags: [structure, metadata, retrieval]
verified: true
verified_by: He0627
pii: none
acl: internal
---

# 用 frontmatter 做检索前的元数据过滤

纯向量检索只衡量语义相似度，无法判断一条结论是否仍然有效。把状态、来源与时效写进 YAML frontmatter，可以让检索系统在召回之前先排除不该用的文档。

## 一概念一文件，路径即标识

每个 Markdown 文件只描述一个概念，文件路径就是概念 ID，去掉 `.md` 后缀。文件之间用标准 Markdown 链接表达关系，目录与链接共同构成一张可遍历的知识图。这样 Agent 可以只打开需要的那一个文件，而不是把整篇长文档塞进上下文。

## 契约保持最小

OKF v0.1 只强制每个概念文档有一个非空 `type` 字段，其余字段由生产者自行决定；v0.2 才把 `sources`、`generated`、`verified`、`status`、`stale_after` 作为可选的信任信号加入。契约越薄越容易跨工具迁移，字段必须是真的有下游消费者才加，否则只是每次检索都要付的 token 税。

## 检索前过滤，而不是检索后补救

`status != active`、已过 `stale_after`、被新版 `supersedes` 指向的文档，应在进入候选集之前就被排除。新旧两版定义在向量空间里往往高度相似，靠排序区分并不可靠。常见做法是「元数据预过滤 + 向量检索」的混合臂：元数据先砍掉明显不可用项，向量再处理真正模糊的匹配。

## 保留版本链，不删旧版

被替代的文档标为 `superseded` 并保留，新版用 `supersedes` 指向它。审计、历史口径查询和「为什么当时这么做」都需要旧版；物理删除会同时丢掉溯源与引用链接。生成 `index.md` 时可以只列 `active` 项，但仓库里必须留全。
