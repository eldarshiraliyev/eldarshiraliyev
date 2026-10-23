
#!/usr/bin/env python3
"""
Automatically sync GitHub profile README project cards with pinned repositories.

Requirements:
- Python 3.10+
- GITHUB_TOKEN environment variable
- README.md containing PINNED_PROJECTS_START and PINNED_PROJECTS_END markers

Optional:
- GITHUB_USERNAME (defaults to eldarshiraliyev)
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

USERNAME = os.environ.get("GITHUB_USERNAME", "eldarshiraliyev")
TOKEN = os.environ.get("GITHUB_TOKEN")

README_PATH = Path("README.md")

START_MARKER = "<!-- PINNED_PROJECTS_START -->"
END_MARKER = "<!-- PINNED_PROJECTS_END -->"

MAX_REPOSITORIES = 6
MAX_DESCRIPTION_LENGTH = 170
MAX_TOPICS = 3

ACCENT_COLOR = "D4F36A"
BACKGROUND_COLOR = "202124"

API_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          url
          description
          stargazerCount
          forkCount
          primaryLanguage {
            name
            color
          }
          repositoryTopics(first: 3) {
            nodes {
              topic {
                name
              }
            }
          }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------
# GitHub API
# ---------------------------------------------------------

def fetch_pinned_repositories():
    """Fetch repositories pinned on the specified GitHub profile."""

    if not TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is missing. "
            "Run this script through GitHub Actions or set the token locally."
        )

    payload = {
        "query": QUERY,
        "variables": {"login": USERNAME},
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "github-profile-readme-sync",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API returned HTTP {exc.code}.\n{body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to GitHub API: {exc.reason}"
        ) from exc

    if result.get("errors"):
        messages = [
            error.get("message", "Unknown GraphQL error")
            for error in result["errors"]
        ]
        raise RuntimeError(
            "GitHub GraphQL query failed:\n- " + "\n- ".join(messages)
        )

    user = result.get("data", {}).get("user")

    if user is None:
        raise RuntimeError(
            f"GitHub user '{USERNAME}' was not found or is inaccessible."
        )

    repositories = (
        user.get("pinnedItems", {}).get("nodes", [])
    )

    return [
        repo for repo in repositories
        if repo and repo.get("name") and repo.get("url")
    ][:MAX_REPOSITORIES]


# ---------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------

def escape_text(value):
    """Escape text before inserting it into HTML."""
    return html.escape(str(value or ""), quote=True)


def make_language_badge(language, color):
    """Build a valid Shields.io badge URL."""

    language = language or "Other"

    # Use a safe fallback if GitHub provides no valid color.
    if not isinstance(color, str) or not re.fullmatch(
        r"#[0-9a-fA-F]{6}", color
    ):
        color = f"#{ACCENT_COLOR}"

    label = urllib.parse.quote(language, safe="")
    message = urllib.parse.quote(language, safe="")
    badge_color = color.lstrip("#")

    return (
        "https://img.shields.io/badge/"
        f"Language-{label}-{badge_color}"
        "?style=flat-square"
        f"&labelColor={BACKGROUND_COLOR}"
    )


def make_topic_tags(repository):
    """Render repository topics as compact code tags."""

    topic_nodes = (
        repository.get("repositoryTopics") or {}
    ).get("nodes", [])

    topics = []

    for node in topic_nodes[:MAX_TOPICS]:
        topic = (node.get("topic") or {}).get("name")

        if topic:
            topics.append(
                f"<code>{escape_text(topic)}</code>"
            )

    return " &nbsp; ".join(topics)


# ---------------------------------------------------------
# Project cards
# ---------------------------------------------------------

def render_repository_card(repository, width="50%"):
    """Render a single repository card."""

    name = escape_text(repository.get("name"))
    url = escape_text(repository.get("url"))

    description = (
        repository.get("description") or "No description added yet."
    ).strip()

    if len(description) > MAX_DESCRIPTION_LENGTH:
        description = (
            description[:MAX_DESCRIPTION_LENGTH - 3].rstrip() + "..."
        )

    description = escape_text(description)

    language_data = repository.get("primaryLanguage") or {}
    language = language_data.get("name") or "Other"
    language_color = language_data.get("color")

    badge_url = make_language_badge(language, language_color)
    badge_url = escape_text(badge_url)
    safe_language = escape_text(language)

    stars = int(repository.get("stargazerCount") or 0)
    forks = int(repository.get("forkCount") or 0)

    topics = make_topic_tags(repository)

    if not topics:
        topics = "<sub>PINNED PROJECT</sub>"

    return f"""<td width="{width}" valign="top">

<h3><a href="{url}">{name} ↗</a></h3>

<p>{description}</p>

<p>
  <img src="{badge_url}" alt="{safe_language}" />
  &nbsp; <strong>★</strong> {stars}
  &nbsp; <strong>⑂</strong> {forks}
</p>

<p>{topics}</p>

</td>"""


def render_repository_section(repositories):
    """Render all pinned repositories in a two-column layout."""

    if not repositories:
        return (
            '<p align="center">'
            '<em>No repositories are pinned yet. '
            'Pin repositories on your GitHub profile and run this '
            'workflow again.</em>'
            '</p>'
        )

    tables = []

    for index in range(0, len(repositories), 2):
        group = repositories[index:index + 2]

        cells = [
            render_repository_card(repository)
            for repository in group
        ]

        # Use the full row width when only one repository remains.
        if len(cells) == 1:
            cells[0] = render_repository_card(
                group[0], width="100%"
            )

        table = (
            "<table>\n"
            "<tr>\n"
            + "\n".join(cells)
            + "\n</tr>\n"
            "</table>"
        )

        tables.append(table)

    return "\n\n".join(tables)


# ---------------------------------------------------------
# README updater
# ---------------------------------------------------------

def update_readme(repositories):
    """Replace only the content between the pinned-project markers."""

    if not README_PATH.is_file():
        raise RuntimeError(
            f"{README_PATH} was not found. "
            "Run this script from the repository root."
        )

    readme = README_PATH.read_text(encoding="utf-8")

    start_index = readme.find(START_MARKER)
    end_index = readme.find(END_MARKER)

    if start_index == -1 or end_index == -1:
        raise RuntimeError(
            "README.md is missing the required marker comments:\n"
            f"{START_MARKER}\n"
            f"{END_MARKER}"
        )

    if end_index <= start_index:
        raise RuntimeError(
            "README markers are in the wrong order."
        )

    content_start = start_index + len(START_MARKER)

    project_section = render_repository_section(repositories)

    updated_readme = (
        readme[:content_start]
        + "\n\n"
        + project_section
        + "\n\n"
        + readme[end_index:]
    )

    if updated_readme == readme:
        print("README is already up to date.")
        return

    README_PATH.write_text(
        updated_readme,
        encoding="utf-8",
        newline="\n",
    )

    print("README.md updated successfully.")


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

def main():
    print(f"Fetching pinned repositories for @{USERNAME}...")

    repositories = fetch_pinned_repositories()

    print(f"Found {len(repositories)} pinned repositories.")

    update_readme(repositories)

    print("Pinned project synchronization completed.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
