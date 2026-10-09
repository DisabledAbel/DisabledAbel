"""Refresh the generated README sections using GitHub's public profile data."""

import hashlib
import html
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    avatarUrl(size: 256)
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar { totalContributions }
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


def render_profile(user, avatar):
    login = html.escape(user["login"], quote=True)
    digest = hashlib.sha256(avatar).hexdigest()[:16]
    header = (
        '<p align="center">\n'
        f'  <a href="https://github.com/{login}">\n'
        f'    <img src="assets/profile-avatar.png?v={digest}" '
        f'width="160" height="160" alt="{login}\'s GitHub profile picture"/>\n'
        '  </a>\n'
        '</p>\n'
        f'<h2 align="center">@{login}</h2>'
    )
    stats = user["contributionsCollection"]
    rows = [
        ("Total contributions", stats["contributionCalendar"]["totalContributions"]),
        ("Commits", stats["totalCommitContributions"]),
        ("Pull requests", stats["totalPullRequestContributions"]),
        ("Issues", stats["totalIssueContributions"]),
        ("Code reviews", stats["totalPullRequestReviewContributions"]),
    ]
    table = "| Contribution | Count |\n| :--- | ---: |\n"
    table += "\n".join(f"| {label} | {int(count):,} |" for label, count in rows)
    table += (
        f"\n\n[View my contribution activity](https://github.com/{login}?tab=overview)\n\n"
        "Public activity over the past 12 months. Checked every two hours; "
        "updated when the photo or counts change."
    )
    return header, table


def main():
    login = os.environ["PROFILE_USERNAME"]
    payload = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
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
    # Avatar requests deliberately omit the API authorization header.
    with urlopen(Request(user["avatarUrl"], headers={"User-Agent": "profile-readme-updater"}), timeout=30) as response:
        avatar = response.read()
        if not avatar or not response.headers.get_content_type().startswith("image/"):
            raise ValueError("GitHub returned an invalid avatar")

    header, stats = render_profile(user, avatar)
    readme_path = ROOT / "README.md"
    original = readme_path.read_text(encoding="utf-8")
    updated = replace_section(original, "PROFILE", header)
    updated = replace_section(updated, "CONTRIBUTION-STATS", stats)
    # Validate all data and markers before changing any files.
    avatar_path = ROOT / "assets" / "profile-avatar.png"
    avatar_path.parent.mkdir(parents=True, exist_ok=True)
    if not avatar_path.exists() or avatar_path.read_bytes() != avatar:
        avatar_path.write_bytes(avatar)
    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
