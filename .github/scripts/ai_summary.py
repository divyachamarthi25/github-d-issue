"""
ai_summary.py
─────────────
Reads a GitHub issue (+ its comments), calls Claude, and posts a structured
AI summary comment directly on the issue.

Called by:
  - Job 1: auto-runs on every new issue
  - Job 2: /ai summary command
  - Job 3: needs-summary label applied
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    REPO, ISSUE_NUMBER, call_claude,
    fetch_issue, fetch_comments, enrich_issue,
    post_comment, comment_header, comment_footer
)


def build_prompt(issue, comments):
    comment_text = ""
    for c in comments[:12]:
        author = c["user"]["login"]
        body   = (c.get("body") or "")[:400]
        comment_text += f"\n**@{author}:** {body}\n"

    return f"""Analyse this GitHub issue and produce a structured summary.

━━━ ISSUE #{issue['number']} ━━━
Title:      {issue['title']}
State:      {issue['state']}
Author:     @{issue['author']}
Assignees:  {', '.join(issue['assignees']) or 'None'}
Labels:     {', '.join(issue['labels']) or 'None'}
Milestone:  {issue['milestone'] or 'None'}
Days open:  {issue['days_open']}
Last update:{issue['days_since_update']} days ago
Comments:   {issue['comments_count']}

Description:
{issue['body'] or '*(no description)*'}

Recent comments ({len(comments)} total):
{comment_text or '*(no comments yet)*'}
━━━━━━━━━━━━━━━━━

Respond with EXACTLY these sections — no extra text before or after:

## 📋 Status Snapshot
[1-2 sentences. Current state at a glance.]

## 🎯 What & Why
[What problem is being solved. Why it matters.]

## 🚧 Blockers & Risks
[Specific blockers or risks. Say "None identified" if none.]

## ✅ Next Actions
[Concrete next steps. Include suggested owner where possible.]

## ⏱️ ETA Assessment
[On track / At risk / Stalled — with brief reasoning.]

## 🏷️ Suggested Labels
[Any label additions or removals worth making. Say "No changes needed" if current labels are fine.]"""


def run():
    # ── Get issue data ─────────────────────────────────────────────────────────
    issue_number = ISSUE_NUMBER or os.environ.get("ISSUE_NUMBER")
    if not issue_number:
        print("❌ ISSUE_NUMBER not set")
        sys.exit(1)

    print(f"📖 Fetching issue #{issue_number} from {REPO}…")
    raw      = fetch_issue(issue_number)
    issue    = enrich_issue(raw)
    comments = fetch_comments(issue_number)

    print(f"   Title:    {issue['title']}")
    print(f"   Author:   @{issue['author']}")
    print(f"   Labels:   {issue['labels']}")
    print(f"   Comments: {len(comments)}")

    # ── Call Claude ────────────────────────────────────────────────────────────
    print("🤖 Calling Claude…")
    system = (
        "You are a senior engineering project manager. "
        "Analyse GitHub issues and produce clear, structured, actionable summaries "
        "for both engineering teams and leadership. "
        "Be specific and concise. Never use filler phrases."
    )
    ai_body = call_claude(system, build_prompt(issue, comments), max_tokens=1500)

    # ── Compose comment ────────────────────────────────────────────────────────
    stale_warning = ""
    if issue["is_stale"]:
        stale_warning = (
            f"\n> ⚠️ **Stale alert** — this issue has not been updated "
            f"in **{issue['days_since_update']} days**. "
            f"{'No assignee.' if not issue['assignees'] else ''}\n"
        )

    unassigned_warning = ""
    if not issue["assignees"]:
        unassigned_warning = (
            "\n> 🔴 **Unassigned** — no owner set on this issue.\n"
        )

    comment_body = (
        comment_header("🤖", f"AI Summary — #{issue['number']}")
        + stale_warning
        + unassigned_warning
        + ai_body
        + comment_footer()
    )

    # ── Post to GitHub ─────────────────────────────────────────────────────────
    post_comment(issue_number, comment_body)
    print("✅ Done.")


if __name__ == "__main__":
    run()
