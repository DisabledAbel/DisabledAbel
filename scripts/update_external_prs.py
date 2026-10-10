"""Generate EXTERNAL_PRS.md from open public PRs authored by the profile user."""

import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    pullRequests(first: 100, after: $after, states: [OPEN], orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title url state isDraft createdAt
        repository { nameWithOwner isPrivate owner { login } }
      }
    }
  }
}
"""


def github_request(login, cursor):
    payload = json.dumps({"query": QUERY, "variables": {"login": login, "after": cursor}}).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "external-pr-report-updater",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"GitHub API returned HTTP {error.code}; check PAT access and rate limits") from None
    except URLError:
        raise RuntimeError("Cannot reach the GitHub API") from None


def fetch_pull_requests(login):
    prs = {}
    cursor = None
    seen_cursors = set()
    while True:
        result = github_request(login, cursor)
        if result.get("errors"):
            raise RuntimeError("GitHub GraphQL returned errors; the existing report was preserved")
        user = result.get("data", {}).get("user")
        if not user:
            raise ValueError(f"GitHub user not found: {login}")
        connection = user["pullRequests"]
        for pr in connection["nodes"]:
            repo = pr["repository"]
            if (
                pr["state"] == "OPEN"
                and not repo["isPrivate"]
                and repo["owner"]["login"].casefold() != login.casefold()
            ):
                prs[pr["url"]] = pr
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            return list(prs.values())
        cursor = page["endCursor"]
        if not cursor or cursor in seen_cursors:
            raise RuntimeError("GitHub returned an invalid pagination cursor")
        seen_cursors.add(cursor)


def markdown_text(value):
    # Titles are API data, so escape markup and table delimiters.
    value = html.escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!~|])", r"\\\1", value)


def render_report(login, prs):
    prs = sorted(prs, key=lambda pr: (pr["createdAt"], pr["url"]), reverse=True)
    repos = {pr["repository"]["nameWithOwner"] for pr in prs}
    lines = [
        "# Open pull requests to other repositories",
        "",
        f"Open public pull requests authored by [@{login}](https://github.com/{login}) in repositories owned by other accounts.",
        "Organization repositories are included even when the author is a member or collaborator.",
        "Draft PRs are included. PRs are removed when they close or merge.",
        "",
        f"**{len(prs)} open PRs across {len(repos)} repositories**",
        "",
        "Checked every 12 hours by [the update workflow](.github/workflows/update-external-prs.yml). Updated only when the report changes.",
        "",
        "| Repository | Pull request | Status | Opened (UTC) |",
        "| --- | --- | --- | --- |",
    ]
    for pr in prs:
        repo = pr["repository"]["nameWithOwner"]
        state = "Draft" if pr["isDraft"] else "Open"
        lines.append(
            f"| [{repo}](https://github.com/{repo}) | [#{pr['number']} — {markdown_text(pr['title'])}]({pr['url']}) | {state} | {pr['createdAt'][:10]} |"
        )
    if not prs:
        lines += ["", "No open public pull requests to other accounts' repositories found."]
    return "\n".join(lines) + "\n"


def main():
    login = os.environ.get("PROFILE_USERNAME", "DisabledAbel")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", login):
        raise ValueError("PROFILE_USERNAME must be a GitHub username")
    if not os.environ.get("GH_TOKEN"):
        raise ValueError("Set the repository Actions secret PR_REPORT_PAT (or GH_TOKEN for a local run)")
    report = render_report(login, fetch_pull_requests(login))
    path = ROOT / "EXTERNAL_PRS.md"
    if path.exists() and path.read_text(encoding="utf-8") == report:
        print("External PR report is unchanged.")
        return
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(path)
    print("Updated EXTERNAL_PRS.md.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError) as error:
        print(f"External PR report failed: {error}", file=sys.stderr)
        sys.exit(1)
