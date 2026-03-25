"""
ai_stale.py
───────────
Daily job that scans all open issues for stale and unassigned issues,
then posts a concise alert issue with AI-generated recommendations.

Runs every day at 08:00 UTC. Only posts if there are actionable issues.

Called by:
  - Job 5: daily schedule
  - Job 6: workflow_dispatch action=stale_check
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    REPO, POST_AS_ISSUE, ISSUE_NUMBER, call_claude,
    fetch_issues, enrich_issue,
    post_comment, create_issue,
    comment_header, comment_footer, issue_summary_text
)
from datetime import datetime

STALE_DAYS     = int(os.environ.get("STALE_DAYS", "3"))
CRITICAL_DAYS  = 7   # Issues older than this get flagged as critical


def build_prompt(stale_issues, unassigned_issues, critical_issues):
    stale_list    = "\n".join(f"- {issue_summary_text(i)}" for i in stale_issues[:15])
    unassig_list  = "\n".join(f"- {issue_summary_text(i)}" for i in unassigned_issues[:10])
    critical_list = "\n".join(f"- {issue_summary_text(i)}" for i in critical_issues[:8])

    return f"""Review these stale/unassigned GitHub issues from {REPO} and provide recommendations.

CRITICAL (>{CRITICAL_DAYS} days no update):
{critical_list or '(none)'}

STALE (>{STALE_DAYS} days no update):
{stale_list or '(none)'}

UNASSIGNED:
{unassig_list or '(none)'}

Write a concise daily alert with EXACTLY these sections:

## 🔴 Critical — Act Today
[Issues that have been stale for over {CRITICAL_DAYS} days. What should happen? Who should own it?]

## 🟡 Needs Attention This Week
[Stale or unassigned issues that need an owner or update soon.]

## 💬 Suggested Actions
[3-5 specific, named actions — e.g. "@alice to update #42 by EOD", "close #17 if no activity by Friday"]"""


def run():
    print(f"📖 Scanning open issues in {REPO} for stale/unassigned…")
    raw_issues  = fetch_issues(state="open", per_page=100)
    issues      = [enrich_issue(i) for i in raw_issues]

    stale_issues    = [i for i in issues if i["is_stale"]]
    unassigned      = [i for i in issues if not i["assignees"]]
    critical        = [i for i in issues if i["days_since_update"] > CRITICAL_DAYS]

    print(f"   Total open: {len(issues)} | Stale: {len(stale_issues)} | Unassigned: {len(unassigned)} | Critical: {len(critical)}")

    # Only post if there's something worth flagging
    if len(stale_issues) == 0 and len(unassigned) == 0:
        print("✅ No stale or unassigned issues. All clear — skipping report.")
        return

    print("🤖 Calling Claude for stale issue recommendations…")
    system = (
        "You are an engineering programme manager doing a daily health check. "
        "Be direct. Call out specific issues and owners. "
        "The goal is to get things moving — not to write a report for its own sake."
    )
    ai_body = call_claude(
        system,
        build_prompt(stale_issues, unassigned, critical),
        max_tokens=1000
    )

    # ── Full stale list ────────────────────────────────────────────────────────
    stale_table = "| # | Title | Days Open | Last Update | Assignee |\n|---|---|---|---|---|\n"
    for i in sorted(stale_issues, key=lambda x: -x["days_since_update"])[:20]:
        assignee = ", ".join(f"@{a}" for a in i["assignees"]) or "**unassigned**"
        stale_table += (
            f"| #{i['number']} | {i['title'][:55]} | {i['days_open']}d "
            f"| {i['days_since_update']}d ago | {assignee} |\n"
        )

    full_body = (
        comment_header(
            "⚠️", f"Daily Stale Issue Alert — {datetime.now().strftime('%d %b %Y')}",
            f"`{REPO}` · **{len(stale_issues)}** stale · **{len(unassigned)}** unassigned · **{len(critical)}** critical"
        )
        + ai_body
        + "\n\n---\n\n"
        + "### All Stale Issues\n\n"
        + stale_table
        + comment_footer()
    )

    if POST_AS_ISSUE:
        title = f"⚠️ Stale Issues Alert — {datetime.now().strftime('%d %b %Y')} ({len(stale_issues)} issues)"
        create_issue(title, full_body, labels=["ai-report"])
    elif ISSUE_NUMBER:
        post_comment(ISSUE_NUMBER, full_body)
    else:
        print(full_body)

    print("✅ Done.")


if __name__ == "__main__":
    run()
