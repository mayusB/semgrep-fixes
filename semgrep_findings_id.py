#!/usr/bin/env python3
"""List finding ids for one scan ref.

Useful when a customer reports "the MR scan shows findings the branch scan
doesn't". Pulling the ids for each ref makes the two sets diffable instead of
comparing screenshots.

    export SEMGREP_APP_TOKEN=...
    export SEMGREP_DEPLOYMENT_SLUG=...
    python semgrep_findings_id.py --ref gitlab-mr
"""

from __future__ import annotations

import argparse
import sys

from semgrep_api import (
    SEMGREP_API_ROOT,
    ApiError,
    paginate,
    require_env,
    semgrep_session,
)


def finding_ids(deployment_slug: str, token: str, ref: str | None) -> list[str]:
    """Return finding ids for the deployment, optionally filtered to one ref.

    A ref of None returns everything, which is how you find out what refs exist
    in the first place.
    """
    session = semgrep_session(token)
    url = f"{SEMGREP_API_ROOT}/deployments/{deployment_slug}/findings"

    return [
        finding["id"]
        for finding in paginate(session, url)
        if ref is None or finding.get("ref") == ref
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ref",
        default="gitlab-mr",
        help="scan ref to filter on (default: %(default)s)",
    )
    parser.add_argument(
        "--all-refs",
        action="store_true",
        help="ignore --ref and list findings from every ref",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token, deployment_slug = require_env("SEMGREP_APP_TOKEN", "SEMGREP_DEPLOYMENT_SLUG")
    ref = None if args.all_refs else args.ref

    try:
        ids = finding_ids(deployment_slug, token, ref)
    except ApiError as exc:
        print(exc, file=sys.stderr)
        return 1

    label = "all refs" if ref is None else f"ref {ref}"
    print(f"findings on {label}: {len(ids)}", file=sys.stderr)

    # ids go to stdout so the output pipes cleanly into diff, sort or wc
    for finding_id in ids:
        print(finding_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
