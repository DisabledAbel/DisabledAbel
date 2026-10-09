"""Refresh the generated README sections using GitHub's public profile data."""

import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

from profile_card import render_card

ROOT = Path(__file__).resolve().parents[1]
QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    login
    name
    createdAt
    followers { totalCount }
    avatarUrl(size: 256)
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      }
    }
    repositories(first: 100, after: $after, privacy: PUBLIC, ownerAffiliations: [OWNER]) {
      pageInfo { hasNextPage endCursor }
      nodes {
        isFork
        stargazerCount
        forkCount
        languages(first: 100) { edges { size node { name color } } }
      }
    }
    pullRequests(first: 2, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes { title repository { nameWithOwner } }
    }
  }
}
"""


def replace_section(readme, name, content):
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"
    if readme.count(start) != 1 or readme.count(end) != 1:
        raise ValueError(f"Expected exactly one {name} section")
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    updated, count = pattern.subn(lambda _: f"{start}\n{content}\n{end}", readme)
    if count != 1:
        raise ValueError(f"Invalid {name} marker order")
    return updated


def render_profile(user, card):
    login = user["login"]
    digest = hashlib.sha256(card.encode()).hexdigest()[:16]
    header = (
        '<p align="center">\n'
        f'  <a href="https://github.com/{login}">\n'
        f'    <img src="assets/profile-metrics.svg?v={digest}" '
        f'width="980" alt="@{login}: profile picture, contribution stats, calendar, and languages"/>\n'
        '  </a>\n'
        '</p>'
    )
    stats = user["contributionsCollection"]
    summary = (
        '<p align="center">\n'
        f'  <a href="https://github.com/{login}?tab=overview">'
        f"{stats['contributionCalendar']['totalContributions']:,} contributions"
        f" · {stats['totalCommitContributions']:,} commits"
        f" · {stats['totalPullRequestContributions']:,} pull requests</a><br/>\n"
        '  <sub>Public activity over the past 12 months · '
        'Checked every two hours · Updated only when data changes</sub>\n'
        '</p>'
    )
    return header, summary


def fetch_profile(login):
    repositories = []
    cursor = None
    while True:
        payload = json.dumps({"query": QUERY, "variables": {"login": login, "after": cursor}}).encode()
        request = Request(
            "https://api.github.com/graphql",
            data=payload,
            headers={
                "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                "Content-Type": "application/json",
                "User-Agent": "profile-readme-updater",
            },
        )
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if result.get("errors"):
            raise RuntimeError(f"GitHub API failed: {result['errors']}")
        user = result["data"]["user"]
        if not user:
            raise ValueError(f"GitHub user not found: {login}")
        connection = user["repositories"]
        repositories.extend(connection["nodes"])
        if not connection["pageInfo"]["hasNextPage"]:
            return user, repositories
        cursor = connection["pageInfo"]["endCursor"]


def main():
    login = os.environ["PROFILE_USERNAME"]
    user, repositories = fetch_profile(login)
    # Avatar requests deliberately omit the API authorization header.
    with urlopen(Request(user["avatarUrl"], headers={"User-Agent": "profile-readme-updater"}), timeout=30) as response:
        avatar = response.read()
        avatar_type = response.headers.get_content_type()
        if not avatar or avatar_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
            raise ValueError("GitHub returned an invalid avatar")

    card = render_card(user, repositories, avatar, avatar_type)
    header, stats = render_profile(user, card)
    readme_path = ROOT / "README.md"
    original = readme_path.read_text(encoding="utf-8")
    updated = replace_section(original, "PROFILE", header)
    updated = replace_section(updated, "CONTRIBUTION-STATS", stats)
    # Validate all data and markers before changing any files.
    avatar_path = ROOT / "assets" / "profile-avatar.png"
    avatar_path.parent.mkdir(parents=True, exist_ok=True)
    if not avatar_path.exists() or avatar_path.read_bytes() != avatar:
        avatar_path.write_bytes(avatar)
    card_path = ROOT / "assets" / "profile-metrics.svg"
    if not card_path.exists() or card_path.read_text(encoding="utf-8") != card:
        card_path.write_text(card, encoding="utf-8")
    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
