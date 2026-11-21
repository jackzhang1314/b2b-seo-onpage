"""Read one planned page from the site-architecture Skill's CSV delivery."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit


def rows(path: Path, required: set[str]) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path.name} lacks required columns: {sorted(required)}")
        for number, row in enumerate(reader, 2):
            yield {**row, "source_row": str(number), "source_file": path.name}


def url_key(value: str) -> tuple[str, str, int | None, str, str]:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Expected an absolute planned HTTP(S) URL")
    port = parsed.port
    if port == (443 if parsed.scheme == "https" else 80):
        port = None
    return parsed.scheme, parsed.hostname, port, parsed.path.rstrip("/") or "/", parsed.query


def read_page(directory: Path, url: str | None, page_id: str | None) -> dict[str, object]:
    if bool(url) == bool(page_id):
        raise ValueError("Select exactly one planned URL or page ID")
    wanted = url_key(url) if url else None
    matches: list[dict[str, str]] = []
    gaps: list[str] = []
    for name in ("pages.csv", "content-plan.csv"):
        path = directory / name
        if not path.is_file():
            gaps.append(f"未提供 {name}")
            continue
        columns = {"id", "page_type"} if page_id else {"id", "url", "page_type"}
        for page in rows(path, columns):
            matched = page["id"] == page_id if page_id else bool(page["url"]) and url_key(page["url"]) == wanted
            if matched:
                matches.append(page)
    if len(matches) != 1:
        raise ValueError(f"Found {len(matches)} matching page rows. Check project, URL and page ID; consult the supplied HTML/Markdown when needed.")
    selected = matches[0]
    decisions_path = directory / "keyword-decisions.csv"
    decisions: list[dict[str, str]] = []
    if decisions_path.is_file():
        decisions = [r for r in rows(decisions_path, {"page_id", "keyword", "disposition"}) if r["page_id"] == selected["id"]]
    else:
        gaps.append("缺少逐词去向，covered_keywords 不能区分整页词、章节词和筛选词")
    project: dict[str, object] = {}
    plan_path = directory / "architecture-plan.json"
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        if not isinstance(plan, dict) or not isinstance(plan.get("project"), dict):
            raise ValueError("architecture-plan.json requires a project object")
        project = {k: plan["project"][k] for k in ("name", "site_url", "market", "language", "mode") if k in plan["project"]}
    if not project.get("mode"):
        gaps.append("架构资料性质未知，需核查来源和确认状态")
    validation_path = directory / "validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8-sig")) if validation_path.is_file() else {}
    if not isinstance(validation, dict):
        raise ValueError("validation.json requires an object")
    complete = validation.get("research_complete")
    if complete is not True:
        gaps.append("上游架构研究覆盖不完整或未知")
    return {"source_directory": str(directory.resolve()), "matched_by": "page_id" if page_id else "planned_url",
            "project": project, "upstream_research_complete": complete, "page": selected,
            "keyword_decisions": decisions, "gaps": gaps}
