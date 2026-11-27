"""Validate analyst-written research and bind it to local evidence; no SEO inference or network."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from architecture_page import query_key, url_key
from keyword_discovery import ranking_columns, ranking_url


def object_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError("Research expects an object")
    return {str(k): v for k, v in value.items()}


def items(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("Research expects an array")
    return list(value)


def string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Research expects a nonempty string")
    return value


def strings(value: object) -> list[str]:
    return [string(item) for item in items(value)]


def term(value: str) -> str:
    return " ".join(value.split()).casefold()


def url(value: object) -> str:
    text = string(value)
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Research requires an HTTP(S) URL without credentials")
    return text


@dataclass
class ResearchReview:
    status: str
    gaps: list[str]
    sources: list[dict[str, str]]
    keywords: list[dict[str, str]]
    serp: list[dict[str, str]]
    competitors: list[dict[str, str]]
    brief_body: str

    @property
    def brief(self) -> str:
        return self.brief_body + "\n".join(["", f"研究记录状态为 {self.status}", "",
            *[f"- {gap}" for gap in self.gaps], "", "文件与引用已校验。语义和实际覆盖由编辑核对。", ""])


def validate_research(value: object, context: dict[str, object], focus: dict[str, object],
                      base: Path) -> ResearchReview:
    """Check references and coverage declarations, not the truth of supplied observations."""
    research = object_value(value)
    for key in ("target_url", "keyword", "market", "language"):
        if research.get(key) != context.get(key):
            raise ValueError(f"Research context differs: {key}")
    evidence_class = research.get("evidence_class")
    if evidence_class not in {"observed", "simulation"}:
        raise ValueError("Research evidence_class must be observed or simulation")
    gaps = strings(research.get("limitations", []))
    sources: list[dict[str, str]] = []
    kinds: dict[str, str] = {}
    for item in items(research.get("sources")):
        source = object_value(item)
        sid, kind = string(source.get("id")), string(source.get("kind"))
        if sid in kinds or "#" in sid or kind not in {"library", "page_plan", "keyword_group", "serp", "competitor", "business", "site", "gsc"}:
            raise ValueError("Invalid or duplicate research source id/kind")
        kinds[sid] = kind
        path = Path(string(source.get("path"))).expanduser()
        path = (base / path).resolve() if not path.is_absolute() else path.resolve()
        data = path.read_bytes()
        if not data.strip():
            raise ValueError("Research evidence file is empty")
        collected_at = string(source.get("collected_at"))
        datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
        snapshot = {"id": sid, "kind": kind, "path": str(path), "source": string(source.get("source")),
                    "collected_at": collected_at, "sha256": hashlib.sha256(data).hexdigest()}
        if kind == "gsc":
            start = date.fromisoformat(string(source.get("start_date")))
            end = date.fromisoformat(string(source.get("end_date")))
            if start > end:
                raise ValueError("GSC start_date must not follow end_date")
            snapshot.update(page_url=url(source.get("page_url")), start_date=start.isoformat(),
                            end_date=end.isoformat(), filters=string(source.get("filters")))
            if "canonical_ref" in source:
                snapshot["canonical_ref"] = string(source["canonical_ref"])
        sources.append(snapshot)

    def refs(value: object, required_kind: str | None = None) -> list[str]:
        result = strings(value)
        if not result or any(ref.split("#", 1)[0] not in kinds for ref in result):
            raise ValueError("Research references missing or unknown sources")
        if required_kind and not any(kinds[ref.split("#", 1)[0]] == required_kind for ref in result):
            raise ValueError(f"Research requires a {required_kind} evidence reference")
        return result

    gsc_pages: dict[str, set[str]] = {}
    for snapshot in sources:
        if snapshot["kind"] == "gsc":
            pages = {snapshot["page_url"]}
            if "canonical_ref" in snapshot:
                refs([snapshot["canonical_ref"]], "site")
                pages.add(url(context["target_url"]))
            gsc_pages[snapshot["id"]] = pages

    library = object_value(research.get("library"))
    independent = library.get("coverage") == "unavailable" and "unavailable_reason" in library
    if independent:
        gaps.append("未取得用户行业词库：" + string(library["unavailable_reason"]))
        if any(library.get(k) for k in ("source_refs", "source_kinds", "competitors")) or "library" in kinds.values():
            raise ValueError("Independent research cannot claim customer library inputs")
        if not {"serp", "competitor", "gsc"}.intersection(kinds.values()) or not {"site", "business"}.intersection(kinds.values()):
            raise ValueError("Independent research needs observed queries or competitor evidence plus site or business evidence")
    else:
        refs(library.get("source_refs"), "library")
        origins = set(strings(library.get("source_kinds")))
        if not origins <= {"product_terms", "seed_expansion", "competitor_rankings", "customer_curated"} or not origins:
            raise ValueError("Invalid library source_kinds")
        domains = strings(library.get("competitors", []))
        if len({domain.lower().strip() for domain in domains}) != len(domains):
            raise ValueError("Library competitor list contains duplicates")
        if "rank_cutoff" in library:
            cutoff = library["rank_cutoff"]
            if type(cutoff) is not int or cutoff < 1:
                raise ValueError("rank_cutoff is the positive last included ranking position")
        expected = {term(d) for d in strings(library.get("expected_competitors", []))}
        missing = expected - {term(d) for d in domains}
        if missing:
            gaps.append("客户指定清单中尚缺竞品：" + ", ".join(sorted(missing)))
        if "competitor_rankings" in origins and not domains and not library.get("scope_note"):
            gaps.append("竞品排名表的实际来源范围待核")

    def coverage(part: dict[str, object], label: str) -> None:
        if part.get("coverage") not in {"complete", "partial", "unknown", "unavailable"}:
            raise ValueError(f"Invalid {label} coverage")
        if part["coverage"] != "complete":
            gaps.append(f"{label}覆盖：{part['coverage']}")

    coverage(library, "行业词库")
    serp = object_value(research.get("serp"))
    multi = "queries" in serp
    searches = [object_value(item) for item in items(serp["queries"])] if multi else [serp]
    coverage(serp, "SERP")
    if not searches:
        gaps.append("未记录实际搜索查询")
    serp_rows: list[dict[str, str]] = []
    date_by_source = {s["id"]: s["collected_at"] for s in sources}
    for search in searches:
        query = string(search.get("query"))
        provider = string(search.get("source"))
        if multi:
            coverage(search, query)
        actual_market, actual_language = string(search.get("actual_market")), string(search.get("actual_language"))
        if (actual_market, actual_language) != (context.get("market"), context.get("language")):
            gaps.append(f"{query} 的实际市场或语言与本页不符或未核定")
        basis = string(search.get("position_kind", "reported" if not multi else None))
        if basis not in {"google_organic", "provider_order", "unverified", "reported"}:
            raise ValueError("Unknown SERP position_kind")
        positions: set[int] = set()
        for key in ("results", "samples"):
            for item in items(search.get(key, [])):
                row = object_value(item)
                position = row.get("position")
                if key == "results":
                    if basis == "unverified" or type(position) is not int or position < 1 or position in positions:
                        raise ValueError("Use unique positive positions per query, or unranked samples")
                    positions.add(position)
                elif position is not None:
                    raise ValueError("An unranked sample cannot carry a position")
                citations = refs(row.get("evidence_refs"), "serp")
                times = sorted({date_by_source[r.split("#", 1)[0]] for r in citations
                                if kinds[r.split("#", 1)[0]] == "serp"})
                screening = string(row.get("screening", "unreviewed"))
                if screening not in {"candidate", "skip", "unreviewed"}:
                    raise ValueError("Unknown result screening decision")
                reason = string(row.get("screening_reason")) if screening == "skip" else str(row.get("screening_reason", ""))
                serp_rows.append({"query": query, "source": provider, "position_kind": basis if position else "unverified",
                                  "actual_market": actual_market, "actual_language": actual_language,
                                  "collected_at": str(search.get("collected_at") or " | ".join(times)),
                                  "position": str(position or ""), "url": url(row.get("url")),
                                  "title": str(row.get("title", "")), "page_type": string(row.get("page_type")),
                                  "screening": screening, "screening_reason": reason, "evidence_refs": " | ".join(citations)})
        if search.get("coverage") == "complete" and not (search.get("results") or search.get("samples")):
            gaps.append(f"{query} 没有可复查的搜索记录")

    competitors: list[dict[str, str]] = []
    coverage(object_value(research.get("competitor_coverage")), "竞品页面")
    qualified: set[str] = set()
    for item in items(research.get("competitor_pages")):
        page = object_value(item)
        state, page_url = string(page.get("read_state")), url(page.get("url"))
        requested = url(page.get("requested_url", page_url))
        discovery = url(page.get("discovery_url", requested))
        if state not in {"read", "partial", "failed"}:
            raise ValueError("Invalid competitor read_state")
        citations = refs(page.get("evidence_refs"), "competitor" if state != "failed" else None)
        row_out = {"url": page_url, "requested_url": requested, "discovery_url": discovery,
                   "read_state": state, "evidence_refs": " | ".join(citations)}
        for field in ("selection_reason", "observed_strengths", "page_gap", "recommendation"):
            row_out[field] = string(page.get(field))
        if "site_type" in page or multi:
            site_type = string(page.get("site_type"))
            if site_type not in {"export_b2b_independent", "mixed_b2b_page"}:
                raise ValueError("Only a qualified export B2B independent page belongs in competitor_pages; log other results as skip")
            for field in ("company", "business_evidence", "page_type", "discovery_source"):
                row_out[field] = string(page.get(field))
            discovery_source = row_out["discovery_source"]
            if discovery_source not in {"search", "architecture", "customer"}:
                raise ValueError("Invalid competitor discovery_source")
            if discovery_source == "search":
                hits = [hit for hit in serp_rows if hit["url"] == discovery and hit["screening"] != "skip"]
                if not hits:
                    raise ValueError("The discovery_url must be an observed, non-skipped search result")
                row_out["search_observations"] = " | ".join(
                    f"{hit['query']} · {hit['source']} · {hit['position_kind']} {hit['position']} · {hit['evidence_refs']}"
                    for hit in hits)
                if (urlsplit(discovery).hostname or "").removeprefix("www.") != (urlsplit(page_url).hostname or "").removeprefix("www."):
                    row_out["discovery_relation_ref"] = refs([page.get("discovery_relation_ref")], "competitor")[0]
            row_out["site_type"] = site_type
            if state == "read":
                for field in ("seo_title", "h1", "subtitle", "subtitle_tag"):
                    row_out[field] = string(page.get(field))
                row_out["h2"] = "\n".join(strings(page.get("h2")))
                qualified.add(term(row_out["company"]))
        else:
            row_out["site_type"] = "legacy_unclassified"
        if state != "read":
            gaps.append(f"竞品页面未完整读取：{page_url} ({state})")
        competitors.append(row_out)
    if not qualified:
        gaps.append("尚无具备外贸 B2B 身份和页型记录的已读同行")

    brief = object_value(research.get("brief"))
    if brief.get("page_role") != focus.get("page_role"):
        raise ValueError("Research brief page_role differs from confirmed focus")
    lines = [f"# 页面简报 · {context['keyword']}", "", f"页面：{context['target_url']}",
             f"页型：{brief['page_role']}", f"市场/语言：{context['market']} / {context['language']}", ""]
    for key, label in (("architecture_ref", "页面规划"), ("grouping_ref", "关键词分组"), ("library_ref", "行业词库")):
        if key in focus:
            lines.append(f"- {label} · {string(focus[key])}")
    lines.append(f"已读并登记资格的外贸 B2B 同行：{len(qualified)} 家")
    lines.append("")
    for key, label in (("audience", "受众"), ("intent", "搜索意图与页型适配"), ("angle", "本页价值与依据")):
        lines.append(f"{label}：{string(brief.get(key))}")
    modules: set[str] = set()
    for item in items(brief.get("modules")):
        module = object_value(item)
        mid = string(module.get("id"))
        if mid in modules:
            raise ValueError("Duplicate brief module id")
        modules.add(mid)
        lines.extend(["", f"## {mid} · {string(module.get('heading'))}", "",
                      string(module.get("task")), "", "依据：" + " | ".join(refs(module.get("evidence_refs")))])
    if not modules:
        raise ValueError("Full-page research requires concrete brief modules")
    keywords: list[dict[str, str]] = []
    included: set[str] = set()
    seen: set[str] = set()
    observed_candidate = False
    for item in items(research.get("keyword_decisions")):
        decision = object_value(item)
        keyword = string(decision.get("keyword"))
        normalized = term(keyword)
        if normalized in seen:
            raise ValueError("Duplicate candidate keyword; preserve multiple sources in evidence_refs")
        seen.add(normalized)
        choice, origin = string(decision.get("decision")), string(decision.get("origin"))
        if choice not in {"include", "other_page", "exclude", "review"} or origin not in {"library", "planning", "web", "editorial", "gsc"}:
            raise ValueError("Invalid keyword decision/origin")
        citations = refs(decision.get("evidence_refs"), origin if origin in {"library", "gsc"} else None)
        group_ids = strings(decision.get("group_ids", []))
        group_labels = strings(decision.get("group_labels", []))
        planned_role = string(decision["planned_role"]) if "planned_role" in decision else ""
        planned_page = string(decision["planned_page_id"]) if "planned_page_id" in decision else ""
        if origin == "planning" or group_ids or group_labels or planned_role or planned_page:
            if not any(kinds[ref.split("#", 1)[0]] in {"page_plan", "keyword_group"} for ref in citations):
                raise ValueError("Planned keyword roles and groups need a page plan or keyword group reference")
        if multi and origin == "web" and choice == "include":
            skipped = {ref for row in serp_rows if row["screening"] == "skip" for ref in row["evidence_refs"].split(" | ")}
            usable = {ref for row in serp_rows if row["screening"] != "skip" for ref in row["evidence_refs"].split(" | ")}
            if set(citations) <= skipped - usable:
                raise ValueError("Skipped search results cannot be the sole evidence for included web keywords")
        if origin == "web" and any(kinds[ref.split("#", 1)[0]] in {"serp", "competitor"} for ref in citations):
            observed_candidate = True
        targets = strings(decision.get("module_ids", []))
        if not set(targets) <= modules or (choice == "include" and not targets):
            raise ValueError("Included keywords need existing brief module_ids")
        if choice != "include" and targets:
            raise ValueError("Excluded/other-page/unresolved keywords cannot be placed in brief modules")
        if choice == "include":
            included.add(normalized)
        other_target = url(decision["target_url"]) if decision.get("target_url") else ""
        other_role = string(decision["target_page_role"]) if decision.get("target_page_role") else ""
        if (other_target or other_role) and choice != "other_page":
            raise ValueError("Other target URL/role only belongs to an other_page decision")
        metrics = object_value(decision["metrics"]) if "metrics" in decision else {}
        measured_pages = {page for ref in citations for page in gsc_pages.get(ref.split("#", 1)[0], ())}
        if measured_pages and (origin == "gsc" or choice == "include" or "gsc" in metrics):
            target_page = string(context["target_url"])
            if measured_pages.isdisjoint({target_page, other_target}):
                raise ValueError("GSC query evidence must identify the current page or the explicit other_page URL")
            if choice == "include" and target_page in measured_pages:
                observed_candidate = True
        override = ""
        if decision.get("ownership_override_ref"):
            override = refs([decision["ownership_override_ref"]])[0]
            if kinds[override.split("#", 1)[0]] not in {"page_plan", "keyword_group"}:
                raise ValueError("An ownership override needs an approved planning source")
        answer_kind = str(decision.get("answer_kind", ""))
        if answer_kind not in {"", "identity", "detail"}:
            raise ValueError("answer_kind must be identity or detail")
        keywords.append({"keyword": keyword, "origin": origin, "decision": choice, "answer_kind": answer_kind,
                         "keyword_id": string(decision["keyword_id"]) if "keyword_id" in decision else "",
                         "intent_group": str(decision.get("intent_group", "")),
                         "ownership_override_ref": override,
                         "planned_page_id": planned_page, "group_ids": " | ".join(group_ids),
                         "group_labels": " | ".join(group_labels), "planned_role": planned_role,
                         "reason": string(decision.get("reason")), "module_ids": " | ".join(targets),
                         "target_url": other_target, "target_page_role": other_role,
                         "metrics": json.dumps(metrics, ensure_ascii=False) if metrics else "",
                         "evidence_refs": " | ".join(citations)})
    if independent:
        if not observed_candidate:
            raise ValueError("Independent research needs an externally observed candidate or an included GSC query for this page")
    elif not any(row["origin"] == "library" for row in keywords):
        if not library.get("no_match_reason"):
            raise ValueError("Research must evaluate candidates from the industry library")
        gaps.append("用户词库中未找到本页候选：" + string(library["no_match_reason"]))
    for keyword in strings(focus.get("secondary_keywords", [])):
        if term(keyword) not in included:
            raise ValueError("Focus secondary keyword was not included by research")
    if term(string(context.get("keyword"))) not in included:
        gaps.append("已选主词尚未在研究中确认同页适配；保留主词并说明冲突")
    for mid in sorted(modules):
        terms = [row["keyword"] for row in keywords if row["decision"] == "include" and mid in row["module_ids"].split(" | ")]
        lines.extend(["", f"模块 {mid} 选词：{'；'.join(terms) or '无指定关键词，按内容任务表达'}"])
    status = "simulation" if evidence_class == "simulation" else "partial" if gaps else "documented"
    return ResearchReview(status, gaps, sources, keywords, serp_rows, competitors, "\n".join(lines) + "\n")


def check_architecture_target(snapshot: dict[str, object], context: dict[str, object],
                              sources: Sequence[Mapping[str, object]]) -> None:
    page = object_value(snapshot.get("page", {}))
    focus = object_value(context.get("focus", {}))
    same_id = bool(page.get("id")) and page["id"] == focus.get("planned_page_id")
    mapped = str(focus.get("page_url_mapping_ref", "")).split("#", 1)[0]
    verified_mapping = same_id and any(s.get("id") == mapped and s.get("kind") == "page_plan" for s in sources)
    if page.get("url"):
        if url_key(string(page["url"])) != url_key(string(context.get("target_url"))) and not verified_mapping:
            raise ValueError("Architecture page URL differs from the selected page")
    elif snapshot and not same_id:
        raise ValueError("A planned page without a URL requires its confirmed focus.planned_page_id")


def reconcile_inventory(snapshot: dict[str, object], context: dict[str, object], review: ResearchReview,
                        placements: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int | None]]:
    inventory = object_value(snapshot.get("keyword_inventory", {}))
    page = object_value(snapshot.get("page", {}))
    focus = object_value(context.get("focus"))
    check_architecture_target(snapshot, context, review.sources)
    if inventory and (inventory.get("page_id") != page.get("id") or inventory.get("page_url", "") != page.get("url", "")):
        raise ValueError("Inventory belongs to another planned page")
    planned_primary = str(page.get("primary_keyword") or "").strip()
    if planned_primary and query_key(planned_primary) != query_key(string(context.get("keyword"))):
        ref = str(focus.get("primary_override_ref", "")).split("#", 1)[0]
        if not any(s["id"] == ref and s["kind"] in {"page_plan", "keyword_group"} for s in review.sources):
            raise ValueError("A different planned primary keyword requires a confirmed planning reference")
    for name in ("market", "language"):
        observed = inventory.get(name) if inventory else page.get(name)
        if (inventory or observed) and query_key(string(observed)) != query_key(string(context.get(name))):
            raise ValueError(f"Inventory {name} differs from the selected page")
    decisions = {query_key(r["keyword"]): r for r in review.keywords}
    locations: dict[str, list[dict[str, str]]] = {}
    for placement in placements:
        locations.setdefault(query_key(placement["keyword"]), []).append(placement)
    result: list[dict[str, str]] = []
    original_groups: set[str] = set()
    added_groups: set[str] = set()
    drafted_groups: set[str] = set()
    peer_evidence = {ranking_url(row["url"]) for row in review.competitors
                     if row["read_state"] == "read" and row["site_type"] in {"export_b2b_independent", "mixed_b2b_page"}}
    peer_by_ref: dict[str, set[str]] = {}
    peer_by_source: dict[str, set[str]] = {}
    competitor_sources = {src["id"] for src in review.sources if src["kind"] == "competitor"}
    for peer in review.competitors:
        for ref in peer["evidence_refs"].split(" | "):
            sid = ref.split("#", 1)[0]
            if sid in competitor_sources:
                peer_by_ref.setdefault(ref, set()).add(peer["url"])
                peer_by_source.setdefault(sid, set()).add(peer["url"])

    def source_line(record: dict[str, object]) -> str:
        file = record.get("input_csv_path") or record.get("input_csv_file") or record.get("source_file", "")
        number = record.get("input_csv_row") or record.get("source_row", "")
        return f"{file}#{number}" if file else ""

    def ranking_reference(record: dict[str, object]) -> str:
        if "reported_position" in record and "reported_date" in record:
            position, stamp = record["reported_position"], record["reported_date"]
        else:
            raw = ranking_columns(record)
            position, stamp = record.get(raw["position"], ""), record.get(raw["date"], "")
        return f"{source_line(record)} · {record['ranking_url']} · {position} · {stamp}"

    planned = added = covered = retained_additions = 0
    planned_with_text = added_with_text = 0
    checked: set[str] = set()
    candidates = [object_value(v) for v in items(inventory.get("candidates", []))]
    from_inventory = {query_key(string(c.get("keyword"))) for c in candidates}
    candidates.extend({"keyword": row["keyword"], "ownership": "research_only"} for key, row in decisions.items()
                      if key not in from_inventory)
    for candidate in candidates:
        phrase = string(candidate.get("keyword"))
        key = query_key(phrase)
        if key in checked:
            raise ValueError(f"Duplicate inventory keyword: {phrase}")
        checked.add(key)
        decision = decisions.get(key)
        if decision is None:
            raise ValueError(f"Missing inventory decision for: {phrase}")
        ownership = string(candidate.get("ownership"))
        assigned = candidate.get("assigned") is True
        if decision["decision"] == "include" and ownership in {"other_page", "review"} and not decision["ownership_override_ref"]:
            raise ValueError(f"Existing ownership needs review before inclusion: {phrase}")
        uses = locations.get(key, [])
        if key in from_inventory and decision["decision"] == "include" and not uses:
            raise ValueError(f"Included inventory keyword needs an actual placement or an explained not_used: {phrase}")
        ranking_rows = [object_value(r) for r in items(candidate.get("rankings", []))]
        if ranking_rows and not assigned and decision["decision"] == "include":
            qualified_url = any(ranking_url(string(r["ranking_url"])) in peer_evidence for r in ranking_rows)
            if not qualified_url and not any(object_value(r).get("matched_terms") for r in items(candidate.get("library_matches", []))):
                raise ValueError(f"Rank-only addition needs the qualified peer's actual reviewed URL: {phrase}")
        group = decision["intent_group"].strip()
        states = {r["copy_state"] for r in uses if r["location"] != "not_used"}
        has_text = bool(states)
        required = set(decision["module_ids"].split(" | ")) - {""}
        def answering(accepted: set[str]) -> set[str]:
            return {r["module_id"] for r in uses if r["answer_state"] in accepted and r["module_id"]}
        ready_modules = answering({"ready", "preserved_snapshot_text"})
        draft_modules = ready_modules | answering({"blocked"})
        placed = bool(required) and required <= ready_modules
        complete_draft = bool(required) and required <= draft_modules
        if decision["decision"] != "include" and has_text:
            raise ValueError(f"Placement contradicts the keyword decision: {phrase}")
        if assigned:
            planned += 1
            planned_with_text += int(has_text)
            covered += int(placed)
            original_groups.add(group)
        elif has_text:
            added_with_text += 1
            if complete_draft:
                drafted_groups.add(group)
            if placed:
                added += 1
                retained_additions += int(required <= answering({"preserved_snapshot_text"}))
                added_groups.add(group)
        if placed:
            copy_status = "placed"
        elif complete_draft:
            copy_status = "draft_pending_confirmation"
        elif has_text:
            copy_status = "incomplete_answer"
        else:
            copy_status = "content_gap" if decision["decision"] == "include" else "not_placed"
        def values(column: str) -> str:
            return "\n".join(dict.fromkeys(r[column] for r in uses if r[column]))
        citations = set(decision["evidence_refs"].split(" | "))
        source_ids = {ref.split("#", 1)[0] for ref in citations}
        observed_pages = {address for ref in citations for address in peer_by_ref.get(ref, set())
                          if len(peer_by_ref[ref]) == 1}
        observed_pages.update(address for sid in source_ids for address in peer_by_source.get(sid, set())
                              if len(peer_by_source[sid]) == 1)
        final_placements = "\n".join(f"{r['location']} · {r['module_id']} · {r['change_id'] or r['block_id']} → "
                                     f"{r['answer_ref'] or '待补答案'} · {r['answer_state']}" for r in uses if r["location"] != "not_used")
        pool = ("planned" if assigned else "library_or_rankings" if key in from_inventory or decision["origin"] == "library"
                else "planning_record" if decision["origin"] == "planning" else "research_only")
        planning = [object_value(r) for r in items(candidate.get("planning", []))]
        def planned_values(column: str, original: str) -> str:
            entries = decision[column].split(" | ") + [str(r[original]) for r in planning if r.get(original)]
            return " | ".join(dict.fromkeys(value for value in entries if value))
        result.append({"keyword": phrase, "assigned": str(assigned).lower() if key in from_inventory else "", "ownership": ownership,
                       "source_pool": pool, "final_placements": final_placements,
                       "keyword_id": planned_values("keyword_id", "keyword_id"), "group_ids": planned_values("group_ids", "group_id"),
                       "planned_role": planned_values("planned_role", "disposition"), "group_labels": planned_values("group_labels", "group_label"),
                       "planned_page_id": decision["planned_page_id"] or (str(page.get("id", "")) if assigned else ""),
                       "origin": decision["origin"], "metrics": decision["metrics"],
                       "observed_peer_urls": " | ".join(sorted(u for u in observed_pages if ranking_url(u) in peer_evidence)),
                       "required_modules": decision["module_ids"], "missing_answers": " | ".join(sorted(required - draft_modules)),
                       **{column: values(column) for column in ("module_id", "design_module_id", "block_id", "final_text", "answer_ref",
                           "answer_text", "answer_state", "field_ids", "attribute_ids", "design_refs")},
                       "decision": decision["decision"], "intent_group": group, "reason": decision["reason"],
                       "copy_status": copy_status, "copy_states": " | ".join(sorted(states)),
                       "locations": " | ".join(dict.fromkeys(r["location"] for r in uses)),
                       "expressions": " | ".join(dict.fromkeys(r["expression"] for r in uses if r["expression"])),
                       "planning_refs": " | ".join(source_line(r) for r in planning),
                       "library_refs": " | ".join(source_line(object_value(r)) for r in items(candidate.get("library_matches", []))),
                       "peer_urls": " | ".join(dict.fromkeys(string(r["ranking_url"]) for r in ranking_rows)),
                       "ranking_refs": "\n".join(ranking_reference(r) for r in ranking_rows),
                       "owners": " | ".join(dict.fromkeys(str(r.get("target_url") or r.get("owner_page_id") or r.get("page_id") or "")
                                           for r in (object_value(v) for v in items(candidate.get("owner_rows", []))))),
                       "other_target": decision["target_url"] or decision["target_page_role"],
                       "evidence_refs": decision["evidence_refs"]})
    def distinct_new(groups: set[str]) -> int | None:
        if not inventory or groups and ("" in original_groups or "" in groups):
            return None
        return len(groups - original_groups)

    return result, {"planned_terms": planned if inventory else None, "evaluated_planned_terms": planned if inventory else None, "planned_with_text": planned_with_text,
                    "placed_planned_terms": covered, "added_with_text": added_with_text, "added_placed_terms": added,
                    "already_in_copy": retained_additions, "new_copy_terms": added - retained_additions,
                    "draft_added_intents": distinct_new(drafted_groups), "added_intents": distinct_new(added_groups)}
