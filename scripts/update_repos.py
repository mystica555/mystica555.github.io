#!/usr/bin/env python3
"""Regenerate the repository cards in index.html from the public GitHub API."""

from __future__ import annotations

import json
import os
import re
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

USER = "mystica555"
SITE_REPO = f"{USER}.github.io"
PINNED = ("TVPowerSync",)
FEATURED_EXTRAS = {"TVPowerSync": ("KDE Plasma 6",)}
API = "https://api.github.com"
INDEX = Path(__file__).resolve().parent.parent / "index.html"
INDENT = "          "

LANG_COLORS = {
    "C": "#555555",
    "C++": "#f34b7d",
    "CSS": "#563d7c",
    "Go": "#00add8",
    "HTML": "#e34c26",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Objective-C": "#438eff",
    "PHP": "#4f5d95",
    "Python": "#3572a5",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "TypeScript": "#3178c6",
}
DEFAULT_LANG_COLOR = "#8b949e"

_PARENT_CACHE: dict[str, dict] = {}


def api_get(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-homepage-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API}{path}", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise SystemExit(f"GitHub API request failed ({exc.code}) for {path}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"GitHub API request failed for {path}: {exc.reason}") from exc


def fetch_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        batch = api_get(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        if not isinstance(batch, list):
            raise SystemExit(f"Unexpected API response for page {page}")
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def fork_parent(repo: dict) -> dict:
    """Return the upstream repo object, fetching it if the list response omitted it."""
    full_name = repo["full_name"]
    if full_name in _PARENT_CACHE:
        return _PARENT_CACHE[full_name]

    parent = repo.get("parent") or {}
    if not parent.get("full_name"):
        detail = api_get(f"/repos/{quote(full_name, safe='/')}")
        parent = detail.get("parent") or {}

    _PARENT_CACHE[full_name] = parent
    return parent


def description(repo: dict) -> str:
    text = " ".join((repo.get("description") or "").split())
    if text:
        return escape(text)

    if repo.get("fork"):
        parent = fork_parent(repo)
        if parent.get("full_name"):
            return f"Fork of {escape(parent['full_name'])}."

    return "No description provided."


def page_url(repo: dict) -> str | None:
    if not repo.get("has_pages"):
        return None

    homepage = (repo.get("homepage") or "").strip()
    if homepage.startswith(("http://", "https://")):
        return homepage

    return f"https://{USER}.github.io/{quote(repo['name'])}/"


def lang_color(language: str) -> str:
    return LANG_COLORS.get(language, DEFAULT_LANG_COLOR)


def meta_item(repo: dict) -> str | None:
    language = repo.get("language")
    if not language:
        return None
    return (
        f'<li><span class="lang-dot" style="--dot: {lang_color(language)}" '
        f'aria-hidden="true"></span>{escape(language)}</li>'
    )


def action_links(repo: dict) -> list[str]:
    code_url = escape(repo["html_url"], quote=True)
    live_url = page_url(repo)
    links: list[str] = []

    if live_url:
        links.append(
            f'<a class="btn btn-primary" href="{escape(live_url, quote=True)}">'
            f'Visit the page <span aria-hidden="true">&#8599;</span></a>'
        )

    links.append(
        f'<a class="btn" href="{code_url}">'
        f'Source code <span aria-hidden="true">&#8599;</span></a>'
    )
    return links


def render_project(repo: dict, featured: bool) -> str:
    card_class = "card card-featured" if featured else "card"
    lines = [
        f'<article class="{card_class}">',
        '  <div class="card-head">',
        f'    <h3><a href="{escape(repo["html_url"], quote=True)}">{escape(repo["name"])}</a></h3>',
    ]

    if page_url(repo):
        lines.append('    <span class="badge badge-live">Live site</span>')

    lines.extend([
        '  </div>',
        f'  <p class="desc">{description(repo)}</p>',
    ])

    meta = [item for item in (meta_item(repo),) if item]
    if featured:
        meta.extend(f'<li>{escape(extra)}</li>' for extra in FEATURED_EXTRAS.get(repo["name"], ()))
    if meta:
        lines.append('  <ul class="meta">')
        lines.extend(f'    {item}' for item in meta)
        lines.append('  </ul>')

    lines.append('  <div class="actions">')
    lines.extend(f'    {link}' for link in action_links(repo))
    lines.append('  </div>')
    lines.append('</article>')
    return "\n".join(lines)


def render_fork(repo: dict) -> str:
    parent = fork_parent(repo)
    lines = [
        '<article class="card">',
        '  <div class="card-head">',
        f'    <h3><a href="{escape(repo["html_url"], quote=True)}">{escape(repo["name"])}</a></h3>',
        '    <span class="badge">Fork</span>',
        '  </div>',
        f'  <p class="desc">{description(repo)}</p>',
        '  <div class="card-foot">',
    ]

    language = repo.get("language")
    if language:
        lines.append(
            f'    <span class="lang"><span class="lang-dot" style="--dot: {lang_color(language)}" '
            f'aria-hidden="true"></span>{escape(language)}</span>'
        )

    if parent.get("full_name"):
        parent_url = parent.get("html_url") or f"https://github.com/{parent['full_name']}"
        lines.append(
            f'    <span class="fork-of">Fork of '
            f'<a href="{escape(parent_url, quote=True)}">{escape(parent["full_name"])}</a></span>'
        )

    lines.extend([
        '  </div>',
        '</article>',
    ])
    return "\n".join(lines)


def replace_block(html: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(?P<indent>[ \t]*)<!-- {re.escape(name)}:start -->.*?<!-- {re.escape(name)}:end -->",
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        raise SystemExit(f"Missing {name}:start / {name}:end markers in {INDEX}")

    indent = match.group("indent")
    block = f"{indent}<!-- {name}:start -->\n{body}\n{indent}<!-- {name}:end -->"
    return html[:match.start()] + block + html[match.end():]


def indent_cards(cards: list[str]) -> str:
    body = "\n\n".join(cards)
    return "\n".join(f"{INDENT}{line}" if line else "" for line in body.splitlines())


def main() -> None:
    original = INDEX.read_text(encoding="utf-8")
    for marker in ("projects", "forks", "repo-count"):
        if f"<!-- {marker}:start -->" not in original:
            raise SystemExit(f"Missing {marker}:start marker in {INDEX}")

    repos = fetch_repos()
    visible = [repo for repo in repos if repo["name"] != SITE_REPO]
    own = [repo for repo in visible if not repo.get("fork")]
    forks = [repo for repo in visible if repo.get("fork")]

    by_name = {repo["name"]: repo for repo in own}
    pinned = [by_name[name] for name in PINNED if name in by_name]
    pinned_names = {repo["name"] for repo in pinned}

    remaining = [repo for repo in own if repo["name"] not in pinned_names]
    remaining.sort(key=lambda repo: repo["name"].lower())
    remaining.sort(key=lambda repo: repo.get("pushed_at") or "", reverse=True)

    project_cards = [
        render_project(repo, featured=repo["name"] in pinned_names)
        for repo in pinned + remaining
    ]
    fork_cards = [
        render_fork(repo)
        for repo in sorted(forks, key=lambda repo: repo["name"].lower())
    ]

    updated = replace_block(original, "projects", indent_cards(project_cards))
    updated = replace_block(updated, "forks", indent_cards(fork_cards))
    updated, count = re.subn(
        r"(<!-- repo-count:start -->).*?(<!-- repo-count:end -->)",
        rf"\g<1>{len(repos)}\g<2>",
        updated,
        flags=re.DOTALL,
    )
    if count != 1:
        raise SystemExit(f"Expected one repo-count marker pair in {INDEX}")

    if updated == original:
        print(f"index.html is already current ({len(repos)} public repositories).")
        return

    INDEX.write_text(updated, encoding="utf-8")
    print(
        f"Updated index.html: {len(project_cards)} projects, "
        f"{len(fork_cards)} forks, {len(repos)} public repositories."
    )


if __name__ == "__main__":
    main()
