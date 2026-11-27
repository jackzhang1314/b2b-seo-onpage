"""Local contract tests for selecting SEO work and certifying WordPress progress."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/b2b-seo-onpage/scripts"
sys.path.insert(0, str(SCRIPTS))
URL = "https://fixture.example/cases/"
NOW = "2026-11-28T04:00:00+08:00"


class WorkbenchSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.workbench = self.root / "workbench"
        self.workbench.mkdir()
        self.job = {"page_id": "P", "url": URL, "issue": "", "next_step": "research_and_draft"}
        self.active = {"id": "P", "url": URL, "decision": "pending", "seo_decision": "requested",
                       "seo_eligible": True, "page_action": "revise", "history": []}
        self.selection: dict[str, object] = {"workbench": str(self.workbench), "site_url": "https://fixture.example/",
                                            "revision_id": "rev-A", "mode": "simulation", "has_seo_selection": True,
                                            "pages": {"P": self.active}}

    def save(self, name: str, data: object) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_independent_selections_and_legacy_readability(self) -> None:
        from workbench_bridge import page_binding, select_jobs
        pages = {"P": self.active}
        for pid, decision, seo in (("B", "build", "hold"), ("S", "skip", "hold"), ("N", "pending", "requested")):
            pages[pid] = {**self.active, "id": pid, "decision": decision, "seo_decision": seo, "seo_eligible": False}
        state = {**self.selection, "pages": pages}
        jobs = [{**self.job, "page_id": key} for key in pages]
        picked, summary = select_jobs(jobs, state)
        self.assertEqual([r["page_id"] for r in picked], ["P"])
        self.assertEqual(summary["mode"], "seo_selection")
        self.assertFalse(page_binding(state, "missing")["tracked"])
        old = {**state, "has_seo_selection": False, "pages": {"B": {"id": "B", "decision": "build"}}}
        self.assertEqual(select_jobs(jobs, old)[0], [])
        self.assertEqual(select_jobs(jobs, {})[0], jobs)

    def test_optimized_event_reads_saved_draft_and_rechecks_selection(self) -> None:
        from workbench_bridge import page_binding, sync
        (self.workbench / "pages.csv").write_text("id,url,page_type\nP,https://fixture.example/cases/,category\n")
        note = self.save("note.json", {"workbench_progress": page_binding(self.selection, "P"),
                         "source_directory": str(self.workbench), "page": {"id": "P", "url": URL}})
        plan = {"target_url": URL, "focus": {"scope": "full_page"}, "changes": []}
        raw = self.save("plan.json", plan)
        inputs = [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in (raw,note)]
        run = {"command": "check-plan", "completed_at": NOW, "commercial_headings": "pass", "inputs": inputs}
        self.save("draft/run.json", run)
        self.save("draft/plan.json", plan)
        (self.root / "draft/onpage-review.md").write_text("Reviewed page copy")
        (self.root / "draft/page-copy.md").write_text("The saved page copy")
        self.save("draft/commercial-headings.json", {"status":"pass"})
        args = (note, raw, self.root / "draft", self.root / "owned-cli")
        with patch("workbench_bridge.read_selection", return_value=self.selection), patch("workbench_bridge.invoke", return_value={"ok": True}) as writer:
            self.assertTrue(sync(*args)["ok"])
            event = writer.call_args.args
            self.assertIn("optimized", event)
            self.assertNotIn("published", event)
            self.assertEqual(sync(*args), {"ok": True})
            self.assertEqual(writer.call_args.args, event)
        changed = {**self.selection, "revision_id": "rev-B"}
        for state in (changed, {**self.selection, "pages": {"P": {**self.active, "seo_eligible": False}}}):
            with patch("workbench_bridge.read_selection", return_value=state), patch("workbench_bridge.invoke") as writer:
                with self.assertRaises(ValueError):
                    sync(*args)
                writer.assert_not_called()
        self.save("draft/plan.json", {**plan, "target_url": "https://wrong.example/"})
        with patch("workbench_bridge.read_selection", return_value=self.selection), patch("workbench_bridge.invoke") as writer:
            with self.assertRaises(ValueError):
                sync(*args)
            writer.assert_not_called()

    def test_published_requires_matching_cms_and_actual_frontend(self) -> None:
        from workbench_bridge import confirm_public
        record = {"id": 17, "type": "page", "link": URL, "modified_gmt": "2026-11-27T19:59:59",
                  "version": "v1", "values": {"status": "publish"}}
        saved = self.save("wp-save.json", {"ok": True, "result": {**record, "evidenceDirectory": "wp-journal"}})
        reopened = self.save("wp-read.json", {**record, "rawComplete": True})
        html = self.root / "page.html"
        html.write_text("<h1>Custom Phone Cases</h1>")
        snapshot: dict[str, object] = {"target_url": URL, "content_stage": "source_html", "capture": {
            "final_url": URL, "retrieved_at": NOW, "http_status": 200}, "input": {"path": str(html),
            "sha256": hashlib.sha256(html.read_bytes()).hexdigest()}, "headings": [], "content_blocks": []}
        plan: dict[str, object] = {"target_url": URL, "changes": [{"change_id":"H","field": "h1", "after": "Custom Phone Cases"}]}
        with (self.root / "implementation-observations.csv").open("w", newline="") as out:
            writer = csv.DictWriter(out, ["change_id","observation"])
            writer.writeheader()
            writer.writerow({"change_id":"H","observation":"observed_in_snapshot"})
        self.assertEqual(confirm_public(plan, snapshot, saved, reopened, self.root), "page:17@v1")
        for changed in ({"content_stage": "supplied_html"}, {"capture": {"final_url": URL, "retrieved_at":"2020-01-01T00:00:00Z"}},
                        {"capture": {"final_url": "https://fixture.example/preview/", "retrieved_at":NOW}}):
            with self.assertRaises(ValueError):
                confirm_public(plan, {**snapshot, **changed}, saved, reopened, self.root)
        for record_change in ({"values": {"status": "draft"}}, {"id": 18}, {"version": "v2"}, {"rawComplete": False}):
            self.save("wp-read.json", {**record, "rawComplete": True, **record_change})
            with self.assertRaises(ValueError):
                confirm_public(plan, snapshot, saved, reopened, self.root)
