"""
Push testimonial.yml to GitHub via the API.

When the file is updated in the repo, CloudCannon detects the commit
and automatically rebuilds the Jekyll site.
"""

import base64
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


async def push_testimonial_yml(content: str) -> dict:
    """Commit updated testimonial.yml to the GitHub repo.

    Uses the GitHub Contents API:
    PUT /repos/{owner}/{repo}/contents/{path}
    """
    if not settings.github_token or not settings.github_repo:
        raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be set in .env")

    repo = settings.github_repo
    path = settings.github_testimonial_path
    branch = settings.github_branch
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"

    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        # Get current file SHA (needed for updates)
        get_resp = await client.get(url, headers=headers, params={"ref": branch})

        sha = None
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
        elif get_resp.status_code != 404:
            get_resp.raise_for_status()

        # Encode content to base64
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Build commit payload
        payload = {
            "message": "Update testimonials from review sync",
            "content": encoded,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        # Push the update
        put_resp = await client.put(url, headers=headers, json=payload)
        put_resp.raise_for_status()

        result = put_resp.json()
        commit_sha = result.get("commit", {}).get("sha", "unknown")

    logger.info(f"Pushed testimonial.yml to {repo} (commit: {commit_sha[:7]})")
    return {
        "repo": repo,
        "path": path,
        "branch": branch,
        "commit": commit_sha,
    }
