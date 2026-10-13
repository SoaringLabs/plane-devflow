#!/usr/bin/env python3
"""Plane API v1 by default, v2 for explicit capabilities. Python standard library only."""
from __future__ import annotations

import argparse
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

CONFIG_NAME = ".plane-for-codex.json"
VERSION = "0.6.0"
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
PROJECT_RE = re.compile(r"[A-Z][A-Z0-9_-]{0,29}\Z")
BINDING_RE = re.compile(r"<!--\s*plane-for-codex\s+(\{.*?\})\s*-->", re.S)


class WorkflowError(Exception):
    """An actionable error that is safe to print without API response bodies."""


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def validate_url(value, *, allow_localhost=False):
    parsed = urlparse(value)
    local = allow_localhost and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    require(parsed.scheme == "https" or (local and parsed.scheme == "http"),
            "Plane URLs require HTTPS (loopback HTTP is allowed only in explicit test mode).")
    require(parsed.hostname and not parsed.username and not parsed.password and
            not parsed.query and not parsed.fragment and parsed.path in {"", "/"},
            "Use a Plane origin URL without credentials, path, query, or fragment.")
    return value.rstrip("/")


def validate_config(config, *, allow_localhost=False):
    require(isinstance(config, dict) and type(config.get("version")) is int and config["version"] in {1, 2},
            "Expected config version 1 or 2.")
    for section in ("plane", "github", "states", "completion"):
        require(isinstance(config.get(section), dict), f"Missing config section: {section}.")
    plane, github, states = config["plane"], config["github"], config["states"]
    for key in ("api_url", "app_url"):
        validate_url(plane.get(key, ""), allow_localhost=allow_localhost)
    require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", plane.get("workspace", "")),
            "Invalid Plane workspace slug.")
    require(PROJECT_RE.fullmatch(plane.get("project_identifier", "")), "Invalid Plane project identifier.")
    for key, value in [("project_id", plane.get("project_id"))] + list(states.items()):
        try:
            uuid.UUID(value)
        except (ValueError, TypeError, AttributeError):
            raise WorkflowError(f"{key} must be a Plane UUID.") from None
    if config["version"] == 1:
        require(set(states) == {"in_progress", "in_review", "done"}, "Configure all three legacy workflow states.")
        require(len(set(states.values())) == 3, "Legacy development, review, and done require distinct states.")
    else:
        require(config.get("status_sync") == {"enabled": False} and
                type(config["status_sync"]["enabled"]) is bool,
                "Version 2 basic mapping requires status_sync.enabled=false; custom rules come later.")
        require(not states, "Basic mapping has no state targets; use existing legacy configuration for state sync.")
    require(REPO_RE.fullmatch(github.get("repository", "")), "GitHub repository must be owner/repo.")
    require(all(p not in {".", ".."} for p in github["repository"].split("/")), "Invalid repository.")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", github.get("base_branch", "")),
            "Invalid base branch.")
    ref = github["base_branch"]
    require(".." not in ref and "//" not in ref and not ref.endswith(("/", ".")) and
            all(not part.startswith(".") and not part.endswith(".lock") for part in ref.split("/")),
            "Invalid base branch ref.")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", github.get("branch_prefix", "codex")),
            "Invalid branch prefix.")
    require(config["completion"].get("policy") in {"on_merge", "manual"}, "Choose on_merge or manual completion.")
    require(isinstance(config["completion"].get("manual_label", "manual-acceptance"), str) and
            bool(config["completion"].get("manual_label", "manual-acceptance").strip()), "Invalid manual label.")
    # A small explicit schema keeps accidental credentials out of committed config.
    sync = config.get("sync", {})
    require(isinstance(sync, dict) and set(sync) <= {"provider", "api_version"}, "Unknown synchronization settings.")
    require(sync.get("provider", "actions") in {"actions", "native"}, "Choose actions or native synchronization.")
    require(sync.get("api_version", "v1") in {"v1", "v2"}, "Choose v1 or v2 API routing.")
    allowed = {"version", "plane", "github", "states", "completion", "sync"}
    if config["version"] == 2:
        allowed.add("status_sync")
    require(set(config) <= allowed, "Unknown config keys; credentials belong in a secret store.")
    require(set(plane) <= {"api_url", "app_url", "workspace", "project_id", "project_identifier"}, "Unknown Plane config keys.")
    require(set(github) <= {"repository", "base_branch", "branch_prefix"}, "Unknown GitHub config keys.")
    require(set(config["completion"]) <= {"policy", "manual_label"}, "Unknown completion config keys.")
    return config


def sync_provider(config):
    return config.get("sync", {}).get("provider", "actions")


def api_version(config):
    return config.get("sync", {}).get("api_version", "v1")


def state_sync_enabled(config):
    return config["version"] == 1 and sync_provider(config) == "actions"


def read_config(path, *, allow_localhost=False):
    try:
        return validate_config(json.loads(Path(path).read_text()), allow_localhost=allow_localhost)
    except (OSError, json.JSONDecodeError) as error:
        raise WorkflowError(f"Cannot read config: {Path(path).name}. Run plane-setup.") from error


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PlaneClient:
    def __init__(self, config, token, *, allow_localhost=False, sleep=time.sleep):
        require(bool(token), "PLANE_API_KEY is missing. Configure the repository Secret for Actions.")
        self.origin = validate_url(config["plane"]["api_url"], allow_localhost=allow_localhost)
        self.workspace = config["plane"]["workspace"]
        self.api_version = api_version(config)
        self.project_id = config["plane"]["project_id"]
        self.token, self.sleep = token, sleep
        self.opener = build_opener(NoRedirect())

    def request(self, method, path, body=None, query=None):
        url = self.origin + path + (("?" + urlencode(query)) if query else "")
        payload = json.dumps(body).encode() if body is not None else None
        for attempt in range(3):
            request = Request(url, data=payload, method=method, headers={
                "X-Api-Key": self.token, "Accept": "application/json",
                "Content-Type": "application/json", "User-Agent": f"plane-for-codex/{VERSION}"})
            try:
                with self.opener.open(request, timeout=20) as response:
                    raw = response.read()
                    return json.loads(raw) if raw else {}
            except HTTPError as error:
                error.close()
                if error.code in {502, 503, 504} and method != "GET":
                    raise WorkflowError(f"Plane API HTTP {error.code}. Write result is ambiguous; inspect current state before retrying.") from None
                if error.code in {429, 502, 503, 504} and attempt < 2:
                    try:
                        delay = float(error.headers.get("Retry-After", 2 ** attempt))
                    except (ValueError, TypeError):
                        try:
                            delay = max(0, (parsedate_to_datetime(error.headers["Retry-After"]) - datetime.now(timezone.utc)).total_seconds())
                        except (ValueError, TypeError, KeyError, OverflowError):
                            delay = 2 ** attempt
                    require(0 <= delay <= 20, "Plane retry delay exceeds this run's budget. Retry later; Retry-After was not shortened.")
                    self.sleep(delay)
                    continue
                hint = {401: "Re-authenticate or replace the API token.",
                        402: "This operation is unavailable on your Plane plan; no upgrade is performed.",
                        403: "Check the token owner's project permissions.",
                        404: "Check workspace, project, task, and API availability.",
                        409: "Plane workflow rejected the transition. Inspect the task and retry.",
                        429: "Rate limited. Retry the same operation later."}.get(error.code, "Inspect the endpoint and retry.")
                raise WorkflowError(f"Plane API HTTP {error.code}. {hint}") from None
            except (URLError, TimeoutError, OSError):
                # Avoid blindly replaying an ambiguous write. Upsert is replayable by the caller.
                if method == "GET" and attempt < 2:
                    self.sleep(2 ** attempt)
                    continue
                raise WorkflowError("Plane network request failed. Inspect current state before retrying a write.") from None
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise WorkflowError("Plane returned an invalid JSON response.") from None

    def workspace_path(self, version=None):
        return f"/api/{version or self.api_version}/workspaces/{quote(self.workspace, safe='')}/"

    def records(self, path):
        """Read a complete cursor collection; never make decisions on a partial list."""
        records, cursor, seen = [], None, set()
        for _ in range(100):
            page = self.request("GET", path, query={"cursor": cursor} if cursor else None)
            require(isinstance(page, (list, dict)), "Invalid Plane collection response.")
            records.extend(page if isinstance(page, list) else page.get("results", []))
            if isinstance(page, list) or not page.get("next_page_results"):
                return records
            cursor = page.get("next_cursor")
            require(cursor and cursor not in seen, "Invalid Plane pagination; cannot safely synchronize.")
            seen.add(cursor)
        raise WorkflowError("Plane collection exceeded pagination limit.")

    def work_item(self, identifier):
        raw = self.request("GET", self.workspace_path() + f"work-items/{quote(identifier, safe='')}/",
                           query={"expand": "state,labels"})
        require(isinstance(raw, dict), "Invalid Plane work item response.")
        if self.api_version == "v2":
            # The verified v2 expanded relation reads can lag. Safety decisions
            # use a fresh v1 snapshot, while explicit v2 writes remain supported.
            guard = self.request("GET", self.workspace_path("v1") + f"work-items/{quote(identifier, safe='')}/",
                                 query={"expand": "state,labels"})
            require(isinstance(guard, dict) and guard.get("id") == raw.get("id"), "API versions resolved different tasks.")
            require("labels" in guard, "Cannot resolve current acceptance labels; no writes performed.")
            raw = dict(raw, project_id=guard.get("project_id", guard.get("project")),
                       state_id=None, state=guard.get("state"), labels=guard.get("labels", []))
        item = dict(raw)
        project = raw.get("project_id", raw.get("project"))
        item["project_id"] = project.get("id") if isinstance(project, dict) else project
        require(item["project_id"] == self.project_id, "Resolved task does not belong to configured Plane project.")
        state = raw.get("state")
        item["state_id"] = raw.get("state_id") or (state.get("id") if isinstance(state, dict) else state)
        item["state"] = state if isinstance(state, dict) else {}
        if not item["state"].get("group"):
            states = self.records(self.workspace_path("v1") + f"projects/{quote(item['project_id'], safe='')}/states/")
            item["state"] = next((row for row in states if row.get("id") == item["state_id"]), {})
            require(item["state"].get("group"), "Cannot resolve current state group; no writes performed.")
        require("labels" in raw or "label_ids" in raw, "Cannot resolve current acceptance labels; no writes performed.")
        labels = raw.get("labels", raw.get("label_ids", []))
        require(isinstance(labels, list), "Invalid Plane labels response.")
        unresolved = [label for label in labels if not isinstance(label, dict)]
        if unresolved:
            rows = self.records(self.workspace_path("v1") + f"projects/{quote(item['project_id'], safe='')}/labels/")
            names = {row["id"]: row for row in rows}
            require(all(label in names for label in unresolved), "Cannot resolve acceptance labels; no writes performed.")
            labels = [names[label] if not isinstance(label, dict) else label for label in labels]
        require(all(isinstance(label.get("name"), str) for label in labels), "Cannot resolve acceptance label names.")
        item["labels"] = labels
        return item

    def item_path(self, item, version=None):
        return self.workspace_path(version) + f"projects/{quote(item['project_id'], safe='')}/work-items/{quote(item['id'], safe='')}/"

    def update_state(self, item, state_id):
        key = "state" if self.api_version == "v1" else "state_id"
        return self.request("PATCH", self.item_path(item), {key: state_id})

    def upsert_comment(self, item, external_id, comment_html):
        # v1 has no documented atomic upsert. Use v2 only for this capability.
        return self.request("POST", self.item_path(item, "v2") + "comments/upsert/", {
            "comment_html": comment_html, "access": "INTERNAL",
            "external_source": "plane-for-codex", "external_id": external_id})


def parse_task(value, config):
    prefix = config["plane"]["project_identifier"]
    pattern = re.compile(rf"(?<![A-Z0-9_-])({re.escape(prefix)}-[1-9][0-9]*)(?![A-Z0-9_-])", re.I)
    if "://" in value:
        parsed = urlparse(value)
        origin = urlparse(config["plane"]["app_url"])
        require(parsed.scheme == origin.scheme and parsed.netloc == origin.netloc, "Task URL belongs to a different Plane host.")
        segments = parsed.path.strip("/").split("/")
        require(segments and segments[0] == config["plane"]["workspace"], "Task URL belongs to a different workspace.")
        value = parsed.path
    keys = set(match.group(1).upper() for match in pattern.finditer(value))
    require(len(keys) == 1, f"Provide one task from project {prefix}.")
    return keys.pop()


def binding(config, task):
    return {"version": 1, "workspace": config["plane"]["workspace"],
            "project_id": config["plane"]["project_id"], "task": parse_task(task, config)}


def pr_task(pr, config):
    text = (pr.get("title") or "") + "\n" + (pr.get("body") or "")
    prefix = re.escape(config["plane"]["project_identifier"])
    keys = set(re.findall(rf"\[({prefix}-[1-9][0-9]*)\]", text, re.I))
    keys = {key.upper() for key in keys}
    matches = BINDING_RE.findall(pr.get("body") or "")
    require(len(matches) <= 1, "A PR can carry only one Plane binding.")
    if matches:
        try:
            record = json.loads(matches[0])
        except json.JSONDecodeError:
            raise WorkflowError("Invalid Plane binding in PR body.") from None
        require(isinstance(record, dict), "Invalid Plane binding.")
        expected = binding(config, record.get("task", ""))
        require(record == expected, "PR binding belongs to a different workspace/project or unsupported version.")
        keys.add(expected["task"])
    require(len(keys) <= 1, "v1 synchronizes one primary Plane task per PR. Use unbracketed references for other tasks.")
    return next(iter(keys), None)


def phase(pr):
    if pr.get("merged") or pr.get("merged_at"):
        return "merged"
    if pr.get("state") == "closed":
        return "closed"
    return "draft" if pr.get("draft") else "review"


def target_state(config, pr, item):
    if not state_sync_enabled(config):
        return None
    states = config["states"]
    current = item.get("state_id")
    state = item.get("state") or {}
    if current == states["done"] or state.get("group") in {"completed", "cancelled", "canceled"}:
        return None
    labels = {label.get("name") for label in item.get("labels", []) if isinstance(label, dict)}
    manual = config["completion"]["policy"] == "manual" or config["completion"].get("manual_label", "manual-acceptance") in labels
    lifecycle = phase(pr)
    wanted = {"draft": states["in_progress"], "review": states["in_review"],
              "merged": states["in_review"] if manual else states["done"], "closed": None}[lifecycle]
    rank = {states["in_progress"]: 0, states["in_review"]: 1, states["done"]: 2}
    if wanted == current or (wanted is not None and current in rank and rank[wanted] < rank[current]):
        return None
    return wanted


def validate_event(event, config):
    require(isinstance(event, dict), "Expected a GitHub PR event object.")
    repo = (event.get("repository") or {}).get("full_name")
    require(isinstance(repo, str) and repo.lower() == config["github"]["repository"].lower(), "Event repository does not match config.")
    pr = event.get("pull_request")
    require(isinstance(pr, dict), "Expected a pull_request payload.")
    number = pr.get("number", event.get("number"))
    require(type(number) is int and number > 0, "Invalid pull request number.")
    pr = dict(pr, number=number)
    base = pr.get("base") or {}
    base_repo = (base.get("repo") or {}).get("full_name")
    require(base_repo and base_repo.lower() == repo.lower(), "PR base repository does not match config.")
    url = pr.get("html_url", "")
    require(url.lower() == f"https://github.com/{repo}/pull/{number}".lower(), "Invalid GitHub PR URL.")
    return pr


def github_snapshot(event, token):
    """Read latest PR state so retried/delayed events converge on current GitHub state."""
    repo = event["repository"]["full_name"]
    number = event["pull_request"].get("number", event.get("number"))
    require(REPO_RE.fullmatch(repo) and type(number) is int, "Invalid GitHub snapshot lookup.")
    request = Request(f"https://api.github.com/repos/{repo}/pulls/{number}", headers={
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": f"plane-for-codex/{VERSION}"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            pr = json.load(response)
    except (HTTPError, URLError, OSError, ValueError):
        raise WorkflowError("Cannot read current GitHub PR state. Plane has not been updated.") from None
    return dict(event, pull_request=pr)


def sync_event(event, config, client=None, *, dry_run=False):
    pr = validate_event(event, config)
    if sync_provider(config) == "native":
        return {"status": "skipped", "reason": "native_provider_owns_pr_events"}
    if pr["base"].get("ref") != config["github"]["base_branch"]:
        return {"status": "skipped", "reason": "different_base_branch"}
    task = pr_task(pr, config)
    if task is None:
        return {"status": "skipped", "reason": "no_primary_task"}
    result = {"status": "planned" if dry_run else "synced", "task": task,
              "pr": pr["html_url"], "phase": phase(pr)}
    if dry_run:
        result["note"] = "No API calls or mutations. Live state and acceptance labels are checked when applying."
        return result
    require(client is not None, "A Plane API client is required to apply sync.")
    item = client.work_item(task)
    require(isinstance(item, dict) and item.get("project_id") == config["plane"]["project_id"], "Resolved task does not belong to configured Plane project.")
    try:
        uuid.UUID(item["id"])
    except (KeyError, ValueError, TypeError):
        raise WorkflowError("Plane returned an invalid work item ID.") from None
    desired = target_state(config, pr, item)
    if desired:
        client.update_state(item, desired)
    # Upsert one lifecycle comment per PR. Repo workflow serializes this key.
    label_names = {label.get("name") for label in item.get("labels", []) if isinstance(label, dict)}
    manual = config["completion"]["policy"] == "manual" or config["completion"].get("manual_label", "manual-acceptance") in label_names
    detail = {"draft": "Draft PR; implementation is in progress.",
              "review": "PR is ready for review. Implementation and acceptance are tracked separately.",
              "merged": "Code merged; human acceptance and remaining completion conditions are checked separately in Codex." if manual else "PR merged into the configured base branch.",
              "closed": "PR closed without merging; the task has not been marked complete."}[phase(pr)]
    if not state_sync_enabled(config):
        detail = "Task state synchronization is disabled; the current Plane state is unchanged."
    text = f'<p><strong>GitHub: {html.escape(phase(pr))}</strong></p><p><a href="{html.escape(pr["html_url"], quote=True)}">{html.escape(pr.get("title") or str(pr["number"]))}</a></p><p>{detail}</p>'
    external_id = f'{config["github"]["repository"]}:pr:{pr["number"]}:lifecycle'
    client.upsert_comment(item, external_id, text)
    result["state_changed"] = desired is not None
    result["manual_acceptance"] = manual
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=CONFIG_NAME)
    parser.add_argument("--event", default=os.getenv("GITHUB_EVENT_PATH"))
    parser.add_argument("--apply", action="store_true", help="Apply Plane API mutations; default is an offline plan.")
    parser.add_argument("--allow-localhost", action="store_true", help="Explicit local HTTP test mode.")
    parser.add_argument("--refresh-github", action="store_true", help="Read current PR using GITHUB_TOKEN before applying.")
    args = parser.parse_args(argv)
    try:
        require(args.event, "Provide --event or GITHUB_EVENT_PATH.")
        config = read_config(args.config, allow_localhost=args.allow_localhost)
        event = json.loads(Path(args.event).read_text())
        validate_event(event, config)
        if args.apply and args.refresh_github:
            require(os.getenv("GITHUB_TOKEN"), "GITHUB_TOKEN is missing for current PR verification.")
            event = github_snapshot(event, os.environ["GITHUB_TOKEN"])
        client = PlaneClient(config, os.getenv("PLANE_API_KEY"), allow_localhost=args.allow_localhost) if args.apply and sync_provider(config) == "actions" else None
        print(json.dumps(sync_event(event, config, client, dry_run=not args.apply), ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, TypeError) as error:
        # Configuration/event parse errors contain no API response bodies or credentials.
        print(f"plane-for-codex: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
