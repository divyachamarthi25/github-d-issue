"""
ai_triage.py
────────────
Fetches all open issues, calls Claude for a bulk triage report, and
posts the result either as:
  - A comment on the triggering issue (slash command mode)
  - A new issue in the repo (scheduled/manual mode, POST_AS_ISSUE=true)

Called by:
  - Job 2: /ai triage command (posts as comment)
  - Job 4: weekly Monday schedule (creates new issue)
  - Job 6: workflow_dispatch action=triage
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    REPO, ISSUE_NUMBER, POST_AS_ISSUE, call_claude,
    fetch_issues, enrich_issue,
    post_comment, create_issue,
    comment_header, comment_footer, issue_summary_text
)
from datetime import datetime


def build_issue_listing(issues):
    lines = []
    for i in issues[:30]:
        stale   = " [STALE]"       if i["is_stale"] else ""
        unassig = " [UNASSIGNED]"  if not i["assignees"] else ""
        lines.append(
            f"#{i['number']} [{i['state'].upper()}]{stale}{unassig} {i['title']}\n"
            f"  Labels: {', '.join(i['labels']) or 'none'} | "
            f"Assignees: {', '.join(i['assignees']) or 'NONE'} | "
            f"Days open: {i['days_open']} | "
            f"Days since update: {i['days_since_update']} | "
            f"Comments: {i['comments_count']}"
            + (f" | Milestone: {i['milestone']}" if i['milestone'] else "")
        )
    return "\n".join(lines)


def build_prompt(issues, open_count, stale_count, unassigned_count):
    return f"""Triage {len(issues)} GitHub issues for the repository: {REPO}

SUMMARY METRICS:
- Total open issues: {open_count}
- Stale (>{os.environ.get('STALE_DAYS','3')} days no update): {stale_count}
- Unassigned: {unassigned_count}
- Date: {datetime.now().strftime('%d %b %Y')}

ISSUES:
{build_issue_listing(issues)}

Produce a structured triage report with EXACTLY these sections:

## 🚨 Critical — Immediate Attention Required
[Issues that are stale >7 days, unassigned, or blocking others. List by number with one-line reasoning.]

## 🔥 Top 5 — This Sprint's Focus
[The 5 most important open issues to close this sprint. Brief reasoning for each.]

## 📊 Pattern Analysis
[2-3 sentences. What themes or hotspots appear across the issues? Common labels, areas of the codebase, or types of problems?]

## ⚠️ Risk Flags
[Issues that look at risk: poorly scoped, missing acceptance criteria, no owner, or have been open too long.]

## 👥 Workload Balance
[Are any individuals overloaded? Any issues that should be redistributed? Be specific about usernames if possible.]

## 💡 Process Recommendations
[2-3 actionable suggestions to improve how issues are tracked in this repo.]

## 📈 Programme Health Score
[Score 1–10 with one paragraph justification. Be honest.]"""


def run():
    print(f"📖 Fetching all open issues from {REPO}…")
    raw_issues = fetch_issues(state="open", per_page=100)
    issues     = [enrich_issue(i) for i in raw_issues]

    open_count      = len(issues)
    stale_count     = sum(1 for i in issues if i["is_stale"])
    unassigned_count= sum(1 for i in issues if not i["assignees"])

    print(f"   Open: {open_count} | Stale: {stale_count} | Unassigned: {unassigned_count}")

    if open_count == 0:
        msg = "✅ No open issues found — nothing to triage!"
        if ISSUE_NUMBER:
            post_comment(ISSUE_NUMBER, msg)
        else:
            print(msg)
        return

    print("🤖 Calling Claude for bulk triage…")
    system = (
        "You are a senior engineering programme manager. "
        "Triage GitHub issues with sharp, data-driven analysis. "
        "Flag risks clearly. Give concrete, actionable recommendations. "
        "Never pad with filler. Be specific about issue numbers."
    )
    ai_body = call_claude(
        system,
        build_prompt(issues, open_count, stale_count, unassigned_count),
        max_tokens=2500
    )

    # ── Build stats header ─────────────────────────────────────────────────────
    stats = (
        f"| Metric | Count |\n|---|---|\n"
        f"| Open issues | **{open_count}** |\n"
        f"| Stale (no update >{os.environ.get('STALE_DAYS','3')}d) | **{stale_count}** |\n"
        f"| Unassigned | **{unassigned_count}** |\n"
        f"| Closed issues | **{len(fetch_issues(state='closed', per_page=30))}** |\n"
    )

    full_body = (
        comment_header(
            "⚡", "AI Bulk Triage Report",
            f"Analysed **{open_count}** open issues in `{REPO}`"
        )
        + stats
        + "\n---\n\n"
        + ai_body
        + comment_footer()
    )

    # ── Post result ────────────────────────────────────────────────────────────
    if POST_AS_ISSUE:
        title = f"📊 AI Triage Report — {datetime.now().strftime('%d %b %Y')}"
        create_issue(title, full_body, labels=["ai-report"])
    elif ISSUE_NUMBER:
        post_comment(ISSUE_NUMBER, full_body)
    else:
        print(full_body)

    print("✅ Done.")


if __name__ == "__main__":
    run()
