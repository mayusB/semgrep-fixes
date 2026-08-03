# Counts reachable supply-chain findings for a deployment.
#
# The Supply Chain tab in the UI paginates, so eyeballing a total is slow once a
# deployment has more than a page of findings. This asks the API instead.
#
#   export SEMGREP_APP_TOKEN=...
#   export SEMGREP_DEPLOYMENT_ID=...
#   python semgrep_ssc_vuln.py

import os
import sys

import requests

SEMGREP_APP_TOKEN = os.getenv("SEMGREP_APP_TOKEN")
DEPLOYMENT_ID = os.getenv("SEMGREP_DEPLOYMENT_ID")


def get_reachable_vulns(deployment_id, semgrep_token):
    url = f"https://semgrep.dev/api/v1/deployments/{deployment_id}/ssc-vulns"

    headers = {
        "Authorization": f"Bearer {semgrep_token}",
        "Content-Type": "application/json",
    }

    # exposure REACHABLE drops the transitive findings that aren't actually
    # called, which is the number people usually mean by "how many do we have".
    payload = {
        "pageSize": 100,
        "exposure": ["REACHABLE"],
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json().get("vulns", [])


if not SEMGREP_APP_TOKEN or not DEPLOYMENT_ID:
    sys.exit("Set SEMGREP_APP_TOKEN and SEMGREP_DEPLOYMENT_ID before running.")

vulns = get_reachable_vulns(DEPLOYMENT_ID, SEMGREP_APP_TOKEN)
count = sum(1 for vuln in vulns if "title" in vuln)

print(f"Reachable supply-chain findings on this page: {count}")
