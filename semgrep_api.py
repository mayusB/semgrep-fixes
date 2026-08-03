"""Shared helpers for talking to the Semgrep and GitHub APIs.

The three scripts in this repo all need the same three things: a session with the
right auth header, a request that fails loudly instead of hanging, and a way to
follow pagination. Keeping that here means each script is just the query it
actually cares about.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from typing import Any

import requests

SEMGREP_API_ROOT = "https://semgrep.dev/api/v1"
GITHUB_API_ROOT = "https://api.github.com"

# Every request gets one. Without it a hung connection blocks forever, which is a
# miserable thing to debug from inside a CI job.
DEFAULT_TIMEOUT = 30


class ApiError(RuntimeError):
    """Raised when the API returns a response we can't use."""


def require_env(*names: str) -> list[str]:
    """Return the named environment variables, or exit with a usable message.

    Exits rather than raising because these are scripts — a traceback about a
    missing key is less helpful than being told which variable to set.
    """
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        sys.exit(f"Missing required environment variable(s): {', '.join(missing)}")
    return [os.environ[name] for name in names]


def semgrep_session(token: str) -> requests.Session:
    """A session pre-loaded with Semgrep auth headers."""
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
    )
    return session


def github_session(token: str) -> requests.Session:
    """A session pre-loaded with GitHub auth headers."""
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return session


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs: Any,
) -> Any:
    """Make a request and return the decoded JSON body.

    Wraps the two failure modes that actually happen in practice — the network
    call failing, and a 4xx/5xx whose body explains why — into one error type
    carrying the server's own message.
    """
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    try:
        response = session.request(method, url, **kwargs)
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = exc.response.text.strip()
        raise ApiError(f"{method} {url} -> {exc.response.status_code}: {body}") from exc
    except requests.RequestException as exc:
        raise ApiError(f"{method} {url} failed: {exc}") from exc

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise ApiError(f"{method} {url} returned a non-JSON body") from exc


def paginate(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Yield items from every page of a Link-header-paginated endpoint.

    requests parses the Link header for us via `response.links`, so there's no
    need to regex it out by hand.
    """
    params = {"per_page": 100, **(params or {})}

    while url:
        try:
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiError(f"GET {url} failed: {exc}") from exc

        payload = response.json()
        yield from _items(payload)

        # Subsequent URLs already carry their own query string.
        url = response.links.get("next", {}).get("url", "")
        params = None


def _items(payload: Any) -> list[Any]:
    """Normalise a page body to a list of items.

    Some endpoints return a bare list; the search-style ones wrap the results in
    an object alongside metadata like `total_count`.
    """
    if isinstance(payload, list):
        return payload
    if not payload:
        return []

    ignored = {"incomplete_results", "repository_selection", "total_count"}
    for key, value in payload.items():
        if key not in ignored and isinstance(value, list):
            return value
    return []
