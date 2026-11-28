"""Apply a workbench's saved demand decisions to the current planning rows in memory."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from architecture_page import id_list, in_plan_scope, query_key, rows
from project_sources import indexed_files, on_site, url_key
from seo_project import INDEX

Row = dict[str, str]
Json = dict[str, object]
MOVE_COLUMNS = ["source_page_id", "source_page_url", "source_module_id", "source_disposition", "source_role",
                "source_planning_reason", "target_module_id", "resolution_reason", "resolution_revision_id"]


def strings(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("Expected a list of workbench strings")
    return [str(item) for item in value]


def native_rows(path: Path, market: str, language: str) -> list[Row]:
    if not path.is_file():
        return []
    return [row for row in rows(path, {"page_id", "keyword", "disposition"})
            if in_plan_scope(row, market, language)]


@dataclass
class Demand:
    decisions: list[Row]
    moves: dict[str, Row] = field(default_factory=dict)
    issues: dict[str, list[str]] = field(default_factory=dict)
    _by_query: dict[str, list[Row]] = field(default_factory=dict)

    @classmethod
    def from_workbench(cls, folder: Path, selection: Json, market: str, language: str) -> Demand:
        files = indexed_files(folder / INDEX) if (folder / INDEX).is_file() else {}
        decisions = native_rows(files.get("decisions", folder / "keyword-decisions.csv"), market, language)
        result = cls(decisions)
        pages = selection.get("pages")
        if not isinstance(pages, dict):
            return result
        requested: dict[str, tuple[Json, Json, str, str]] = {}
        for pid, source in pages.items():
            saved = source.get("demand_resolution") or {}
            if source.get("decision") != "skip" or not isinstance(saved, dict) or saved.get("action") != "merge":
                continue
            target_id, module = str(saved.get("target_page_id") or ""), str(saved.get("target_module_id") or "")
            target = pages.get(target_id)
            if (not isinstance(target, dict) or target_id == pid or target.get("decision") not in {"pending", "build"}
                    or not module or module not in strings(target.get("module_ids", []))):
                result.issues.setdefault(pid, []).append("已保存的合并目标或章节现已不可用，请复核工作台。")
                continue
            requested[pid] = (saved, target, target_id, module)
        if not requested:
            return result
        entries: dict[str, Row] = {}
        ambiguous: set[str] = set()
        for row in rows(files.get("pages", folder / "pages.csv"), {"id", "url"}):
            if in_plan_scope(row, market, language):
                if row["id"] in entries:
                    ambiguous.add(row["id"])
                entries[row["id"]] = row
        by_id: dict[str, list[Row]] = defaultdict(list)
        for row in decisions:
            if row.get("keyword_id"):
                by_id[row["keyword_id"]].append(row)

        def same_page(pid: str, handoff: Json) -> bool:
            address = str(handoff.get("url") or "")
            planned = entries.get(pid, {}).get("url")
            return bool(pid not in ambiguous and planned and address and url_key(address) == url_key(planned)
                        and on_site(address, str(selection["site_url"])))

        for source_id, (saved, target, target_id, module) in requested.items():
            source = pages[source_id]
            if (not same_page(source_id, source) or not same_page(target_id, target)
                    or (entries[target_id].get("module_ids") and module not in id_list(entries[target_id]["module_ids"]))):
                result.issues.setdefault(target_id, []).append(f"来源页 {source_id} 的合并与本版规划网址或模块不同。")
                continue
            frozen = set(strings(saved.get("keyword_ids", [])))
            current = set(strings(source.get("assigned_keyword_ids", list(frozen))))
            for kid in sorted(frozen & current):
                matches = by_id.get(kid, [])
                # An ID has to still designate the same query and original owner in this locale.
                if (not matches or {r["page_id"] for r in matches} != {source_id}
                        or len({query_key(r["keyword"]) for r in matches}) != 1
                        or any(r.get("target_url") and url_key(r["target_url"]) != url_key(str(source["url"])) for r in matches)):
                    result.issues.setdefault(target_id, []).append(f"{kid} 的现行原表归属与合并选择不符，保留待核。")
                    continue
                original = matches[0]
                move = {**original, "source_page_id": source_id, "source_page_url": str(source["url"]),
                        "source_module_id": original.get("module_id", ""), "source_disposition": original["disposition"],
                        "source_role": original.get("role", ""), "source_planning_reason": original.get("reason", ""),
                        "resolution_revision_id": str(selection["revision_id"]), "resolution_reason": str(saved.get("reason") or ""),
                        "page_id": target_id, "target_url": str(target["url"]), "module_id": module, "target_module_id": module,
                        "disposition": "section", "role": "section", "reason": str(saved.get("reason") or "")}
                result.moves[kid] = move
                result._by_query.setdefault(query_key(original["keyword"]), []).append(move)
        if result.moves:
            result.decisions = [r for r in decisions if r.get("keyword_id") not in result.moves] + list(result.moves.values())
        return result

    def map_row(self, row: Row) -> Row:
        """A customer map may still refer to the old page. Keep independent owners as conflicts."""
        kid = row.get("keyword_id", "")
        if kid:
            candidates = [self.moves[kid]] if kid in self.moves else []
        else:
            candidates = self._by_query.get(query_key(row["keyword"]), [])
        owner, address = row.get("owner_page_id", ""), row.get("target_url", "")
        matches = [r for r in candidates if query_key(r["keyword"]) == query_key(row["keyword"]) and (owner or address)
                   and (not owner or owner == r["source_page_id"])
                   and (not address or url_key(address) == url_key(r["source_page_url"]))]
        if len(matches) != 1:
            return row
        move = matches[0]
        return {**row, "owner_page_id": move["page_id"], "target_url": move["target_url"], "keyword_id": move["keyword_id"],
                "module_id": move["module_id"], "role": "section", "disposition": "section",
                **{k: move[k] for k in MOVE_COLUMNS}}

    def page_note(self, page: Row, selection: Json) -> Json:
        pid = page["id"]
        pages = selection.get("pages")
        state = pages.get(pid, {}) if isinstance(pages, dict) else {}
        if not any(k in state for k in ("demand_resolution", "business_answer", "onpage_alignment")):
            return {}
        incoming = [r for r in self.moves.values() if r["page_id"] == pid]
        outgoing = [r for r in self.moves.values() if r["source_page_id"] == pid]
        fields = ("keyword_id", "keyword", "page_id", "target_url", "module_id", "source_file", "source_row", *MOVE_COLUMNS)
        note: Json = {"source_directory": selection["workbench"], "revision_id": selection["revision_id"],
                      "page_id": pid, "url": page.get("url", ""), "market": selection["market"], "language": selection["language"],
                      "business_question": state.get("business_question", ""), "business_answer": state.get("business_answer", ""),
                      "module_ids": strings(state.get("module_ids", [])),
                      "demand_resolution": state.get("demand_resolution", {}), "review_after": state.get("onpage_review_after") or "",
                      "incoming": [{k: r.get(k, "") for k in fields} for r in incoming],
                      "outgoing": [{k: r.get(k, "") for k in fields} for r in outgoing], "issues": self.issues.get(pid, [])}
        current_terms = sorted((r.get("keyword_id",""), r["keyword"], r["disposition"], r.get("module_id",""))
                               for r in self.decisions if r["page_id"] == pid)
        review = state.get("revision_review") or {}
        note["revision_review"] = review
        review_terms = {r["keyword_id"]: r["module_id"] for r in incoming}
        if isinstance(review, dict) and review.get("status") == "changed":
            delta = review.get("keyword_changes") or {}
            if isinstance(delta, dict) and delta.get("added_count"):
                examples = {query_key(t) for t in strings(delta.get("added_examples", []))}
                complete = len(examples) == delta["added_count"]
                review_terms.update({r["keyword_id"]: r.get("module_id", "") for r in self.decisions
                                     if r["page_id"] == pid and r.get("keyword_id") and r["disposition"] in {"page", "section", "filter"}
                                     and (not complete or query_key(r["keyword"]) in examples)})
        note["review_terms"] = review_terms
        identity = [note, current_terms, page.get("primary_keyword"), state.get("module_ids"), state.get("decision"),
                    state.get("revision_review"), state.get("business_version")]
        signature = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        return {**note, "scope_sha256": signature, "read_at": datetime.now(timezone.utc).isoformat(),
                "onpage_alignment": state.get("onpage_alignment", "not_reviewed")}

    def page_summary(self, page: Row, note: Json) -> Row:
        incoming = [r for r in self.moves.values() if r["page_id"] == page["id"]]
        outgoing = {query_key(r["keyword"]) for r in self.moves.values() if r["source_page_id"] == page["id"]}
        if not (incoming or outgoing):
            return page
        updated = dict(page)
        retained = {query_key(r["keyword"]) for r in self.decisions if r["page_id"] == page["id"]}
        removed = outgoing - retained
        for key in ("covered_keywords", "section_keywords", "support_keywords"):
            terms = [t for t in page.get(key, "").splitlines() if query_key(t) not in removed]
            seen = {query_key(t) for t in terms}
            if key in {"covered_keywords", "section_keywords"}:
                for r in incoming:
                    if query_key(r["keyword"]) not in seen:
                        terms.append(r["keyword"])
                        seen.add(query_key(r["keyword"]))
            updated[key] = "\n".join(terms)
        if "group_ids" in page:
            remaining_groups = {r.get("group_id") for r in self.decisions if r["page_id"] == page["id"]}
            old_groups = {r.get("group_id") for r in self.moves.values() if r["source_page_id"] == page["id"]}
            groups = [g for g in id_list(page["group_ids"]) if g not in old_groups or g in remaining_groups]
            groups.extend(r["group_id"] for r in incoming if r.get("group_id"))
            updated["group_ids"] = "\n".join(dict.fromkeys(groups))
        primary = page.get("primary_keyword", "")
        kid = page.get("primary_keyword_id", "")
        if (kid in self.moves and self.moves[kid]["source_page_id"] == page["id"]) or (not kid and query_key(primary) in removed):
            note.update(original_primary_keyword=primary, original_primary_keyword_id=kid)
            updated.update(primary_keyword="", primary_keyword_id="")
        return updated

    def modules(self, pid: str, content: list[Row]) -> list[Row]:
        departing = {kid: r for kid, r in self.moves.items() if r["source_page_id"] == pid}
        incoming = [r for r in self.moves.values() if r["page_id"] == pid]
        if not departing and not incoming:
            return content
        result = []
        for module in content:
            ids = strings(json.loads(module.get("keyword_ids") or "[]"))
            terms = strings(json.loads(module.get("keywords") or "[]"))
            if len(ids) != len(terms):
                raise ValueError("Content module keyword IDs and terms do not match")
            kept = {kid: term for kid, term in zip(ids, terms) if kid not in departing}
            for move in incoming:
                if move["module_id"] == module["module_id"]:
                    kept[move["keyword_id"]] = move["keyword"]
            result.append({**module, "keyword_ids": json.dumps(list(kept), ensure_ascii=False),
                           "keywords": json.dumps(list(kept.values()), ensure_ascii=False)})
        return result
