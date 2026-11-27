"""Find page candidates in customer exports; keep evidence and existing owners separate."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from architecture_page import in_plan_scope, map_owner, query_key, rows, table_reader, url_key


def ranking_url(value: str) -> tuple[str, str, int | None, str, str]:
    """Preserve path, trailing slash and query for competitor observations."""
    scheme, host, port, _, query = url_key(value)
    return scheme, host, port, urlsplit(value).path or "/", query


RANK_COLUMNS = {
    "url": ("ranking_url", "current url", "url", "landing page", "排名url", "当前url", "排名网址", "竞品排名url"),
    "keyword": ("keyword_original", "keyword", "query", "关键词", "查询词"),
    "keyword_id": ("keyword_id", "关键词id"),
    "market": ("market", "country", "database", "国家", "市场"),
    "language": ("language", "语言"),
    "position": ("position", "current position", "rank", "ranking", "排名", "当前排名", "位置"),
    "date": ("observed_at", "date", "snapshot_date", "report date", "日期", "报告日期", "数据日期", "导出日期"),
}


def ranking_columns(header: Iterable[str]) -> dict[str, str]:
    def label(value: str) -> str:
        return query_key(value).replace(" ", "").replace("_", "")

    labels = {label(name): name for name in header}
    return {key: next((labels[label(n)] for n in choices if label(n) in labels), "") for key, choices in RANK_COLUMNS.items()}


def columns(path: Path) -> dict[str, str]:
    with table_reader(path) as reader:
        return ranking_columns(reader.fieldnames or [])


def page_inventory(page: dict[str, str], decisions: list[dict[str, str]], directory: Path,
                   mapping: Path | None, library: Path | None, market: str, language: str,
                   ranking_files: list[Path], peer_urls: list[str], library_terms: list[str],
                   ranking_date: str | None = None) -> dict[str, object]:
    """One group per normalized phrase. Preserve observations from each original URL/file/row."""
    if ranking_date:
        date.fromisoformat(ranking_date)
    candidates: dict[str, dict[str, list[dict[str, str]]]] = {}
    display: dict[str, str] = {}
    owned: set[str] = set()
    protected: set[str] = set()
    library_by_id: dict[str, set[str]] = defaultdict(set)
    selected_urls = {ranking_url(value): value for value in dict.fromkeys(peer_urls)}
    hits: dict[str, int] = {value: 0 for value in selected_urls.values()}
    unresolved: list[dict[str, str]] = []
    counts: dict[str, int] = {}

    def add(phrase: str, kind: str, record: dict[str, str]) -> str:
        key = query_key(phrase)
        if not key:
            raise ValueError("A selected source row has no keyword")
        display.setdefault(key, phrase)
        candidates.setdefault(key, {}).setdefault(kind, []).append(record)
        return key

    if page.get("primary_keyword"):
        owned.add(add(page["primary_keyword"], "planning", page))
    for row in decisions:
        key = add(row["keyword"], "planning", row)
        owned.add(key)
        if row["disposition"] in {"defer", "exclude"}:
            protected.add(key)

    selected_page_url = url_key(page["url"]) if page.get("url") else None

    owners: dict[str, list[dict[str, str]]] = defaultdict(list)
    owners_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)

    def register_owner(row: dict[str, str], state: str) -> None:
        record = {**row, "ownership": state}
        owners[query_key(row["keyword"])].append(record)
        if row.get("keyword_id"):
            owners_by_id[row["keyword_id"]].append(record)

    if mapping:
        for row in rows(mapping, {"keyword", "market", "language"}, coordinate="input_csv"):
            if (query_key(row["market"]), query_key(row["language"])) != (query_key(market), query_key(language)):
                continue
            state = map_owner(row, page["id"], selected_page_url)
            if state == "here":
                owned.add(add(row["keyword"], "planning", row))
            elif state == "conflict":
                add(row["keyword"], "planning", row)
            if state != "unassigned":
                register_owner(row, state)
    decision_path = directory / "keyword-decisions.csv"
    if decision_path.is_file():
        for row in rows(decision_path, {"page_id", "keyword", "disposition"}):
            if row["page_id"] != page["id"] and in_plan_scope(row, market, language):
                register_owner(row, "elsewhere")

    seeds = list(dict.fromkeys(query_key(t) for t in library_terms if t.strip()))
    if any(not t.strip() for t in library_terms):
        raise ValueError("Empty --library-term")
    patterns = {t: re.compile((r"(?<![a-z0-9])" if t[0].isascii() and t[0].isalnum() else "")
                              + re.escape(t)
                              + (r"(?![a-z0-9])" if t[-1].isascii() and t[-1].isalnum() else "")) for t in seeds}
    if library:
        for row in rows(library, {"keyword_original", "market", "language"}, coordinate="input_csv"):
            if (query_key(row["market"]), query_key(row["language"])) != (query_key(market), query_key(language)):
                continue
            phrase = row["keyword_original"]
            if row.get("keyword_id") and phrase.strip():
                library_by_id[row["keyword_id"]].add(phrase)
            matched = [seed for seed, pattern in patterns.items() if pattern.search(query_key(phrase))]
            if matched:
                add(phrase, "library_matches", {**row, "matched_terms": " | ".join(matched)})

    for path in dict.fromkeys(p.resolve() for p in ranking_files):
        keys = columns(path)
        if not keys["url"] or not (keys["keyword"] or keys["keyword_id"]):
            raise ValueError(f"{path.name} needs a competitor ranking URL and a keyword or keyword_id")
        counts[str(path)] = 0
        for row in rows(path, set(), coordinate="input_csv"):
            counts[str(path)] += 1
            address = row.get(keys["url"], "").strip()
            if not address:
                continue
            try:
                selected = selected_urls.get(ranking_url(address))
            except ValueError:
                continue
            if selected is None:
                continue
            if any(row.get(keys[k], "").strip() and query_key(row[keys[k]]) != query_key(scope)
                   for k, scope in (("market", market), ("language", language))):
                continue
            evidence = {**row, "input_csv_path": str(path), "ranking_url": address,
                        **{f"reported_{k}": row.get(keys[k], "") for k in ("position", "date", "market", "language")}}
            blank_scope = [k for k in ("market", "language") if keys[k] and not row[keys[k]].strip()]
            stamp = row.get(keys["date"], "").strip()
            if blank_scope or (ranking_date and not stamp):
                unresolved.append({**evidence, "issue": "Missing row scope: " + ", ".join(blank_scope or ["date"])})
                continue
            if ranking_date and stamp[:10] != ranking_date:
                continue
            hits[selected] += 1
            inherited = [k for k in ("market", "language") if not row.get(keys[k], "").strip()]
            if inherited:
                evidence["scope_from_file"] = ", ".join(inherited)
            phrase = row.get(keys["keyword"], "").strip()
            kid = row.get(keys["keyword_id"], "")
            phrases = library_by_id.get(kid, set())
            if kid:
                evidence["keyword_id"] = kid
            if not phrase and len({query_key(p) for p in phrases}) == 1:
                phrase = sorted(phrases)[0]
            if not phrase or (phrases and query_key(phrase) not in {query_key(p) for p in phrases}):
                unresolved.append({**evidence, "issue": "Missing or conflicting keyword identity"})
                continue
            add(phrase, "rankings", evidence)

    if library:
        seed_matches = {key for key, evidence in candidates.items() if "library_matches" in evidence}
        for row in rows(library, {"keyword_original", "market", "language"}, coordinate="input_csv"):
            phrase = query_key(row["keyword_original"])
            if phrase in candidates and phrase not in seed_matches and (
                query_key(row["market"]), query_key(row["language"])
            ) == (query_key(market), query_key(language)):
                candidates[phrase].setdefault("library_matches", []).append(row)

    entries: list[dict[str, object]] = []
    for key, evidence_groups in candidates.items():
        other = list(owners.get(key, []))
        candidate_ids = {r["keyword_id"] for group in evidence_groups.values() for r in group if r.get("keyword_id")}
        for kid in sorted(candidate_ids):
            other.extend({**r, "ownership": "conflict"} for r in owners_by_id.get(kid, []) if query_key(r["keyword"]) != key)
        states = {r["ownership"] for r in other}
        if key in protected or "conflict" in states or (key in owned and "elsewhere" in states):
            ownership = "review"
        elif key in owned:
            ownership = "this_page"
        else:
            ownership = "other_page" if "elsewhere" in states else "unassigned"
        entries.append({"keyword": display[key], "assigned": key in owned, "ownership": ownership,
                        "owner_rows": other, **evidence_groups})
    return {"page_id": page["id"], "page_url": page.get("url", ""), "market": market, "language": language,
            "ranking_files_rows_read": counts, "peer_url_matches": hits, "unresolved_ranking_rows": unresolved,
            "library_terms": seeds, "ranking_date": ranking_date, "candidates": entries}
