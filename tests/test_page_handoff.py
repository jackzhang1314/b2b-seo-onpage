"""Regressions for page ownership, exact heading placement, and absent customer libraries."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

CLI = Path(__file__).resolve().parents[1] / "skills/b2b-seo-onpage/scripts/onpage.py"
CONTEXT = {"target_url": "https://fixture.example/pins/", "keyword": "steel pins", "market": "UK", "language": "en"}


class PageHandoffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_cli(self, *args: str, success: bool = True) -> str:
        result = subprocess.run([sys.executable, "-B", str(CLI), *args], cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result.stderr

    def save(self, name: str, value: object) -> None:
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def table(self, name: str, rows: list[dict[str, str]]) -> None:
        with (self.root / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_article_and_filter_ownership_and_evidence_status_survive(self) -> None:
        url = CONTEXT["target_url"]
        self.table("pages.csv", [{"id": "P", "url": url, "page_type": "category"}])
        self.table("content-plan.csv", [{"id": "A", "url": url + "guide", "page_type": "article"}])
        self.table("keyword-decisions.csv", [
            {"page_id": "P", "keyword": "10 mm", "disposition": "filter"},
            {"page_id": "A", "keyword": "steel pin fit", "disposition": "section"}])
        self.save("architecture-plan.json", {"project": {"mode": "simulation"}})
        self.save("validation.json", {"research_complete": False})
        self.run_cli("architecture-page", "--source", ".", "--url", url + "guide/", "--out", "article")
        result = json.loads((self.root / "article/architecture-page.json").read_text())
        self.assertEqual(result["page"]["id"], "A")
        self.assertEqual(result["project"]["mode"], "simulation")
        self.assertIs(result["upstream_research_complete"], False)
        self.assertEqual([(r["keyword"], r["disposition"]) for r in result["keyword_decisions"]], [("steel pin fit", "section")])
        self.run_cli("architecture-page", "--source", ".", "--url", url.replace("fixture", "another"), "--out", "wrong", success=False)
        self.assertFalse((self.root / "wrong").exists())

    def test_duplicate_head_and_moved_heading_are_not_verified_at_requested_location(self) -> None:
        self.save("plan.json", {**CONTEXT, "changes": [
            {"change_id": "heading", "field": "h2", "heading_index": 2, "after": "Sizes"},
            {"change_id": "title", "field": "title", "after": "Steel Pins"}]})
        self.save("after.json", {**CONTEXT, "input_kind": "html", "head_seen": True,
            "head": {"title": ["Old title", "Steel Pins"]}, "headings": [
                {"tag": "h1", "text": "Steel Pins"}, {"tag": "h2", "text": "Specs"}, {"tag": "h2", "text": "Sizes"}]})
        self.run_cli("compare", "--after", "after.json", "--plan", "plan.json", "--out", "review")
        with (self.root / "review/implementation-observations.csv").open(encoding="utf-8-sig") as stream:
            self.assertEqual([r["observation"] for r in csv.DictReader(stream)], ["manual_check_required"] * 2)

    def test_independent_page_research_is_partial_and_checks_retained_heading(self) -> None:
        (self.root / "page.html").write_text("<html><head><title>Steel Pins</title></head><body><h1>Steel Pins</h1><h2>Pin sizes</h2></body></html>")
        self.run_cli("inspect", "--html", "page.html", "--url", CONTEXT["target_url"], "--keyword", CONTEXT["keyword"],
                     "--market", "UK", "--language", "en", "--collected-at", "2026-11-21", "--stage", "supplied_html", "--out", "before")
        (self.root / "review.txt").write_text("Fixture supplier page lists steel pins with dimensions.")
        sources = [{"id": kind, "kind": kind, "path": path, "source": "test fixture", "collected_at": "2026-11-21"}
                   for kind, path in (("site", "page.html"), ("competitor", "review.txt"))]
        focus = {"page_role": "category", "scope": "full_page", "primary_keyword": "steel pins", "buyer_task": "Choose a size"}
        research = {**CONTEXT, "evidence_class": "observed", "sources": sources,
                    "library": {"coverage": "unavailable", "unavailable_reason": "No library in the test project"},
                    "serp": {"query": "steel pins", "source": "Not available in fixture", "actual_market": "unknown",
                             "actual_language": "en", "coverage": "unavailable", "results": []},
                    "competitor_coverage": {"coverage": "partial"},
                    "competitor_pages": [{"url": "https://supplier.example/pins/", "read_state": "read",
                        "selection_reason": "Same product", "observed_strengths": "Sizes listed", "page_gap": "Check sizes",
                        "recommendation": "Keep product identity", "evidence_refs": ["competitor#catalog"]}],
                    "keyword_decisions": [{"keyword": "steel pins", "origin": "web", "decision": "include",
                        "module_ids": ["selection"], "reason": "Same selection task", "evidence_refs": ["competitor#catalog"]}],
                    "brief": {"page_role": "category", "audience": "Buyers", "intent": "Select pins", "angle": "Compare sizes",
                        "modules": [{"id": "selection", "heading": "Sizes", "task": "Check fit", "evidence_refs": ["site#h2"]}]}}
        placement = {"role": "primary", "keyword": "steel pins", "location": "h1", "heading_index": 1,
                     "expression": "Steel Pins", "source_ref": "site#h1", "reason": "Identifies the range"}
        plan = {**CONTEXT, "research": research, "focus": focus, "intent_fit": "fit", "intent_reason": "Catalog",
                "review_outcome": "retain", "retention_reason": "Title and headings already match", "changes": [],
                "keyword_placement": [placement]}
        self.save("plan.json", plan)
        self.run_cli("check-plan", "--evidence", "before/page-evidence.json", "--plan", "plan.json", "--out", "partial")
        self.assertEqual(json.loads((self.root / "partial/run.json").read_text())["research_status"], "partial")
        placement["heading_index"] = 2
        self.save("plan.json", plan)
        self.run_cli("check-plan", "--evidence", "before/page-evidence.json", "--plan", "plan.json", "--out", "wrong", success=False)
        placement["heading_index"] = 1
        research["sources"] = sources[:1]
        self.save("plan.json", plan)
        self.run_cli("check-plan", "--evidence", "before/page-evidence.json", "--plan", "plan.json", "--out", "unsupported", success=False)

    def test_new_h3_must_belong_to_the_intended_h2(self) -> None:
        outline = [{"tag": "h1", "text": "Steel Pins"}, {"tag": "h2", "text": "Finishes"},
                   {"tag": "h2", "text": "Size options"}, {"tag": "h3", "text": "Measurement method"}]
        self.save("after.json", {**CONTEXT, "input_kind": "html", "headings": outline})
        for parent, expected, out in (("Finishes", "manual_check_required", "wrong"), ("Size options", "observed_in_snapshot", "right")):
            self.save("plan.json", {**CONTEXT, "changes": [{"change_id": "method", "field": "h3",
                "after": "Measurement method", "parent_heading": {"tag": "h2", "text": parent}}]})
            self.run_cli("compare", "--after", "after.json", "--plan", "plan.json", "--out", out)
            with (self.root / out / "implementation-observations.csv").open(encoding="utf-8-sig") as stream:
                self.assertEqual(next(csv.DictReader(stream))["observation"], expected)

    def test_existing_page_queries_keep_their_reported_url_and_period(self) -> None:
        page_url = CONTEXT["target_url"]
        guide_url = page_url + "guide/"
        canonical = "https://fixture.example/catalog/steel-pins/"
        (self.root / "page.html").write_text("<main><h1>Steel Pins</h1></main>")
        (self.root / "inspection.txt").write_text(f"Synthetic URL inspection: {page_url} has Google-selected canonical {canonical}")
        self.table("queries.csv", [
            {"page": page_url, "query": "steel pins", "clicks": "4"},
            {"page": guide_url, "query": "how to fit pins", "clicks": "8"},
            {"page": canonical, "query": "steel pins", "clicks": "3"}])
        self.run_cli("inspect", "--html", "page.html", "--url", page_url, "--keyword", "steel pins",
                     "--market", "UK", "--language", "en", "--collected-at", "2026-11-21",
                     "--stage", "supplied_html", "--out", "before")
        common = {"source": "synthetic fixture", "collected_at": "2026-11-21"}
        gsc = {**common, "kind": "gsc", "path": "queries.csv", "start_date": "2026-10-01",
               "end_date": "2026-10-31", "filters": "UK, Web, all devices"}
        category = {**gsc, "id": "category", "page_url": page_url}
        primary: dict[str, object] = {"keyword": "steel pins", "origin": "gsc", "decision": "include",
            "module_ids": ["catalog"], "reason": "Relevant observed query", "evidence_refs": ["category#row=2"],
            "metrics": {"gsc": {"clicks": 4}}}
        research = {**CONTEXT, "evidence_class": "simulation",
            "sources": [category, {**gsc, "id": "guide", "page_url": guide_url},
                        {**common, "id": "page", "kind": "site", "path": "page.html"},
                        {**common, "id": "inspection", "kind": "site", "path": "inspection.txt"}],
            "library": {"coverage": "unavailable", "unavailable_reason": "No industry export"},
            "serp": {"query": "steel pins", "source": "no SERP", "actual_market": "unknown",
                     "actual_language": "unknown", "coverage": "unavailable", "results": []},
            "competitor_coverage": {"coverage": "unavailable"}, "competitor_pages": [],
            "keyword_decisions": [primary, {"keyword": "how to fit pins", "origin": "gsc",
                "decision": "other_page", "target_url": guide_url, "reason": "Separate guide",
                "evidence_refs": ["guide#row=3"]}],
            "brief": {"page_role": "category", "audience": "Buyers", "intent": "Select steel pins",
                "angle": "Keep known demand", "modules": [{"id": "catalog", "heading": "Steel Pins",
                "task": "Keep category identity", "evidence_refs": ["page#h1"]}]}}
        plan = {**CONTEXT, "intent_fit": "fit", "intent_reason": "This catalog serves buyers",
            "focus": {"page_role": "category", "scope": "full_page", "primary_keyword": "steel pins",
                      "buyer_task": "Choose a steel pin"},
            "review_outcome": "retain", "retention_reason": "Original wording identifies this catalog",
            "keyword_placement": [{"keyword": "steel pins", "role": "primary", "location": "h1",
                "expression": "Steel Pins", "source_ref": "page#h1", "reason": "The current H1 fits"}],
            "changes": [], "research": research}

        def check(output: str, success: bool = True) -> str:
            self.save("plan.json", plan)
            return self.run_cli("check-plan", "--evidence", "before/page-evidence.json", "--plan", "plan.json",
                                "--out", output, success=success)

        check("scoped")
        with (self.root / "scoped/keyword-selection.csv").open(encoding="utf-8-sig") as stream:
            first, other = csv.DictReader(stream)
        self.assertEqual((first["origin"], json.loads(first["metrics"])), ("gsc", {"gsc": {"clicks": 4}}))
        self.assertEqual((other["decision"], other["target_url"]), ("other_page", guide_url))
        self.assertEqual(first["research_status"], "simulation")
        primary["evidence_refs"] = ["guide#row=3"]
        self.assertIn("GSC query evidence", check("wrong-page", False))
        primary.update(origin="editorial", evidence_refs=["page#h1", "guide#row=3"])
        self.assertIn("GSC query evidence", check("wrong-supporting-page", False))
        primary["origin"] = "gsc"
        primary["evidence_refs"] = ["page#h1"]
        self.assertIn("gsc evidence reference", check("wrong-kind", False))
        category.update(page_url=canonical, canonical_ref="inspection#result")
        primary.update(evidence_refs=["category#row=4"], metrics={"gsc": {"clicks": 3}})
        check("canonical")
        saved = json.loads((self.root / "canonical/research-sources.json").read_text())[0]
        self.assertEqual((saved["page_url"], saved["canonical_ref"], saved["start_date"], saved["filters"]),
                         (canonical, "inspection#result", "2026-10-01", "UK, Web, all devices"))
        category["canonical_ref"] = "guide#row=3"
        self.assertIn("site evidence reference", check("wrong-canonical-proof", False))
        category["end_date"] = "2026-09-30"
        self.assertIn("start_date must not follow", check("wrong-date", False))


if __name__ == "__main__":
    unittest.main()
