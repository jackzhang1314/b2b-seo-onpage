"""Optional end-to-end test against an actual installation of the shared architecture writer."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_registered_project as fixtures

ARCH = Path(os.environ.get("ONPAGE_TEST_ARCHITECTURE_SKILL") or Path.home() / ".codex/skills/b2b-seo-site-architecture")
CLI = fixtures.CLI


@unittest.skipUnless((ARCH / "scripts/workbench_progress.py").is_file(), "Install the compatible architecture writer to run this integration")
class SharedWriterIntegrationTest(unittest.TestCase):
    def test_selected_draft_to_saved_copy_and_idempotent_event(self) -> None:
        setup = fixtures.RegisteredProjectTest()
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        index = setup.delivery("US")
        folder = index.parent
        data = json.loads(index.read_bytes())
        data["files"]["handoff"] = "workbench-handoff.json"
        index.write_text(json.dumps(data))
        for name in ("index.html", "design.html"):
            (folder / name).write_text('<meta name="workbench-revision" content="__WORKBENCH_REVISION__">')
        setup.publish_entry(index)
        agents = setup.project / "AGENTS.md"
        agents.write_text(agents.read_text().replace("- SEO project index:", "- SEO draft index:"))
        # Simulate the GUI through its public selection functions in the architecture Skill's own module path.
        code = """
import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from page_confirmation import create_handoff, change_page, read_handoff
folder=Path(sys.argv[2])
if sys.argv[3] == 'init':
    create_handoff(folder,json.loads((folder/'architecture-plan.json').read_bytes())['project'])
    change_page(folder, {'page_id':'P','revision_id':read_handoff(folder)['revision_id'],'expected_version':0,'decision':'build'})
else:
    change_page(folder, {'page_id':'P','revision_id':read_handoff(folder)['revision_id'],'expected_version':0,'seo_decision':'requested'})
"""

        def choose(choice: str) -> None:
            result = subprocess.run([sys.executable, "-B", "-c", code, str(ARCH / "scripts"), str(folder), choice],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

        def call(*args: str) -> None:
            result = subprocess.run([sys.executable, "-B", str(CLI), *args], cwd=setup.cwd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

        flags = ("--architecture-skill", str(ARCH))
        choose("init")
        call("site-queue", *flags, "--project-root", str(setup.project), "--out", "build-only")
        self.assertEqual(json.loads((setup.cwd / "build-only/run.json").read_bytes())["pages"], 0)
        call("architecture-page", *flags, "--project-root", str(setup.project), "--page-id", "P", "--out", "lookup")
        self.assertFalse(json.loads((setup.cwd / "lookup/architecture-page.json").read_bytes())["workbench_progress"]["seo_eligible"])
        choose("request")
        call("site-queue", *flags, "--project-root", str(setup.project), "--out", "queue")
        run = json.loads((setup.cwd / "queue/run.json").read_bytes())
        self.assertEqual((run["pages"], run["seo_selection"]["mode"]), (1, "seo_selection"))
        call("architecture-page", *flags, "--source", str(index), "--page-id", "P", "--out", "input")
        html = "<html><head><title>Steel Pins</title></head><body><h1>Steel Pins Supplier</h1></body></html>"
        (setup.cwd / "before.html").write_text(html)
        context = {"target_url":fixtures.TARGET,"keyword":"steel pins","market":"US","language":"en"}
        call("inspect", "--html", "before.html", "--url", fixtures.TARGET, "--keyword", "steel pins", "--market",
             "US", "--language", "en", "--collected-at", "2026-11-28", "--stage", "supplied_html", "--out", "before")
        plan = {**context, "focus":{"scope":"headings","buyer_task":"Find a supplier","page_role":"category",
                "primary_keyword":"steel pins"}, "claims":[{"claim_id":"trade","text":"The test company supplies these pins",
                "source_ref":"private test fixture", "verification_state":"verified","public_use_state":"approved_public"}],
                "commercial_headings":{"category_terms":["steel pins"],"modifiers":[{"phrase":"supplier","claim_id":"trade"}]},
                "changes":[{"change_id":"title", "field":"title", "before":"Steel Pins", "after":"Steel Pins Supplier",
                            "priority":"P1", "copy_state":"ready", "claim_ids":["trade"], "evidence_refs":["before.html"],
                            "reason":"Use the confirmed supplier role in the SEO title."}],
                "intent_fit":"fit","intent_reason":"A business supplier page"}
        (setup.cwd / "plan.json").write_text(json.dumps(plan))
        args = ("--plan", "plan.json", "--architecture-page", "input/architecture-page.json", "--out", "checked", *flags)
        call("check-plan", *args, "--evidence", "before/page-evidence.json", "--sync-workbench")
        first = json.loads((setup.cwd / "checked/workbench-event.json").read_bytes())
        self.assertTrue(first["recorded"])
        call("workbench-sync", *args)
        repeat = json.loads((setup.cwd / "checked/workbench-event.json").read_bytes())
        self.assertFalse(repeat["recorded"])
        self.assertEqual((repeat["status"], repeat["event_id"]), ("optimized", first["event_id"]))
