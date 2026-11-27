"""Check the team's commercial-page heading contract against final copy or a separate capture."""
from __future__ import annotations

import re
from unicodedata import normalize

from page_copy import Block, records
from onpage_research import object_value, strings

ROLES = {
    "home": {"home", "homepage", "home_page", "front_page", "首页", "网站首页"},
    "category": {"category", "category_overview", "collection", "product_category", "product_collection",
                 "category_page", "collection_page", "产品集合页", "产品类目页", "分类页", "产品分类页"},
    "product": {"product", "product_detail", "product_detail_page", "product_page", "model", "model_detail",
                "sku", "pdp", "attachment", "产品详情页", "型号页", "产品页"},
    "other": {"other", "article", "blog", "blog_category", "guide", "company", "about", "about_us", "resource",
              "utility", "inquiry", "contact", "application", "application_hub", "capability", "service",
              "service_page", "support", "文章", "博客", "公司介绍", "联系页", "应用页", "服务页"},
}
# The evidence may establish additional sector- or language-specific buying expressions.
COMMON = ("supplier", "suppliers", "manufacturer", "manufacturers", "factory", "factories",
          "wholesale", "wholesaler", "wholesalers", "bulk", "custom", "customized", "customised",
          "oem", "odm", "private label", "for dealers", "for distributors", "for resellers",
          "for trade buyers", "供应商", "制造商", "厂家", "工厂", "批发", "定制")
NON_BUYING = re.compile(r"\bfactory[ -]+(?:automation|settings|reset)\b|\bbulk[ -]+(?:density|modulus)\b", re.I)


def page_role(value: object) -> str:
    key = re.sub(r"[\s-]+", "_", str(value or "").strip().casefold())
    return next((role for role, names in ROLES.items() if key in names), "unknown")


def normalized(text: str) -> str:
    return re.sub(r"[\s\-‐‑–—]+", " ", normalize("NFKC", text).casefold()).strip()


def spans(phrase: str, text: str) -> list[tuple[int, int]]:
    needle = normalized(phrase)
    if not needle:
        return []
    # Latin/numeric words have boundaries. CJK text can use the phrase in unspaced copy.
    first = r"(?<![^\W_])" if needle[0].isascii() and needle[0].isalnum() else ""
    last = r"(?![^\W_])" if needle[-1].isascii() and needle[-1].isalnum() else ""
    return [m.span() for m in re.finditer(first + re.escape(needle) + last, text)]


def buy_spans(phrase: str, text: str) -> list[tuple[int, int]]:
    if normalized(phrase) in {"customer", "customers", "客户"}:
        return []
    excluded = [m.span() for m in NON_BUYING.finditer(text)]
    return [(a, b) for a, b in spans(phrase, text) if not any(x <= a and b <= y for x, y in excluded)]


def audit(plan: dict[str, object], blocks: list[Block], architecture: dict[str, object]) -> dict[str, object]:
    focus = object_value(plan.get("focus", {}))
    spec = object_value(plan.get("commercial_headings", {}))
    page = object_value(architecture.get("page", {}))
    roles = [page_role(v) for v in (page.get("page_type"), focus.get("page_role"), spec.get("page_type"))]
    role = next((r for r in roles if r != "unknown"), "unknown")
    required = role in {"home", "category", "product"}
    primary = str(page.get("primary_keyword") or focus.get("primary_keyword") or plan.get("keyword") or "")
    categories = strings(spec.get("category_terms", []))
    declared = records(spec.get("modifiers", []))
    claims = {str(c.get("claim_id", "")): c for c in records(plan.get("claims", []))}
    supported: dict[str, str] = {}
    for term in declared:
        phrase = str(term.get("phrase", "")).strip()
        cid = str(term.get("claim_id", ""))
        claim = claims.get(cid, {})
        buying_use = normalized(phrase) in COMMON or term.get("kind") in {"supplier_role", "order_type", "trade_buyer"}
        if (phrase and buying_use and claim.get("verification_state") in {"user_provided", "verified"}
                and claim.get("public_use_state") in {"approved_public", "public_observed"}
                and isinstance(claim.get("source_ref"), str) and str(claim["source_ref"]).strip()):
            supported[phrase] = cid
    terms = list(dict.fromkeys([*COMMON, *(str(t.get("phrase", "")) for t in declared)]))
    primary_terms = [t for t in terms if buy_spans(t, normalized(primary))]
    issues: list[str] = []
    if len({r for r in roles if r != "unknown"}) > 1:
        issues.append("页面规划与改稿声明的页型不同，须核对目标记录。")
    if role == "unknown":
        issues.append("请确认页型，以决定 Title 与 H1 的采购属性要求。")
    checked = []
    if required:
        for kind in ("title", "h1"):
            matches = [block for block in blocks if block.kind == kind]
            text = matches[0].text if len(matches) == 1 else ""
            clean = normalized(text)
            cats = [c for c in categories if spans(c, clean)]
            found = {t: buy_spans(t, clean) for t in terms}
            proof = {t: cid for t, cid in supported.items() if found.get(t)}
            backed = [pos for t in proof for pos in found[t]]
            unbacked = [t for t, positions in found.items() if any(
                not any(x <= a and b <= y for x, y in backed) for a, b in positions)]
            separate = any(b <= x or y <= a for c in cats for a, b in spans(c, clean) for x, y in backed)
            reasons = []
            if len(matches) != 1:
                reasons.append("需要核到唯一的最终文本")
            else:
                if not cats:
                    reasons.append("缺本页品类表达")
                if not proof:
                    reasons.append("缺有本企业公开依据的采购属性")
                elif cats and not separate:
                    reasons.append("品类与采购属性需要可辨认的独立表达")
                if unbacked:
                    reasons.append("这些采购表达缺适用依据：" + "、".join(unbacked))
                if matches[0].state == "blocked":
                    reasons.append("本段稿件仍待确认")
            if reasons:
                issues.append(kind.upper() + "：" + "，".join(reasons))
            checked.append({"field": kind, "text": text, "observed_count": len(matches), "categories": cats,
                            "modifier_claims": proof, "source_refs": list(dict.fromkeys(str(claims[cid]["source_ref"]) for cid in proof.values())),
                            "issues": reasons})
    status = "needs_review" if issues else ("pass" if required else "not_required")
    return {"target_url": plan.get("target_url"), "market": plan.get("market"), "language": plan.get("language"),
            "status": status, "policy_declared": "commercial_headings" in plan, "page_role": role, "primary_keyword": primary, "primary_modifiers": primary_terms,
            "fields": checked, "issues": issues}


def coverage_sheet(report: dict[str, object]) -> list[dict[str, str]]:
    result = []
    for field in records(report["fields"]):
        claims = object_value(field["modifier_claims"])
        result.append({"位置": "SEO Title" if field["field"] == "title" else "主 H1", "最终文案": str(field["text"]),
                       "规划主词": str(report["primary_keyword"]), "主词已有采购表达": "、".join(strings(report["primary_modifiers"])),
                       "命中品类": "、".join(strings(field["categories"])), "采购表达与事实编号": " / ".join(
                           f"{term} ({cid})" for term, cid in claims.items()),
                       "本企业依据": " / ".join(strings(field["source_refs"])), "该位置待核": "、".join(strings(field["issues"]))})
    return result


def compare_reviewed(observed: dict[str, object], approved: dict[str, object]) -> None:
    if any(approved.get(key) != observed.get(key) for key in ("target_url", "market", "language")):
        raise ValueError("Reviewed headings belong to a different page, market or language")
    issues = strings(observed["issues"])
    if approved.get("status") != observed["status"] or approved.get("page_role") != observed["page_role"]:
        issues.append("前台与改稿的页型或双标题检查结果不一致。")
    expected = {str(item["field"]): str(item["text"]) for item in records(approved["fields"])}
    checked = records(observed["fields"])
    for field in checked:
        key = str(field["field"])
        if expected.get(key, "").split() != str(field["text"]).split():
            field["issues"] = [*strings(field["issues"]), "前台文字与核准稿不同"]
            issues.append(key.upper() + " 与核准稿不同。")
    if issues:
        observed.update(status="needs_review", issues=issues, fields=checked)
