#!/usr/bin/env python3
"""Run the pinned Action without checking out or executing pull request code."""
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

from plane_sync import (CONFIG_NAME, REPO_RE, VERSION, NoRedirect, PlaneClient,
                        WorkflowError, github_snapshot, require, sync_event, validate_config,
                        validate_event, sync_provider)


def fetch_config(event, token):
    repo = event["repository"]["full_name"]
    sha = os.getenv("PLANE_CONFIG_SHA") or event["pull_request"]["base"]["sha"]
    require(REPO_RE.fullmatch(repo) and re.fullmatch(r"[0-9a-fA-F]{40}", sha),
            "Invalid base repository or commit.")
    url = f"https://api.github.com/repos/{repo}/contents/{quote(CONFIG_NAME)}?ref={sha}"
    request = Request(url, headers={"Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json", "User-Agent": f"plane-for-codex/{VERSION}"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            record = json.load(response)
        require(record.get("type") == "file" and record.get("encoding") == "base64",
                "Expected the repository mapping as a regular JSON file.")
        return validate_config(json.loads(base64.b64decode(record["content"])))
    except (HTTPError, URLError, OSError, ValueError, KeyError):
        raise WorkflowError("Cannot read valid mapping from the trusted PR base commit. Merge setup first.") from None


def check_connection(event, repository, token, plane_key):
    """Read-only PAT/project/state check, deliberately no task or comment writes."""
    repo = (event.get("repository") or {}).get("full_name", "")
    require(REPO_RE.fullmatch(repo) and repo.lower() == repository.lower(), "Action repository mismatch.")
    default = event["repository"].get("default_branch")
    require(default and event.get("ref") == "refs/heads/" + default,
            "Run the connection check on the trusted default branch.")
    require(token and os.getenv("PLANE_CONFIG_SHA"), "Trusted commit and GitHub token are required.")
    config = fetch_config(event, token)
    require(config["github"]["repository"].lower() == repo.lower(), "Mapping repository mismatch.")
    require(sync_provider(config) == "actions", "Native mode does not use an Actions connection check; verify the official integration mapping.")
    client = PlaneClient(config, plane_key)
    path = client.workspace_path() + "projects/" + config["plane"]["project_id"] + "/"
    project = client.request("GET", path)
    require(project.get("id") == config["plane"]["project_id"] and not project.get("archived_at"),
            "Configured Plane project is inaccessible or archived.")
    states, cursor, seen = set(), None, set()
    for _ in range(100):
        page = client.request("GET", path + "states/", query={"cursor": cursor} if cursor else None)
        records = page if isinstance(page, list) else page.get("results", [])
        states.update(record["id"] for record in records)
        if isinstance(page, list) or not page.get("next_page_results"):
            break
        cursor = page.get("next_cursor")
        require(cursor and cursor not in seen, "Invalid state pagination; cannot verify targets.")
        seen.add(cursor)
    else:
        raise WorkflowError("State pagination exceeded its limit; cannot verify targets.")
    require(set(config["states"].values()) <= states, "Configured state targets no longer exist. Reconfigure rules.")
    return {"status": "connection_verified", "project": config["plane"]["project_identifier"],
            "state_targets_valid": True, "writes_performed": False,
            "note": "Project/state reads verified. A linked PR event must separately verify actual write permissions."}


def run_action(event, repository, token, plane_key):
    repo = (event.get("repository") or {}).get("full_name", "")
    require(REPO_RE.fullmatch(repo) and repo.lower() == repository.lower(), "Action repository mismatch.")
    require(token, "GITHUB_TOKEN is missing.")
    pr = event.get("pull_request") or {}
    base_repo = ((pr.get("base") or {}).get("repo") or {}).get("full_name", "")
    require(base_repo.lower() == repo.lower(), "PR base repository mismatch.")
    current = github_snapshot(event, token)
    config = fetch_config(current, token)
    validate_event(current, config)
    planned = sync_event(current, config, dry_run=True)
    if planned["status"] == "skipped":
        return planned
    return sync_event(current, config, PlaneClient(config, plane_key))


def main():
    try:
        kind = os.getenv("GITHUB_EVENT_NAME")
        require(kind in {"pull_request_target", "workflow_dispatch"}, "Run on pull_request_target or workflow_dispatch.")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        handler = check_connection if kind == "workflow_dispatch" else run_action
        result = handler(event, os.environ["GITHUB_REPOSITORY"], os.getenv("GITHUB_TOKEN"), os.getenv("PLANE_API_KEY"))
        print(json.dumps(result, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"plane-for-codex: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
