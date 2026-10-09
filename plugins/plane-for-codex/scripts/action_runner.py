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
                        validate_event)


def fetch_config(event, token):
    repo = event["repository"]["full_name"]
    sha = event["pull_request"]["base"]["sha"]
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
        require(os.getenv("GITHUB_EVENT_NAME") == "pull_request_target", "Run this Action on pull_request_target.")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        result = run_action(event, os.environ["GITHUB_REPOSITORY"], os.getenv("GITHUB_TOKEN"), os.getenv("PLANE_API_KEY"))
        print(json.dumps(result, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"plane-for-codex: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
