#!/usr/bin/env python3
"""Count reachable supply-chain findings for a deployment.

The Supply Chain view paginates, so totalling it by eye is slow once a
deployment has more than a page of findings. This asks the API instead.

Reachability is the filter that matters: it drops transitive dependencies that
are vulnerable but never actually called, which is usually the difference
between a number teams act on and a number they ignore.

    export SEMGREP_APP_TOKEN=...
    export SEMGREP_DEPLOYMENT_ID=...
    python semgrep_ssc_vuln.py
"""

from __future__ import annotations

import argparse
import sys

from semgrep_api import (
    SEMGREP_API_ROOT,
    ApiError,
    request_json,
    require_env,
    semgrep_session,
)

PAGE_SIZE = 100


def count_by_exposure(
    deployment_id: str,
    token: str,
    exposure: str,
    page_size: int = PAGE_SIZE,
) -> int:
    """Return the number of supply-chain findings at the given exposure level.

    Walks every page, because the count is the whole point and a single page
    silently undercounts any deployment with real traffic.
    """
    session = semgrep_session(token)
    url = f"{SEMGREP_API_ROOT}/deployments/{deployment_id}/ssc-vulns"

    total = 0
    page = 0

    while True:
        payload = request_json(
            session,
            "POST",
            url,
            json={"pageSize": page_size, "page": page, "exposure": [exposure]},
        )
        vulns = (payload or {}).get("vulns", [])
        if not vulns:
            return total

        total += len(vulns)

        # A short page means we've reached the end.
        if len(vulns) < page_size:
            return total
        page += 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--exposure",
        default="REACHABLE",
        choices=["REACHABLE", "UNREACHABLE", "UNKNOWN"],
        help="exposure level to count (default: %(default)s)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=PAGE_SIZE,
        help="results per request (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token, deployment_id = require_env("SEMGREP_APP_TOKEN", "SEMGREP_DEPLOYMENT_ID")

    try:
        total = count_by_exposure(
            deployment_id, token, args.exposure, page_size=args.page_size
        )
    except ApiError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"{args.exposure.lower()} supply-chain findings: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
