#!/usr/bin/env python3
"""Inspect saved page evidence and validate concrete, source-backed change plans."""
from __future__ import annotations

import argparse
import csv
import hashlib
from itertools import chain
import json
import re
import sys
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from urllib.parse import urljoin, urlsplit

from onpage_research import validate_research

VERSION = "2.3.0"
HEADING_TAGS = {f"h{level}" for level in range(1, 7)}
TEXT_BREAK_TAGS = HEADING_TAGS | {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "footer", "form", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}
CHANGE_FIELDS = {"title", "description", "body", "link", "image_alt", "schema", "other"} | HEADING_TAGS
CHANGE_COLUMNS = ["change_id", "field", "heading_index", "after_tag", "placement", "before", "proposed_after",
                  "reason", "priority", "copy_state", "apply_state", "claim_ids", "evidence_refs"]


def text_workbook(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    """Spreadsheet reading copy: explicit text cells, no formulas or external links.

    The sibling CSV remains the exact machine input. XML-incompatible control
    characters and Excel-oversized values are replaced/truncated in this view only.
    """
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with ZipFile(path.with_suffix(".xlsx"), "w", ZIP_DEFLATED) as book:
        book.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                      '<Default Extension="xml" ContentType="application/xml"/>'
                      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                      '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        book.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                      f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        book.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="{rel}">'
                      '<sheets><sheet name="阅读表" sheetId="1" r:id="rId1"/></sheets></workbook>')
        book.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                      f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        with book.open("xl/worksheets/sheet1.xml", "w") as sheet:
            sheet.write(f'<worksheet xmlns="{main}"><sheetViews><sheetView workbookViewId="0">'
                        '<pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><sheetData>'.encode())
            values = chain([fields], ([row.get(key, "") for key in fields] for row in rows))
            for index, row_values in enumerate(values, 1):
                sheet.write(f'<row r="{index}">'.encode())
                for value in row_values:
                    clean = "".join(c if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or
                                    0xE000 <= ord(c) <= 0xFFFD or ord(c) >= 0x10000 else "\uFFFD" for c in value)
                    if len(clean) > 32767:
                        clean = clean[:32700] + "…[阅读截断；完整值见CSV]"
                    sheet.write(('<c t="inlineStr"><is><t xml:space="preserve">' +
                                 escape(clean).replace("\r", "&#13;") + '</t></is></c>').encode("utf-8"))
                sheet.write(b'</row>')
            sheet.write(b'</sheetData></worksheet>')


def obj(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError("Expected object")
    return {str(k): v for k, v in value.items()}


def arr(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("Expected array")
    return list(value)


def string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty string")
    return value


def texts(value: object) -> list[str]:
    return [string(v) for v in arr(value)]


def head_texts(value: object) -> list[str]:
    result = arr(value)
    if not all(isinstance(v, str) for v in result):
        raise ValueError("Head observations must be strings, including genuinely empty values")
    return [str(v) for v in result]


def compact(value: str) -> str:
    return " ".join(value.split())


def valid_url(url: str) -> str:
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("Expected HTTP(S) target without credentials")
    return url


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)
    text_workbook(path, rows, fields)


def digest(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@contextmanager
def output_dir(destination: Path) -> Iterator[Path]:
    if destination.exists():
        raise ValueError("Choose a new output directory; previous evidence is preserved")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".onpage-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir()
        yield stage
        if destination.exists():
            raise ValueError("Output appeared during run")
        stage.rename(destination)


class PageParser(HTMLParser):
    """Document head is separate from body widgets; text is not a visibility audit."""

    def __init__(self, url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.url = url
        self.base = url
        self.base_seen = False
        self.in_head = False
        self.head_seen = False
        self.iframe_depth = 0
        self.head: dict[str, list[str]] = {"title": [], "description": [], "canonical": [], "robots": [], "language": []}
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.schemas: list[dict[str, object]] = []
        self.fragments: list[str] = []
        self.active: list[tuple[str, dict[str, str], list[str]]] = []
        self.skips: list[str] = []
        self.script: dict[str, str] | None = None
        self.script_parts: list[str] = []

    def text_break(self) -> None:
        """Separate structural text without inserting spaces inside inline-split words."""
        for _, _, fragments in self.active:
            fragments.append(" ")
        if not self.in_head:
            self.fragments.append(" ")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "iframe":
            self.iframe_depth += 1
            return
        if self.iframe_depth:
            return
        values = {k: v or "" for k, v in attrs}
        line = str(self.getpos()[0])
        if tag == "head" and not self.head_seen:
            self.in_head, self.head_seen = True, True
        if tag == "html" and "lang" in values and not self.head["language"]:
            self.head["language"].append(values["lang"])
        if tag == "script" and not self.skips:
            self.script, self.script_parts = values, []
        if tag in {"script", "style", "template", "noscript"}:
            self.skips.append(tag)
        if self.skips:
            return
        if tag in TEXT_BREAK_TAGS:
            self.text_break()
        if self.in_head and tag == "base" and "href" in values and not self.base_seen:
            self.base = urljoin(self.url, values["href"])
            self.base_seen = True
        if self.in_head and tag == "meta":
            name = values.get("name", "").lower()
            if name == "description":
                self.head["description"].append(values.get("content", ""))
            if name in {"robots", "googlebot", "bingbot"}:
                self.head["robots"].append(name + ": " + values.get("content", ""))
        if self.in_head and tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.head["canonical"].append(urljoin(self.base, values.get("href", "")))
        if tag == "title" and self.in_head:
            self.active.append(("title", {"line": line}, []))
        if re.fullmatch("h[1-6]", tag):
            self.active.append((tag, {"line": line, "id": values.get("id", "")}, []))
        if tag == "a" and "href" in values:
            self.active.append(("a", {"line": line, **values}, []))
        if tag == "img":
            image = {"line": line, "alt_state": "present" if "alt" in values else "missing", **values}
            image["resolved_src"] = urljoin(self.base, values.get("src", ""))
            self.images.append(image)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.iframe_depth:
            if tag == "iframe":
                self.iframe_depth -= 1
            return
        if tag == "script" and self.script is not None:
            if self.script.get("type", "").split(";")[0].strip().lower() == "application/ld+json":
                raw = "".join(self.script_parts)
                try:
                    data = json.loads(raw)
                    self.schemas.append({"raw": raw, "json_state": "valid_json", "data": data})
                except json.JSONDecodeError as exc:
                    self.schemas.append({"raw": raw, "json_state": "invalid_json", "error": str(exc)})
            self.script, self.script_parts = None, []
        if tag in self.skips:
            index = len(self.skips) - 1 - self.skips[::-1].index(tag)
            del self.skips[index:]
        if not self.skips:
            for index in range(len(self.active) - 1, -1, -1):
                kind, values, fragments = self.active[index]
                if kind == tag:
                    del self.active[index]
                    text = compact("".join(fragments))
                    if kind == "title":
                        self.head["title"].append(text)
                    elif kind == "a":
                        self.links.append({**values, "text": text, "resolved_href": urljoin(self.base, values["href"])})
                    else:
                        self.headings.append({**values, "tag": kind, "text": text})
                    break
            if tag in TEXT_BREAK_TAGS:
                self.text_break()
        if tag == "head":
            self.in_head = False

    def handle_data(self, data: str) -> None:
        if self.iframe_depth:
            return
        if self.script is not None:
            self.script_parts.append(data)
        if self.skips:
            return
        for _, _, fragments in self.active:
            fragments.append(data)
        if not self.in_head:
            self.fragments.append(data)


def schema_types(value: object) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in obj(value).items():
            if key == "@type":
                if isinstance(child, str):
                    result.add(child)
                elif isinstance(child, list):
                    result.update(v for v in child if isinstance(v, str))
            result.update(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            result.update(schema_types(child))
    return result


def inspect_page(source: Path, kind: str, url: str, keyword: str, market: str, language: str,
                 collected_at: str, stage_kind: str, capture_path: Path | None, out: Path,
                 rendered_head_path: Path | None = None) -> None:
    valid_url(url)
    string(keyword)
    string(market)
    string(language)
    string(collected_at)
    raw = source.read_text(encoding="utf-8-sig")
    evidence: dict[str, object] = {"schema_version": VERSION, "target_url": url, "keyword": keyword,
        "market": market, "language": language, "collected_at": collected_at, "content_stage": stage_kind,
        "input": digest(source), "input_kind": kind, "technical_scope": "not_observed",
        "limits": ["Saved evidence only; no fetch, Google index verification or performance measurement.",
                   "HTML parser text can include navigation, hidden elements and widgets; inspect rendered page as needed.",
                   "JSON validity is not Schema.org validation or Google rich-result eligibility."]}
    if capture_path:
        capture = obj(json.loads(capture_path.read_text(encoding="utf-8")))
        final = capture.get("final_url")
        if final and final != url:
            raise ValueError("Use capture final_url as target; preserve requested URL in capture")
        evidence["capture"] = capture
        evidence["capture_input"] = digest(capture_path)
    observations: list[dict[str, str]] = []
    if kind == "html":
        parser = PageParser(url)
        parser.feed(raw)
        parser.close()
        for index, heading in enumerate(parser.headings, 1):
            heading["heading_index"] = str(index)
        body = compact("".join(parser.fragments))
        selected_head, selected_head_seen = parser.head, parser.head_seen
        if rendered_head_path:
            rendered = obj(json.loads(rendered_head_path.read_text(encoding="utf-8")))
            if rendered.get("target_url") != url:
                raise ValueError("Rendered head target differs from page target")
            string(rendered.get("collected_at"))
            string(rendered.get("source_ref"))
            rendered_head = obj(rendered.get("head"))
            if not rendered_head or not set(rendered_head) <= set(parser.head):
                raise ValueError("Supply only actually observed, known head fields")
            selected_head = {key: head_texts(rendered_head[key]) if key in rendered_head else values
                             for key, values in parser.head.items()}
            selected_head_seen = True
            evidence.update({"source_head": parser.head, "rendered_head_input": digest(rendered_head_path),
                             "rendered_head_observation": rendered, "rendered_head_fields": sorted(rendered_head),
                             "head_origin": "source_head_with_supplied_browser_field_observations"})
        evidence.update({"head": selected_head, "head_seen": selected_head_seen, "headings": parser.headings,
                         "links": parser.links, "images": parser.images, "schemas": parser.schemas,
                         "schema_types": sorted(set().union(*(schema_types(x.get("data")) for x in parser.schemas))),
                         "technical_scope": "saved_head_and_browser_head_observation" if rendered_head_path else
                         "saved_document_head_only" if parser.head_seen else "head_not_observed"})
        if selected_head_seen:
            for field in ("title", "description", "canonical"):
                count = len(selected_head[field])
                if count != 1 or not selected_head[field][0].strip():
                    observations.append({"check": field, "state": "review", "detail": f"Saved head has {count} {field} entries; inspect intent/configuration", "source": "document_head"})
            if any(re.search(r"(?:^|[\s,:])noindex(?:$|[\s,])", r, re.I) for r in selected_head["robots"]):
                observations.append({"check": "robots", "state": "review", "detail": "Saved head contains noindex; confirm intended environment and applicable bot", "source": "document_head"})
        else:
            observations.append({"check": "head", "state": "not_observed", "detail": "Cannot infer missing tags from a fragment", "source": "input_scope"})
        missing_alt = sum(i["alt_state"] == "missing" for i in parser.images)
        observations.append({"check": "image_alt", "state": "review" if missing_alt else "observed",
                             "detail": f"{missing_alt}/{len(parser.images)} image elements lack alt; decorative empty alt is distinct", "source": "saved_html"})
        observations.append({"check": "h1_count", "state": "observed", "detail": str(sum(h["tag"] == "h1" for h in parser.headings)), "source": "saved_html_not_visibility"})
    else:
        if rendered_head_path:
            raise ValueError("Use rendered head observations with HTML evidence; text-only stays text-only")
        body = raw
        evidence["head"] = None
        observations.append({"check": "technical_metadata", "state": "not_observed", "detail": "Text/Markdown cannot establish canonical, robots, schema or image attributes", "source": "input_scope"})
    evidence["text"] = body
    with output_dir(out) as destination:
        write_json(destination / "page-evidence.json", evidence)
        (destination / "extracted-text.txt").write_text(body + "\n", encoding="utf-8")
        write_csv(destination / "observations.csv", observations, ["check", "state", "detail", "source"])
        write_json(destination / "run.json", {"version": VERSION, "command": "inspect", "input": digest(source),
                   "target_url": url, "content_stage": stage_kind, "source_kind": kind,
                   "limits": evidence["limits"]})


def heading_before(change: dict[str, object], evidence: dict[str, object]) -> None:
    """Validate a heading's actual position without treating its count as a ranking rule."""
    if evidence.get("input_kind") != "html":
        raise ValueError("Heading tags require HTML evidence; text-only cannot establish H1-H6")
    field, before = str(change["field"]), str(change["before"])
    headings = [obj(h) for h in arr(evidence.get("headings", []))]
    index = change.get("heading_index")
    if index is not None:
        if type(index) is not int or not 1 <= index <= len(headings):
            raise ValueError("heading_index must be a valid one-based position in saved headings")
        heading = headings[index - 1]
        if heading.get("tag") != field or heading.get("text") != before:
            raise ValueError("Heading before/tag does not match heading_index")
    elif before:
        matches = [h for h in headings if h.get("tag") == field and h.get("text") == before]
        if len(matches) != 1:
            raise ValueError("Heading before is absent or ambiguous; use heading_index for repeated text")
    elif any(h.get("tag") == field for h in headings):
        if not isinstance(change.get("placement"), str) or not str(change["placement"]).strip():
            raise ValueError("Adding another heading requires a concrete placement")
    if change.get("after_tag", field) not in HEADING_TAGS:
        raise ValueError("after_tag must be H1-H6 in lowercase")


def placement_rows(plan: dict[str, object], evidence: dict[str, object],
                   changes: list[dict[str, str]]) -> list[dict[str, str]]:
    """Check analyst-written placement references; never enforce keyword density or exact-match use."""
    if "focus" not in plan:
        if plan.get("keyword_placement"):
            raise ValueError("keyword_placement requires focus")
        return []
    focus = obj(plan["focus"])
    if focus.get("primary_keyword") != plan.get("keyword"):
        raise ValueError("focus.primary_keyword must preserve the selected page keyword")
    for key in ("page_role", "buyer_task"):
        string(focus.get(key))
    if focus.get("scope") not in {"metadata", "headings", "section", "full_page"}:
        raise ValueError("Invalid focus.scope")
    primary = string(focus["primary_keyword"])
    secondary = texts(focus.get("secondary_keywords", []))
    terms = [compact(t).casefold() for t in [primary, *secondary]]
    if len(terms) != len(set(terms)):
        raise ValueError("Primary/secondary keywords must be distinct")
    for optional in ("architecture_ref", "selection_ref"):
        if optional in focus:
            string(focus[optional])
    texts(focus.get("preserve", []))
    changes_by_id = {c["change_id"]: c for c in changes}
    result: list[dict[str, str]] = []
    for value in arr(plan.get("keyword_placement", [])):
        row = obj(value)
        keyword, role = string(row.get("keyword")), string(row.get("role"))
        if role not in {"primary", "secondary"}:
            raise ValueError("Placement role must be primary or secondary")
        allowed = [primary] if role == "primary" else secondary
        if compact(keyword).casefold() not in {compact(t).casefold() for t in allowed}:
            raise ValueError("Placement keyword/role is not in the confirmed focus")
        location, reason = string(row.get("location")), string(row.get("reason"))
        if location not in CHANGE_FIELDS - {"schema", "other"} | {"intro", "not_used"}:
            raise ValueError("Invalid keyword placement location")
        expression, change_id, source_ref = row.get("expression", ""), row.get("change_id", ""), row.get("source_ref", "")
        if not all(isinstance(v, str) for v in (expression, change_id, source_ref)):
            raise ValueError("Placement expression/change_id/source_ref must be strings")
        expression, change_id, source_ref = str(expression), str(change_id), str(source_ref)
        state = "not_used"
        if location == "not_used":
            if expression or change_id or source_ref:
                raise ValueError("Unused terms have a reason, not a claimed placement")
        else:
            string(expression)
            if bool(change_id) == bool(source_ref):
                raise ValueError("Placement needs exactly one change_id or source_ref")
            if change_id:
                if change_id not in changes_by_id:
                    raise ValueError("Placement references unknown change_id")
                change = changes_by_id[change_id]
                effective_field = change["after_tag"] or change["field"]
                if effective_field != ("body" if location == "intro" else location):
                    raise ValueError("Placement location differs from referenced change field")
                if compact(expression).casefold() not in compact(change["proposed_after"]).casefold():
                    raise ValueError("Placement expression not found in proposed copy")
                state = change["copy_state"]
            else:
                if location in {"title", "description"}:
                    head = obj(evidence["head"]) if evidence.get("head") is not None else {}
                    samples = head_texts(head.get(location, []))
                elif location in HEADING_TAGS:
                    samples = [str(obj(h).get("text", "")) for h in arr(evidence.get("headings", []))
                               if obj(h).get("tag") == location]
                elif location in {"link", "image_alt"}:
                    key, attribute = ("links", "text") if location == "link" else ("images", "alt")
                    samples = [str(obj(item).get(attribute, "")) for item in arr(evidence.get(key, []))]
                else:
                    samples = [str(evidence.get("text", ""))]
                if not any(compact(expression).casefold() in compact(s).casefold() for s in samples):
                    raise ValueError("Preserved placement expression not found in saved evidence")
                state = "preserved_snapshot_text"
        result.append({"keyword": keyword, "role": role, "location": location, "expression": expression,
                       "change_id": change_id, "source_ref": source_ref, "reason": reason, "copy_state": state})
    if focus["scope"] == "full_page" and not any(r["role"] == "primary" for r in result):
        raise ValueError("Full-page focus needs a primary placement or an explained not_used record")
    if focus["scope"] == "full_page":
        covered = {compact(row["keyword"]).casefold() for row in result}
        if any(term not in covered for term in terms):
            raise ValueError("Full-page focus needs placement or explained not_used for every selected secondary keyword")
    return result


def check_plan(evidence_path: Path, plan_path: Path, out: Path) -> None:
    evidence, plan = (obj(json.loads(p.read_text(encoding="utf-8"))) for p in (evidence_path, plan_path))
    for key in ("target_url", "keyword", "market", "language"):
        if plan.get(key) != evidence.get(key):
            raise ValueError(f"Plan context differs from evidence: {key}")
    if plan.get("intent_fit") not in {"fit", "mixed", "mismatch", "unknown"}:
        raise ValueError("Invalid intent_fit")
    string(plan.get("intent_reason"))
    serp = obj(plan["serp"]) if plan.get("serp") is not None else {
        "source": "not_requested", "actual_scope": "本次未使用 SERP", "collected_at": "",
        "coverage": "依据已选目标页与业务资料进行优化", "results": []}
    for key in ("source", "actual_scope", "coverage"):
        string(serp.get(key))
    if serp["source"] != "not_requested":
        string(serp.get("collected_at"))
    for value in arr(serp.get("results", [])):
        row = obj(value)
        valid_url(string(row.get("url")))
        string(row.get("page_type"))
        string(row.get("evidence_ref"))
    claims: dict[str, dict[str, object]] = {}
    for value in arr(plan.get("claims", [])):
        claim = obj(value)
        cid = string(claim.get("claim_id"))
        if cid in claims:
            raise ValueError("Duplicate claim_id")
        for key in ("text", "source_ref"):
            string(claim.get(key))
        if claim.get("verification_state") not in {"page_observed", "user_provided", "verified", "unverified", "contradicted"}:
            raise ValueError("Invalid claim verification_state")
        if claim.get("public_use_state") not in {"public_observed", "approved_public", "internal_only", "pending"}:
            raise ValueError("Invalid claim public_use_state")
        claims[cid] = claim
    rows: list[dict[str, str]] = []
    ids: set[str] = set()
    head = obj(evidence["head"]) if evidence.get("head") is not None else None
    for value in arr(plan.get("changes")):
        change = obj(value)
        cid, field = string(change.get("change_id")), string(change.get("field"))
        if cid in ids or field not in CHANGE_FIELDS:
            raise ValueError("Duplicate change_id or unknown field")
        ids.add(cid)
        before, after = change.get("before"), string(change.get("after"))
        if not isinstance(before, str):
            raise ValueError("Before must be a string; empty denotes verified absence/new section")
        if field in {"title", "description"}:
            if head is None or not evidence.get("head_seen"):
                raise ValueError("Cannot assert title/description before from text/HTML fragment")
            values = head_texts(head[field])
            if (values and before not in values) or (not values and before):
                raise ValueError("Before does not match saved head")
        if field in HEADING_TAGS:
            heading_before(change, evidence)
        elif "after_tag" in change or "heading_index" in change:
            raise ValueError("Heading selectors are only valid for heading changes")
        if "placement" in change:
            string(change["placement"])
        if field == "body" and before and compact(before) not in compact(str(evidence.get("text", ""))):
            raise ValueError("Body before not found in saved extracted text")
        if change.get("priority") not in {"P1", "P2", "P3"} or change.get("copy_state") not in {"ready", "blocked"}:
            raise ValueError("Invalid priority or copy_state")
        # This export is a proposal, never evidence of a successful CMS/live write.
        if change.get("apply_state", "proposed") != "proposed":
            raise ValueError("Change plan export only accepts proposed; record implementation proof separately")
        for claim_id in texts(change.get("claim_ids", [])):
            if claim_id not in claims:
                raise ValueError("Unknown claim_id")
            claim = claims[claim_id]
            ready = claim["verification_state"] in {"page_observed", "user_provided", "verified"} and claim["public_use_state"] in {"public_observed", "approved_public"}
            if change["copy_state"] == "ready" and not ready:
                raise ValueError("Ready copy references an unverified/contradicted/private claim")
        evidence_refs = texts(change.get("evidence_refs"))
        if not evidence_refs:
            raise ValueError("Change requires evidence_refs")
        rows.append({"change_id": cid, "field": field, "heading_index": str(change.get("heading_index", "")),
                     "after_tag": str(change.get("after_tag", field if field in HEADING_TAGS else "")),
                     "placement": str(change.get("placement", "")), "before": before, "proposed_after": after,
                     "reason": string(change.get("reason")), "priority": str(change["priority"]),
                     "copy_state": str(change["copy_state"]), "apply_state": "proposed",
                     "claim_ids": json.dumps(texts(change.get("claim_ids", []))),
                     "evidence_refs": json.dumps(evidence_refs, ensure_ascii=False)})
    if not rows:
        if plan.get("review_outcome") != "retain":
            raise ValueError("Plan has no changes; use review_outcome=retain with a retention_reason")
        string(plan.get("retention_reason"))
    elif plan.get("review_outcome") == "retain":
        raise ValueError("retain cannot include proposed changes")
    placements = placement_rows(plan, evidence, rows)
    gaps = texts(plan.get("fact_gaps", []))
    focus = obj(plan.get("focus", {}))
    if focus.get("scope") == "full_page" and "research" not in plan:
        raise ValueError("Full-page optimization requires industry library research; request the library link first")
    research = validate_research(plan["research"], plan, focus, plan_path.parent) if "research" in plan else None
    if research is not None:
        raw_serp = obj(obj(plan["research"])["serp"])
        snapshots = [source for source in research.sources if source["kind"] == "serp"]
        dates = sorted({source["collected_at"] for source in snapshots})
        collected_at = raw_serp.get("collected_at") or (dates[0] if len(dates) == 1 else "Multiple snapshots; see source_snapshots")
        serp = {**raw_serp, "source": raw_serp["source"],
                "actual_scope": f"{raw_serp['actual_market']} / {raw_serp['actual_language']}",
                "coverage": raw_serp["coverage"], "collected_at": collected_at,
                "keyword": plan["keyword"], "market": plan["market"], "language": plan["language"],
                "evidence_class": obj(plan["research"])["evidence_class"],
                "source_snapshots": snapshots, "research_status": research.status, "limitations": research.gaps,
                "results": [{"url": row["url"], "title": row["title"], "page_type": row["page_type"], "evidence_ref": row["evidence_refs"],
                             **({"position": int(row["position"])} if row["position"] else {})} for row in research.serp]}
    with output_dir(out) as destination:
        exported_plan = dict(plan)
        table_context = {"page_url": str(plan["target_url"]), "primary_keyword": str(plan["keyword"]),
                         "target_market": str(plan["market"]), "content_language": str(plan["language"]),
                         "research_evidence_class": str(obj(plan.get("research", {})).get("evidence_class", "not_declared")),
                         "research_status": research.status if research is not None else "not_checked"}

        def plan_table(name: str, values: list[dict[str, str]], fields: list[str]) -> None:
            write_csv(destination / name, [{**table_context, **value} for value in values], [*table_context, *fields])

        if research is not None:
            exported_research = dict(obj(plan["research"]))
            exported_research["sources"] = research.sources
            exported_plan["research"] = exported_research
            write_json(destination / "research.json", exported_research)
            write_json(destination / "research-sources.json", research.sources)
            plan_table("keyword-selection.csv", research.keywords,
                      ["keyword", "origin", "decision", "reason", "module_ids", "target_url", "target_page_role", "metrics", "evidence_refs"])
            plan_table("serp-results.csv", research.serp,
                      ["position", "url", "title", "page_type", "evidence_refs"])
            plan_table("competitor-comparison.csv", research.competitors,
                      ["url", "requested_url", "read_state", "selection_reason", "observed_strengths", "page_gap", "recommendation", "evidence_refs"])
            (destination / "page-brief.md").write_text(research.brief, encoding="utf-8")
        write_json(destination / "plan.json", exported_plan)
        if serp["source"] != "not_requested":
            write_json(destination / "serp-brief.json", serp)
        write_json(destination / "claims.json", list(claims.values()))
        plan_table("page-changes.csv", rows, CHANGE_COLUMNS)
        if "focus" in plan:
            write_json(destination / "page-focus.json", plan["focus"])
            plan_table("keyword-placement.csv", placements,
                      ["keyword", "role", "location", "expression", "change_id", "source_ref", "reason", "copy_state"])
        review = [f"# On-page · {plan['keyword']}", "", f"页面：{plan['target_url']}",
                  f"市场/语言：{plan['market']} / {plan['language']}",
                  f"意图匹配：{plan['intent_fit']}；{plan['intent_reason']}",
                  f"SERP 范围：{serp['actual_scope']}；{serp['coverage']}", ""]
        if research is not None:
            review += [f"研究记录：{research.status}；先读 [页面简报](page-brief.md) 与 keyword-selection.xlsx。",
                       "文件与引用校验不等于研究真实性或语义质量验收。", "",
                       *[f"- 研究缺口：{gap}" for gap in research.gaps], ""]
        else:
            review += ["研究记录：未校验完整研究链。本次为局部/旧接口改稿，不代表完整 On-page 研究。", ""]
        if "focus" in plan:
            focus = obj(plan["focus"])
            review += ["## 本页目标与关键词安排", "", f"主词：{focus['primary_keyword']}",
                       f"页面职责：{focus['page_role']}；采购任务：{focus['buyer_task']}；范围：{focus['scope']}",
                       "辅助词：" + "；".join(texts(focus.get("secondary_keywords", []))), ""]
            for item in placements:
                review += [f"- {item['keyword']} → {item['location']}：{item['expression'] or '本次不用'}；{item['reason']}"]
            review += [""]
        if not rows:
            review += ["## 保留现状", "", string(plan.get("retention_reason")), ""]
        for exported in rows:
            review += [f"## {exported['change_id']} · {exported['field']} · {exported['priority']} · {exported['copy_state']}", "",
                       f"现状：{exported['before'] or '拟新增；需在编辑器定位'}", "", exported["proposed_after"], "",
                       f"定位：{exported['placement'] or '原文匹配'}；标题序号：{exported['heading_index'] or '不适用'}；改后标签：{exported['after_tag'] or '不适用'}", "",
                       f"理由：{exported['reason']}", "", f"依据：{exported['evidence_refs']}", ""]
        review += ["## 资料缺口", "", *[f"- {gap}" for gap in gaps], "",
                   "状态：改稿建议。脚本只校验引用、上下文和部分现状匹配，不能自动证明事实完整、语义正确或排名提升。"]
        (destination / "onpage-review.md").write_text("\n".join(review) + "\n", encoding="utf-8")
        write_json(destination / "run.json", {"version": VERSION, "command": "check-plan", "changes": len(rows),
                   "claims": len(claims), "inputs": [digest(evidence_path), digest(plan_path)],
                   "research_status": research.status if research is not None else "not_checked",
                   "research_gaps": research.gaps if research is not None else [],
                   "research_sources": research.sources if research is not None else [],
                   "limits": ["Does not detect every unsupported statement in natural-language copy; Codex must review all claims.",
                              "Does not authenticate supplied citations, validate SERP completeness or apply website changes."]})


def compare_snapshots(plan_path: Path, after_path: Path, out: Path, local_simulation: bool = False) -> None:
    """Observe proposed strings in a later snapshot, without certifying deployment or ranking."""
    plan, after = (obj(json.loads(p.read_text(encoding="utf-8"))) for p in (plan_path, after_path))
    if local_simulation and (obj(plan.get("research", {})).get("evidence_class") != "simulation"
                             or after.get("content_stage") not in {"supplied_html", "supplied_text"}):
        raise ValueError("Local simulation comparison requires simulation research and a supplied local snapshot")
    for key in ("target_url", "keyword", "market", "language"):
        if plan.get(key) != after.get(key):
            raise ValueError(f"After snapshot context differs from plan: {key}")
    rows: list[dict[str, str]] = []
    for value in arr(plan.get("changes")):
        change = obj(value)
        field, text = string(change.get("field")), string(change.get("after"))
        status, detail = "manual_check_required", "Verify the actual element and its context in the rendered page"
        samples: list[str] | None = None
        if change.get("copy_state") == "blocked" and not local_simulation:
            status, detail = "blocked_copy", "Not ready for implementation"
        else:
            if field in {"title", "description"} and after.get("head_seen") and after.get("head") is not None:
                samples = head_texts(obj(after["head"])[field])
            elif field in HEADING_TAGS and after.get("input_kind") == "html":
                samples = [str(obj(h).get("text", "")) for h in arr(after.get("headings", []))
                           if obj(h).get("tag") == change.get("after_tag", field)]
            elif field == "body":
                samples = [str(after.get("text", ""))]
            if samples is not None:
                found = any(compact(text) in compact(s) if field == "body" else compact(text) == compact(s)
                            for s in samples)
                status = "observed_in_snapshot" if found else "not_observed_in_snapshot"
                detail = "String presence only; check position, visibility and duplicate elements manually"
                if local_simulation:
                    detail += "; internal simulation only; original copy/public-use blocks remain unchanged"
        rows.append({"change_id": string(change.get("change_id")), "field": field, "proposed_after": text,
                     "copy_state": str(change.get("copy_state", "unknown")), "observation": status, "detail": detail})
    with output_dir(out) as destination:
        write_csv(destination / "implementation-observations.csv", rows,
                  ["change_id", "field", "proposed_after", "copy_state", "observation", "detail"])
        report = ["# 改后快照回读", "", f"页面：{after['target_url']}",
                  f"证据阶段：{after.get('content_stage', 'unknown')}；采集时间：{after.get('collected_at', 'unknown')}", ""]
        if local_simulation:
            report += ["本次只回读本地模拟稿；blocked 和 internal_only 保持原状态，文字出现不授权公开使用。", ""]
        report += [f"- {r['change_id']}（{r['field']}）：{r['observation']}" for r in rows]
        report += ["", "这是给定快照中的文字观察，不证明修改已上线、位置/视觉正确、Google采用或SEO效果。未观察到不等于确认线上缺失。"]
        (destination / "implementation-review.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        write_json(destination / "run.json", {"version": VERSION, "command": "compare", "inputs": [digest(plan_path), digest(after_path)],
                   "comparison_scope": "local_simulation" if local_simulation else "proposed_copy",
                   "content_stage": after.get("content_stage", "unknown"), "changes": len(rows),
                   "deployment_verified": False, "seo_outcomes_verified": False})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect")
    source = inspect.add_mutually_exclusive_group(required=True)
    source.add_argument("--html", type=Path)
    source.add_argument("--text", type=Path)
    for argument in ("url", "keyword", "market", "language", "collected-at"):
        inspect.add_argument("--" + argument, required=True)
    inspect.add_argument("--stage", required=True, choices=["source_html", "tool_raw_html", "browser_dom", "supplied_html", "supplied_text"])
    inspect.add_argument("--capture", type=Path)
    inspect.add_argument("--rendered-head", type=Path)
    inspect.add_argument("--out", type=Path, required=True)
    plan = commands.add_parser("check-plan")
    plan.add_argument("--evidence", type=Path, required=True)
    plan.add_argument("--plan", type=Path, required=True)
    plan.add_argument("--out", type=Path, required=True)
    compare = commands.add_parser("compare", help="Observe proposed copy in a separately captured after snapshot")
    compare.add_argument("--plan", type=Path, required=True)
    compare.add_argument("--after", type=Path, required=True)
    compare.add_argument("--out", type=Path, required=True)
    compare.add_argument("--local-simulation", action="store_true", help="Read blocked copy only in a supplied local simulation; public-use state is unchanged")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            inspect_page(args.html or args.text, "html" if args.html else "text", args.url, args.keyword,
                         args.market, args.language, args.collected_at, args.stage, args.capture, args.out, args.rendered_head)
        elif args.command == "check-plan":
            check_plan(args.evidence, args.plan, args.out)
        else:
            compare_snapshots(args.plan, args.after, args.out, args.local_simulation)
    except (ValueError, OSError, csv.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Saved {args.command} to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
