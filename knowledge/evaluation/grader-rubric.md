---
type: Evaluation Rubric
title: LLM-as-Judge rubric 的设计要点
description: 写 grader 评分标准时的触发描述、gotchas、指令强度与输出模板四条经验
source_url: https://agentskills.io/skill-creation/best-practices
retrieved_at: 2026-11-14
owner: He0627
status: active
stale_after: 2027-05-14
canonical_id: evaluation/grader-rubric
tags: [eval, grader, rubric]
verified: true
verified_by: He0627
pii: none
acl: internal
---

# LLM-as-Judge rubric 的设计要点

评分标准写不好时，grader 会稳定地给出看似合理但不可复现的分数。以下四条来自公开的 Skill 编写实践。

## 描述写触发条件，不写内容摘要

grader 的说明字段要回答「什么时候该用这套标准」，而不是概括标准内容。调用方通常只把描述放进上下文，靠它判断是否触发；把描述写成摘要会降低路由准确率。写清任务类型、输入形态与典型触发词比罗列评分维度更有用。

## gotchas 是信噪比最高的一节

评分标准里最有价值的是「模型不被告知就会犯的错」：某个字段在两个系统里名字不同、某个状态码返回成功但实际未生效、某张表是追加写要取最大版本。每次人工纠正 grader 的误判，都应把纠正写回 gotchas，而不是只改 prompt。

## 指令强度按任务脆弱度分档

多解且容错的任务给目标和判断依据，允许 grader 自行选路径；顺序敏感、不可逆或要求一致性的任务给出精确步骤与禁止项，不留发挥空间。同一份 rubric 里可以两种写法并存，但必须逐条标明属于哪一档。

## 给默认方案和输出模板

存在多种可行做法时，明确一个默认并简述替代项，不要并列成菜单。输出格式尽量给具体模板而不是散文描述：grader 对具体结构做模式匹配，比按文字要求重新组织输出稳定得多。模板较长时放到单独文件，按需加载，避免挤占上下文预算。
