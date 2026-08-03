# Collects finding IDs for one scan ref.
#
# Useful when a customer reports "the MR scan shows findings the branch scan
# doesn't" — pulling the IDs for a single ref makes the two sets comparable
# instead of arguing about screenshots.
#
#   export SEMGREP_APP_TOKEN=...
#   export SEMGREP_DEPLOYMENT_SLUG=...
#   python semgrep_findings_id.py [ref]        # ref defaults to gitlab-mr

import os
import sys

import requests

SEMGREP_APP_TOKEN = os.getenv("SEMGREP_APP_TOKEN")
DEPLOYMENT_SLUG = os.getenv("SEMGREP_DEPLOYMENT_SLUG")


def get_findings(deployment_slug, semgrep_token):
    url = f"https://semgrep.dev/api/v1/deployments/{deployment_slug}/findings"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {semgrep_token}",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()["findings"]


if not SEMGREP_APP_TOKEN or not DEPLOYMENT_SLUG:
    sys.exit("Set SEMGREP_APP_TOKEN and SEMGREP_DEPLOYMENT_SLUG before running.")

ref = sys.argv[1] if len(sys.argv) > 1 else "gitlab-mr"

findings = get_findings(DEPLOYMENT_SLUG, SEMGREP_APP_TOKEN)
finding_ids = [finding["id"] for finding in findings if finding.get("ref") == ref]

print(f"Findings on ref {ref}: {len(finding_ids)}")
for finding_id in finding_ids:
    print(finding_id)
