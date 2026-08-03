# Tags Semgrep projects whose GitHub repo has been archived.
#
# Archiving a repo on GitHub doesn't tell Semgrep anything, so the project keeps
# showing up in the dashboard and in scan counts. This walks the org's repos,
# finds the archived ones, and tags the matching Semgrep projects so they can be
# filtered out.
#
#   export GITHUB_AUTH_TOKEN=...        # needs repo read on the org
#   export SEMGREP_APP_TOKEN=...
#   export GITHUB_ORG=my-org
#   export SEMGREP_DEPLOYMENT_SLUG=my-deployment
#   python semgrep_git_archive_tag.py

# Importing required libraries
import requests
import os
import re
import sys

# Retrieving authentication tokens and targets from environment variables
GITHUB_AUTH_TOKEN = os.getenv("GITHUB_AUTH_TOKEN")
SEMGREP_APP_TOKEN = os.getenv("SEMGREP_APP_TOKEN")
GITHUB_ORG = os.getenv("GITHUB_ORG")
DEPLOYMENT_SLUG = os.getenv("SEMGREP_DEPLOYMENT_SLUG")

def get_paginated_data(url, github_token):
    next_pattern = r'(?<=<)([\S]*)(?=>; rel="next")'
    pages_remaining = True
    data = []

    while pages_remaining:

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_token}",
            "X-GitHub-Api-Version": "2022-11-28"
            }
        
        response = requests.get(url, params={"per_page": 100}, headers=headers)
        response_data = response.json()

        parsed_data = parse_data(response_data)
        data.extend(parsed_data)

        link_header = response.headers.get("link")

        pages_remaining = link_header and "rel=\"next\"" in link_header

        if pages_remaining:
            next_url_match = re.search(next_pattern, link_header)
            if next_url_match:
                url = next_url_match.group(0)

    return data

def parse_data(data):
    if isinstance(data, list):
        return data

    if not data:
        return []

    del data["incomplete_results"]
    del data["repository_selection"]
    del data["total_count"]

    namespace_key = list(data.keys())[0]
    data = data[namespace_key]

    return data

# Function to retrieve archived repositories from GitHub
def get_archived_repos(data):

    repos = data
    
    # Extracting archived repository names
    archived_repos = [repo["full_name"] for repo in repos if repo.get("archived")]
    
    print(f"GitHub Archived Repos: {archived_repos}")
    return archived_repos
    
# Function to retrieve all projects from SEMGREP
def get_all_projects(archived_repos, semgrep_token):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {semgrep_token}"
    }
    page = 0
    url = f"https://semgrep.dev/api/v1/deployments/{DEPLOYMENT_SLUG}/projects"
    
    # Sending GET request to SEMGREP API to retrieve projects
    response = requests.get(url, params={"page": {page}}, headers=headers)
    
    # Parsing response JSON data
    projects_data = response.json()["projects"]
    
    # Matching archived repositories with SEMGREP projects
    projects_to_tag = [project["name"] for project in projects_data if project["name"] in archived_repos]
    
    print(f"Scanned SCP Projects to Tag: {projects_to_tag}")

    return projects_to_tag    

# Function to tag archived repositories in SEMGREP
def tag_archived_repos(projects_to_tag, semgrep_token):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {semgrep_token}"
    }

    # Constructing payload for tagging archived repositories
    payload = {"tags": ["archived"]}

    # Tagging archived repositories in SEMGREP
    for project_name in projects_to_tag:
        url = f"https://semgrep.dev/api/v1/deployments/{DEPLOYMENT_SLUG}/projects/{project_name}/tags"
        response = requests.put(url, headers=headers, json=payload)
        if response.ok:
            print(f"Project tag successful: {project_name}")
        else:
            print(f"Project tag failed for {project_name}: {response.status_code} {response.text}")

# Fail early rather than sending unauthenticated requests
if not all([GITHUB_AUTH_TOKEN, SEMGREP_APP_TOKEN, GITHUB_ORG, DEPLOYMENT_SLUG]):
    sys.exit(
        "Set GITHUB_AUTH_TOKEN, SEMGREP_APP_TOKEN, GITHUB_ORG and "
        "SEMGREP_DEPLOYMENT_SLUG before running."
    )

# Retrieve archived repositories
data = get_paginated_data(f"https://api.github.com/orgs/{GITHUB_ORG}/repos", GITHUB_AUTH_TOKEN)
archived_repos = get_archived_repos(data)

# Retrieve all projects from SEMGREP
projects_to_tag = get_all_projects(archived_repos, SEMGREP_APP_TOKEN)

# Tag archived repositories in SEMGREP
tag_archived_repos(projects_to_tag, SEMGREP_APP_TOKEN)