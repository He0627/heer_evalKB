# 校验与索引脚本

只用 Python 标准库，CI 不需要安装依赖。

| 命令 | 作用 | 退出码 |
| --- | --- | --- |
| `python scripts/build_index.py` | 生成 `knowledge/index.md` 与 `knowledge/manifest.json` | 正常 0 |
| `python scripts/build_index.py --check` | 只检查生成文件是否与内容一致 | 不一致 1 |
| `python scripts/validate.py --strict` | 跑四道门禁，任一 error 阻断合并 | 有 error 1 |
| `python scripts/validate.py --check-links` | 额外 HEAD 检查外链，只告警不阻断 | 0 |
| `python scripts/validate.py --freshness-report` | 输出已过 `stale_after` 的 active 文件表 | 0 |

## 四道门禁

1. **Schema / frontmatter**：按 `knowledge/schema.json` 检查必填字段、枚举、日期格式、`source_url`、`canonical_id`、H1 唯一、标题不跳级、H2 不重复。
2. **溯源 / 链接 / 密钥**：内部 `.md` 链接必须存在；扫描 GitHub token、OpenAI 风格 key、AWS key id、私钥块。
3. **生成文件 / 去重**：`index.md` 与 `manifest.json` 必须与知识内容逐字节一致；规范化正文的 SHA-256 重复会阻断合并。
4. **评测基线**：金标问题 id 唯一、字段齐全、拒答题不带期望来源、所有期望来源都在白名单且文件存在；少于 25 条只告警。

改契约只改 `knowledge/schema.json`，不要改脚本里的常量；脚本读取该文件作为门禁定义。

## 确定性

两个生成文件**不含时间戳**，相同知识内容永远产生相同字节，因此 Windows（CRLF 环境）和 Linux CI 的 `--check` 结果一致。写入强制 `newline="\n"`，仓库 `.gitattributes` 统一 `eol=lf`。

## frontmatter 支持的 YAML 子集

支持：标量、单/双引号字符串、`[a, b]` 行内列表、`- item` 块列表、`true` / `false`、整行 `#` 注释。

不支持：嵌套映射、多行块（`|` / `>`）、锚点与别名、行尾注释、复杂类型。如果未来需要完整 YAML，就显式引入 PyYAML 并在 CI 固定版本——不要写一个悄悄漏字段的半吊子解析器。

## 扩展点

- 接入会话式 intake 时，在 `inbox/` 里生成草稿，调用 `build_index.py --check` 判断草稿一旦入库是否会破坏索引。
- 接入向量检索时，用 `manifest.json` 的 `sha256` 做增量判断，只重建正文变化的文件；并在回答里带上来源的 `canonical_id` 与 commit SHA。
- `--check-links` 默认关闭，避免第三方站点抖动把 CI 变红；需要时单独开一条定时任务。
