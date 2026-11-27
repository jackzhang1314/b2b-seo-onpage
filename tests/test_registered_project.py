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
        self.assertNotIn("project_context", result)

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
