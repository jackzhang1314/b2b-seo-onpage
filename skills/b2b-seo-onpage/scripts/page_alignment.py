"""Tie current-workbench requirements to the body text that answers them."""
from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path

from architecture_page import query_key
from onpage_research import object_value, string, strings
from page_copy import PageCopy, records
from project_sources import url_key

Json = dict[str, object]


def brief_addendum(note: Json) -> str:
    if not note:
        return ""
    lines = ["", "## 本版工作台的业务答复与章节归属", ""]
    if note.get("business_answer"):
        lines.append(f"企业答复：{note['business_answer']}")
    for direction, label in (("incoming", "并入本页"), ("outgoing", "转交其他页面")):
        for move in records(note.get(direction, [])):
            lines.append(f"- {label}：{move['keyword']} · {move['source_page_id']} → {move['page_id']} / "
                         f"{move['target_module_id']} · {move['resolution_reason']}")
    if note.get("onpage_alignment") == "needs_review":
        lines.append("本版已有内容待核对。可用正式页面中对应章节的原句说明它是否已经回答该需求。")
    return "\n".join(lines) + "\n" if len(lines) > 3 else ""


def check_answers(architecture: Json, plan: Json, evidence: Json, page: PageCopy,
                  placements: list[dict[str, str]]) -> Json:
    note = object_value(architecture.get("workbench_demand", {}))
    if not note:
        return {}
    required = object_value(note["review_terms"])
    owned = {str(r["keyword_id"]): str(r["keyword"]) for r in records(architecture.get("keyword_decisions", [])) if r.get("keyword_id")}
    modules = {str(m["module_id"]): str(m.get("name") or "") for m in
               records(object_value(architecture.get("project_context", {})).get("content_modules", []))}
    labels = {**{mid: str(m.get("name") or "") for mid, m in page.design["modules"].items()}, **modules}
    allowed_modules = set(strings(note.get("module_ids", []))) or set(labels)
    observed = records(evidence.get("headings", []))
    blocks = {b.key: b for b in page.blocks}
    section_owners: dict[str, set[str]] = {}
    ancestors: list[tuple[str, set[str]]] = []
    for heading in (b for b in page.blocks if b.kind in {"h1", "h2", "h3", "h4", "h5", "h6"}):
        while ancestors and ancestors[-1][0] >= heading.kind:
            ancestors.pop()
        name = query_key(heading.text)
        matches = {mid for mid, label in labels.items() if label and query_key(label) == name}
        if 0 < heading.heading <= len(observed):
            anchor = str(observed[heading.heading - 1].get("id") or "")
            if anchor in allowed_modules:
                matches.add(anchor)
        for local, module in page.modules.items():
            if ((heading.heading and module.get("source_heading_index") == heading.heading)
                    or query_key(str(module["heading"])) == name):
                matches.add(page.design_id(local) or local)
        if heading.change and heading.module:
            matches.add(page.design_id(heading.module) or heading.module)
        if not matches and ancestors and ancestors[-1][0] != "h1":
            matches = ancestors[-1][1]
        section_owners[heading.key] = matches
        ancestors.append((heading.kind, matches))
    proofs: list[Json] = []
    addressed: set[str] = set()
    business = False

    def attach(ref: str, quote: str, mid: str, kids: list[str], why: str, answers_business: bool,
               section_heading: str = "", section_reason: str = "") -> None:
        nonlocal business
        block = page.changed.get(ref) or blocks.get(ref)
        if not block or block.kind != "body" or block.state not in {"ready", "preserved_snapshot_text"}:
            raise ValueError(f"Workbench evidence must refer to a usable final body paragraph: {ref}")
        heading = blocks.get(block.section)
        if not heading or not quote.strip() or query_key(quote) not in query_key(block.text):
            raise ValueError("Workbench quotation is missing from the specified section paragraph")
        owners = section_owners.get(heading.key, set())
        if owners:
            mapped = owners == {mid}
        else:
            mapped = bool(section_reason.strip() and section_heading.strip()
                          and query_key(section_heading) == query_key(heading.text))
        if mid not in allowed_modules or not mapped:
            raise ValueError("Workbench quotation belongs to a different or unidentified module")
        if any(k not in owned or (required.get(k) and required[k] != mid) for k in kids):
            raise ValueError("Workbench quotation names a keyword outside its confirmed page or section")
        if answers_business and not note.get("business_answer"):
            raise ValueError("No current business answer to acknowledge")
        addressed.update(kids)
        business |= answers_business
        proofs.append({"module_id": mid, "heading": heading.text, "block_ref": ref, "quote": quote, "keyword_ids": kids,
                       "business_answer_checked": answers_business, "reason": why, "section_reason": section_reason, "state": block.state})

    for finding in records(plan.get("workbench_answers", [])):
        marked = finding.get("business_answer_checked", False)
        if type(marked) is not bool:
            raise ValueError("business_answer_checked must be a boolean")
        attach(string(finding.get("block_ref")), string(finding.get("quote")), string(finding.get("module_id")),
               strings(finding.get("keyword_ids", [])), string(finding.get("reason")), marked,
               string(finding["section_heading"]) if "section_heading" in finding else "",
               string(finding["section_reason"]) if "section_reason" in finding else "")
    by_term: dict[str, list[str]] = {}
    for kid in required:
        if kid in owned:
            by_term.setdefault(query_key(owned[kid]), []).append(kid)
    for placement in placements:
        mid = placement.get("design_module_id") or placement.get("module_id", "")
        kids = [k for k in by_term.get(query_key(placement["keyword"]), []) if k not in addressed and required[k] in ("", mid)]
        if kids and placement.get("answer_state") in {"ready", "preserved_snapshot_text"}:
            ref = placement["answer_ref"]
            paragraph = page.changed.get(ref) or blocks.get(ref)
            if paragraph and paragraph.kind == "body" and paragraph.section:
                attach(ref, placement["answer_text"], mid, kids, placement["reason"], False)
    missing = sorted(set(required) - addressed)
    gaps = list(strings(note.get("issues", [])))
    if missing:
        gaps.append("待核实本页指定章节中的答案：" + "、".join(owned.get(k, k) for k in missing))
    if note.get("business_answer") and not business:
        gaps.append("尚未将企业答复与相关章节的具体内容核对。")
    if (not plan.get("changes") or note.get("onpage_alignment") == "needs_review") and not proofs:
        gaps.append("核对本版内容需要本页正文中的原句、所在小节和复核结论。")
    return {"scope_sha256": note["scope_sha256"], "status": "needs_review" if gaps else "aligned",
            "answers": proofs, "gaps": gaps}


def time_with_zone(value: object) -> datetime:
    stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Workbench evidence needs an ISO timestamp with a UTC offset")
    return stamp


def confirmed_capture(snapshot: Json, architecture: Json, plan: Json, owner: Json) -> str:
    capture = object_value(snapshot.get("capture", {}))
    note = object_value(architecture["workbench_demand"])
    targets = [note["url"], snapshot.get("target_url"), capture.get("final_url"), plan["target_url"]]
    if (snapshot.get("content_stage") not in {"source_html", "browser_dom", "tool_raw_html"}
            or capture.get("http_status") != 200 or len({url_key(str(address or "")) for address in targets}) != 1
            or any(query_key(str(snapshot.get(k, ""))) != query_key(str(note[k])) for k in ("market", "language"))):
        raise ValueError("Reviewed needs the current page's actual successful front-end capture in this locale")
    path = object_value(snapshot["input"])
    if hashlib.sha256(Path(str(path["path"])).read_bytes()).hexdigest() != path["sha256"]:
        raise ValueError("Captured HTML changed after inspection")
    stamp = string(capture.get("retrieved_at"))
    when = time_with_zone(stamp)
    since = owner.get("onpage_review_after")
    if not since and note.get("onpage_alignment") == "needs_review":
        since = note.get("read_at")
    cutoffs = [since, *(e["occurred_at"] for e in records(owner.get("history", [])) if e.get("status") == "published")]
    if any(v and when < time_with_zone(v) for v in cutoffs):
        raise ValueError("The evidence predates this revision's changes or a later publication; read the actual page again")
    return stamp


def check_front_answers(report: Json, snapshot: Json) -> None:
    headings = records(snapshot.get("headings", []))
    blocks = records(snapshot.get("content_blocks", []))
    for proof in records(report.get("answers", [])):
        indexes = {str(i) for i, heading in enumerate(headings, 1) if heading.get("content_scope") != "navigation"
                   and query_key(str(heading.get("text", ""))) == query_key(str(proof["heading"]))}
        if len(indexes) != 1 or not any(str(b["heading_index"]) in indexes
                                        and query_key(str(proof["quote"])) in query_key(str(b["text"])) for b in blocks):
            raise ValueError("The approved business or transferred-keyword answer is missing from its public section")
