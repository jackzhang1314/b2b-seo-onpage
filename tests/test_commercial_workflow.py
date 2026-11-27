"""Commercial-page heading regressions, including a separate public capture."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/b2b-seo-onpage/scripts"
sys.path.insert(0, str(SCRIPTS))
if TYPE_CHECKING:
    from page_copy import Block


def audit(content: dict[str, object], blocks: list[Block], architecture: dict[str, object]) -> dict[str, object]:
    from commercial_headings import audit as audit_headings
    return audit_headings(content, blocks, architecture)

CONTEXT = {"target_url": "https://phone.example/phone-cases/", "keyword": "phone cases",
           "market": "US", "language": "en"}


def plan(role: str = "collection", modifier: str = "custom", verification: str = "verified",
         permission: str = "approved_public") -> dict[str, object]:
    return {**CONTEXT, "focus": {"page_role": role, "scope": "headings", "primary_keyword": "phone cases",
                                 "buyer_task": "Order cases with a brand logo"},
            "claims": [{"claim_id": "orders", "text": "Test company accepts logo print orders.",
                        "source_ref": "test-company/order-terms", "verification_state": verification,
                        "public_use_state": permission}],
            "commercial_headings": {"category_terms": ["phone cases", "phone case"],
                                    "modifiers": [{"phrase": modifier, "claim_id": "orders"}]},
            "intent_fit": "fit", "intent_reason": "Buyer seeking printed cases", "changes": [],
            "review_outcome": "retain", "retention_reason": "Check both existing texts"}


def copy(title: str, h1: str) -> list[Block]:
    from page_copy import Block
    return [Block("t", "title", title), Block("h", "h1", h1)]


class CommercialHeadingsTest(unittest.TestCase):
    def test_category_and_sourced_buying_term_in_each_field(self) -> None:
        for role in ("home", "category_overview", "product", "attachment"):
            with self.subTest(role=role):
                content = plan(role)
                self.assertEqual(audit(content, copy("Custom Phone Cases", "Custom Phone Case Series"), {})["status"], "pass")
                for title, h1 in (("Phone Cases", "Custom Phone Cases"), ("Custom Phone Cases", "Phone Cases"),
                                  ("Custom Factory", "Custom Phone Cases"), ("Custom Phone Cases", "Custom Model XY")):
                    self.assertEqual(audit(content, copy(title, h1), {})["status"], "needs_review")
        result = audit(plan(), copy("Custom Phone Cases", "Custom Phone Cases"), {})
        self.assertEqual(result["primary_keyword"], "phone cases")
        self.assertEqual(result["primary_modifiers"], [])

    def test_uncertain_private_or_old_ai_fact_cannot_authorize_copy(self) -> None:
        for state, permission in (("page_observed", "public_observed"), ("unverified", "approved_public"),
                                  ("user_provided", "internal_only")):
            self.assertEqual(audit(plan(verification=state, permission=permission),
                                   copy("Custom Phone Cases", "Custom Phone Cases"), {})["status"], "needs_review")
        self.assertEqual(audit(plan(), copy("Custom Phone Cases Manufacturer", "Custom Phone Cases"), {})["status"], "needs_review")

    def test_customer_and_false_buying_contexts(self) -> None:
        for term, title in (("customer", "Customer Phone Cases"), ("bulk", "Phone Cases Bulk Density"),
                            ("factory", "Factory Automation Phone Cases"), ("custom", "Customer Phone Cases"),
                            ("model", "Phone Cases Model")):
            self.assertEqual(audit(plan(modifier=term), copy(title, title), {})["status"], "needs_review")

    def test_natural_alternate_and_non_english_phrase(self) -> None:
        content = plan()
        content["commercial_headings"] = {"category_terms": ["手机壳"], "modifiers": [
            {"phrase": "面向经销商", "kind": "trade_buyer", "claim_id": "orders"}]}
        result = audit(content, copy("面向经销商的手机壳", "手机壳系列，面向经销商供货"), {})
        self.assertEqual(result["status"], "pass")
        content = plan(modifier="private label")
        self.assertEqual(audit(content, copy("Private-Label Phone Cases", "Private Label Phone Cases"), {})["status"], "pass")

    def test_information_page_and_conflicting_architecture(self) -> None:
        product: dict[str, object] = {"page": {"page_type": "product", "primary_keyword": "phone case"}}
        self.assertEqual(audit(plan("article"), copy("Phone Cases", "Phone Cases"), {})["status"], "not_required")
        result = audit(plan("article"), copy("Custom Phone Cases", "Custom Phone Cases"), product)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["primary_keyword"], "phone case")

    def test_wrong_main_h1_duplicate_title_and_wrong_readback(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            def run(expected: int, *args: str) -> None:
                actual = subprocess.run([sys.executable, "-B", str(SCRIPTS / "onpage.py"), *args],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(actual.returncode, expected, actual.stdout + actual.stderr)

            def capture(name: str, head: str, h1: str) -> None:
                html = (f"<html><head>{head}</head><body><nav><h1>Custom Phone Cases</h1></nav>"
                        f"<main><h1>{h1}</h1></main></body></html>")
                (root / "page.html").write_text(html)
                run(0, "inspect", "--html", "page.html", "--url", CONTEXT["target_url"], "--keyword", "phone cases",
                    "--market", "US", "--language", "en", "--collected-at", "2026-11-28", "--stage", "supplied_html", "--out", name)

            capture("old", "<title>Custom Phone Cases</title>", "Phone Cases")
            (root / "plan.json").write_text(json.dumps(plan()))
            args = ("--plan", "plan.json", "--require-b2b-headings")
            run(2, "check-plan", *args, "--evidence", "old/page-evidence.json", "--out", "rejected")
            run(2, "check-plan", "--plan", "plan.json", "--evidence", "old/page-evidence.json", "--out", "default-policy")
            content = plan()
            content.pop("review_outcome")
            content.pop("retention_reason")
            content["changes"] = [{"change_id": "h1", "field": "h1", "before": "Phone Cases", "after": "Custom Phone Cases",
                                   "priority": "P1", "copy_state": "ready", "reason": "Approved print service",
                                   "claim_ids": ["orders"], "evidence_refs": ["test-company/order-terms"], "heading_index": 2}]
            (root / "plan.json").write_text(json.dumps(content))
            run(0, "check-plan", *args, "--evidence", "old/page-evidence.json", "--out", "draft")
            compare = ("compare", *args, "--reviewed-headings", "draft/commercial-headings.json")
            run(2, *compare, "--after", "old/page-evidence.json", "--out", "stale")
            capture("variant", "<title>Custom Phone Cases for Summer</title>", "Custom Phone Cases")
            run(2, *compare, "--after", "variant/page-evidence.json", "--out", "different")
            capture("duplicate", "<title>Custom Phone Cases</title><title>Custom Phone Cases</title>", "Custom Phone Cases")
            run(2, *compare, "--after", "duplicate/page-evidence.json", "--out", "ambiguous")
            capture("final", "<title>Custom Phone Cases</title>", "Custom Phone Cases")
            run(0, *compare, "--after", "final/page-evidence.json", "--out", "match")
            result = json.loads((root / "match/run.json").read_bytes())
            self.assertEqual(result["commercial_headings"], "pass")
            self.assertFalse(result["deployment_verified"])
