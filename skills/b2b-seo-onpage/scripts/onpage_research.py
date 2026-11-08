"""Validate analyst-written research and bind it to local evidence; no SEO inference or network."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


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
    brief: str


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
        if sid in kinds or "#" in sid or kind not in {"library", "serp", "competitor", "business", "site"}:
            raise ValueError("Invalid or duplicate research source id/kind")
        kinds[sid] = kind
        path = Path(string(source.get("path"))).expanduser()
        path = (base / path).resolve() if not path.is_absolute() else path.resolve()
        data = path.read_bytes()
        if not data.strip():
            raise ValueError("Research evidence file is empty")
        date = string(source.get("collected_at"))
        datetime.fromisoformat(date.replace("Z", "+00:00"))
        sources.append({"id": sid, "kind": kind, "path": str(path), "source": string(source.get("source")),
                        "collected_at": date, "sha256": hashlib.sha256(data).hexdigest()})

    def refs(value: object, required_kind: str | None = None) -> list[str]:
        result = strings(value)
        if not result or any(ref.split("#", 1)[0] not in kinds for ref in result):
            raise ValueError("Research references missing or unknown sources")
        if required_kind and not any(kinds[ref.split("#", 1)[0]] == required_kind for ref in result):
            raise ValueError(f"Research requires a {required_kind} evidence reference")
        return result

    library = object_value(research.get("library"))
    refs(library.get("source_refs"), "library")
    origins = set(strings(library.get("source_kinds")))
    if not origins <= {"seed_expansion", "competitor_rankings"} or not origins:
        raise ValueError("Invalid library source_kinds")
    if origins != {"seed_expansion", "competitor_rankings"}:
        gaps.append("行业词库未覆盖种子扩展与竞品排名两类来源")
    domains = strings(library.get("competitors"))
    if len({domain.lower().strip() for domain in domains}) != len(domains):
        raise ValueError("Library competitor list contains duplicates")
    if len(domains) < 20:
        gaps.append(f"行业词库仅登记 {len(domains)} 家竞品，未达到 Top 20 覆盖")
    if type(library.get("rank_cutoff")) is not int or library["rank_cutoff"] != 30:
        raise ValueError("Library rank_cutoff must be position 30, not 30 keywords")

    def coverage(part: dict[str, object], label: str) -> None:
        if part.get("coverage") not in {"complete", "partial", "unknown", "unavailable"}:
            raise ValueError(f"Invalid {label} coverage")
        if part["coverage"] != "complete":
            gaps.append(f"{label}覆盖：{part['coverage']}")

    coverage(library, "行业词库")
    serp = object_value(research.get("serp"))
    coverage(serp, "SERP")
    string(serp.get("source"))
    if serp.get("query") != context.get("keyword"):
        raise ValueError("SERP query differs from selected primary keyword")
    for key in ("market", "language"):
        if string(serp.get("actual_" + key)) != context.get(key):
            gaps.append(f"SERP 实际{key}与目标不一致或未核定")
    serp_rows: list[dict[str, str]] = []
    positions: set[int] = set()
    for item in items(serp.get("results")):
        row = object_value(item)
        position = row.get("position")
        if type(position) is not int or not 1 <= position <= 10 or position in positions:
            raise ValueError("SERP needs distinct observed organic positions 1-10; use partial for unranked samples")
        positions.add(position)
        serp_rows.append({"position": str(position), "url": url(row.get("url")),
                          "title": str(row.get("title", "")),
                          "page_type": string(row.get("page_type")),
                          "evidence_refs": " | ".join(refs(row.get("evidence_refs"), "serp"))})
    if positions != set(range(1, 11)):
        gaps.append(f"SERP 仅登记 {len(positions)} 个前十自然位置")
    for item in items(serp.get("samples", [])):
        row = object_value(item)
        serp_rows.append({"position": "", "url": url(row.get("url")),
                          "title": str(row.get("title", "")),
                          "page_type": string(row.get("page_type")),
                          "evidence_refs": " | ".join(refs(row.get("evidence_refs"), "serp"))})
    if serp.get("samples"):
        gaps.append("存在未核定排名的搜索样本，未作为前十位置计数")

    competitors: list[dict[str, str]] = []
    read_urls: set[str] = set()
    coverage(object_value(research.get("competitor_coverage")), "竞品页面")
    for item in items(research.get("competitor_pages")):
        page = object_value(item)
        state, page_url = string(page.get("read_state")), url(page.get("url"))
        requested_url = url(page.get("requested_url", page_url))
        if state not in {"read", "partial", "failed"}:
            raise ValueError("Invalid competitor read_state")
        citations = refs(page.get("evidence_refs"), "competitor" if state != "failed" else None)
        if state == "read":
            read_urls.add(page_url)
            read_urls.add(requested_url)
        else:
            gaps.append(f"竞品页面未完整读取：{page_url} ({state})")
        competitor_row = {"url": page_url, "requested_url": requested_url,
                          "read_state": state, "evidence_refs": " | ".join(citations)}
        for key in ("selection_reason", "observed_strengths", "page_gap", "recommendation"):
            competitor_row[key] = string(page.get(key))
        competitors.append(competitor_row)
    if not read_urls.intersection(row["url"] for row in serp_rows):
        gaps.append("没有完整读取过的 SERP 代表页面")

    brief = object_value(research.get("brief"))
    if brief.get("page_role") != focus.get("page_role"):
        raise ValueError("Research brief page_role differs from confirmed focus")
    lines = [f"# 页面简报 · {context['keyword']}", "", f"页面：{context['target_url']}",
             f"页型：{brief['page_role']}", f"市场/语言：{context['market']} / {context['language']}", ""]
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
    for item in items(research.get("keyword_decisions")):
        decision = object_value(item)
        keyword = string(decision.get("keyword"))
        normalized = term(keyword)
        if normalized in seen:
            raise ValueError("Duplicate candidate keyword; preserve multiple sources in evidence_refs")
        seen.add(normalized)
        choice, origin = string(decision.get("decision")), string(decision.get("origin"))
        if choice not in {"include", "other_page", "exclude", "review"} or origin not in {"library", "web", "editorial"}:
            raise ValueError("Invalid keyword decision/origin")
        citations = refs(decision.get("evidence_refs"), "library" if origin == "library" else None)
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
        keywords.append({"keyword": keyword, "origin": origin, "decision": choice,
                         "reason": string(decision.get("reason")), "module_ids": " | ".join(targets),
                         "target_url": other_target, "target_page_role": other_role,
                         "metrics": json.dumps(metrics, ensure_ascii=False) if metrics else "",
                         "evidence_refs": " | ".join(citations)})
    if not any(row["origin"] == "library" for row in keywords):
        raise ValueError("Research must evaluate candidates from the industry library")
    for keyword in strings(focus.get("secondary_keywords", [])):
        if term(keyword) not in included:
            raise ValueError("Focus secondary keyword was not included by research")
    if term(string(context.get("keyword"))) not in included:
        gaps.append("已选主词尚未在研究中确认同页适配；保留主词并说明冲突")
    for mid in sorted(modules):
        terms = [row["keyword"] for row in keywords if row["decision"] == "include" and mid in row["module_ids"].split(" | ")]
        lines.extend(["", f"模块 {mid} 选词：{'；'.join(terms) or '无指定关键词，按内容任务表达'}"])
    status = "simulation" if evidence_class == "simulation" else "partial" if gaps else "documented"
    lines.extend(["", f"研究记录状态：{status}", "", *[f"- {gap}" for gap in gaps], "",
                  "文件与引用已校验；不自动证明来源真实、覆盖无遗漏、语义正确、上线或排名提升。"])
    return ResearchReview(status, gaps, sources, keywords, serp_rows, competitors, "\n".join(lines) + "\n")
