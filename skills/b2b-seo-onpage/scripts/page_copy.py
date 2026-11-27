"""Project proposed edits and retained evidence into one page used by both copy and coverage."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re

from architecture_page import id_list, query_key
from onpage_research import items, object_value, string, strings

PLACEMENT_DETAIL = ["module_id", "design_module_id", "block_id", "final_text", "answer_ref", "answer_text",
                    "answer_state", "field_ids", "attribute_ids", "design_refs"]
DESIGN_COLUMNS = ["kind", "id", "name", "source_ref", "condition", "source_status", "missing_policy",
                  "copy_status", "block_refs", "final_text", "keywords"]


def records(value: object) -> list[dict[str, object]]:
    return [object_value(row) for row in items(value)]


def has_text(fragment: str, text: str) -> bool:
    return bool(fragment) and query_key(fragment) in query_key(text)


@dataclass
class Block:
    key: str
    kind: str
    text: str
    heading: int = 0
    module: str = ""
    state: str = "preserved_snapshot_text"
    change: str = ""
    fields: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    section: str = ""
    claims: set[str] = field(default_factory=set)


class PageCopy:
    def __init__(self, evidence: dict[str, object], changes: list[dict[str, str]],
                 brief: dict[str, object], design: dict[str, object], claims: dict[str, bool]) -> None:
        self.modules = {string(m["id"]): m for m in records(brief.get("modules", []))}
        self.design = {kind: {string(row["id"]): row for row in records(design.get(kind, []))}
                       for kind in ("modules", "fields", "attributes")}
        self.design_gaps = [str(g) for g in items(design.get("gaps", []))]
        self.blocks: list[Block] = []
        self.changed: dict[str, Block] = {}
        self.parts_of_subtitle: set[str] = set()
        self.sectioned = "content_blocks" in evidence
        self.has_design = bool(design)
        self.claims = claims
        self.read_snapshot(evidence)
        self.bind_outline(changes)
        self.apply_changes(changes)
        self.bind_sections(changes)
        for row in changes:
            b = self.changed[row["change_id"]]
            b.claims.update(json.loads(row["claim_ids"]))
            self.bind_design(b, id_list(row["field_ids"]), id_list(row["attribute_ids"]))

    def read_snapshot(self, evidence: dict[str, object]) -> None:
        head = object_value(evidence.get("head") or {})
        for kind in ("title", "description"):
            for index, value in enumerate(items(head.get(kind, [])), 1):
                self.blocks.append(Block(f"{kind}-{index}", kind, str(value)))
        observed_subtitle = object_value(evidence.get("subtitle", {}))
        subtitle = str(observed_subtitle.get("text", ""))
        if subtitle:
            self.blocks.append(Block("subtitle", "subtitle", subtitle))
        sections: dict[int, list[Block]] = {}
        for row in records(evidence.get("content_blocks", [])):
            idx = int(str(row["heading_index"]))
            sections.setdefault(idx, []).append(Block(string(row["block_id"]), "body", string(row["text"]), idx))
        self.blocks.extend(sections.get(0, []))
        for idx, row in enumerate(records(evidence.get("headings", [])), 1):
            if row.get("content_scope") == "navigation":
                continue
            self.blocks.append(Block(f"heading-{idx}", string(row["tag"]), str(row["text"]), idx))
            self.blocks.extend(sections.get(idx, []))
        # A hero paragraph (or H2) is one visible node, even if it has two observations.
        alias = [b for b in self.blocks if b.kind in {"body", str(observed_subtitle.get("tag", ""))}
                 and b.key != "subtitle" and subtitle and query_key(b.text) == query_key(subtitle)]
        if len(alias) == 1:
            self.parts_of_subtitle.add(alias[0].key)
        if not self.sectioned and evidence.get("text"):
            self.blocks.append(Block("unscoped-text", "body", str(evidence["text"])))
        for kind, key, prop in (("link", "links", "text"), ("image_alt", "images", "alt")):
            for idx, row in enumerate(records(evidence.get(key, [])), 1):
                self.blocks.append(Block(f"{kind}-{idx}", kind, str(row.get(prop, ""))))

    def bind_outline(self, changes: list[dict[str, str]]) -> None:
        headings = [b for b in self.blocks if re.fullmatch(r"h[1-6]", b.kind)]
        owners: dict[int, str] = {}
        for mid, module in self.modules.items():
            design_id = self.design_id(mid)
            if design_id and self.has_design and design_id not in self.design["modules"]:
                raise ValueError(f"Unknown design module for this page: {design_id}")
            idx = module.get("source_heading_index")
            if idx is not None and (type(idx) is not int or not any(b.heading == idx for b in headings)):
                raise ValueError(f"Unknown source_heading_index for brief module {mid}")
            matches = [b for b in headings if query_key(b.text) == query_key(str(module["heading"]))]
            if idx is None and len(matches) == 1:
                idx = matches[0].heading
            if isinstance(idx, int):
                if idx in owners:
                    raise ValueError("One original heading cannot represent two different brief modules")
                owners[idx] = mid
        # A replacement heading can establish the section of the old heading and its paragraphs.
        for change in changes:
            if not change["before"] or not re.fullmatch(r"h[1-6]", change["field"]):
                continue
            mid = self.heading_module(change["proposed_after"], change["module_id"])
            matched = [b for b in headings if b.kind == change["field"] and b.text == change["before"]
                       and (not change["heading_index"] or b.heading == int(change["heading_index"]))]
            if mid and len(matched) == 1:
                idx = matched[0].heading
                if idx in owners and owners[idx] != mid:
                    raise ValueError(f"Change contradicts the real heading's brief module: {change['change_id']}")
                owners[idx] = mid
        single = next(iter(self.modules)) if len(self.modules) == 1 else ""
        stack: list[tuple[str, str]] = []
        for b in headings:
            while stack and stack[-1][0] >= b.kind:
                stack.pop()
            # An unmapped sibling section does not inherit a page-wide H1 as its trade topic.
            owner = owners.get(b.heading, single or (stack[-1][1] if stack and stack[-1][0] != "h1" else ""))
            owners[b.heading] = owner
            stack.append((b.kind, owner))
        hero_ids = {owners[b.heading] for b in headings if b.kind == "h1" and owners.get(b.heading)}
        self.hero = next(iter(hero_ids)) if len(hero_ids) == 1 else single
        for b in self.blocks:
            b.module = (self.hero if b.kind in {"title", "description", "subtitle"} else owners.get(b.heading, single))
        for mid, module in self.modules.items():
            for bid in strings(module.get("source_block_ids", [])):
                original = next((b for b in self.blocks if b.key == bid and b.kind == "body"), None)
                if not original or original.key == "unscoped-text" or original.module and original.module != mid:
                    raise ValueError(f"Original paragraph {bid} does not belong to brief module {mid}")
                original.module = mid

    def heading_module(self, heading: str, declared: str) -> str:
        names = [mid for mid, m in self.modules.items() if query_key(str(m["heading"])) == query_key(heading)]
        if declared and declared not in self.modules:
            raise ValueError(f"Unknown brief module: {declared}")
        if declared and names and declared not in names:
            raise ValueError("Heading text belongs to a different brief module")
        return declared or (names[0] if len(names) == 1 else "")

    def apply_changes(self, changes: list[dict[str, str]]) -> None:
        single = next(iter(self.modules)) if len(self.modules) == 1 else ""
        touched: set[str] = set()
        head_edits: set[str] = set()
        for row in changes:
            cid, kind, before, after = (row[k] for k in ("change_id", "field", "before", "proposed_after"))
            if kind in {"title", "description", "subtitle"}:
                if kind in head_edits:
                    raise ValueError(f"Multiple final edits to the same {kind}")
                head_edits.add(kind)
            declared = row["module_id"]
            if declared and declared not in self.modules:
                raise ValueError(f"Unknown brief module: {declared}")
            target: Block | None = None
            if before:
                matches = [b for b in self.blocks if b.kind == kind and
                           (has_text(before, b.text) if kind == "body" else b.text == before)]
                if row["heading_index"]:
                    matches = [b for b in matches if b.heading == int(row["heading_index"])]
                if row["source_block_id"]:
                    matches = [b for b in matches if b.key == row["source_block_id"]]
                if len(matches) > 1 and declared:
                    matches = [b for b in matches if b.module == declared]
                if len(matches) > 1:
                    raise ValueError(f"Ambiguous original location for {cid}; supply a heading_index or source_block_id")
                if not matches and (row["source_block_id"] or kind in {"body", "title", "description", "subtitle"}
                                    or re.fullmatch(r"h[1-6]", kind)):
                    raise ValueError(f"Original content block not found for {cid}")
                target = matches[0] if matches else None
            elif row["source_block_id"]:
                raise ValueError("source_block_id selects a nonempty original block")
            effective = row["after_tag"] or kind
            owner = (self.heading_module(after, declared) if re.fullmatch(r"h[1-6]", effective) else declared)
            if target and target.module and owner and target.module != owner:
                raise ValueError(f"Change {cid} is assigned to a different section from its original block")
            owner = owner or (target.module if target else "") or (self.hero if kind in {"title", "subtitle", "description", "h1"} else single)
            if target and target.key == "unscoped-text":
                # An old flat capture proves the phrase, not its section. Keep unrelated text separate.
                target.text = re.sub(re.escape(" ".join(before.split())), "", " ".join(target.text.split()), count=1)
                target = None
            if target:
                if target.key in touched:
                    raise ValueError(f"Overlapping edits to the same original block: {cid}")
                if kind == "body" and query_key(before) != query_key(target.text):
                    original = " ".join(target.text.split())
                    needle = " ".join(before.split())
                    if original.count(needle) != 1:
                        raise ValueError(f"Ambiguous body replacement in {cid}; use the full original paragraph")
                    after = original.replace(needle, after, 1)
                b = target
            else:
                b = Block(f"new-{cid}", effective, after)
                self.blocks.append(b)
            touched.add(b.key)
            b.kind, b.text, b.change, b.module, b.state = effective, after, cid, owner, row["copy_state"]
            self.changed[cid] = b
        hero = next((b for b in self.blocks if b.key == "subtitle"), None)
        for alias in (b for b in self.blocks if b.key in self.parts_of_subtitle):
            if hero and (hero.change or alias.change):
                if hero.change and alias.change and hero.change != alias.change:
                    raise ValueError("Subtitle and its visible text have overlapping edits")
                edited, other = (hero, alias) if hero.change else (alias, hero)
                other.text, other.state, other.change = edited.text, edited.state, edited.change

    def bind_design(self, block: Block, fields: list[str], attributes: list[str]) -> None:
        mid = self.design_id(block.module)
        if self.has_design:
            allowed = set(id_list(str(self.design["modules"].get(mid, {}).get("field_ids", ""))))
            detail_fields = {fid for aid in attributes for fid in
                             id_list(str(self.design["attributes"].get(aid, {}).get("page_detail_fields", "")))}
            for fid in fields:
                if fid not in self.design["fields"] or (self.design["modules"] and fid not in allowed | detail_fields):
                    raise ValueError(f"Field {fid} does not belong to this page/module")
            for aid in attributes:
                if aid not in self.design["attributes"]:
                    raise ValueError(f"Attribute {aid} does not belong to this page")
        block.fields = list(dict.fromkeys([*block.fields, *fields]))
        block.attributes = list(dict.fromkeys([*block.attributes, *attributes]))

    def design_id(self, module: str) -> str:
        return str(self.modules.get(module, {}).get("design_module_id", module if module in self.design["modules"] else ""))

    def bind_sections(self, changes: list[dict[str, str]]) -> None:
        headings = {b.key: b for b in self.blocks if re.fullmatch("h[1-6]", b.kind)}
        for b in self.blocks:
            if b.key in headings:
                b.section = b.key
            elif b.heading and f"heading-{b.heading}" in headings:
                b.section = f"heading-{b.heading}"
        for row in changes:
            b = self.changed[row["change_id"]]
            anchor = row["under_heading"]
            if anchor:
                target = self.changed.get(anchor) or headings.get(anchor)
                if (b.kind != "body" or not target or target.key not in headings or
                        b.section and b.section != target.key or b.module and target.module != b.module):
                    raise ValueError(f"Body change {b.change} is bound to the wrong final heading")
                b.section, b.module = target.key, target.module
            elif b.kind == "body" and not b.section and b.module:
                options = [h for h in headings.values() if h.module == b.module and h.kind != "h1"]
                if len(options) == 1:
                    b.section = options[0].key
                elif len(options) > 1:
                    raise ValueError(f"Multiple headings in {b.module}; set under_heading for {b.change}")

    def design_refs(self, block: Block) -> list[str]:
        pairs = [("modules", self.design_id(block.module)),
                 *(("fields", key) for key in block.fields), *(("attributes", key) for key in block.attributes)]
        return [f"{row['source_file']}#{row['source_row']}" for kind, key in pairs
                if (row := self.design[kind].get(key))]

    def retained(self, kind: str, expression: str, index: object, block_id: str, module: str) -> Block:
        matches = [b for b in self.blocks if not b.change and b.kind == kind and has_text(expression, b.text)
                   and (index is None or index == b.heading) and (not block_id or b.key == block_id)]
        if len(matches) > 1 and module:
            matches = [b for b in matches if b.module == module]
        if len(matches) != 1:
            raise ValueError(f"Retained {kind} expression is missing or ambiguous in final copy: {expression}")
        return matches[0]

    def placement_block(self, row: dict[str, object], kind: str, expression: str, cid: str) -> Block:
        if not cid:
            return self.retained(kind, expression, row.get("heading_index"), str(row.get("block_id", "")), str(row.get("module_id", "")))
        block = self.changed.get(cid)
        if block is None or block.kind != kind or not has_text(expression, block.text):
            raise ValueError(f"Placement expression/field does not match final change {cid}: {expression}")
        if row.get("block_id"):
            raise ValueError("Use block_id for a retained placement or change_id for an edit")
        return block

    def prepare_placements(self, placements: list[dict[str, object]]) -> None:
        """All uses of one visible paragraph share its business facts, regardless of row order."""
        for row in placements:
            if row.get("location") == "not_used":
                continue
            if any(row.get(k) for k in ("field_ids", "attribute_ids", "claim_ids", "answer_claim_ids")):
                kind = string(row.get("location"))
                b = self.placement_block(row, "body" if kind == "intro" else kind, string(row.get("expression")), str(row.get("change_id", "")))
                self.bind_design(b, strings(row.get("field_ids", [])), strings(row.get("attribute_ids", [])))
                b.claims.update(strings(row.get("claim_ids", [])))
                if row.get("answer_claim_ids"):
                    ac, ab = str(row.get("answer_change_id", "")), str(row.get("answer_block_id", ""))
                    answer = self.changed.get(ac) if ac else next((p for p in self.blocks if p.key == ab and not p.change), None)
                    if answer is None:
                        raise ValueError("answer_claim_ids requires an actual supporting answer block")
                    answer.claims.update(strings(row["answer_claim_ids"]))
        aliases = [b for b in self.blocks if b.key == "subtitle" or b.key in self.parts_of_subtitle]
        if len(aliases) > 1:
            shared = set.union(*(b.claims for b in aliases))
            fields = list(dict.fromkeys(fid for b in aliases for fid in b.fields))
            attrs = list(dict.fromkeys(aid for b in aliases for aid in b.attributes))
            for b in aliases:
                b.claims.update(shared)
                b.fields, b.attributes = fields.copy(), attrs.copy()
        for b in self.blocks:
            if b.claims - self.claims.keys():
                raise ValueError(f"Unknown claim_id on final copy {b.change or b.key}")
            private_field = any(query_key(str(self.design["fields"].get(fid, {}).get("value_status", ""))) in
                                {"internal_only", "private", "contradicted"} for fid in b.fields)
            if any(not self.claims[c] for c in b.claims) or private_field and not b.claims:
                if b.change and b.state == "ready":
                    raise ValueError(f"Ready copy {b.change} requires an approved public claim for its restricted facts")
                b.state = "blocked"

    def placement(self, row: dict[str, object], kind: str, expression: str, cid: str,
                  required_modules: set[str], answer_kind: str) -> dict[str, str]:
        if kind == "not_used":
            return {**dict.fromkeys(PLACEMENT_DETAIL, ""), "copy_state": "not_used"}
        declared = str(row.get("module_id", ""))
        block = self.placement_block(row, kind, expression, cid)
        if declared and declared != block.module or required_modules and block.module and block.module not in required_modules:
            raise ValueError(f"Keyword placement points to the wrong brief module: {row['keyword']} → {block.module or block.key}")
        answer = block
        ac, ab = str(row.get("answer_change_id", "")), str(row.get("answer_block_id", ""))
        if ac and ab:
            raise ValueError("Select one final answer change or retained block")
        if ac or ab:
            selected = self.changed.get(ac) if ac else next((b for b in self.blocks if b.key == ab and not b.change), None)
            if (selected is None or selected.kind not in {"body", "subtitle"} or not block.module or
                    selected.module != block.module or re.fullmatch("h[2-6]", kind) and selected.section != block.key):
                raise ValueError(f"Supporting answer must be final text in the same brief module: {row['keyword']}")
            answer = selected
        quote = string(row["answer_quote"]) if "answer_quote" in row else answer.text
        if not has_text(quote, answer.text):
            raise ValueError(f"Answer quote not found in the final section: {row['keyword']}")
        answer_state = ("blocked" if "blocked" in (block.state, answer.state) else
                        "ready" if "ready" in (block.state, answer.state) else "preserved_snapshot_text")
        if block.key == "unscoped-text" or answer.key == "unscoped-text" or required_modules and not block.module:
            answer_state = "module_unconfirmed"
        elif not (ac or ab) and (re.fullmatch(r"h[2-6]", kind)
                                 or answer_kind == "detail" and kind not in {"body", "subtitle"}):
            answer_state = "heading_only"
        has_answer = answer_state not in {"heading_only", "module_unconfirmed"}
        return {"module_id": block.module, "design_module_id": self.design_id(block.module), "block_id": block.key,
                "final_text": block.text if block.key != "unscoped-text" else expression,
                "answer_ref": (answer.change or answer.key) if has_answer else "", "answer_text": quote if has_answer else "",
                "answer_state": answer_state, "field_ids": " | ".join(dict.fromkeys([*block.fields, *answer.fields])),
                "attribute_ids": " | ".join(dict.fromkeys([*block.attributes, *answer.attributes])),
                "design_refs": " | ".join(dict.fromkeys([*self.design_refs(block), *self.design_refs(answer)])),
                "copy_state": block.state}

    def design_coverage(self, placements: list[dict[str, str]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for kind, records_by_id in self.design.items():
            for key, record in records_by_id.items():
                uses = [b for b in self.blocks if b.key != "unscoped-text" and b.key not in self.parts_of_subtitle and key in
                        ([self.design_id(b.module)] if kind == "modules" else b.fields if kind == "fields" else b.attributes)]
                refs = {v for b in uses for v in (b.key, b.change) if v}
                terms = [p["keyword"] for p in placements if p["block_id"] in refs or p["answer_ref"] in refs]
                state = ("content_gap" if not uses else "incomplete_answer" if all(re.fullmatch("h[2-6]", b.kind) for b in uses)
                         else "draft_pending_confirmation" if any(b.state == "blocked" for b in uses) else "ready")
                result.append({"kind": kind, "id": key, "name": str(record.get("name") or record.get("label") or key),
                               "source_ref": f"{record['source_file']}#{record['source_row']}",
                               "condition": str(record.get("condition", "")), "missing_policy": str(record.get("missing_policy", "")),
                               "source_status": str(record.get("value_status") or record.get("source_status") or record.get("filter_status") or ""),
                               "copy_status": state, "block_refs": "\n".join(b.change or b.key for b in uses),
                               "final_text": "\n".join(b.text for b in uses), "keywords": "\n".join(dict.fromkeys(terms))})
        return result

    def render(self, design_rows: list[dict[str, str]]) -> str:
        labels = {"ready": "可用稿", "blocked": "待确认稿", "preserved_snapshot_text": "保留原文"}
        lines = ["# 最终页面稿", ""]

        def write(b: Block) -> None:
            label = {"title": "SEO Title", "subtitle": "Subtitle", "body": "正文", "description": "Meta description"}.get(b.kind, b.kind.upper())
            lines.extend([f"**{label}**（{labels[b.state]}） · {b.change or b.key}", "", b.text, ""])

        for kind in ("title", "description", "h1", "subtitle"):
            for b in self.blocks:
                if b.kind == kind and b.text:
                    write(b)
        sections = [b for b in self.blocks if b.kind not in {"title", "description", "h1", "subtitle"}
                    and b.key not in self.parts_of_subtitle and b.key != "unscoped-text"
                    and (b.kind == "body" or re.fullmatch("h[2-6]", b.kind) or b.change)]
        design_order = list(self.design["modules"])
        ordered = sorted(self.modules, key=lambda mid: design_order.index(self.design_id(mid))
                         if self.design_id(mid) in design_order else len(design_order))
        assigned: dict[str, list[Block]] = {}
        nearby: dict[str, list[Block]] = {}
        preceding = self.hero
        for b in sections:
            if b.module:
                assigned.setdefault(b.module, []).append(b)
                if not b.key.startswith("new-"):
                    preceding = b.module
            elif b.text:
                nearby.setdefault(preceding, []).append(b)
        for b in nearby.pop("", []):
            write(b)
        for mid in ordered:
            blocks = assigned.get(mid, [])
            if blocks:
                title = str(self.modules[mid]["heading"]) if mid else "其他可定位的原文与改动"
                if not any(b.kind.startswith("h") and b.text == title for b in blocks):
                    lines.extend([f"## {title}", ""])
                headings = {b.key for b in blocks if re.fullmatch("h[2-6]", b.kind)}
                for b in blocks:
                    if b.kind == "body" and b.section in headings:
                        continue
                    write(b)
                    if b.key in headings:
                        for paragraph in blocks:
                            if paragraph.kind == "body" and paragraph.section == b.key:
                                write(paragraph)
            for b in nearby.get(mid, []):
                write(b)
        if any(b.key == "unscoped-text" and b.text.strip() for b in self.blocks):
            lines += ["旧快照中的整页纯文本缺少段落位置。已定位的改稿见上文，保留段落可从原始 HTML 补取。", ""]
        if self.has_design:
            lines.extend(["## 上游规划的落实情况", ""])
            kinds = {"modules": "模块", "fields": "字段", "attributes": "产品属性"}
            for row in design_rows:
                loc = row["block_refs"].replace("\n", "、") or "尚无对应文案"
                notes = " · ".join(row[k] for k in ("condition", "source_status", "missing_policy") if row[k])
                lines.append(f"- {kinds[row['kind']]} {row['id']} · {row['name']} · {loc} · {row['source_ref']}"
                             + (f" · {notes}" if notes else ""))
            lines.extend(f"- {gap}" for gap in self.design_gaps)
        return "\n".join(lines).rstrip() + "\n"
