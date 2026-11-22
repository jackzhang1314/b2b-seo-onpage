"""Read one planned page from the site-architecture Skill's CSV delivery."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator
from unicodedata import normalize
from urllib.parse import urlsplit


def rows(path: Path, required: set[str], *, coordinate: str = "source") -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path.name} lacks required columns: {sorted(required)}")
        for number, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path.name} has an uneven number of fields at record {number}")
            yield {**row, f"{coordinate}_row": str(number), f"{coordinate}_file": path.name}


def url_key(value: str) -> tuple[str, str, int | None, str, str]:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Expected an absolute planned HTTP(S) URL")
    port = parsed.port
    if port == (443 if parsed.scheme == "https" else 80):
        port = None
    return parsed.scheme, parsed.hostname, port, parsed.path.rstrip("/") or "/", parsed.query


def query_key(value: str) -> str:
    return " ".join(normalize("NFC", value).casefold().split())


def in_plan_scope(row: dict[str, str], market: str | None, language: str | None) -> bool:
    return all(not expected or not row.get(key) or query_key(row[key]) == query_key(expected)
               for key, expected in (("market", market), ("language", language)))


def page_keyword_sources(page: dict[str, str], decisions: list[dict[str, str]], mapping: Path,
                         library: Path | None, decision_path: Path, market: str, language: str) -> dict[str, object]:
    """Read a page's assigned groups and original library rows in one market and language."""
    columns = {"keyword_id", "keyword", "target_url", "market", "language"}
    target = url_key(page["url"]) if page.get("url") else None

    def same_scope(row: dict[str, str]) -> bool:
        return query_key(row["market"]) == query_key(market) and query_key(row["language"]) == query_key(language)

    def owner(row: dict[str, str]) -> str:
        page_id = row.get("owner_page_id", "").strip()
        address = row["target_url"].strip()
        id_matches = bool(page_id) and page_id == page["id"]
        url_matches = bool(address and target and url_key(address) == target)
        if page_id and address and target and id_matches != url_matches:
            return "conflict"
        return "here" if id_matches or url_matches else "elsewhere"

    assigned: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    map_rows = 0
    for row in rows(mapping, columns, coordinate="input_csv"):
        map_rows += 1
        if same_scope(row):
            ownership = owner(row)
            if ownership == "here":
                assigned.append(row)
            elif ownership == "conflict":
                review.append(row)

    page_terms = [*decisions, *assigned]
    ids = {r["keyword_id"] for r in page_terms if r.get("keyword_id")}
    if page.get("primary_keyword_id"):
        ids.add(page["primary_keyword_id"])
    phrases = {query_key(r["keyword"]) for r in page_terms if r.get("keyword")}
    phrases_by_id: dict[str, set[str]] = {}
    for record in page_terms:
        if record.get("keyword_id") and record.get("keyword"):
            phrases_by_id.setdefault(record["keyword_id"], set()).add(query_key(record["keyword"]))
    # Keep overlapping assignments to other URLs and deferred rows visible to the editor.
    for row in rows(mapping, columns, coordinate="input_csv"):
        if same_scope(row) and (row["keyword_id"] in ids or query_key(row["keyword"]) in phrases) and owner(row) == "elsewhere":
            review.append(row)

    result: dict[str, object] = {"market": market, "language": language, "keyword_map": str(mapping.resolve()),
                                "map_rows_read": map_rows, "assigned_rows": assigned, "ownership_review": review}
    if decision_path.is_file():
        result["architecture_ownership_review"] = [
            row for row in rows(decision_path, {"page_id", "keyword", "disposition"})
            if (row["page_id"] != page["id"] or row["disposition"] in {"defer", "exclude"})
            and in_plan_scope(row, market, language)
            and (row.get("keyword_id") in ids or query_key(row["keyword"]) in phrases)
        ]
    if library is not None:
        originals: list[dict[str, str]] = []
        phrase_candidates: list[dict[str, str]] = []
        id_phrase_review: list[dict[str, str]] = []
        matched_ids: set[str] = set()
        library_rows = 0
        for row in rows(library, {"keyword_id", "keyword_original", "market", "language"}, coordinate="input_csv"):
            library_rows += 1
            if not same_scope(row):
                continue
            phrase = query_key(row["keyword_original"])
            if row["keyword_id"] in ids:
                expected = phrases_by_id.get(row["keyword_id"])
                if expected and phrase not in expected:
                    id_phrase_review.append(row)
                    continue
                originals.append(row)
                matched_ids.add(row["keyword_id"])
            elif phrase in phrases:
                phrase_candidates.append(row)
        result.update(library=str(library.resolve()), library_rows_read=library_rows,
                      library_matches=originals, exact_phrase_candidates=phrase_candidates,
                      id_phrase_review=id_phrase_review, missing_library_ids=sorted(ids - matched_ids))
    return result


def read_page(directory: Path, url: str | None, page_id: str | None, *, keyword_map: Path | None = None,
              library: Path | None = None, market: str | None = None, language: str | None = None) -> dict[str, object]:
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
            if not in_plan_scope(page, market, language):
                continue
            matched = page["id"] == page_id if page_id else bool(page["url"]) and url_key(page["url"]) == wanted
            if matched:
                matches.append(page)
    if len(matches) != 1:
        raise ValueError(f"Found {len(matches)} matching page rows. Check project, URL and page ID; consult the supplied HTML/Markdown when needed.")
    selected = matches[0]
    project: dict[str, object] = {}
    plan_path = directory / "architecture-plan.json"
    if plan_path.is_file():
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        if not isinstance(plan, dict) or not isinstance(plan.get("project"), dict):
            raise ValueError("architecture-plan.json requires a project object")
        project = {k: plan["project"][k] for k in ("name", "site_url", "market", "language", "mode") if k in plan["project"]}
    if not project.get("mode"):
        gaps.append("架构资料性质未知，需核查来源和确认状态")
    project_market, project_language = project.get("market"), project.get("language")
    target_market = market or selected.get("market") or (project_market if isinstance(project_market, str) else "")
    target_language = language or selected.get("language") or (project_language if isinstance(project_language, str) else "")
    decisions_path = directory / "keyword-decisions.csv"
    decisions: list[dict[str, str]] = []
    if decisions_path.is_file():
        decisions = [r for r in rows(decisions_path, {"page_id", "keyword", "disposition"})
                     if r["page_id"] == selected["id"] and in_plan_scope(r, target_market, target_language)]
    elif keyword_map is None:
        gaps.append("缺少逐词去向，covered_keywords 不能区分整页词、章节词和筛选词")
    validation_path = directory / "validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8-sig")) if validation_path.is_file() else {}
    if not isinstance(validation, dict):
        raise ValueError("validation.json requires an object")
    complete = validation.get("research_complete")
    if complete is not True:
        gaps.append("上游架构研究覆盖不完整或未知")
    result: dict[str, object] = {"source_directory": str(directory.resolve()), "matched_by": "page_id" if page_id else "planned_url",
                                 "project": project, "upstream_research_complete": complete, "page": selected,
                                 "keyword_decisions": decisions, "gaps": gaps}
    if library is not None and keyword_map is None:
        raise ValueError("--library requires --keyword-map for the page-to-group join")
    if keyword_map is not None:
        if not target_market.strip() or not target_language.strip():
            raise ValueError("Supply the map's market and language via the page plan or --market and --language")
        result["planning_inputs"] = page_keyword_sources(selected, decisions, keyword_map, library, decisions_path,
                                                        target_market, target_language)
    return result
