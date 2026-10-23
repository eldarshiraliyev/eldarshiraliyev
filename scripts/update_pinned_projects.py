#!/usr/bin/env python3
"""Sync README project cards with repositories pinned on a GitHub profile."""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "eldarshiraliyev")
TOKEN = os.environ.get("GITHUB_TOKEN")
README_PATH = "README.md"
START = "<!-- PINNED_PROJECTS_START -->"
END = "<!-- PINNED_PROJECTS_END -->"

QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name url description stargazerCount forkCount
          primaryLanguage { name color }
          repositoryTopics(first: 3) { nodes { topic { name } } }
        }
      }
    }
  }
}
"""

def fetch_repos():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing.")
    data = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-readme-pinned-sync"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    if payload.get("errors"):
        raise RuntimeError("GraphQL error: " + json.dumps(payload["errors"]))
    user = payload.get("data", {}).get("user")
    if user is None:
        raise RuntimeError(f"GitHub user {USERNAME!r} was not found.")
    return user.get("pinnedItems", {}).get("nodes", [])

def card(repo):
    name = html.escape(repo.get("name") or "Repository")
    url = html.escape(repo.get("url") or f"https://github.com/{USERNAME}", quote=True)
    desc = html.escape((repo.get("description") or "No description added yet.").strip())
    if len(desc) > 170:
        desc = desc[:167].rstrip() + "..."
    lang = repo.get("primaryLanguage") or {}
    language = html.escape(lang.get("name") or "Code")
    color = lang.get("color") or "#D4F36A"
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        color = "#D4F36A"
    topics = [html.escape(x.get("topic", {}).get("name", ""))
              for x in (repo.get("repositoryTopics") or {}).get("nodes", [])
              if x.get("topic", {}).get("name")]
    tags = " ".join(f"<code>{t}</code>" for t in topics[:3]) or "<sub>PINNED REPOSITORY</sub>"
    stars, forks = int(repo.get("stargazerCount") or 0), int(repo.get("forkCount") or 0)
    safe_badge = language.replace(" ", "%20").replace("-", "--").replace("_", "__")
    badge = f"https://img.shields.io/badge/{safe_badge}- -?style=flat-square&labelColor=202124&color={color[1:]}"
    return f"""<td width="50%" valign="top">

<a href="{url}"><strong>{name} ↗</strong></a>

{desc}

<br/><br/>

<sub><img src="{badge}" alt="{language}"/> &nbsp; ★ {stars} &nbsp;⑂ {forks}</sub>

{tags}

</td>"""

def render(repos):
    if not repos:
        return '<div align="center">\\n\\n_No repositories are pinned yet. Pin repositories on your GitHub profile and run this workflow again._\\n\\n</div>'
    tables = []
    for i in range(0, len(repos), 2):
        cells = [card(r) for r in repos[i:i+2]]
        if len(cells) == 1:
            cells.append('<td width="50%" valign="top"></td>')
        tables.append("<table>\\n<tr>\\n" + "\\n".join(cells) + "\\n</tr>\\n</table>")
    return "\\n\\n".join(tables)

def main():
    repos = fetch_repos()
    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()
    a, b = readme.find(START), readme.find(END)
    if a < 0 or b < 0 or b <= a:
        raise RuntimeError("README pinned-project marker comments are missing or out of order.")
    updated = readme[:a + len(START)] + "\\n" + render(repos) + "\\n" + readme[b:]
    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
    print(f"Synced {len(repos)} pinned repositories for {USERNAME}.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
