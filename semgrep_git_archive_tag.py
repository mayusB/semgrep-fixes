#!/usr/bin/env python3
"""Tag Semgrep projects whose GitHub repository has been archived.

Archiving a repo on GitHub tells Semgrep nothing, so the project keeps appearing
in the dashboard and in scan counts long after anyone stopped working on it.
This walks the org's repos, finds the archived ones, and tags the matching
Semgrep projects so they can be filtered out.

    export GITHUB_AUTH_TOKEN=...          # needs read access to the org's repos
    export SEMGREP_APP_TOKEN=...
    export GITHUB_ORG=my-org
    export SEMGREP_DEPLOYMENT_SLUG=my-deployment
    python semgrep_git_archive_tag.py --dry-run
"""

from __future__ import annotations

import argparse
import sys

from semgrep_api import (
    GITHUB_API_ROOT,
    SEMGREP_API_ROOT,
    ApiError,
    github_session,
    paginate,
    request_json,
    require_env,
    semgrep_session,
)

ARCHIVED_TAG = "archived"


def archived_repo_names(org: str, token: str) -> set[str]:
    """Return `owner/name` for every archived repo in the org."""
    session = github_session(token)
    url = f"{GITHUB_API_ROOT}/orgs/{org}/repos"

    return {
        repo["full_name"]
        for repo in paginate(session, url, params={"type": "all"})
        if repo.get("archived")
    }


def semgrep_project_names(deployment_slug: str, token: str) -> set[str]:
    """Return the name of every project in the deployment."""
    session = semgrep_session(token)
    url = f"{SEMGREP_API_ROOT}/deployments/{deployment_slug}/projects"

    return {project["name"] for project in paginate(session, url)}


def tag_projects(deployment_slug: str, token: str, names: list[str]) -> list[str]:
    """Tag each project as archived. Returns the names that failed."""
    session = semgrep_session(token)
    failed: list[str] = []

    for name in names:
        url = f"{SEMGREP_API_ROOT}/deployments/{deployment_slug}/projects/{name}/tags"
        try:
            request_json(session, "PUT", url, json={"tags": [ARCHIVED_TAG]})
        except ApiError as exc:
            print(f"  failed: {name}: {exc}", file=sys.stderr)
            failed.append(name)
        else:
            print(f"  tagged: {name}")

    return failed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be tagged without changing anything",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    github_token, semgrep_token, org, deployment_slug = require_env(
        "GITHUB_AUTH_TOKEN",
        "SEMGREP_APP_TOKEN",
        "GITHUB_ORG",
        "SEMGREP_DEPLOYMENT_SLUG",
    )

    try:
        archived = archived_repo_names(org, github_token)
        print(f"archived repos in {org}: {len(archived)}")

        projects = semgrep_project_names(deployment_slug, semgrep_token)
        # Set intersection, so a large org doesn't turn into a nested scan.
        to_tag = sorted(archived & projects)

        if not to_tag:
            print("nothing to tag")
            return 0

        print(f"projects to tag: {len(to_tag)}")
        if args.dry_run:
            for name in to_tag:
                print(f"  would tag: {name}")
            return 0

        failed = tag_projects(deployment_slug, semgrep_token, to_tag)
    except ApiError as exc:
        print(exc, file=sys.stderr)
        return 1

    if failed:
        print(f"{len(failed)} of {len(to_tag)} failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
