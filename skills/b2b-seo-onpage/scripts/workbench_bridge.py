"""Read architecture-owned selections and send verified On-page events to the shared writer."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import unquote

from project_sources import delivery_folder, discover, on_site, url_key
from seo_project import INDEX, block_range, load_index, local_file, project_for

SCHEMA = "b2b-seo-workbench-handoff/1"
Json = dict[str, object]


def obj(value: object) -> Json:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Expected a workbench JSON object")
    return {str(key): item for key, item in value.items()}


def read(path: Path) -> Json:
    return obj(json.loads(path.read_bytes()))


def records(data: Json, name: str) -> list[Json]:
    value = data.get(name)
    if not isinstance(value, list):
        raise ValueError(f"Expected a workbench {name} list")
    return [obj(row) for row in value]


def shared_cli(skill: Path | None) -> Path:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return (skill or home / "skills/b2b-seo-site-architecture") / "scripts/workbench_progress.py"


def invoke(cli: Path, *args: str) -> Json:
    if not cli.is_file():
        raise ValueError("Install the website architecture Skill with scripts/workbench_progress.py to sync this workbench")
    result = subprocess.run([sys.executable, "-B", str(cli), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "Architecture workbench operation failed")
    return obj(json.loads(result.stdout))


def handoff_file(folder: Path) -> Path | None:
    if not (folder / INDEX).is_file():
        return None
    relative = obj(load_index(folder / INDEX)["files"]).get("handoff")
    return local_file(folder, str(relative)) if relative else None


def read_selection(folder: Path, cli: Path) -> Json:
    path = handoff_file(folder)
    if path is None:
        return {}
    data = read(path)
    if data.get("schema") != SCHEMA or not data.get("revision_id"):
        raise ValueError("Unsupported workbench selection schema or missing revision")
    declared = any("seo_decision" in p or "seo_eligible" in p for p in records(data, "pages"))
    if declared and cli.is_file():
        live = invoke(cli, "resolve", "--workbench", str(folder))
        if (Path(str(live.get("workbench", ""))).resolve() != folder.resolve()
                or live.get("revision_id") != data["revision_id"]):
            raise ValueError("The shared resolver returned a different workbench revision")
        data = {**data, "pages": records(live, "pages")}
    pages: dict[str, Json] = {}
    for page in records(data, "pages"):
        pid = str(page.get("id") or page.get("page_id") or "")
        if not pid or pid in pages:
            raise ValueError("Workbench page IDs must be present and unique")
        if declared and (type(page.get("seo_eligible")) is not bool or page.get("seo_decision") not in {"requested", "hold"}):
            raise ValueError("Incomplete SEO decision in workbench")
        if page.get("seo_eligible") is True and page.get("seo_decision") != "requested":
            raise ValueError("Eligible page lacks an explicit SEO request")
        pages[pid] = page
    return {"workbench": str(folder.resolve()), "revision_id": data["revision_id"], "mode": obj(data["project"]).get("mode"),
            "site_url": obj(data["project"]).get("site_url"), "has_seo_selection": declared, "pages": pages}


def locate(source: Path | None, root: Path | None, url: str | None, market: str | None, language: str | None,
           mode: str | None, cli: Path) -> tuple[Path, tuple[Path, Path] | None]:
    if source:
        return delivery_folder(source), None
    try:
        registered = discover(root, url, market, language, mode)
    except ValueError as error:
        # Only the architecture resolver may select a sole explicitly checked draft.
        if not cli.is_file() or not ("Only draft" in str(error) or "Found 0 matching SEO indexes" in str(error)):
            raise
        project = root.resolve() if root else project_for(Path.cwd())
        if not project:
            raise
        flags = [item for key, val in (("--market", market), ("--language", language), ("--mode", mode))
                 if val for item in (key, val)]
        body = local_file(project, "AGENTS.md").read_text(encoding="utf-8-sig")
        bounds = block_range(body)
        area = body[slice(*bounds)] if bounds else ""
        refs = re.findall(r"^- SEO draft index: \[[^\]]*\]\(<([^>]+)>\)", area, re.M)
        indexes = [local_file(project, unquote(ref)) for ref in refs]
        sites = {str(load_index(index)["site_url"]) for index in indexes if handoff_file(index.parent)}
        if not sites:
            raise
        if url:
            candidates = [site for site in sites if on_site(url, site)]
            if len(candidates) != 1:
                raise ValueError("Choose the workbench for the intended website or site path") from error
            flags += ["--site-url", candidates[0]]
        resolved = invoke(cli, "resolve", "--project-root", str(project), *flags)
        folder = delivery_folder(Path(str(resolved["workbench"])))
        if folder / INDEX not in indexes:
            raise ValueError("The resolved draft is not registered in this website's SEO section")
        registered = (project, folder / INDEX)
    return registered[1].parent, registered


def page_binding(selection: Json, page_id: str) -> Json:
    if not selection:
        return {}
    row = obj(obj(selection["pages"]).get(page_id, {}))
    return {key: selection[key] for key in ("workbench", "revision_id", "mode", "has_seo_selection")} | {
        "page_id": page_id, "decision": row.get("decision"), "seo_decision": row.get("seo_decision"),
        "seo_eligible": row.get("seo_eligible") is True, "tracked": bool(row)}


def select_jobs(jobs: list[dict[str, str]], selection: Json) -> tuple[list[dict[str, str]], Json]:
    if not selection:
        return jobs, {"mode": "planning_inventory", "planned_or_live_pages": len(jobs)}
    selected = []
    omitted = []
    for job in jobs:
        bound = page_binding(selection, job["page_id"])
        if bound["seo_eligible"]:
            row = obj(obj(selection["pages"])[job["page_id"]])
            if row.get("url") and job["url"] and url_key(str(row["url"])) != url_key(job["url"]):
                raise ValueError("The selected page URL differs from the planning table")
            progress = obj(obj(row.get("progress", {})).get("onpage", {}))
            job.update(revision_id=str(bound["revision_id"]), decision=str(bound["decision"]),
                       seo_decision=str(bound["seo_decision"]), progress=str(progress.get("status") or "pending"))
            if not job["issue"] and job["progress"] in {"optimized", "published"}:
                job["next_step"] = "resume_from_review" if job["progress"] == "optimized" else "check_current_version"
            selected.append(job)
        else:
            omitted.append({"page_id": job["page_id"], "url": job["url"], "decision": bound["decision"],
                            "seo_decision": bound["seo_decision"]})
    active = {pid for pid, p in obj(selection["pages"]).items() if obj(p).get("seo_eligible") is True}
    absent = active - {row["page_id"] for row in selected}
    if absent:
        raise ValueError("Selected workbench IDs missing from in-scope planning tables: " + ", ".join(sorted(absent)))
    return selected, {"mode": "seo_selection" if selection["has_seo_selection"] else "legacy_build_choices_only",
                      "revision_id": selection["revision_id"], "planned_or_live_pages": len(jobs), "omitted": omitted}


def cms_record(path: Path) -> Json:
    data = read(path)
    if "result" in data:
        if data.get("ok") is not True:
            raise ValueError("The supplied Harness operation did not succeed")
        return obj(data["result"])
    return data


def confirm_public(plan: Json, after: Json, saved: Path, reopened: Path, report: Path) -> str:
    a, b = cms_record(saved), cms_record(reopened)
    if (saved.resolve() == reopened.resolve() or not a.get("evidenceDirectory") or b.get("rawComplete") is not True
            or not a.get("id") or not a.get("type") or not a.get("version")
            or any(a.get(k) != b.get(k) for k in ("id", "type", "version"))
            or any(obj(row.get("values")).get("status") != "publish" for row in (a, b))):
        raise ValueError("Need a successful published CMS save and an independent re-read of the same record/version")
    url = url_key(str(plan["target_url"]))
    capture = obj(after.get("capture", {}))
    if (after.get("content_stage") not in {"source_html", "browser_dom", "tool_raw_html"} or not capture.get("retrieved_at")
            or any(url_key(str(value or "")) != url for value in (capture.get("final_url"), after.get("target_url"), a.get("link"), b.get("link")))):
        raise ValueError("Need a fresh front-end capture at the published WordPress URL")
    seen = datetime.fromisoformat(str(capture["retrieved_at"]).replace("Z", "+00:00"))
    modified = datetime.fromisoformat(str(b.get("modified_gmt") or "").replace("Z", "+00:00"))
    if modified.tzinfo is None:
        modified = modified.replace(tzinfo=timezone.utc)
    if seen.tzinfo is None or seen < modified or capture.get("http_status") != 200:
        raise ValueError("The front-end capture must be successful and follow the CMS save")
    source = obj(after.get("input", {}))
    if hashlib.sha256(Path(str(source.get("path"))).read_bytes()).hexdigest() != source.get("sha256"):
        raise ValueError("The captured HTML changed since inspection")
    with (report / "implementation-observations.csv").open(encoding="utf-8-sig", newline="") as stream:
        observations = list(csv.DictReader(stream))
    changes = records(plan, "changes")
    if len(observations) != len(changes) or any(row["observation"] != "observed_in_snapshot" for row in observations):
        raise ValueError("Not all requested changes were observed in the correct front-end elements")
    headings = records(after, "headings")
    paragraphs = records(after, "content_blocks")
    for change in changes:
        if change.get("field") == "body" and change.get("under_heading"):
            indexes = {str(i) for i, h in enumerate(headings, 1) if h.get("content_scope") != "navigation"
                       and h.get("text") == change["under_heading"]}
            if not any(str(p.get("heading_index")) in indexes and str(change["after"]) in str(p.get("text", ""))
                       for p in paragraphs):
                raise ValueError("A changed paragraph was not found under its intended heading")
    return f"{b['type']}:{b['id']}@{b['version']}"


def sync(note: Path, plan_path: Path, folder: Path, cli: Path, *, after: Path | None = None,
         reviewed: Path | None = None, saved: Path | None = None, reopened: Path | None = None) -> Json:
    architecture, plan, run = read(note), read(plan_path), read(folder / "run.json")
    pinned = obj(architecture.get("workbench_progress", {}))
    pid = str(pinned.get("page_id") or "")
    if not pid or not pinned.get("seo_eligible"):
        raise ValueError("This workbench page has no requested, eligible SEO task")
    workbench = delivery_folder(Path(str(pinned["workbench"])))
    selection = read_selection(workbench, cli)
    owner = obj(obj(selection.get("pages", {})).get(pid, {}))
    planned = obj(architecture.get("page", {}))
    if (planned.get("id") != pid or planned.get("url") != owner.get("url")
            or Path(str(architecture.get("source_directory"))).resolve() != workbench
            or not on_site(str(plan["target_url"]), str(selection.get("site_url") or ""))):
        raise ValueError("The selected workbench, page ID, and actual website do not match the review")
    fresh = page_binding(selection, pid)
    if fresh["revision_id"] != pinned["revision_id"] or fresh.get("seo_eligible") is not True:
        raise ValueError("Workbench revision or SEO selection changed; keep the draft and re-read the workbench")
    if run.get("commercial_headings") not in {"pass", "not_required"} or any(c.get("copy_state") != "ready" for c in records(plan, "changes")):
        raise ValueError("Unresolved heading or blocked copy cannot mark this page optimized or published")
    if not plan.get("focus"):
        raise ValueError("A workbench update needs an explicit page focus")
    if fresh.get("mode") == "real" and obj(plan.get("research", {})).get("evidence_class") == "simulation":
        raise ValueError("Simulation content cannot update a real workbench")
    inputs = {str(row["path"]): row["sha256"] for row in records(run, "inputs")}
    for file in [plan_path, note, *([after] if after else []), *([reviewed] if reviewed else [])]:
        if inputs.get(str(file.resolve())) != hashlib.sha256(file.read_bytes()).hexdigest():
            raise ValueError("Review inputs do not match the selected page, plan, or capture")
    status, document, target = "optimized", "onpage-review.md", ""
    when = str(run.get("completed_at") or "")
    if after:
        if run.get("command") != "compare" or run.get("comparison_scope") == "local_simulation" or not (reviewed and saved and reopened):
            raise ValueError("Publishing needs the reviewed headings, CMS save and independent CMS and frontend readbacks")
        draft = read(reviewed.parent / "run.json")
        if (draft.get("command") != "check-plan" or read(reviewed.parent / "plan.json") != plan
                or draft.get("commercial_headings") not in {"pass", "not_required"}
                or not any(row.get("sha256") == inputs[str(note.resolve())] for row in records(draft, "inputs"))):
            raise ValueError("Published readback must match the previously reviewed plan and workbench page")
        public_snapshot = read(after)
        target = confirm_public(plan, public_snapshot, saved, reopened, folder)
        when = str(obj(public_snapshot["capture"])["retrieved_at"])
        status, document = "published", "implementation-review.md"
    elif run.get("command") != "check-plan" or read(folder / "plan.json") != plan:
        raise ValueError("Need the saved and re-read On-page plan")
    evidence = folder / document
    if not evidence.read_text(encoding="utf-8").strip():
        raise ValueError("Missing saved On-page review")
    key = [pinned["revision_id"], pid, status, plan, target]
    event = "onpage-" + hashlib.sha256(json.dumps(key, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    summary = f"{pid} · {status} · {obj(plan['focus'])['scope']} · {plan['target_url']}"
    proof = folder / "workbench-proof.json"
    documents = [evidence, note, plan_path, folder / "run.json", folder / "commercial-headings.json"]
    for source in (reviewed, after, saved, reopened):
        if source:
            documents.append(source)
    if not after:
        documents.append(folder / ("page-copy.md" if obj(plan["focus"]).get("scope") == "full_page" else "onpage-review.md"))
    proof_data = {"workbench": str(workbench), "revision_id": pinned["revision_id"], "page_id": pid,
                  "target_url": plan["target_url"], "scope": obj(plan["focus"])["scope"], "mode": fresh["mode"],
                  "status": status, "record_version": target, "event_id": event,
                  "documents": [{"ref": f.resolve().as_uri(), "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
                                for f in dict.fromkeys(documents)]}
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, delete=False) as tmp:
        json.dump(proof_data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
    Path(tmp.name).replace(proof)
    evidence_ref = proof.resolve().as_uri()
    # The shared writer compares the original payload for a repeat event.
    for previous in records(owner, "history") if "history" in owner else []:
        if previous.get("track") == "onpage" and previous.get("event_id") == event:
            evidence_ref, when = str(previous["evidence"]), str(previous["occurred_at"])
            break
    args = ["record", "--workbench", str(workbench), "--revision-id", str(pinned["revision_id"]),
            "--page-id", pid, "--track", "onpage", "--status", status, "--event-id", event,
            "--evidence", evidence_ref, "--summary", summary]
    if when:
        args += ["--occurred-at", when]
    return invoke(cli, *args)
