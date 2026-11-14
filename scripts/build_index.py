#!/usr/bin/env python3
"""Generate knowledge/index.md and knowledge/manifest.json from canonical files.

Usage:
    python scripts/build_index.py           # write generated files
    python scripts/build_index.py --check  # verify they are up to date

Only the Python standard library is used. Output is deterministic: the same
knowledge files always produce byte-identical output (no timestamps), so CI can
compare generated files across platforms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
INDEX_PATH = KNOWLEDGE / "index.md"
MANIFEST_PATH = KNOWLEDGE / "manifest.json"


def parse_scalar(text: str):
    """Parse one scalar of the supported YAML subset."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part) for part in inner.split(",")]
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text in ("", "null", "~"):
        return None
    return text


def parse_frontmatter(text: str):
    """Return (frontmatter dict or None, body).

    Supported subset: scalars, quoted strings, inline [a, b] lists, block
    - item lists, booleans, whole-line comments. Nested mappings, multiline
    blocks, anchors and trailing comments are NOT supported.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    data = {}
    last_key = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.lstrip().startswith("- "):
            if last_key is None:
                return None, text
            if not isinstance(data.get(last_key), list):
                data[last_key] = []
            data[last_key].append(parse_scalar(raw.lstrip()[2:]))
            continue
        if ":" not in raw:
            return None, text
        key, value = raw.split(":", 1)
        last_key = key.strip()
        data[last_key] = parse_scalar(value)
    return data, "\n".join(lines[end + 1:])


def iter_knowledge_files():
    """Canonical knowledge files, excluding generated files and docs."""
    excluded = {"index.md", "README.md"}
    return [
        path for path in sorted(KNOWLEDGE.rglob("*.md"))
        if path.name not in excluded and not path.name.startswith("_")
    ]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def body_hash(text: str) -> str:
    _, body = parse_frontmatter(text)
    normalized = "\n".join(line.rstrip() for line in body.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def collect():
    records = []
    for path in iter_knowledge_files():
        text = path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        meta = meta or {}
        default_id = relative(path)[:-3].removeprefix("knowledge/")
        records.append({
            "canonical_id": str(meta.get("canonical_id") or default_id),
            "path": relative(path),
            "title": str(meta.get("title") or path.stem),
            "description": str(meta.get("description") or ""),
            "status": str(meta.get("status") or "draft"),
            "stale_after": str(meta.get("stale_after") or ""),
            "sha256": body_hash(text),
        })
    return records


def render_index(records) -> str:
    lines = [
        "# 知识索引",
        "",
        "> 由 `scripts/build_index.py` 自动生成，禁止手工编辑。",
        "> 新增、修改或删除 `knowledge/` 下的知识文件后，运行 `python scripts/build_index.py`。",
        "",
    ]
    groups = {}
    for record in records:
        cid = record["canonical_id"]
        group = cid.split("/")[0] if "/" in cid else "root"
        groups.setdefault(group, []).append(record)
    for group in sorted(groups):
        lines.append(f"## {group}")
        lines.append("")
        for record in sorted(groups[group], key=lambda item: item["canonical_id"]):
            rel = record["path"].removeprefix("knowledge/")
            due = record["stale_after"] or "未设置"
            lines.append(
                f"- [{record['title']}]({rel}) — {record['description']} "
                f"· `{record['status']}` · 复核 {due}"
            )
        lines.append("")
    lines.append(f"共 {len(records)} 个 canonical 知识文件。")
    lines.append("")
    return "\n".join(lines)


def render_manifest(records) -> str:
    payload = {"version": 1, "count": len(records), "files": records}
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="only verify generated files are up to date")
    args = parser.parse_args()

    records = collect()
    expected = ((INDEX_PATH, render_index(records)),
                (MANIFEST_PATH, render_manifest(records)))

    if args.check:
        stale = [
            relative(path) for path, text in expected
            if not path.exists() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            print("stale generated files: " + ", ".join(stale), file=sys.stderr)
            print("run: python scripts/build_index.py", file=sys.stderr)
            return 1
        print(f"generated files up to date ({len(records)} knowledge files)")
        return 0

    for path, text in expected:
        write_lf(path, text)
    print(f"wrote {relative(INDEX_PATH)} and {relative(MANIFEST_PATH)} "
          f"({len(records)} knowledge files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
