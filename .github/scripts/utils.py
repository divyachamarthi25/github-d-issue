"""
utils.py — Shared helpers for all GitHub AI PM scripts.
All scripts import from here. No external dependencies beyond requests.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
REPO              = os.environ.get("REPO", "")          # "owner/repo"
ISSUE_NUMBER      = os.environ.get("ISSUE_NUMBER", "")
POST_AS_ISSUE     = os.environ.get("POST_AS_ISSUE", "false").lower() == "true"


# ── GitHub API ────────────────────────────────────────────────────────────────
def _gh_headers():
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GH-AI-PM-Action/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def gh_get(url):
    """GET from GitHub API, returns parsed JSON."""
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GitHub GET {url} → {e.code}: {body}") from e


def gh_post(url, payload):
    """POST JSON to GitHub API, returns parsed JSON."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={**_gh_headers(), "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"GitHub POST {url} → {e.code}: {body}") from e


def post_comment(issue_number, body):
    """Post a comment on a GitHub issue."""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
    result = gh_post(url, {"body": body})
    print(f"✅ Posted comment on #{issue_number}: {result['html_url']}")
    return result


def create_issue(title, body, labels=None):
    """Create a new GitHub issue (used for weekly reports)."""
    url = f"https://api.github.com/repos/{REPO}/issues"
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    result = gh_post(url, payload)
    print(f"✅ Created issue #{result['number']}: {result['html_url']}")
    return result


def fetch_issues(state="open", per_page=100):
    """Fetch all issues (excluding PRs) from the repo."""
    url = f"https://api.github.com/repos/{REPO}/issues?state={state}&per_page={per_page}&sort=updated"
    raw = gh_get(url)
    return [i for i in raw if "pull_request" not in i]


def fetch_issue(number):
    """Fetch a single issue by number."""
    return gh_get(f"https://api.github.com/repos/{REPO}/issues/{number}")


def fetch_comments(issue_number, per_page=20):
    """Fetch comments for an issue."""
    try:
        url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments?per_page={per_page}"
        return gh_get(url)
    except Exception:
        return []


def enrich_issue(issue):
    """Add computed fields (days_open, is_stale, etc.) to an issue dict."""
    now     = datetime.now(timezone.utc)
    created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    updated = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
    return {
        "number":            issue["number"],
        "title":             issue["title"],
        "state":             issue["state"],
        "body":              (issue.get("body") or "")[:600],
        "labels":            [l["name"] for l in issue.get("labels", [])],
        "assignees":         [a["login"] for a in issue.get("assignees", [])],
        "author":            issue["user"]["login"],
        "created_at":        issue["created_at"],
        "updated_at":        issue["updated_at"],
        "days_open":         (now - created).days,
        "days_since_update": (now - updated).days,
        "comments_count":    issue.get("comments", 0),
        "url":               issue["html_url"],
        "is_stale":          (now - updated).days > int(os.environ.get("STALE_DAYS", "3")),
        "milestone":         (issue.get("milestone") or {}).get("title"),
    }


# ── Claude API ────────────────────────────────────────────────────────────────
def call_claude(system: str, user: str, max_tokens: int = 2000) -> str:
    """Call Anthropic Claude and return the text response."""
    if not ANTHROPIC_API_KEY:
        return (
            "⚠️ **AI features disabled** — `ANTHROPIC_API_KEY` secret is not set.\n\n"
            "Add it in: **Settings → Secrets → Actions → New repository secret**\n"
            "Name: `ANTHROPIC_API_KEY`  Value: your Anthropic API key from console.anthropic.com"
        )

    payload = json.dumps({
        "model":      "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "system":     system,
        "messages":   [{"role": "user", "content": user}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":    "application/json",
            "x-api-key":       ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Claude API error {e.code}: {body}") from e


# ── Formatters ────────────────────────────────────────────────────────────────
def comment_header(icon, title, subtitle=None):
    """Standard header block for all AI comments."""
    today = datetime.now().strftime("%d %b %Y, %H:%M UTC")
    lines = [
        f"## {icon} {title}",
        f"*Generated by GitHub AI PM · {today}*",
    ]
    if subtitle:
        lines.append(f"\n{subtitle}")
    lines.append("\n---\n")
    return "\n".join(lines)


def comment_footer():
    return (
        "\n\n---\n"
        "*🤖 Powered by [Claude](https://anthropic.com) · "
        "Use `/ai help` for available commands · "
        "[View workflow runs](../../actions)*"
    )


def issue_summary_text(issue):
    """One-line summary of an issue for use in tables."""
    stale  = " ⚠️" if issue["is_stale"] else ""
    unassigned = " 🔴" if not issue["assignees"] else ""
    labels = f" `{'` `'.join(issue['labels'][:2])}`" if issue["labels"] else ""
    return (
        f"#{issue['number']} — **{issue['title'][:70]}**"
        f"{labels}{stale}{unassigned}\n"
        f"  └ {issue['days_open']}d open · "
        f"{'@' + ', @'.join(issue['assignees']) if issue['assignees'] else 'unassigned'} · "
        f"{issue['days_since_update']}d since update"
    )
