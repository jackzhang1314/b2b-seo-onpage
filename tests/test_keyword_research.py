"""Public CLI regressions for a simulated B2B collection and its adjacent page."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from typing import Any
from zipfile import ZipFile

CLI = Path(__file__).resolve().parents[1] / "skills/b2b-seo-onpage/scripts/onpage.py"
PAGE = "https://customer.example/collections/cases/"
HOME = "https://exporter.example/"
PEER = HOME + "phone-cases/"
OTHER = PAGE + "stock/"
CONTEXT = {"target_url": PAGE, "keyword": "phone cases", "market": "US", "language": "en"}


class KeywordResearchTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.table("pages.csv", [["id", "url", "page_type", "primary_keyword", "market", "language"],
                                ["P1", PAGE, "collection", "phone cases", "US", "en"]])
        self.table("map.csv", [["owner_page_id", "target_url", "keyword", "market", "language"],
                               ["P1", PAGE, "phone cases", "US", "en"], ["P1", PAGE, "cases for brands", "US", "en"],
                               ["P2", OTHER, "stock cases", "US", "en"]])
        self.table("library.csv", [["keyword_id", "keyword_original", "market", "language"],
                                   ["1", "phone cases", "US", "en"], ["2", "private label covers", "US", "en"],
                                   ["3", "stock cases", "US", "en"], ["4", "handset sleeves", "US", "en"],
                                   ["5", "sleevestring", "US", "en"]])
        self.table("ranking-observations.csv", [["keyword_id", "url", "position", "market", "observed_at"],
                   ["2", PEER, "81", "US", "2026-11-01"], ["3", PEER, "16", "US", "2026-11-01"],
                   ["2", HOME, "4", "US", "2026-11-01"], ["3", PEER, "2", "CA", "2026-11-01"],
                   ["8", PEER.rstrip("/"), "7", "US", "2026-11-01"], ["9", PEER + "?sort=a", "5", "US", "2026-11-01"],
                   ["6", PEER, "5", "US", "2026-10-01"]])
        self.table("export.csv", [["Keyword", "URL", "Position", "Country", "Date"],
                   ["Private Label Covers", PEER + "#hero", "41", "US", "2026-11-01"],
                   ["untagged market", PEER, "19", "", "2026-11-01"]])

    def table(self, name: str, records: list[list[str]]) -> None:
        with (self.root / name).open("w", encoding="utf-8-sig", newline="") as stream:
            csv.writer(stream).writerows(records)

    def save(self, name: str, data: object) -> None:
        (self.root / name).write_text(json.dumps(data), encoding="utf-8")

    def read(self, name: str) -> Any:
        return json.loads((self.root / name).read_text(encoding="utf-8"))

    def run_cli(self, *args: str, error: str = "") -> None:
        result = subprocess.run([sys.executable, "-B", str(CLI), *args], cwd=self.root, text=True, capture_output=True)
        if error:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, result.stderr)
        else:
            self.assertEqual(result.returncode, 0, result.stderr)

    def inventory(self) -> dict[str, Any]:
        self.run_cli("architecture-page", "--source", ".", "--page-id", "P1", "--keyword-map", "map.csv",
                     "--library", "library.csv", "--peer-url", PEER, "--peer-url", HOME + "absent/",
                     "--rankings", "ranking-observations.csv", "--rankings", "export.csv", "--library-term", "sleeves",
                     "--ranking-date", "2026-11-01", "--out", "input")
        return self.read("input/architecture-page.json")["keyword_inventory"]

    def test_url_lookup_preserves_original_sources_scope_and_ownership(self) -> None:
        data = self.inventory()
        self.assertEqual(data["peer_url_matches"], {PEER: 3, HOME + "absent/": 0})
        self.assertEqual(len(data["unresolved_ranking_rows"]), 1)
        words = {r["keyword"].casefold(): r for r in data["candidates"]}
        self.assertEqual(set(words), {"phone cases", "cases for brands", "private label covers", "stock cases", "handset sleeves"})
        private = words["private label covers"]
        self.assertEqual([r["input_csv_row"] for r in private["rankings"]], ["2", "2"])
        self.assertEqual([r["input_csv_file"] for r in private["rankings"]], ["ranking-observations.csv", "export.csv"])
        self.assertEqual(private["library_matches"][0]["keyword_id"], "2")
        self.assertEqual(words["stock cases"]["ownership"], "other_page")
        self.assertEqual(words["stock cases"]["owner_rows"][0]["target_url"], OTHER)

    def test_typed_subtitle_uses_the_visible_observation(self) -> None:
        (self.root / "page.html").write_text("<html><head><title>Cases</title></head><body><h1>Cases</h1>"
                                             "<p>Trade orders</p><footer>Retail orders</footer></body></html>")
        self.save("hero.json", {"target_url": PAGE, "text": "Trade orders", "tag": "p", "source_ref": "visible hero"})
        self.run_cli("inspect", "--html", "page.html", "--url", PAGE, "--keyword", "phone cases", "--market", "US",
                     "--language", "en", "--collected-at", "2026-11-01", "--stage", "supplied_html",
                     "--subtitle", "hero.json", "--out", "capture")
        self.save("change.json", {**CONTEXT, "changes": [{"change_id": "hero", "field": "subtitle",
                 "after": "Retail orders", "copy_state": "ready"}]})
        self.run_cli("compare", "--after", "capture/page-evidence.json", "--plan", "change.json", "--out", "compare")
        with (self.root / "compare/implementation-observations.csv").open(encoding="utf-8-sig") as f:
            self.assertNotEqual(next(csv.DictReader(f))["observation"], "observed_in_snapshot")

    def research_plan(self) -> dict[str, Any]:
        self.inventory()
        self.save("page.json", {**CONTEXT, "input_kind": "html", "head_seen": True, "head": {"title": ["Phone Cases"]},
                                "headings": [{"tag": "h1", "text": "Phone Cases"}], "text": "Phone Cases",
                                "subtitle": {"text": "", "tag": "", "source_ref": "hero without a subtitle"}})
        source_ids = ["library", "page_plan", "competitor", "serp", "keyword_group"]
        sources = [{"id": k, "kind": k, "source": "simulated " + k, "path": "map.csv", "collected_at": "2026-11-01"}
                   for k in source_ids]
        hit = {"url": HOME, "position": 13, "page_type": "home", "title": "Factory", "evidence_refs": ["serp#13"]}
        query = {"query": "phone case factory", "source": "local provider fixture", "position_kind": "provider_order",
                 "actual_market": "US", "actual_language": "en", "coverage": "complete", "results": [hit]}
        skip = {"url": "https://retail.example/", "position": 1, "page_type": "b2c", "screening": "skip",
                "screening_reason": "single-piece checkout", "evidence_refs": ["serp#1"]}
        peer = {"company": "Exporter", "site_type": "export_b2b_independent", "business_evidence": "OEM export to brands",
                "page_type": "collection", "discovery_source": "search", "discovery_url": HOME, "url": PEER,
                "read_state": "read", "selection_reason": "same product range", "observed_strengths": "OEM terms",
                "page_gap": "private label", "recommendation": "cover brand packaging", "evidence_refs": ["competitor#hero"],
                "seo_title": "OEM Phone Cases", "h1": "Phone Cases", "subtitle": "Brand supply", "subtitle_tag": "p",
                "h2": ["Materials", "Retail packaging"]}
        decisions = []
        for keyword, choice, group in [("phone cases","include","case"),("cases for brands","include","case"),
                                       ("private label covers","include","label"),("stock cases","other_page","stock"),
                                       ("handset sleeves","exclude","sleeves")]:
            decisions.append({"keyword": keyword, "decision": choice, "origin": "library", "intent_group": group,
                              "reason": "simulated scope", "module_ids": ["hero"] if choice == "include" else [],
                              "evidence_refs": ["library#input"], **({"target_url": OTHER} if choice == "other_page" else {})})
        return {**CONTEXT, "intent_fit": "fit", "intent_reason": "brand collection", "focus": {"scope": "full_page",
            "page_role": "collection", "buyer_task": "order cases", "primary_keyword": "phone cases",
            "secondary_keywords": ["cases for brands", "private label covers"]},
            "research": {**CONTEXT, "evidence_class": "simulation", "sources": sources,
                "library": {"coverage": "complete", "source_refs": ["library"], "source_kinds": ["customer_curated", "competitor_rankings"],
                            "competitors": ["exporter.example"], "rank_cutoff": 100},
                "serp": {"coverage": "complete", "queries": [{**query, "results": [skip, hit]},
                         {**query, "query": "custom phone case manufacturer", "results": [{**hit, "position": 1}]}]},
                "competitor_coverage": {"coverage": "complete"}, "competitor_pages": [peer], "keyword_decisions": decisions,
                "brief": {"page_role": "collection", "audience": "brands", "intent": "buy cases", "angle": "customization",
                          "modules": [{"id": "hero", "heading": "Custom phone cases", "task": "Explain private label",
                                       "evidence_refs": ["competitor"]}]}},
            "claims": [], "changes": [{"change_id": "subtitle", "field": "subtitle", "before": "",
               "after": "Private label covers and cases for brands.", "placement": "Under product H1", "reason": "company offering",
               "priority": "P1", "copy_state": "ready", "evidence_refs": ["page_plan"]}],
            "keyword_placement": [{"keyword": "phone cases", "role": "primary", "location": "h1", "source_ref": "page#h1",
                                    "expression": "Phone Cases", "reason": "in range"},
                *[{"keyword": kw, "role": "secondary", "location": "subtitle", "expression": kw, "change_id": "subtitle",
                   "reason": "one sentence covers related phrases"} for kw in ["cases for brands","private label covers"]]]}

    def check(self, plan: dict[str, Any], error: str = "") -> None:
        self.save("plan.json", plan)
        self.run_cli("check-plan", "--evidence", "page.json", "--plan", "plan.json",
                     "--architecture-page", "input/architecture-page.json", "--out", "report", error=error)

    def test_full_export_reports_new_terms_and_distinct_intents(self) -> None:
        self.check(self.research_plan())
        summary = self.read("report/run.json")
        self.assertEqual(summary["research_status"], "simulation")
        self.assertEqual(summary["keyword_coverage"], {"planned_terms": 2, "evaluated_planned_terms": 2,
                         "planned_with_text": 2, "placed_planned_terms": 2, "added_with_text": 1, "added_placed_terms": 1,
                         "draft_added_intents": 1, "added_intents": 1, "already_in_copy": 0, "new_copy_terms": 1})
        self.assertTrue(any("还原" in gap for gap in summary["research_gaps"]))
        with (self.root / "report/serp-results.csv").open(encoding="utf-8-sig") as f:
            self.assertEqual([(r["position_kind"],r["position"]) for r in csv.DictReader(f)],
                             [("provider_order","1"),("provider_order","13"),("provider_order","1")])
        with (self.root / "report/competitor-comparison.csv").open(encoding="utf-8-sig") as f:
            peer = next(csv.DictReader(f))
            self.assertEqual((peer["discovery_url"],peer["url"],peer["subtitle_tag"]), (HOME,PEER,"p"))
        with ZipFile(self.root / "report/keyword-coverage.xlsx") as book:
            self.assertIn(b"Private label covers".lower(),book.read("xl/worksheets/sheet1.xml").lower())

    def test_draft_only_has_text_but_needs_confirmation(self) -> None:
        plan = self.research_plan()
        plan["changes"][0]["copy_state"] = "blocked"
        self.check(plan)
        counts = self.read("report/run.json")["keyword_coverage"]
        self.assertEqual((counts["planned_with_text"], counts["placed_planned_terms"]), (2, 1))
        self.assertEqual((counts["added_with_text"], counts["added_placed_terms"]), (1, 0))
        self.assertEqual((counts["draft_added_intents"], counts["added_intents"]), (1, 0))
        with (self.root / "report/keyword-coverage.csv").open(encoding="utf-8-sig") as f:
            entries = {r["keyword"].casefold(): r for r in csv.DictReader(f)}
        self.assertEqual(entries["private label covers"]["copy_status"], "draft_pending_confirmation")
        self.assertEqual(entries["private label covers"]["copy_states"], "blocked")
        report = (self.root / "report/onpage-review.md").read_text()
        preview = report.split("## 本页标题与首屏文案")[1].split("\n## ")[0]
        self.assertIn("**H1**（原页） Phone Cases", preview)
        self.assertIn("**Subtitle**（待确认稿） Private label covers", preview)

    def test_new_subtitle_requires_an_observation_of_the_hero(self) -> None:
        plan = self.research_plan()
        evidence = self.read("page.json")
        del evidence["subtitle"]
        self.save("page.json", evidence)
        self.check(plan, "Record the visible hero")

    def section_plan(self) -> dict[str, Any]:
        plan = self.research_plan()
        ev = self.read("page.json")
        ev.update(headings=[{"tag": "h1", "text": "Phone Cases"}, {"tag": "h2", "text": "Materials"},
                            {"tag": "h2", "text": "Print options"}],
                  content_blocks=[{"block_id": "body-1", "heading_index": "2", "text": "TPU is available."},
                                  {"block_id": "body-2", "heading_index": "3", "text": "We print your logo on the case."}],
                  text="Phone Cases Materials TPU is available. Print options We print your logo on the case.")
        self.save("page.json", ev)
        modules = plan["research"]["brief"]["modules"]
        modules[0]["source_heading_index"] = 1
        modules.extend([{"id": mid, "source_heading_index": idx, "heading": title, "task": task, "evidence_refs": ["page_plan"]}
                        for mid, idx, title, task in [("materials", 2, "Materials", "Select material"),
                                                    ("printing", 3, "Print options", "Specify branding")]])
        plan["changes"][0]["module_id"] = "hero"
        keyword = "private label phone case manufacturer"
        plan["focus"]["secondary_keywords"].append(keyword)
        plan["research"]["keyword_decisions"].append({"keyword": keyword, "origin": "web", "decision": "include",
            "intent_group": "manufacturer with branding", "module_ids": ["hero", "printing"], "answer_kind": "detail",
            "reason": "Supplier identity and branding", "evidence_refs": ["competitor#hero"]})
        plan["keyword_placement"].append({"keyword": keyword, "role": "secondary", "location": "h2",
            "source_ref": "page#heading-3", "heading_index": 3, "expression": "Print options", "answer_block_id": "body-2",
            "answer_quote": "print your logo", "reason": "Explains what the buyer can brand"})
        return plan

    def coverage(self) -> dict[str, dict[str, str]]:
        with (self.root / "report/keyword-coverage.csv").open(encoding="utf-8-sig") as stream:
            return {row["keyword"].casefold(): row for row in csv.DictReader(stream)}

    def test_retained_h1_cannot_survive_replacement_or_retagging(self) -> None:
        plan = self.section_plan()
        change = {"change_id": "new-h1", "field": "h1", "heading_index": 1, "before": "Phone Cases",
                  "after": "Our Collection", "reason": "Change the hero", "priority": "P1", "copy_state": "ready",
                  "evidence_refs": ["page_plan"]}
        plan["changes"].append(change)
        self.check(plan, "missing or ambiguous in final copy")
        change.update(after="Phone Cases", after_tag="h2")
        self.check(plan, "missing or ambiguous in final copy")
        self.assertFalse((self.root / "report").exists())

    def test_label_query_cannot_point_to_materials(self) -> None:
        plan = self.section_plan()
        row = plan["keyword_placement"][-1]
        row.update(heading_index=2, expression="Materials")
        self.check(plan, "wrong brief module")
        row.update(heading_index=3, expression="Print options", answer_block_id="body-1")
        self.check(plan, "same brief module")
        row.update(answer_block_id="body-2", answer_quote="orders of 500")
        self.check(plan, "Answer quote not found")

    def test_a_heading_alone_and_half_a_compound_query_are_not_answers(self) -> None:
        plan = self.section_plan()
        row = plan["keyword_placement"][-1]
        del row["answer_block_id"], row["answer_quote"]
        self.check(plan)
        coverage = self.coverage()[row["keyword"]]
        self.assertEqual((coverage["source_pool"], coverage["copy_status"], coverage["answer_state"]),
                         ("research_only", "incomplete_answer", "heading_only"))
        self.assertEqual(set(coverage["missing_answers"].split(" | ")), {"hero", "printing"})
        self.assertEqual(coverage["observed_peer_urls"], PEER)

    def test_compound_phrase_uses_both_final_answers_and_respects_private_copy(self) -> None:
        plan = self.section_plan()
        keyword = plan["keyword_placement"][-1]["keyword"]
        subtitle = plan["changes"][0]
        subtitle.update(after=subtitle["after"] + " We manufacture the cases.", copy_state="blocked")
        plan["keyword_placement"].append({"keyword": keyword, "role": "secondary", "location": "subtitle",
            "expression": "We manufacture the cases.", "change_id": "subtitle", "reason": "Identifies manufacturer"})
        self.check(plan)
        row = self.coverage()[keyword]
        self.assertEqual(row["copy_status"], "draft_pending_confirmation")
        self.assertFalse(row["missing_answers"])
        self.assertIn("print your logo", row["answer_text"])
        self.assertIn("We manufacture the cases.", row["answer_text"])
        self.assertEqual(row["metrics"], "")
        draft = (self.root / "report/page-copy.md").read_text()
        self.assertLess(draft.index("TPU is available."), draft.index("We print your logo on the case."))
        self.assertIn("We manufacture the cases.", draft)
        with ZipFile(self.root / "report/keyword-coverage.xlsx") as book:
            self.assertIn(keyword.encode(), book.read("xl/worksheets/sheet1.xml"))

    def test_answer_cannot_point_to_a_different_heading_in_the_same_brief_module(self) -> None:
        plan = self.section_plan()
        ev = self.read("page.json")
        ev["headings"].append({"tag": "h3", "text": "Box sizes"})
        ev["content_blocks"].append({"block_id": "body-3", "heading_index": "4", "text": "Choose a box size."})
        self.save("page.json", ev)
        plan["keyword_placement"][-1].update(answer_block_id="body-3", answer_quote="box")
        self.check(plan, "same brief module")

    def test_replaced_body_cannot_be_used_as_a_retained_answer(self) -> None:
        plan = self.section_plan()
        plan["changes"].append({"change_id": "rewrite-print", "module_id": "printing", "field": "body", "source_block_id": "body-2",
            "before": "We print your logo on the case.", "after": "Ask us about branding.", "priority": "P1",
            "copy_state": "ready", "reason": "Replace the original detail", "evidence_refs": ["page_plan"]})
        self.check(plan, "same brief module")

    def test_design_handoff_scopes_modules_fields_and_attributes_to_the_page(self) -> None:
        self.table("pages.csv", [["id", "url", "page_type", "template_id", "variant", "market", "language"],
                                ["P1", PAGE, "collection", "CASE", "made-to-order", "US", "en"]])
        self.table("design-modules.csv", [["template_id", "id", "order", "variants", "field_ids", "condition"],
                  ["CASE", "print", "2", "made-to-order", "logo", "Confirmed service"], ["CASE", "hero", "1", "", "quote", ""],
                  ["CASE", "stock", "1", "stock", "stock-level", ""], ["OTHER", "unrelated", "1", "", "colour", ""]])
        self.table("design-fields.csv", [["template_id", "id", "value_status"], ["CASE", "logo", "internal"],
                   ["SITE", "quote", "missing"], ["CASE", "stock-level", "missing"], ["OTHER", "colour", ""]])
        self.table("product-attributes.csv", [["id", "filter_page_ids", "detail_bindings"], ["material", "P1", ""],
                   ["case-depth", "", '[{"template_id":"OTHER","field_id":"depth"}]']])
        plan = self.research_plan()
        d = self.read("input/architecture-page.json")["page_design"]
        self.assertEqual([r["id"] for r in d["modules"]], ["hero", "print"])
        self.assertEqual({r["id"] for r in d["fields"]}, {"logo", "quote"})
        self.assertEqual([r["id"] for r in d["attributes"]], ["material"])
        plan["changes"][0].update(module_id="hero", field_ids=["logo"])
        self.check(plan, "does not belong to this page/module")
        plan["changes"][0].update(field_ids=["quote"], attribute_ids=["case-depth"])
        self.check(plan, "does not belong to this page")
        plan["changes"][0].update(attribute_ids=["material"], copy_state="blocked")
        self.check(plan)
        with (self.root / "report/page-design-coverage.csv").open(encoding="utf-8-sig") as stream:
            rows = {row["id"]: row for row in csv.DictReader(stream)}
        self.assertEqual(rows["logo"]["copy_status"], "content_gap")
        self.assertEqual(rows["quote"]["copy_status"], "draft_pending_confirmation")
        self.assertIn("private label covers", rows["material"]["keywords"])
        self.assertIn("Private label covers", rows["quote"]["final_text"])
        with ZipFile(self.root / "report/keyword-coverage.xlsx") as book:
            self.assertIn("上游模块与字段".encode(), book.read("xl/workbook.xml"))
            self.assertIn(b"design-fields.csv#3", book.read("xl/worksheets/sheet2.xml"))
        row = self.coverage()["private label covers"]
        self.assertEqual((row["design_module_id"], row["field_ids"], row["attribute_ids"]), ("hero", "quote", "material"))

    def test_shared_template_without_eligible_modules_does_not_leak_fields(self) -> None:
        self.table("pages.csv", [["id", "url", "page_type", "template_id", "variant"], ["P1", PAGE, "collection", "T", "custom"]])
        self.table("design-modules.csv", [["id","template_id","variants","field_ids"], ["stock","T","stock","stock_qty"]])
        self.table("design-fields.csv", [["id","template_id"], ["stock_qty","T"]])
        self.run_cli("architecture-page", "--source", ".", "--page-id", "P1", "--out", "input")
        result = self.read("input/architecture-page.json")["page_design"]
        self.assertEqual((result["fields"], result["modules"]), ([], []))

    def test_kept_private_fact_is_pending_for_all_queries_and_the_design_sheet(self) -> None:
        plan = self.section_plan()
        snapshot = self.read("input/architecture-page.json")
        snapshot["page_design"] = {"modules": [{"id":"printing","field_ids":"logo","source_file":"design-modules.csv","source_row":"2"}],
                                   "fields": [{"id":"logo","value_status":"internal_only","source_file":"design-fields.csv","source_row":"2"}]}
        self.save("input/architecture-page.json", snapshot)
        plan["claims"] = [{"claim_id":"print","text":"We print on cases.","source_ref":"page_plan#production",
                           "verification_state":"user_provided","public_use_state":"internal_only"}]
        for name in ("logo printing", "logo printed cases"):
            plan["focus"]["secondary_keywords"].append(name)
            plan["research"]["keyword_decisions"].append({"keyword":name,"origin":"web","decision":"include","intent_group":"printing",
                 "module_ids":["printing"],"reason":"Check printing","evidence_refs":["competitor#hero"]})
            plan["keyword_placement"].append({"keyword":name,"role":"secondary","location":"body","block_id":"body-2",
                 "expression":"print your logo","source_ref":"page#body-2","reason":"Existing draft",
                 **({"claim_ids":["print"],"field_ids":["logo"]} if name=="logo printed cases" else {})})
        self.check(plan)
        coverage = self.coverage()
        for name in ("logo printing","logo printed cases"):
            self.assertEqual(coverage[name]["copy_status"], "draft_pending_confirmation")
        with (self.root / "report/page-design-coverage.csv").open(encoding="utf-8-sig") as f:
            self.assertEqual({row["copy_status"] for row in csv.DictReader(f)}, {"draft_pending_confirmation"})
        self.assertIn("**正文**（待确认稿） · body-2", (self.root / "report/page-copy.md").read_text())

    def test_original_group_cannot_disappear_before_copywriting(self) -> None:
        plan = self.research_plan()
        plan["research"]["keyword_decisions"].pop(1)
        plan["focus"]["secondary_keywords"].pop(0)
        plan["keyword_placement"].pop(1)
        self.check(plan, "Missing inventory decision")
        self.assertFalse((self.root / "report").exists())

    def test_retail_result_cannot_substitute_for_a_qualified_peer(self) -> None:
        plan = self.research_plan()
        peer = plan["research"]["competitor_pages"][0]
        peer["site_type"] = "retail"
        self.check(plan, "qualified export B2B")
        peer["site_type"] = "export_b2b_independent"
        peer["discovery_url"] = "https://retail.example/"
        self.check(plan, "non-skipped")

    def test_rank_only_addition_cannot_borrow_homepage_evidence(self) -> None:
        plan = self.research_plan()
        plan["research"]["competitor_pages"][0]["url"] = HOME
        self.check(plan, "actual reviewed URL")

    def test_other_page_cannot_be_silently_reassigned(self) -> None:
        plan = self.research_plan()
        decision = plan["research"]["keyword_decisions"][3]
        decision.update(decision="include", module_ids=["hero"])
        del decision["target_url"]
        self.check(plan, "Existing ownership needs review")

    def test_comparison_export_keeps_current_url_and_position(self) -> None:
        with (self.root / "comparison.tsv").open("w", encoding="utf-16", newline="") as stream:
            csv.writer(stream, delimiter="\t").writerows([
                ["Keyword", "Previous URL", "Current URL", "Previous position", "Current position", "Report Date"],
                ["case assembly", HOME, PEER, "5", "84", "2026-11-01"],
                ["old owner", PEER, HOME, "6", "62", "2026-11-01"]])
        (self.root / "other.csv").write_text(f'关键词;排名 URL;当前排名;数据日期\n"case; printed";{PEER};53;2026-11-01\n')
        self.run_cli("architecture-page", "--source", ".", "--page-id", "P1", "--peer-url", PEER, "--rankings",
                     "comparison.tsv", "--rankings", "other.csv", "--ranking-date", "2026-11-01", "--out", "mixed")
        rows = {c["keyword"]: c for c in self.read("mixed/architecture-page.json")["keyword_inventory"]["candidates"]}
        self.assertNotIn("old owner", rows)
        self.assertEqual(rows["case assembly"]["rankings"][0]["reported_position"], "84")
        self.assertEqual(rows["case; printed"]["rankings"][0]["reported_position"], "53")

    def test_raw_snapshot_ranking_fields_survive_csv_and_workbook(self) -> None:
        plan = self.research_plan()
        snapshot = self.read("input/architecture-page.json")
        addition = next(c for c in snapshot["keyword_inventory"]["candidates"]
                        if c["keyword"].casefold() == "private label covers")
        for row in addition["rankings"]:
            for key in ("reported_position", "reported_date"):
                row.pop(key)
        self.save("input/architecture-page.json", snapshot)
        self.check(plan)
        with (self.root / "report/keyword-coverage.csv").open(encoding="utf-8-sig") as stream:
            ref = next(r["ranking_refs"] for r in csv.DictReader(stream) if r["keyword"].casefold() == "private label covers")
        with ZipFile(self.root / "report/keyword-coverage.xlsx") as book:
            sheet = book.read("xl/worksheets/sheet1.xml").decode()
        for detail in ("81 · 2026-11-01", "41 · 2026-11-01"):
            self.assertIn(detail, ref)
            self.assertIn(detail, sheet)

    def test_original_file_date_and_blank_market_are_auditable(self) -> None:
        self.table("source-cn.csv", [["关键词","排名URL","排名","国家","数据日期"],
                   ["current phrase", PEER, "96", "US", "2026-11-01"],
                   ["old phrase", PEER, "3", "US", "2026-09-01"],
                   ["missing locale", PEER, "4", "", "2026-11-01"]])
        self.run_cli("architecture-page","--source",".","--page-id","P1","--rankings","source-cn.csv",
                     "--ranking-date","2026-11-01","--peer-url",PEER,"--out","cn")
        inv = self.read("cn/architecture-page.json")["keyword_inventory"]
        self.assertEqual({r["keyword"] for r in inv["candidates"]}, {"phone cases","current phrase"})
        self.assertEqual(inv["unresolved_ranking_rows"][0]["关键词"], "missing locale")

    def test_target_page_and_market_cannot_be_substituted(self) -> None:
        plan = self.research_plan()
        note = self.read("input/architecture-page.json")
        note["page"]["url"] = OTHER
        self.save("input/architecture-page.json", note)
        self.check(plan, "Architecture page URL differs")
        note["page"]["url"] = PAGE
        note["keyword_inventory"]["market"] = "CA"
        self.save("input/architecture-page.json", note)
        self.check(plan, "Inventory market differs")

    def test_planned_page_without_url_uses_its_confirmed_id(self) -> None:
        plan = self.research_plan()
        note = self.read("input/architecture-page.json")
        note["page"]["url"] = ""
        note["keyword_inventory"]["page_url"] = ""
        self.save("input/architecture-page.json", note)
        self.check(plan, "confirmed focus.planned_page_id")
        plan["focus"]["planned_page_id"] = "P1"
        self.check(plan)

    def test_an_added_synonym_is_not_an_added_intent(self) -> None:
        plan = self.research_plan()
        plan["research"]["keyword_decisions"][2]["intent_group"] = "case"
        self.check(plan)
        metrics = self.read("report/run.json")["keyword_coverage"]
        self.assertEqual((metrics["added_placed_terms"],metrics["added_intents"]), (1,0))

    def test_new_intents_are_unknown_without_group_judgment(self) -> None:
        plan = self.research_plan()
        del plan["research"]["keyword_decisions"][0]["intent_group"]
        self.check(plan)
        self.assertIsNone(self.read("report/run.json")["keyword_coverage"]["added_intents"])

    def test_included_term_cannot_rely_only_on_a_skipped_result(self) -> None:
        plan = self.research_plan()
        row = plan["research"]["keyword_decisions"][2]
        row.update(origin="web", evidence_refs=["serp#1"])
        self.check(plan, "Skipped search results")

    def test_distinct_query_positions_reject_duplicates_within_one_snapshot(self) -> None:
        plan = self.research_plan()
        plan["research"]["serp"]["queries"][0]["results"][1]["position"] = 1
        self.check(plan, "unique positive positions")
