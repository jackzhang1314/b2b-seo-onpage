"""Read an existing website's SEO data from a fresh process in its workspace."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

CLI = Path(__file__).resolve().parents[1] / "skills/b2b-seo-onpage/scripts/onpage.py"
PEER = "https://peer.example/pins/"
TARGET = "https://demo.example/pins/"


class RegisteredProjectTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.project = Path(tmp.name) / "网站 项目"
        self.cwd = self.project / "working"
        self.cwd.mkdir(parents=True)

    @staticmethod
    def table(path: Path, header: list[str], rows: list[list[str]]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)

    def delivery(self, market: str, mode: str = "simulation") -> Path:
        folder = self.project / f"{market} {mode}"
        folder.mkdir()
        project = {"site_url": "https://demo.example/", "mode": mode, "market": market, "language": "en"}
        files = {"plan": "architecture-plan.json", "pages": "pages.csv", "library": "clean-keywords.csv",
                 "decisions": "keyword-decisions.csv", "rankings": "received-rankings.csv",
                 "top_pages": "page-traffic-observations.csv", "comparables": "comparable-pages.csv"}
        (folder / files["plan"]).write_text(json.dumps({"project": project}))
        self.table(folder / files["pages"], ["id", "url", "page_type"], [["P", TARGET, "category"]])
        self.table(folder / files["decisions"], ["page_id", "disposition", "keyword"],
                   [["P", "page", "steel pins"], ["Q", "page", "steel pin kit"]])
        self.table(folder / files["library"], ["keyword_original", "market", "language"],
                   [["steel pins", market, "en"]])
        self.table(folder / files["rankings"], ["keyword", "url", "market", "language", "position"],
                   [["steel pin kit", PEER, market, "en", "25"]])
        self.table(folder / files["top_pages"], ["url", "market", "language", "observed_at", "source_ref"],
                   [[PEER, market, "en", "2026-11-21", "export:record:3"],
                    [PEER, "JP", "ja", "2026-11-21", "export:record:4"]])
        self.table(folder / files["comparables"], ["page_id", "url", "status"],
                   [["P", PEER, "partial"], ["P", "https://blocked.example", "blocked"]])
        (folder / "original.csv").write_bytes(b"fixture original")
        index = {"kind": "b2b-seo-site-architecture", "schema_version": 1, **project, "files": files,
                 "originals": [{"kind": "keywords", "path": "original.csv", "availability": "included"}]}
        path = folder / "seo-project-index.json"
        path.write_text(json.dumps(index))
        return path

    def publish_entry(self, *paths: Path) -> None:
        links = [f"- SEO project index: [资料](<{quote(p.relative_to(self.project).as_posix())}>)" for p in paths]
        body = ["客户说明", "<!-- b2b-seo:architecture:start -->", *links, "<!-- b2b-seo:architecture:end -->"]
        (self.project / "AGENTS.md").write_text("\n".join(body))

    def call(self, *args: str, fail: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, "-B", str(CLI), "architecture-page", *args],
                                cwd=self.cwd, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode == 0, not fail, result.stdout + result.stderr)
        return result

    def test_fresh_lookup_reuses_all_sources_and_preserves_other_owners(self) -> None:
        index = self.delivery("US")
        self.publish_entry(index)
        self.call("--page-id", "P", "--out", "handoff")
        data = json.loads((self.cwd / "handoff/architecture-page.json").read_bytes())
        inventory = data["keyword_inventory"]
        self.assertEqual(inventory["peer_url_matches"], {PEER: 1})
        self.assertEqual({r["keyword"]: r["ownership"] for r in inventory["candidates"]},
                         {"steel pins": "this_page", "steel pin kit": "other_page"})
        ctx = data["project_context"]
        self.assertEqual([r["source_ref"] for r in ctx["page_traffic_observations"]], ["export:record:3"])
        self.assertEqual(ctx["originals"][0]["availability"], "included")
        (index.parent / "original.csv").unlink()
        (index.parent / "page-traffic-observations.csv").unlink()
        self.call("--url", TARGET, "--out", "later")
        ctx = json.loads((self.cwd / "later/architecture-page.json").read_bytes())["project_context"]
        self.assertEqual(ctx["originals"][0]["availability"], "missing")
        self.assertEqual(ctx["missing_files"], {"top_pages": "page-traffic-observations.csv"})

    def test_multiple_scopes_require_an_unambiguous_selection(self) -> None:
        sim = self.delivery("US")
        real = self.delivery("US", "real")
        ca = self.delivery("CA")
        self.publish_entry(sim, ca, real)
        self.assertIn("3 matching", self.call("--page-id", "P", "--out", "ambiguous", fail=True).stderr)
        self.assertFalse((self.cwd / "ambiguous").exists())
        self.call("--page-id", "P", "--market", "US", "--mode", "real", "--out", "us")
        self.assertEqual(json.loads((self.cwd / "us/architecture-page.json").read_bytes())["project"]["mode"], "real")
        self.call("--page-id", "P", "--source", str(ca.parent), "--out", "explicit")
        result = json.loads((self.cwd / "explicit/architecture-page.json").read_bytes())
        self.assertEqual(result["project"]["market"], "CA")
        self.assertEqual(result["workbench_selection"], "explicit")
        self.assertEqual(result["project_context"]["market"], "CA")
        self.assertEqual(result["keyword_inventory"]["peer_url_matches"], {PEER: 1})

    def test_missing_or_external_index_cannot_silently_use_a_different_project(self) -> None:
        index = self.delivery("US")
        self.publish_entry(index)
        (self.cwd / ".git").mkdir()
        self.assertIn("No website AGENTS.md", self.call("--page-id", "P", "--out", "wrong", fail=True).stderr)
        data = json.loads(index.read_bytes())
        data["originals"][0]["path"] = "../elsewhere/private.csv"
        index.write_text(json.dumps(data))
        self.assertIn("project-relative", self.call("--project-root", str(self.project), "--page-id", "P",
                                                   "--out", "escape", fail=True).stderr)


    def test_full_workbench_queue_retains_hidden_conflicts_and_article_rows(self) -> None:
        index = self.delivery("CA")
        folder = index.parent
        self.publish_entry(index)
        self.table(folder / "content-plan.csv", ["id", "url", "page_type", "market"], [
            ["H", "https://demo.example/", "home", "CA"],
            ["A", "https://demo.example/guide", "article", "CA"],
            ["D", TARGET.rstrip("/"), "product", "CA"],
            ["X", "https://other.example/", "product", "CA"],
            ["U", "https://demo.example/us", "product", "US"]])
        (folder / "index.html").write_text("<title>Workbench</title>")
        run = subprocess.run([sys.executable, "-B", str(CLI), "site-queue", "--source", str(folder / "index.html"),
                              "--market", "CA", "--out", "queue"], cwd=self.cwd, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        with (self.cwd / "queue/site-queue.csv").open(encoding="utf-8-sig", newline="") as stream:
            jobs = {row["page_id"]: row for row in csv.DictReader(stream)}
        self.assertEqual(set(jobs), {"P", "H", "A", "D", "X"})
        self.assertEqual({pid for pid, row in jobs.items() if row["next_step"] == "resolve_target"}, {"P", "D", "X"})
        self.assertEqual(jobs["H"]["heading_policy"], "title_and_h1")
        self.assertEqual(jobs["A"]["heading_policy"], "by_intent")
        manifest = json.loads((self.cwd / "queue/run.json").read_bytes())
        self.assertEqual(manifest["project"]["mode"], "simulation")
        self.assertFalse(manifest["deployment_verified"])

    def test_new_url_uses_clean_inputs_and_protects_neighboring_terms(self) -> None:
        index = self.delivery("US")
        self.publish_entry(index)
        new_url = "https://demo.example/new-pins/"
        self.call("--url", new_url, "--out", "ordinary", fail=True)
        self.call("--url", new_url, "--allow-unplanned", "--library-term", "steel", "--peer-url", PEER, "--out", "new")
        data = json.loads((self.cwd / "new/architecture-page.json").read_bytes())
        self.assertEqual(data["matched_by"], "unplanned_url")
        self.assertEqual(data["page"]["primary_keyword"], "")
        self.assertEqual(data["keyword_decisions"], [])
        self.assertNotIn("page_design", data)
        self.assertEqual({r["ownership"] for r in data["keyword_inventory"]["candidates"]}, {"other_page"})
        self.call("--source", str(index), "--url", "https://other.example/new/", "--allow-unplanned", "--out", "foreign", fail=True)
        self.call("--url", TARGET, "--allow-unplanned", "--out", "existing")
        self.assertEqual(json.loads((self.cwd / "existing/architecture-page.json").read_bytes())["matched_by"], "planned_url")

    def test_draft_only_index_requires_explicit_selection(self) -> None:
        index = self.delivery("US")
        self.publish_entry(index)
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text().replace("- SEO project index:", "- SEO draft index:"))
        self.assertIn("Only draft", self.call("--page-id", "P", "--out", "detected", fail=True).stderr)
        self.call("--source", str(index), "--page-id", "P", "--out", "explicit")


    def test_site_inventory_matches_existing_and_finds_unplanned_live_pages(self) -> None:
        index = self.delivery("US", mode="real")
        live = self.cwd / "wordpress.csv"
        self.table(live, ["url", "page_type", "cms_record", "status"], [
            [TARGET, "collection", "page:10", "publish"], [TARGET.rstrip("/"), "category", "page:10", "publish"],
            ["https://demo.example/new-item/", "product", "product:11", "publish"],
            ["https://demo.example/draft/", "product", "product:12", "draft"],
            ["https://outside.example/x/", "product", "product:13", "publish"],
            ["https://demo.example/alias1/", "category", "page:14", "publish"],
            ["https://demo.example/alias2/", "category", "page:14", "publish"]])
        result = subprocess.run([sys.executable, "-B", str(CLI), "site-queue", "--source", str(index),
                                 "--site-inventory", str(live), "--out", "queue"], cwd=self.cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with (self.cwd / "queue/site-queue.csv").open(encoding="utf-8-sig", newline="") as stream:
            jobs = {row["url"]: row for row in csv.DictReader(stream)}
        self.assertEqual(len(jobs), 4)
        self.assertEqual((jobs[TARGET]["page_id"], jobs[TARGET]["cms_record"]), ("P", "page:10"))
        added = jobs["https://demo.example/new-item/"]
        self.assertEqual((added["page_id"], added["next_step"], added["heading_policy"]), ("", "research_unplanned_url", "title_and_h1"))
        self.assertEqual(jobs["https://demo.example/alias1/"]["next_step"], "resolve_target")
        self.assertEqual(jobs["https://demo.example/alias2/"]["next_step"], "resolve_target")
