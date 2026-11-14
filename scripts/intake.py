#!/usr/bin/env python3
"""Conversational intake pipeline for heer_evalKB (Plan 3).

Usage:
    python scripts/intake.py add <url-or-path>... [--title T] [--type T]
    python scripts/intake.py status
    python scripts/intake.py promote <inbox_id> --category C --owner O [options]
    python scripts/intake.py pr <inbox_id> [--branch B] [--base main]

`add` snapshots the raw material under sources/ (immutable) and produces a
draft under inbox/<id>/. Extraction success does NOT mean admission: the
inbox entry gets one of four states (digested / needs-review / ignored /
unsupported). `promote` turns a digested entry into a canonical draft under
knowledge/, rebuilds the index and runs the strict gates. `pr` commits the
promoted entry on a kb/ branch, pushes it and prints the PR creation link.
The script never merges and never pushes to main. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_lib
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from build_index import ROOT, parse_frontmatter

SOURCES = ROOT / "sources"
INBOX = ROOT / "inbox"
KNOWLEDGE = ROOT / "knowledge"

STATES = ("digested", "needs-review", "ignored", "unsupported", "promoted")
TYPE_DEFAULT = "Method"
STALE_DAYS_DEFAULT = 180
REPO_URL = "https://github.com/He0627/heer_evalKB"

MARKDOWN_EXTS = {".md", ".markdown"}
TEXT_EXTS = {".txt"}
HTML_EXTS = {".html", ".htm"}
TABLE_EXTS = {".csv", ".tsv"}
JSON_EXTS = {".json"}
UNSUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".png",
                    ".jpg", ".jpeg", ".webp", ".gif", ".zip", ".exe", ""}

SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_RE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
HEADING_TAG_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.S | re.I)


def write_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str, fallback: str = "doc") -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text or "").strip("-").lower()
    return slug[:48] or fallback


def new_inbox_id(slug: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slug}"


def existing_source_for(digest: str) -> str | None:
    for path in sorted(SOURCES.rglob("*")):
        if path.is_file():
            with path.open("rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() == digest:
                    return path.relative_to(ROOT).as_posix()
    return None


def fetch_url(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "heer_evalKB-intake"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
    if "html" in content_type:
        return raw, ".html"
    if "json" in content_type:
        return raw, ".json"
    if "csv" in content_type:
        return raw, ".csv"
    if "text/plain" in content_type:
        return raw, ".txt"
    if url.lower().endswith((".md", ".markdown", ".txt", ".csv", ".tsv", ".json")):
        return raw, Path(url).suffix.lower()
    return raw, ".html"


# ---------------------------------------------------------------- normalizers

def normalize_markdown(text: str, title: str) -> str:
    meta, body = parse_frontmatter(text)
    body = (body or text).strip()
    if not re.search(r"^#\s+", body, re.M):
        body = f"# {title}\n\n{body}"
    return body + "\n"


def normalize_text(text: str, title: str) -> str:
    return f"# {title}\n\n{text.strip()}\n"


def normalize_html(text: str, title: str) -> str:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    extracted = html_lib.unescape(title_match.group(1)).strip() if title_match else ""
    work = SCRIPT_STYLE_RE.sub("", text)
    work = re.sub(r"<head\b[^>]*>.*?</head>", "", work, flags=re.S | re.I)

    def heading(match):
        level, inner = int(match.group(1)), html_lib.unescape(match.group(2)).strip()
        return f"\n\n{'#' * level} {inner}\n\n"

    work = HEADING_TAG_RE.sub(heading, work)
    work = ANCHOR_RE.sub(lambda m: f"[{html_lib.unescape(m.group(2)).strip()}]({m.group(1)})", work)
    work = re.sub(r"<li\b[^>]*>", "\n- ", work, flags=re.I)
    work = re.sub(r"<(p|div|br|tr|table|ul|ol|section|article)\b[^>]*>", "\n\n", work, flags=re.I)
    work = TAG_RE.sub("", work)
    work = html_lib.unescape(work)
    lines = [line.strip() for line in work.splitlines()]
    blocks, buffer, items = [], [], []

    def flush_buffer():
        if buffer:
            blocks.append(" ".join(buffer))
            buffer.clear()

    def flush_items():
        if items:
            blocks.append("\n".join(items))
            items.clear()

    for line in lines:
        if line.startswith("- "):
            flush_buffer()
            items.append(line)
        elif line:
            flush_items()
            buffer.append(line)
        else:
            flush_buffer()
            flush_items()
    flush_buffer()
    flush_items()
    body = "\n\n".join(blocks).strip()
    h1_count = len(re.findall(r"^# ", body, re.M))
    if h1_count == 0:
        heading_title = extracted or title
        body = f"# {heading_title}\n\n{body or '（正文抽取为空，需人工补充）'}"
    return body + "\n"


def normalize_table(path: Path, title: str, snapshot: str) -> str:
    delimiter = "\t" if path.suffix == ".tsv" else ","
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        body = "（空表格）"
    else:
        width = max(len(row) for row in rows)
        padded = [row + [""] * (width - len(row)) for row in rows]
        cells = lambda row: " | ".join(cell.strip().replace("|", "\\|") for cell in row)
        lines = ["| " + cells(padded[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
        lines += ["| " + cells(row) + " |" for row in padded[1:51]]
        body = "\n".join(lines)
        if len(padded) > 51:
            body += f"\n\n（仅预览前 50 行，完整表格见 `{snapshot}`）"
    return (f"# {title}\n\n表格已按结构保存到 `{snapshot}`。"
            f"结构化数据留在原文，不要在 Markdown 里手工维护全量数据。\n\n{body}\n")


def normalize_json(data, title: str, snapshot: str) -> str:
    if isinstance(data, dict):
        body = "\n".join(f"- `{key}`: {type(value).__name__}" for key, value in data.items())
        summary = f"顶层字段 {len(data)} 个：\n\n{body}"
    elif isinstance(data, list):
        summary = f"顶层数组，共 {len(data)} 项。"
    else:
        summary = f"顶层标量：{data!r}"
    return f"# {title}\n\n原文快照见 `{snapshot}`。\n\n{summary}\n"


# --------------------------------------------------------------------- add

def cmd_add(args) -> int:
    results = []
    for raw_input in args.inputs:
        results.append(add_one(raw_input, args))
    failures = [item for item in results if item["state"] not in ("digested", "ignored")]
    for item in results:
        print(f"[{item['state']}] {item['inbox_id']}: {item['message']}")
    return 1 if failures else 0


def add_one(raw_input: str, args) -> dict:
    is_url = raw_input.startswith(("http://", "https://"))
    title = args.title
    if is_url:
        slug = slugify(title or raw_input.split("//", 1)[1].split("/")[0], "url")
    else:
        path = Path(raw_input).expanduser()
        if not path.is_file():
            return make_entry(raw_input, None, "needs-review", None, None,
                              f"本地文件不存在: {raw_input}")
        slug = slugify(title or path.stem, path.stem)

    inbox_id = new_inbox_id(slug)
    try:
        if is_url:
            raw, ext = fetch_url(raw_input)
            source_location = raw_input
        else:
            raw = path.read_bytes()
            ext = path.suffix.lower()
            source_location = str(path.resolve())
    except Exception as exc:
        return make_entry(inbox_id, raw_input, "needs-review", None, None,
                          f"抓取/读取失败: {type(exc).__name__}: {exc}")

    digest = hashlib.sha256(raw).hexdigest()
    reused = existing_source_for(digest)
    if reused:
        snapshot = reused
        note = f"原文与已有快照 {reused} 逐字节相同，复用不重存"
    else:
        snapshot = (SOURCES / f"{date.today().strftime('%Y%m%d')}-{slug}{ext}").relative_to(ROOT).as_posix()
        write_bytes(ROOT / snapshot, raw)
        note = f"原文快照已存 {snapshot}"

    if ext in UNSUPPORTED_EXTS:
        state, message = "unsupported", f"{ext or '无扩展名'} 需先归一化：PDF/Office 视为编译产物，先转 Markdown，表格转 CSV/JSON，图片配等价文字"
        return make_entry(inbox_id, raw_input, state, snapshot, digest, message)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            state = "needs-review"
            return make_entry(inbox_id, raw_input, state, snapshot, digest,
                              "无法按 UTF-8 解码，转人工处理")

    resolved_title = title or slug.replace("-", " ").title() or "Untitled"
    if ext in MARKDOWN_EXTS:
        body = normalize_markdown(text, resolved_title)
        h1 = re.search(r"^#\s+(.+)$", body, re.M)
        resolved_title = h1.group(1).strip() if h1 else resolved_title
    elif ext in HTML_EXTS:
        body = normalize_html(text, resolved_title)
    elif ext in TABLE_EXTS:
        body = normalize_table(Path(ROOT / snapshot), resolved_title, snapshot)
    elif ext in JSON_EXTS:
        body = normalize_json(json.loads(text), resolved_title, snapshot)
    elif ext in TEXT_EXTS:
        body = normalize_text(text, resolved_title)
    else:
        return make_entry(inbox_id, raw_input, "unsupported", snapshot, digest,
                          f"未登记的扩展名 {ext}")

    inbox_dir = INBOX / inbox_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    write_lf(inbox_dir / "draft.md", body)
    metadata = {
        "inbox_id": inbox_id,
        "state": "digested",
        "created_at": now_iso(),
        "source": {
            "kind": "url" if is_url else "file",
            "location": source_location,
            "retrieved_at": now_iso(),
            "sha256": digest,
            "snapshot": snapshot,
            "reused_snapshot": bool(reused),
        },
        "draft": "draft.md",
        "proposed": {"title": resolved_title, "type": args.type},
        "message": note,
    }
    write_lf(inbox_dir / "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return {"inbox_id": inbox_id, "state": "digested",
            "message": f"{note}；草稿 inbox/{inbox_id}/draft.md"}


def make_entry(inbox_id, source, state, snapshot, digest, message):
    inbox_dir = INBOX / inbox_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "inbox_id": inbox_id,
        "state": state,
        "created_at": now_iso(),
        "source": {"kind": "url" if str(source).startswith(("http://", "https://")) else "file",
                   "location": str(source), "retrieved_at": now_iso(),
                   "sha256": digest or "", "snapshot": snapshot or ""},
        "draft": "",
        "proposed": {},
        "message": message,
    }
    write_lf(inbox_dir / "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return {"inbox_id": inbox_id, "state": state, "message": message}


def write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


# ------------------------------------------------------------------ status

def iter_entries():
    for meta_path in sorted(INBOX.glob("*/metadata.json")):
        try:
            yield meta_path.parent, json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue


def cmd_status(_args) -> int:
    entries = list(iter_entries())
    if not entries:
        print("inbox/ 为空，暂无待准入材料。")
        return 0
    print(f"{'inbox_id':<32} {'state':<14} title / source")
    for _folder, meta in entries:
        source = meta.get("source", {}).get("location", "")
        title = meta.get("proposed", {}).get("title") or source
        print(f"{meta.get('inbox_id', '?'):<32} {meta.get('state', '?'):<14} {title}")
    states = {}
    for _folder, meta in entries:
        states[meta.get("state", "?")] = states.get(meta.get("state", "?"), 0) + 1
    print(f"共 {len(entries)} 条：" +
          ", ".join(f"{key}={value}" for key, value in sorted(states.items())))
    return 0


# ----------------------------------------------------------------- promote

def cmd_promote(args) -> int:
    entry = find_entry(args.inbox_id)
    if entry is None:
        print(f"找不到 inbox 条目 {args.inbox_id}", file=sys.stderr)
        return 1
    folder, meta = entry
    if meta.get("state") != "digested":
        print(f"{args.inbox_id} 状态为 {meta.get('state')}，只有 digested 可 promote", file=sys.stderr)
        return 1

    draft_path = folder / "draft.md"
    if not draft_path.is_file():
        print(f"缺少 {draft_path}", file=sys.stderr)
        return 1
    body = draft_path.read_text(encoding="utf-8")

    proposed = meta.get("proposed", {})
    source = meta.get("source", {})
    title = args.title or proposed.get("title") or folder.name
    doc_type = args.type or proposed.get("type") or TYPE_DEFAULT
    slug = slugify(title)
    if not slug or slug == "doc":
        print("标题无法生成有效文件名，请用 --title 指定", file=sys.stderr)
        return 1
    target = KNOWLEDGE / args.category / f"{slug}.md"
    if target.exists():
        print(f"目标已存在 {target.relative_to(ROOT)}，请换 --title 或建 supersedes 版本链", file=sys.stderr)
        return 1

    retrieved_at = source.get("retrieved_at") or now_iso()
    source_url = source.get("location") if str(source.get("location", "")).startswith("http") \
        else (source.get("snapshot") or "")
    stale_after = args.stale_after or (date.today() + timedelta(days=STALE_DAYS_DEFAULT)).isoformat()

    frontmatter = [
        "---",
        f"type: {doc_type}",
        f"title: \"{title.replace('\"', '')}\"",
        f"description: \"{(args.description or f'{title}（intake 草稿，待人工复核）').replace('\"', '')}\"",
        f"source_url: {source_url}",
        f"retrieved_at: {retrieved_at}",
        f"owner: {args.owner}",
        "status: draft",
        f"stale_after: {stale_after}",
    ]
    if args.tags:
        frontmatter.append(f"tags: [{args.tags}]")
    frontmatter.append("---")

    target.parent.mkdir(parents=True, exist_ok=True)
    write_lf(target, "\n".join(frontmatter) + "\n\n" + body)
    print(f"已生成 {target.relative_to(ROOT)}（status: draft）")

    run([sys.executable, str(ROOT / "scripts" / "build_index.py")], "build_index")
    ok, output = run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--strict"],
                     "validate --strict", capture=True)
    if not ok:
        print(output)
        print("校验未通过，知识文件已保留，请修正后重试；详情如上。", file=sys.stderr)
        update_state(folder, meta, "needs-review", output.strip())
        return 1

    update_state(folder, meta, "promoted",
                 f"promoted to knowledge/{args.category}/{slug}.md at {now_iso()}")
    print(f"{args.inbox_id} 已提升为 canonical 草稿，校验通过。")
    print(f"下一步: python scripts/intake.py pr {args.inbox_id}")
    return 0


def find_entry(inbox_id):
    folder = INBOX / inbox_id
    meta_path = folder / "metadata.json"
    if meta_path.is_file():
        try:
            return folder, json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    for candidate, meta in iter_entries():
        if meta.get("inbox_id") == inbox_id or candidate.name == inbox_id:
            return candidate, meta
    return None


def update_state(folder: Path, meta: dict, state: str, message: str) -> None:
    meta["state"] = state
    meta["message"] = message
    if state == "promoted":
        meta.setdefault("knowledge", {})
    write_lf(folder / "metadata.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def run(command, label, capture=False):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if not capture:
        print(output)
    return result.returncode == 0, output


# ---------------------------------------------------------------------- pr

def cmd_pr(args) -> int:
    entry = find_entry(args.inbox_id)
    if entry is None:
        print(f"找不到 inbox 条目 {args.inbox_id}", file=sys.stderr)
        return 1
    folder, meta = entry
    if meta.get("state") != "promoted" or not meta.get("message", "").startswith("promoted to"):
        print(f"{args.inbox_id} 尚未 promote，先运行 promote", file=sys.stderr)
        return 1

    knowledge_rel = meta["message"].split("promoted to ", 1)[1].split(" at ", 1)[0]
    branch = args.branch or f"kb/intake-{slugify(meta.get('proposed', {}).get('title', args.inbox_id))}"
    base = args.base

    ok, output = run(["git", "rev-parse", "--verify", branch], "check branch", capture=True)
    if ok:
        print(f"分支 {branch} 已存在，拒绝覆盖", file=sys.stderr)
        return 1
    run(["git", "checkout", "-b", branch], "create branch")
    paths = [
        meta.get("source", {}).get("snapshot", ""),
        f"inbox/{folder.name}/",
        knowledge_rel,
        "knowledge/index.md",
        "knowledge/manifest.json",
    ]
    for rel in filter(None, paths):
        run(["git", "add", rel], f"add {rel}")
    run(["git", "commit", "-m",
         f"docs: intake {meta.get('proposed', {}).get('title', args.inbox_id)}"],
        "commit", capture=False)
    ok, _ = run(["git", "push", "-u", "origin", branch], "push")
    if not ok:
        print("推送失败，分支与文件已留在本地", file=sys.stderr)
        return 1

    compare = f"{REPO_URL}/compare/{base}...{branch}" if base and base != branch \
        else f"{REPO_URL}/pull/new/{branch}"
    print(f"\n分支 {branch} 已推送。开 PR：{compare}")
    print("Agent 不合并 PR；由 owner 评审合并。")
    return 0


# ------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="抓取 URL 或读取本地文件，进入 inbox")
    add.add_argument("inputs", nargs="+", help="URL 或本地文件路径")
    add.add_argument("--title", help="覆盖标题（默认从内容推导）")
    add.add_argument("--type", default=TYPE_DEFAULT, help="frontmatter type")
    add.set_defaults(func=cmd_add)

    status = sub.add_parser("status", help="列出 inbox 条目与状态")
    status.set_defaults(func=cmd_status)

    promote = sub.add_parser("promote", help="把 digested 条目提升为 canonical 草稿")
    promote.add_argument("inbox_id")
    promote.add_argument("--category", required=True, help="knowledge/ 下的分类目录")
    promote.add_argument("--owner", required=True, help="责任人 GitHub 用户名")
    promote.add_argument("--title")
    promote.add_argument("--type")
    promote.add_argument("--description")
    promote.add_argument("--tags", help="逗号分隔，如 eval,retrieval")
    promote.add_argument("--stale-after", help="YYYY-MM-DD，默认 180 天后")
    promote.set_defaults(func=cmd_promote)

    pr = sub.add_parser("pr", help="为 promoted 条目建分支、提交并推送")
    pr.add_argument("inbox_id")
    pr.add_argument("--branch")
    pr.add_argument("--base", default="", help="PR 基分支（默认用 pull/new 链接）")
    pr.set_defaults(func=cmd_pr)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
