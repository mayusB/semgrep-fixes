# semgrep-fixes

Working reference configs for running Semgrep in CI across GitHub Actions, Azure
Pipelines and Jenkins/Bitbucket, plus a few API scripts for the questions the
dashboard can't answer.

## Why

I supported Semgrep customers through CI integration issues, and the same
handful of problems came back over and over: a monorepo reporting as one giant
project instead of per-service, diff scans and full scans configured the wrong
way round so the dashboard never showed a complete branch, Java projects with no
lockfile so supply-chain scanning silently found nothing, and Bitbucket PRs that
scan the wrong ref under Jenkins.

Each one took a round of back-and-forth to diagnose from a customer's redacted
YAML. This is the collection of configs that actually work, so the answer is a
link instead of a thread.

## What's here

```
ci-cd/
  semgrep_full_scan_GH.yaml    full scan: default branch + schedule, no PR trigger
  semgrep_pr_scan_GH.yaml      diff scan on PRs, monorepo matrix
  semgrep_full_pr_scan.yaml    both jobs in one file, include/exclude side by side
  semgrep_java.yml             build a Gradle lockfile first, then scan
  semgrep_python.yaml          pip-installed semgrep instead of the container
  azure_pipeline.yaml          Azure Pipelines, matrix over monorepo subdirs
  Jenkinsfile                  Jenkins + Bitbucket, picks diff vs full by PR id

semgrep_api.py                 shared session, pagination and error handling
semgrep_git_archive_tag.py     tag Semgrep projects whose GitHub repo is archived
semgrep_findings_id.py         list finding ids for one scan ref
semgrep_ssc_vuln.py            count reachable supply-chain findings
```

Three patterns run through the configs and are the actual content:

- **Monorepo split.** `SEMGREP_REPO_DISPLAY_NAME` combined with `semgrep ci
  --include=<subdir>` is what makes each service show up as its own project.
  Without it a monorepo is one project and per-team triage is impossible.
- **Diff vs full.** A `pull_request` trigger makes `semgrep ci` diff against the
  merge base. That's wanted on PRs and wrong on the default branch, which is why
  the full-scan workflow has push and schedule triggers only.
- **Lockfile before scan.** Supply-chain scanning reads the dependency lockfile.
  Gradle projects don't have one by default, so `semgrep_java.yml` generates it
  and passes it forward as an artifact before the scan job runs.

## Running it

The CI files are references — copy the relevant one into `.github/workflows/`
(or your Azure/Jenkins equivalent) and set `SEMGREP_APP_TOKEN` as a secret.

The scripts need Python 3.9+. Credentials come from the environment, everything
else from flags — `--help` on any of them lists the options.

```bash
pip install -r requirements.txt

export SEMGREP_APP_TOKEN=...
export SEMGREP_DEPLOYMENT_SLUG=your-deployment

python semgrep_findings_id.py --ref gitlab-mr
python semgrep_findings_id.py --all-refs        # to see which refs exist
```

`semgrep_git_archive_tag.py` also needs `GITHUB_AUTH_TOKEN` and `GITHUB_ORG`, and
takes `--dry-run` — it writes tags, so check what it matched before letting it
loose on a real deployment. `semgrep_ssc_vuln.py` reads `SEMGREP_DEPLOYMENT_ID`
instead of the slug, since that's what the `ssc-vulns` endpoint was called with.

Finding ids print to stdout and progress to stderr, so the output pipes into
`diff` or `wc -l` without needing to be cleaned up first.

## Notes

- These target Semgrep's hosted product. Self-hosted differs, particularly on SSO
  and on how the SCM connection is authorised.
- Written and last exercised against the API as it stood in 2024. I haven't
  re-verified the endpoints since, so treat the scripts as a starting point
  rather than a maintained client.
- All three scripts paginate, so counts don't quietly stop at 100. The Semgrep
  endpoints are page-number based and GitHub's are Link-header based, which is
  why `semgrep_api.py` handles both shapes.
- There are no tests. The scripts are thin wrappers over API calls, so the
  useful test would need a recorded fixture or a live deployment, and I had
  neither when writing them.
- Covers CI integration and the API only. Nothing here is about rule authoring.
