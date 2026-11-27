"""Enumerate the selected workbench's page owners. This inventory never writes to WordPress."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from architecture_page import in_plan_scope, rows
from commercial_headings import page_role
from project_sources import indexed_files, on_site, url_key
from seo_project import INDEX

UrlKey = tuple[str, str, int | None, str, str]
Target = tuple[UrlKey, str, str]

COLUMNS = ["page_id", "page_name", "url", "page_type", "primary_keyword", "parent_id", "action", "approval",
           "market", "language", "source", "source_row", "heading_policy", "next_step",
           "revision_id", "decision", "seo_decision", "progress", "cms_record", "backend_readback", "frontend_readback", "issue"]


def heading_policy(kind: str) -> str:
    role = page_role(kind)
    if role in {"home", "category", "product"}:
        return "title_and_h1"
    return "classify" if role == "unknown" else "by_intent"


def attach_site_inventory(path: Path, scope: dict[str, str], queue: list[dict[str, str]],
                          targets: dict[Target, list[int]]) -> None:
    if not scope["site_url"]:
        raise ValueError("A site inventory needs the website URL in the selected workbench")
    for row in rows(path, {"url", "page_type", "cms_record", "status"}):
        if row["status"] != "publish" or not in_plan_scope(row, scope["market"], scope["language"]):
            continue
        address = row["url"].strip()
        if not on_site(address, scope["site_url"]) or "#" in address:
            continue
        market = row.get("market") or scope["market"]
        language = row.get("language") or scope["language"]
        key = (url_key(address), market.casefold(), language.casefold())
        indexes = targets.setdefault(key, [])
        if not indexes:
            job = dict.fromkeys(COLUMNS, "")
            job.update(page_name=row.get("page_name", ""), url=address, page_type=row["page_type"], market=market,
                       language=language, source=path.name, source_row=row["source_row"], action="unplanned",
                       heading_policy=heading_policy(row["page_type"]), next_step="research_unplanned_url", progress="pending")
            indexes.append(len(queue))
            queue.append(job)
        for i in indexes:
            job = queue[i]
            record = row["cms_record"].strip()
            known_roles = {page_role(job["page_type"]), page_role(row["page_type"])} - {"unknown"}
            if not record or (job["cms_record"] and record != job["cms_record"]):
                job["issue"] = "公开网址对应的 WordPress 记录待核"
            elif len(known_roles) > 1:
                job["issue"] = "实际页型与规划不同，核实对应页面"
            else:
                job["cms_record"] = record
    count = Counter(job["cms_record"] for job in queue if job["cms_record"])
    for job in queue:
        if job["cms_record"] and count[job["cms_record"]] > 1:
            job["issue"] = "多个网址对应同一 WordPress 记录，先核正式地址"
        if job["issue"]:
            job["next_step"] = "resolve_target"


def site_queue(folder: Path, market: str | None, language: str | None,
               site_inventory: Path | None = None) -> tuple[dict[str, str], list[dict[str, str]]]:
    index = folder / INDEX
    files = indexed_files(index) if index.is_file() else {}
    plan = files.get("plan", folder / "architecture-plan.json")
    project = json.loads(plan.read_bytes())["project"] if plan.is_file() else {}
    scope = {k: str(project.get(k) or "") for k in ("site_url", "market", "language", "mode")}
    if any(want and scope[k] and want.casefold() != scope[k].casefold() for k, want in (("market", market), ("language", language))):
        raise ValueError("Requested market/language does not match the workbench")
    scope["market"] = market or scope["market"]
    scope["language"] = language or scope["language"]
    queue: list[dict[str, str]] = []
    url_rows: dict[Target, list[int]] = {}
    ids: Counter[str] = Counter()
    for filename in ("pages.csv", "content-plan.csv"):
        if not (folder / filename).is_file():
            continue
        for row in rows(folder / filename, {"id", "page_type"}):
            if not in_plan_scope(row, scope["market"], scope["language"]):
                continue
            pid, url = row["id"], row.get("url", "").strip()
            row_market, row_language = row.get("market") or scope["market"], row.get("language") or scope["language"]
            issue = ""
            if url:
                try:
                    key = url_key(url)
                    if scope["site_url"] and not on_site(url, scope["site_url"]):
                        issue = "网址在所选站点范围之外"
                    if "#" in url:
                        issue = "锚点需映射到实际页面记录"
                    url_rows.setdefault((key, row_market.casefold(), row_language.casefold()), []).append(len(queue))
                except ValueError:
                    issue = "需核对完整网址"
            else:
                issue = "先按规划行改稿，实施需核实实际网址"
            ids[pid] += 1
            queue.append({"page_id": pid, "page_name": row.get("name") or row.get("name_en", ""), "url": url,
                          "page_type": row["page_type"], "primary_keyword": row.get("primary_keyword", ""),
                          "parent_id": row.get("parent_id", ""), "action": row.get("page_action", ""),
                          "approval": row.get("approval", ""), "market": row_market, "language": row_language,
                          "source": filename, "source_row": row["source_row"], "issue": issue,
                          "heading_policy": heading_policy(row["page_type"]),
                          "next_step": "research_and_draft", "progress": "pending", "cms_record": "",
                          "backend_readback": "", "frontend_readback": ""})
    duplicates = {i for positions in url_rows.values() if len(positions) > 1 for i in positions}
    for i, job in enumerate(queue):
        if ids[job["page_id"]] > 1 or not job["page_id"] or i in duplicates:
            job["issue"] = "页面编号或目标网址的归属待核，核清后只处理一次"
        if job["issue"]:
            job["next_step"] = "resolve_target"
    if site_inventory:
        attach_site_inventory(site_inventory, scope, queue, url_rows)
    return scope, queue
