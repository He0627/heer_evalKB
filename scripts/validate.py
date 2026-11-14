#!/usr/bin/env python3
"""Docs-as-Code validation gates for heer_evalKB.

Usage:
    python scripts/validate.py --strict
    python scripts/validate.py --check-links
    python scripts/validate.py --freshness-report > freshness-report.md

Four gates: frontmatter schema, provenance/links/secrets, generated files and
deduplication, evaluation baseline. With --strict any error exits 1, which is
what the CI required check uses to block a merge.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from build_index import (
    ROOT, KNOWLEDGE, INDEX_PATH, MANIFEST_PATH,
    parse_frontmatter, iter_knowledge_files, collect,
    render_index, render_manifest, relative,
)

SCHEMA_PATH = KNOWLEDGE / "schema.json"
EVALS = ROOT / "evals"
GOLDEN_PATH = EVALS / "golden_questions.json"
WHITELIST_PATH = EVALS / "expected_sources.json"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?)?$"
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.M)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub personal access token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "OpenAI-style API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
]


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)


def load_json(path, report):
    if not path.is_file():
        report.error(f"{relative(path)}: 文件不存在")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"{relative(path)}: 无法解析 JSON: {exc}")
        return None


def check_headings(path, body, report):
    headings = [(len(m.group(1)), m.group(2).strip())
                for m in HEADING_RE.finditer(body)]
    if sum(1 for level, _ in headings if level == 1) != 1:
        report.error(f"{relative(path)}: 必须恰好有一个 H1")
    previous = 0
    for level, _ in headings:
        if previous and level > previous + 1:
            report.error(f"{relative(path)}: 标题层级跳级 (H{previous} -> H{level})")
            break
        previous = level
    h2s = [title for level, title in headings if level == 2]
    if len(h2s) != len(set(h2s)):
        report.error(f"{relative(path)}: H2 标题重复，Agent 会按标题去重锚点")


def check_links(path, text, report, external_urls):
    for match in LINK_RE.finditer(text):
        raw = match.group(1).strip()
        target = raw.split("#")[0].strip()
        if not target:
            continue
        if target.startswith(("http://", "https://")):
            external_urls.add(target)
            continue
        if target.startswith("mailto:"):
            continue
        if not target.endswith(".md"):
            continue
        resolved = (ROOT / target.lstrip("/")) if target.startswith("/") \
            else (path.parent / target)
        if not resolved.resolve().is_file():
            report.error(f"{relative(path)}: 内部链接不存在 -> {target}")


def check_file(path, required, enums, report, external_urls):
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    if meta is None:
        report.error(f"{relative(path)}: 缺少或无法解析 YAML frontmatter")
        return

    for key in required:
        value = meta.get(key)
        if value is None or value == "" or value == []:
            report.error(f"{relative(path)}: 缺少必填字段 `{key}`")

    for key, allowed in enums.items():
        value = meta.get(key)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if str(item) not in allowed:
                report.error(
                    f"{relative(path)}: `{key}` 取值 `{item}` 不在枚举 {allowed} 内"
                )

    for key, pattern, label in (
        ("retrieved_at", TIMESTAMP_RE, "ISO 8601 日期或日期时间"),
        ("stale_after", DATE_RE, "YYYY-MM-DD"),
    ):
        value = meta.get(key)
        if isinstance(value, str) and not pattern.match(value):
            report.error(f"{relative(path)}: `{key}` 应为 {label}，实际为 `{value}`")

    source = meta.get("source_url")
    if isinstance(source, str) and not (
        source.startswith("http://")
        or source.startswith("https://")
        or source.startswith("sources/")
    ):
        report.error(f"{relative(path)}: `source_url` 必须是 http(s) URL 或 sources/ 路径")

    expected_id = relative(path)[:-3].removeprefix("knowledge/")
    if "canonical_id" in meta and str(meta["canonical_id"]) != expected_id:
        report.error(
            f"{relative(path)}: `canonical_id` 应为 `{expected_id}`，"
            f"实际为 `{meta['canonical_id']}`"
        )

    check_headings(path, body, report)
    check_links(path, text, report, external_urls)

    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            report.error(f"{relative(path)}: 疑似包含{label}，禁止提交")

    if len(body.strip()) > 12000:
        report.warn(f"{relative(path)}: 正文较长，建议拆成一概念一文件")


def check_generated(records, report):
    for path, expected in (
        (INDEX_PATH, render_index(records)),
        (MANIFEST_PATH, render_manifest(records)),
    ):
        if not path.is_file():
            report.error(f"{relative(path)}: 生成文件缺失，运行 build_index.py")
        elif path.read_text(encoding="utf-8") != expected:
            report.error(f"{relative(path)}: 与知识内容不一致，运行 build_index.py 重建")


def check_dedup(records, report):
    seen = {}
    for record in records:
        digest = record["sha256"]
        if digest in seen:
            report.error(
                f"正文重复: {record['path']} 与 {seen[digest]}，"
                "请合并为一条 canonical 或建立 supersedes 版本链"
            )
        else:
            seen[digest] = record["path"]


def check_evals(report):
    golden = load_json(GOLDEN_PATH, report)
    whitelist = load_json(WHITELIST_PATH, report)
    count = 0
    if not isinstance(golden, dict) or not isinstance(whitelist, dict):
        return count

    allowed = set(whitelist.get("sources", []))
    for source in sorted(allowed):
        if not (ROOT / source).is_file():
            report.error(f"expected_sources.json: 白名单文件不存在 -> {source}")

    seen_ids = set()
    for question in golden.get("questions", []):
        count += 1
        qid = question.get("id", "<missing id>")
        if qid in seen_ids:
            report.error(f"golden_questions.json: 重复的 id `{qid}`")
        seen_ids.add(qid)
        for key in ("id", "question", "category", "expected_sources", "refusal_expected"):
            if key not in question:
                report.error(f"golden_questions.json: {qid} 缺少字段 `{key}`")
        sources = question.get("expected_sources", [])
        refusal = bool(question.get("refusal_expected", False))
        if refusal and sources:
            report.error(f"golden_questions.json: {qid} 为拒答测试，expected_sources 必须为空")
        for source in sources:
            if source not in allowed:
                report.error(f"golden_questions.json: {qid} 引用未登记来源 -> {source}")
            elif not (ROOT / source).is_file():
                report.error(f"golden_questions.json: {qid} 引用的文件不存在 -> {source}")
    if count < 25:
        report.warn(f"golden_questions.json: 当前 {count} 条，建议扩充到 25-50 条")
    return count


def check_external_links(urls, report):
    import urllib.request
    for url in sorted(urls)[:20]:
        try:
            request = urllib.request.Request(url, method="HEAD",
                                             headers={"User-Agent": "heer_evalKB-validator"})
            with urllib.request.urlopen(request, timeout=3):
                pass
        except Exception as exc:
            report.warn(f"外链不可达（不阻断）: {url} -> {type(exc).__name__}")


def render_freshness(records):
    today = date.today().isoformat()
    stale = [r for r in records
             if r["status"] == "active" and r["stale_after"] and r["stale_after"] < today]
    lines = [
        "# 知识时效性报告",
        "",
        f"- 检查日期：{today}",
        f"- 已过复核期的 active 文件：{len(stale)}",
        "",
    ]
    if stale:
        lines.append("| canonical_id | 复核期限 | 状态 |")
        lines.append("| --- | --- | --- |")
        for record in sorted(stale, key=lambda item: item["stale_after"]):
            lines.append(
                f"| {record['canonical_id']} | {record['stale_after']} | {record['status']} |"
            )
        lines.append("")
        lines.append("请为上述文件开 PR 更新内容或调整 `status`，不要静默改 main。")
    else:
        lines.append("没有过期的 active 文件。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when any error is found (CI required check)")
    parser.add_argument("--check-links", action="store_true",
                        help="HEAD-check external URLs (warnings only)")
    parser.add_argument("--freshness-report", action="store_true",
                        help="print a freshness report and exit")
    args = parser.parse_args()

    records = collect()
    if args.freshness_report:
        sys.stdout.write(render_freshness(records))
        return 0

    report = Report()
    schema = load_json(SCHEMA_PATH, report)
    required = schema.get("required", []) if isinstance(schema, dict) else []
    enums = schema.get("enums", {}) if isinstance(schema, dict) else {}

    files = iter_knowledge_files()
    if not files:
        report.error("knowledge/ 下没有 canonical 知识文件")
    external_urls = set()
    for path in files:
        check_file(path, required, enums, report, external_urls)

    check_generated(records, report)
    check_dedup(records, report)
    question_count = check_evals(report)
    if args.check_links:
        check_external_links(external_urls, report)

    for message in report.errors:
        print(f"[ERROR] {message}", file=sys.stderr)
    for message in report.warnings:
        print(f"[WARN] {message}", file=sys.stderr)
    print(f"checked {len(files)} knowledge files, {question_count} golden questions: "
          f"{len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if (args.strict and report.errors) else 0


if __name__ == "__main__":
    sys.exit(main())
