"""Read one planned page from the site-architecture Skill's CSV delivery."""
from __future__ import annotations

from contextlib import contextmanager
import csv
import json
import re
from pathlib import Path
from typing import Iterator
from unicodedata import normalize
from urllib.parse import urlsplit
from project_sources import comparable_pages, context as project_context, indexed_files


@contextmanager
def table_reader(path: Path) -> Iterator[csv.DictReader[str]]:
    with path.open("rb") as raw:
        encoding = "utf-16" if raw.read(2) in {b"\xff\xfe", b"\xfe\xff"} else "utf-8-sig"
    with path.open(encoding=encoding, newline="") as stream:
        first = stream.readline()
        stream.seek(0)
        try:
            delimiter = csv.Sniffer().sniff(first, delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","
        yield csv.DictReader(stream, delimiter=delimiter)


def rows(path: Path, required: set[str], *, coordinate: str = "source") -> Iterator[dict[str, str]]:
    with table_reader(path) as reader:
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


def map_owner(row: dict[str, str], page_id: str, target: tuple[str, str, int | None, str, str] | None) -> str:
    owner_id = row.get("owner_page_id", "").strip()
    address = row.get("target_url", "").strip()
    by_id = bool(owner_id) and owner_id == page_id
    by_url = bool(address and target and url_key(address) == target)
    if owner_id and address and target and by_id != by_url:
        return "conflict"
    if by_id or by_url:
        return "here"
    return "elsewhere" if owner_id or address else "unassigned"


def page_keyword_sources(page: dict[str, str], decisions: list[dict[str, str]], mapping: Path,
                         library: Path | None, decision_path: Path, market: str, language: str) -> dict[str, object]:
    """Read a page's assigned groups and original library rows in one market and language."""
    columns = {"keyword", "market", "language"}
    target = url_key(page["url"]) if page.get("url") else None

    def same_scope(row: dict[str, str]) -> bool:
        return query_key(row["market"]) == query_key(market) and query_key(row["language"]) == query_key(language)

    assigned: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    map_rows = 0
    for row in rows(mapping, columns, coordinate="input_csv"):
        map_rows += 1
        if same_scope(row):
            ownership = map_owner(row, page["id"], target)
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
        if same_scope(row) and (row.get("keyword_id") in ids or query_key(row["keyword"]) in phrases) and map_owner(row, page["id"], target) in {"elsewhere", "unassigned"}:
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
        for row in rows(library, {"keyword_original", "market", "language"}, coordinate="input_csv"):
            library_rows += 1
            if not same_scope(row):
                continue
            phrase = query_key(row["keyword_original"])
            if row.get("keyword_id") in ids:
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


def id_list(value: str) -> list[str]:
    """List cells in architecture exports use newlines; normalized customer tables may use separators."""
    return [part.strip() for part in re.split(r"[\n,;|]", value) if part.strip()]


def page_design(directory: Path, page: dict[str, str], market: str, language: str) -> dict[str, object]:
    template = page.get("template_id", "")
    page_id = page["id"]
    offerings = set(id_list(page.get("offering_ids", "")))
    gaps: list[str] = []

    def selected_rows(name: str) -> Iterator[dict[str, str]]:
        path = directory / (name + ".csv")
        if not path.is_file():
            return
        for row in rows(path, {"id"}):
            if not in_plan_scope(row, market, language):
                continue
            if row.get("page_id") and row["page_id"] != page_id:
                continue
            if row.get("variants") and page.get("variant", "") not in id_list(row["variants"]):
                continue
            if row.get("offering_ids") and offerings.isdisjoint(id_list(row["offering_ids"])):
                continue
            yield row

    def this_template(row: dict[str, str]) -> bool:
        return (row.get("template_id") == template and bool(template)
                or row.get("page_id") == page_id and not row.get("template_id"))

    modules = [row for row in selected_rows("design-modules") if this_template(row)]
    modules.sort(key=lambda row: int(row["order"]) if row.get("order", "").isdigit() else 10**9)
    linked_fields = {fid for module in modules for fid in id_list(module.get("field_ids", ""))}
    attributes: list[dict[str, str]] = []
    for row in selected_rows("product-attributes"):
        bindings = json.loads(row.get("detail_bindings") or "[]")
        if not isinstance(bindings, list) or not all(isinstance(b, dict) for b in bindings):
            raise ValueError(f"Invalid detail_bindings at {row['source_file']} row {row['source_row']}")
        detail = [b for b in bindings if template and b.get("template_id") == template
                  and (not b.get("page_id") or b["page_id"] == page_id)]
        catalog = page_id in id_list(row.get("filter_page_ids", ""))
        if catalog or detail or row.get("page_id") == page_id:
            attrs = {**row, "page_usage": " | ".join(kind for kind, applies in
                     (("filter", catalog), ("detail", bool(detail)), ("page", row.get("page_id") == page_id)) if applies),
                     "page_detail_fields": "\n".join(str(b["field_id"]) for b in detail if b.get("field_id"))}
            attributes.append(attrs)
            linked_fields.update(id_list(attrs["page_detail_fields"]))
    module_table = (directory / "design-modules.csv").is_file()
    fields = [row for row in selected_rows("design-fields")
              if (this_template(row) and (not module_table or row.get("page_id") == page_id or row["id"] in linked_fields)
                  or row.get("template_id") == "SITE" and row["id"] in linked_fields)]
    missing = linked_fields - {row["id"] for row in fields}
    if missing:
        gaps.append("模块或产品属性引用了未取得的字段：" + "、".join(sorted(missing)))
    for label, selected in (("module", modules), ("field", fields), ("attribute", attributes)):
        ids = [row["id"] for row in selected]
        if not all(ids) or len(set(ids)) != len(ids):
            raise ValueError(f"Ambiguous {label} IDs for planned page {page_id}")
    return {"modules": modules, "fields": fields, "attributes": attributes, "gaps": gaps}


def read_page(directory: Path, url: str | None, page_id: str | None, *, keyword_map: Path | None = None,
              library: Path | None = None, market: str | None = None, language: str | None = None,
              ranking_files: list[Path] | None = None, peer_urls: list[str] | None = None,
              library_terms: list[str] | None = None, ranking_date: str | None = None,
              registered: tuple[Path, Path] | None = None) -> dict[str, object]:
    if bool(url) == bool(page_id):
        raise ValueError("Select exactly one planned URL or page ID")
    wanted = url_key(url) if url else None
    matches: list[dict[str, str]] = []
    gaps: list[str] = []
    files = indexed_files(registered[1]) if registered else {}
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
    if any((directory / name).is_file() for name in ("design-modules.csv", "design-fields.csv", "product-attributes.csv")):
        result["page_design"] = page_design(directory, selected, target_market, target_language)
    if registered:
        reviews = comparable_pages(files.get("comparables"), selected["id"], project.get("mode"))
        peer_urls = peer_urls if peer_urls is not None else list(dict.fromkeys(r["url"] for r in reviews))
        library = library or files["library"]
        if peer_urls and not ranking_files and "rankings" in files:
            ranking_files = [files["rankings"]]
        result["project_context"] = project_context(*registered, files, selected, target_market, target_language,
                                                    peer_urls, reviews, ranking_date)
    if ranking_files and not peer_urls:
        raise ValueError("--rankings requires at least one qualified --peer-url")
    if library_terms and not library:
        raise ValueError("--library-term requires --library")
    if keyword_map is not None:
        if not target_market.strip() or not target_language.strip():
            raise ValueError("Supply the map's market and language via the page plan or --market and --language")
        result["planning_inputs"] = page_keyword_sources(selected, decisions, keyword_map, library, decisions_path,
                                                        target_market, target_language)
    if keyword_map or library or peer_urls or decisions:
        from keyword_discovery import columns as ranking_columns, page_inventory

        sources = list(ranking_files or [])
        if peer_urls and not sources:
            upstream = directory / "ranking-observations.csv"
            if upstream.is_file():
                sources.append(upstream)
            elif library and ranking_columns(library)["url"]:
                sources.append(library)
            else:
                gaps.append("没有可按同行 URL 反查的排名明细")
        if (sources or library) and not (target_market and target_language):
            raise ValueError("Specify the market and language of the keyword inputs")
        result["keyword_inventory"] = page_inventory(selected, decisions, directory, keyword_map, library,
                                                     target_market, target_language, sources, peer_urls or [],
                                                     library_terms or [], ranking_date)
    return result
