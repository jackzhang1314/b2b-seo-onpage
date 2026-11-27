"""Resolve a registered website delivery and read its page-specific research context."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

from seo_project import index_paths, load_index, local_file, local_path, project_for


def delivery_folder(source: Path) -> Path:
    source = source.resolve()
    if source.is_file() and source.name in {"index.html", "design.html", "workbench-handoff.json", "seo-project-index.json"}:
        source = source.parent
    if not source.is_dir() or not any((source / f).is_file() for f in ("pages.csv", "content-plan.csv")):
        raise ValueError("Use the complete architecture workbench or its index.html together with the companion page tables.")
    return source


def url_key(value: str) -> tuple[str, str, int | None, str, str]:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Expected an absolute planned HTTP(S) URL")
    port = parsed.port
    if port == (443 if parsed.scheme == "https" else 80):
        port = None
    return parsed.scheme, parsed.hostname, port, parsed.path.rstrip("/") or "/", parsed.query


def on_site(url: str, site: str) -> bool:
    address, base = url_key(url), url_key(site)
    return address[:3] == base[:3] and (address[3] == base[3] or address[3].startswith(base[3].rstrip("/") + "/"))


def discover(root: Path | None, url: str | None, market: str | None, language: str | None,
             mode: str | None = None) -> tuple[Path, Path]:
    root = root.resolve() if root else project_for(Path.cwd())
    if not root or not (root / "AGENTS.md").is_file():
        raise ValueError("No website AGENTS.md found. Specify --project-root or a workbench with --source.")
    agents = local_file(root, "AGENTS.md")
    matches: list[Path] = []
    for path in index_paths(root, agents.read_text(encoding="utf-8-sig")):
        entry = load_index(path)
        if any(value and value.casefold() != str(entry[field]).casefold()
               for field, value in (("market", market), ("language", language), ("mode", mode))):
            continue
        if url and not on_site(url, str(entry["site_url"])):
            continue
        matches.append(path)
    if len(matches) != 1:
        candidates = ", ".join(str(path.parent.relative_to(root)) for path in matches)
        raise ValueError(f"Found {len(matches)} matching SEO indexes in {agents}. Select the market, language and mode, "
                         "use --source for the intended workbench, or register a completed architecture delivery."
                         + (f" Matching workbenches: {candidates}" if candidates else ""))
    return root, matches[0]


def indexed_files(index: Path) -> dict[str, Path]:
    entry = load_index(index)
    roles = entry["files"]
    if not isinstance(roles, dict):
        raise ValueError("Invalid SEO index file roles")
    result: dict[str, Path] = {}
    for key, value in roles.items():
        if not isinstance(value, str):
            raise ValueError(f"Invalid indexed path for {key}")
        path = local_path(index.parent, value)
        if path.is_file():
            result[key] = path
    # The native reader also loads these structured tables by conventional filename.
    for name in ("pages.csv", "content-plan.csv", "keyword-decisions.csv", "architecture-plan.json",
                 "validation.json", "design-modules.csv", "design-fields.csv", "product-attributes.csv",
                 "ranking-observations.csv"):
        if (index.parent / name).exists():
            local_file(index.parent, name)
    for role in ("plan", "pages", "library", "decisions"):
        if role not in result:
            raise ValueError(f"SEO project index lacks {role}")
    project = json.loads(result["plan"].read_bytes())["project"]
    if any(entry[k] != project.get(k) for k in ("site_url", "market", "language", "mode")):
        raise ValueError("SEO project index and architecture plan identify different projects or scopes")
    return result


def comparable_pages(path: Path | None, page_id: str, mode: object) -> list[dict[str, str]]:
    if path is None:
        return []
    allowed = {"observed", "partial"}
    if mode == "simulation":
        allowed.add("simulated")
    with path.open(encoding="utf-8-sig", newline="") as infile:
        return [r for r in csv.DictReader(infile) if r.get("page_id") == page_id and r.get("status") in allowed]


def context(root: Path, index: Path, files: dict[str, Path], page: dict[str, str], market: str, language: str,
            peers: list[str], reviews: list[dict[str, str]], date: str | None) -> dict[str, object]:
    from keyword_discovery import ranking_url

    urls = {ranking_url(url): "selected_peer" for url in peers}
    for url in page.get("ranked_urls", "").splitlines():
        if url:
            urls.setdefault(ranking_url(url), "keyword_ranking_url")
    traffic = []
    if "top_pages" in files and urls:
        with files["top_pages"].open(encoding="utf-8-sig", newline="") as source:
            for n, row in enumerate(csv.DictReader(source), 1):
                if (row.get("market", "").casefold(), row.get("language", "").casefold()) != (market.casefold(), language.casefold()):
                    continue
                if date and row.get("observed_at", "")[:10] != date:
                    continue
                match = urls.get(ranking_url(row["url"])) if row.get("url") else None
                if match:
                    traffic.append({**row, "match": match, "report_record": str(n)})
    modules = []
    if page["id"] and "modules" in files:
        with files["modules"].open(encoding="utf-8-sig", newline="") as stream:
            modules = [row for row in csv.DictReader(stream) if row.get("page_id") == page["id"]]
    entry = load_index(index)
    roles = entry["files"]
    originals = entry["originals"]
    if not isinstance(roles, dict) or not isinstance(originals, list):
        raise ValueError("Invalid SEO file inventory")
    checked_originals = []
    for original in originals:
        if not isinstance(original, dict) or not isinstance(original.get("path"), str):
            raise ValueError("Invalid original entry in SEO project index")
        relative = original["path"]
        availability = "catalog_only"
        if relative:
            availability = "included" if local_path(index.parent, relative).is_file() else "missing"
        checked_originals.append({**original, "availability": availability})
    return {"project_root": str(root), "project_entry": "AGENTS.md" if (root / "AGENTS.md").is_file() else "",
            "index": str(index.relative_to(root)),
            "file_base": str(index.parent.relative_to(root)),
            "files": {role: roles[role] for role in files},
            "missing_files": {role: name for role, name in roles.items() if role not in files},
            "originals": checked_originals,
            "market": market, "language": language, "content_modules": modules,
            "comparable_pages": reviews, "page_traffic_observations": traffic}
