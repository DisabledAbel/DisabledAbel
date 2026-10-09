"""Render a self-contained SVG metrics card for a GitHub profile README."""

import base64
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import html
import math

BG = "#0d1117"
LINE = "#30363d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
LEVELS = {
    "NONE": "#c9d1d9",
    "FIRST_QUARTILE": "#9be9a8",
    "SECOND_QUARTILE": "#40c463",
    "THIRD_QUARTILE": "#30a14e",
    "FOURTH_QUARTILE": "#39d353",
}


def text(x, y, value, size=14, color=TEXT, weight=400, anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>'
    )


def rect(x, y, width, height, color, radius=0, stroke="none"):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{color}" stroke="{stroke}"/>'


def icon(name, x, y):
    paths = {
        "calendar": '<rect x="2" y="4" width="14" height="12" rx="2"/><path d="M2 8h14M6 2v4M12 2v4"/>',
        "activity": '<path d="M2 15h14M3 12l3-5 4 3 5-7"/>',
        "repo": '<path d="M5 2h10v14H5a3 3 0 0 1 0-6h10M3 13V5a3 3 0 0 1 2-3M7 5h5"/>',
        "code": '<path d="M6 5 2 9l4 4M12 5l4 4-4 4M10 3 8 15"/>',
        "pr": '<circle cx="4" cy="3" r="2"/><circle cx="4" cy="15" r="2"/><circle cx="14" cy="15" r="2"/><path d="M4 5v8M10 3h1a3 3 0 0 1 3 3v7M10 3l2-2M10 3l2 2"/>',
        "person": '<circle cx="9" cy="5" r="3"/><path d="M3 16v-2a6 6 0 0 1 12 0v2"/>',
    }
    return f'<g transform="translate({x},{y})" fill="none" stroke="{MUTED}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</g>'


def heading(x, y, label, name):
    return icon(name, x, y - 14) + text(x + 28, y, label, 17, BLUE, 500)


def days_for(user):
    return [d for w in user["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]


def current_streak(days):
    # GitHub may have no contributions yet today; allow the streak to end yesterday.
    today = datetime.now(timezone.utc).date()
    counts = {date.fromisoformat(d["date"]): d["contributionCount"] for d in days}
    cursor = today if counts.get(today, 0) else today - timedelta(days=1)
    streak = 0
    while counts.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def isometric_calendar(weeks):
    parts = []
    maximum = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1) or 1
    for wi, week in enumerate(weeks):
        for day in reversed(week["contributionDays"]):
            di = day["weekday"]
            x, y = 534 + wi * 6.1 + di * 10.5, 256 + wi * 2.4 - di * 5.4
            count = day["contributionCount"]
            h = 2 if not count else 4 + 24 * math.sqrt(count / maximum)
            color = LEVELS.get(day["contributionLevel"], GREEN)
            a, b, c, d = (x, y - h), (x + 6.1, y + 2.4 - h), (x + 16.6, y - 3 - h), (x + 10.5, y - 5.4 - h)
            points = lambda vertices: " ".join(f"{px:.1f},{py:.1f}" for px, py in vertices)
            tooltip = html.escape(f'{day["date"]}: {count} contributions')
            parts.append(f'<g><title>{tooltip}</title>')
            parts.append(f'<polygon points="{points([a, b, (b[0], b[1] + h), (a[0], a[1] + h)])}" fill="{color}" opacity="0.55"/>')
            parts.append(f'<polygon points="{points([b, c, (c[0], c[1] + h), (b[0], b[1] + h)])}" fill="{color}" opacity="0.8"/>')
            parts.append(f'<polygon points="{points([a, b, c, d])}" fill="{color}" stroke="{BG}" stroke-width="0.35"/></g>')
    return "".join(parts)


def render_card(user, repositories, avatar, avatar_type):
    """All displayed counts come from GitHub; no placeholders enter the card."""
    login = user["login"]
    stats = user["contributionsCollection"]
    calendar = stats["contributionCalendar"]
    days = days_for(user)
    total = calendar["totalContributions"]
    name = user.get("name") or login
    description = f"{login}: {total:,} contributions, {stats['totalCommitContributions']:,} commits, {stats['totalPullRequestContributions']:,} pull requests in the past 12 months."
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="980" height="792" viewBox="0 0 980 792" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(name)} · @{html.escape(login)} — GitHub metrics</title>',
        f'<desc id="desc">{html.escape(description)} Public profile, contribution calendar, activity by weekday, repository languages, and recent pull requests.</desc>',
        '<defs><clipPath id="avatar"><circle cx="80" cy="78" r="46"/></clipPath></defs>',
        '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        rect(1, 1, 978, 790, BG, 14, LINE),
        f'<image x="34" y="32" width="92" height="92" clip-path="url(#avatar)" xlink:href="data:{avatar_type};base64,{base64.b64encode(avatar).decode()}"/>',
        '<circle cx="80" cy="78" r="46" fill="none" stroke="#30363d" stroke-width="2"/>',
        text(148, 66, name[:36], 26, BLUE, 600),
        text(148, 93, "@" + login, 17, TEXT),
        text(148, 118, "Building, learning, and contributing in public", 13, MUTED),
        rect(718, 47, 226, 38, "#122419", 19, "#1e4628"),
        '<circle cx="737" cy="66" r="4" fill="#3fb950"/>',
        text(753, 71, "LIVE GITHUB METRICS", 12, GREEN, 600),
        text(944, 113, "Refreshes every 2 hours", 12, MUTED, anchor="end"),
        f'<path d="M32 146H948" stroke="{LINE}"/>',
        heading(32, 181, "Profile overview", "person"),
        heading(512, 181, "Contributions calendar", "calendar"),
    ]
    stars = sum(r["stargazerCount"] for r in repositories)
    forks = sum(r["forkCount"] for r in repositories)
    overview = [
        ("Joined GitHub", user["createdAt"][:10]),
        ("Public repositories", len(repositories)),
        ("Followers", user["followers"]["totalCount"]),
        ("Stargazers", stars),
        ("Forks", forks),
    ]
    for index, (label, value) in enumerate(overview):
        y = 219 + index * 26
        parts += [text(36, y, label, 14, MUTED), text(454, y, f"{value:,}" if isinstance(value, int) else value, 14, TEXT, 500, "end")]
    parts.append(isometric_calendar(calendar["weeks"]))
    parts += [
        text(514, 410, f"{total:,}", 30, GREEN, 600),
        text(514, 433, "contributions in the past year", 12, MUTED),
        text(938, 406, f"{current_streak(days)} day streak", 15, TEXT, 500, "end"),
        text(938, 431, f"{total / max(len(days), 1):.2f} contributions / day", 12, MUTED, anchor="end"),
        heading(32, 392, "Contribution breakdown", "code"),
    ]
    for index, (label, count) in enumerate([
        ("Commits", stats["totalCommitContributions"]),
        ("Pull requests", stats["totalPullRequestContributions"]),
        ("Issues opened", stats["totalIssueContributions"]),
        ("Code reviews", stats["totalPullRequestReviewContributions"]),
    ]):
        x, y = 32 + index % 2 * 222, 410 + index // 2 * 83
        parts += [rect(x, y, 206, 70, "#161b22", 8), text(x + 14, y + 29, f"{count:,}", 25, TEXT, 600), text(x + 14, y + 53, label, 12, MUTED)]

    parts.append(heading(512, 486, "Most used languages", "code"))
    languages, colors = Counter(), {}
    for repository in repositories:
        if repository["isFork"]:
            continue
        for edge in repository["languages"]["edges"]:
            languages[edge["node"]["name"]] += edge["size"]
            colors[edge["node"]["name"]] = edge["node"].get("color") or MUTED
    language_total = sum(languages.values())
    top = languages.most_common(4)
    if language_total:
        x = 512
        parts.append(rect(512, 504, 430, 10, LINE, 5))
        for language, count in languages.most_common():
            width = 430 * count / language_total
            parts.append(rect(round(x, 2), 504, round(width, 2), 10, colors[language]))
            x += width
        for index, (language, count) in enumerate(top):
            y = 540 + index * 24
            parts += [f'<circle cx="519" cy="{y - 4}" r="4" fill="{colors[language]}"/>', text(532, y, language, 13), text(940, y, f"{100 * count / language_total:.1f}%", 13, MUTED, anchor="end")]
    else:
        parts.append(text(512, 531, "No public repository language data yet", 13, MUTED))

    parts.append(heading(32, 609, "Activity by day of the week", "activity"))
    weekdays = [0] * 7
    for day in days:
        weekdays[day["weekday"]] += day["contributionCount"]
    maximum = max(weekdays) or 1
    parts.append(f'<path d="M36 712H448" stroke="{LINE}"/>')
    for index, (label, count) in enumerate(zip(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], weekdays)):
        x = 44 + index * 59
        height = 65 * count / maximum
        if count:
            parts.append(rect(x, round(712 - height, 2), 21, round(height, 2), GREEN, 4))
        parts += [text(x + 10, round(703 - height, 2), count, 10, MUTED, anchor="middle"), text(x + 10, 732, label, 11, MUTED, anchor="middle")]
    parts.append(heading(512, 665, "Recent pull requests", "pr"))
    prs = user["pullRequests"]["nodes"][:2]
    for index, pr in enumerate(prs):
        y = 694 + index * 37
        title = pr["title"] if len(pr["title"]) <= 49 else pr["title"][:46] + "…"
        parts.append(text(514, y, title, 12))
        parts.append(text(514, y + 16, pr["repository"]["nameWithOwner"], 11, MUTED))
    if not prs:
        parts.append(text(514, 700, "No public pull requests yet", 13, MUTED))
    parts += [
        f'<path d="M32 755H948" stroke="{LINE}"/>',
        text(32, 777, "Public GitHub activity · Past 12 months", 11, MUTED),
        text(948, 777, "Repository languages measured by code size", 11, MUTED, anchor="end"),
        '</g></svg>\n',
    ]
    return "".join(parts)
