"""
ai_executive.py
───────────────
Generates a full executive programme health report — RAG status, key metrics,
risks, wins, leadership asks, and next-week outlook.

Posted as a new GitHub issue so it's pinnable, shareable, and preserved
in the repo's issue history.

Called by:
  - Job 2: /ai report command
  - Job 4: weekly Monday schedule (POST_AS_ISSUE=true)
  - Job 6: workflow_dispatch action=executive_report
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    REPO, ISSUE_NUMBER, POST_AS_ISSUE, call_claude,
    fetch_issues, enrich_issue,
    post_comment, create_issue,
    comment_header, comment_footer
)
from datetime import datetime


def build_prompt(open_issues, closed_issues):
    label_freq = {}
    assignee_load = {}
    for i in open_issues:
        for l in i["labels"]:
            label_freq[l] = label_freq.get(l, 0) + 1
        for a in i["assignees"]:
            assignee_load[a] = assignee_load.get(a, 0) + 1

    stale_count     = sum(1 for i in open_issues if i["is_stale"])
    unassigned_count= sum(1 for i in open_issues if not i["assignees"])

    top_open = "\n".join(
        f"#{i['number']} ({i['days_open']}d open) [{', '.join(i['labels'][:2]) or 'no labels'}] {i['title']}"
        for i in open_issues[:12]
    )
    recently_closed = "\n".join(
        f"#{i['number']} {i['title']}"
        for i in closed_issues[:6]
    )
    top_labels = ", ".join(f"{k}({v})" for k, v in sorted(label_freq.items(), key=lambda x: -x[1])[:8])
    workload   = ", ".join(f"@{k}({v})" for k, v in sorted(assignee_load.items(), key=lambda x: -x[1])[:6])

    return f"""Prepare a weekly executive programme health report for {REPO}.

DATE: {datetime.now().strftime('%d %B %Y')}

METRICS:
- Open issues: {len(open_issues)}
- Stale (>3d no update): {stale_count}
- Unassigned: {unassigned_count}
- Recently closed: {len(closed_issues)}
- Top labels: {top_labels or 'none'}
- Team workload: {workload or 'no assignees'}

TOP OPEN ISSUES:
{top_open}

RECENTLY CLOSED:
{recently_closed or '(none in this batch)'}

Write a crisp executive briefing with EXACTLY these sections. Use data — be specific.
Write for a VP of Engineering who has 3 minutes to read this.

# 📊 Weekly Programme Health Report
**Repository:** `{REPO}` · **Week of:** {datetime.now().strftime('%d %B %Y')}

## 🟢 / 🟡 / 🔴 Overall Status: [CHOOSE ONE: GREEN / AMBER / RED]
[One paragraph. What is the overall state of the programme? Why that RAG rating?]

## 📈 Key Metrics This Week
[Small table or bullet list: open count, closed, stale, unassigned, any trends]

## ⚠️ Top Risks Requiring Leadership Attention
[Top 3 issues or patterns that leadership should know about. Be specific — include issue numbers.]

## ✅ Wins This Week
[What was closed or resolved? Even small wins matter — show progress.]

## 📋 Recommended Actions for Leadership
[2-3 specific, actionable asks of leadership — approvals, unblocks, decisions needed.]

## 🔮 Next Week Outlook
[What should we expect next week? Any known risks or milestones coming up?]"""


def run():
    print(f"📖 Fetching issues from {REPO}…")
    open_raw   = fetch_issues(state="open",   per_page=100)
    closed_raw = fetch_issues(state="closed", per_page=30)

    open_issues   = [enrich_issue(i) for i in open_raw]
    closed_issues = [enrich_issue(i) for i in closed_raw]

    stale_count      = sum(1 for i in open_issues if i["is_stale"])
    unassigned_count = sum(1 for i in open_issues if not i["assignees"])

    print(f"   Open: {len(open_issues)} | Closed: {len(closed_issues)} | Stale: {stale_count}")

    print("🤖 Calling Claude for executive report…")
    system = (
        "You are Chief of Staff preparing a crisp, honest executive briefing "
        "for a VP of Engineering. "
        "Use data. Flag real risks. Give concrete recommendations. "
        "Write tight — no filler, no waffle. "
        "Leadership can tell when you're padding."
    )
    ai_body = call_claude(
        system,
        build_prompt(open_issues, closed_issues),
        max_tokens=2000
    )

    full_body = (
        comment_header(
            "📊", f"Weekly Programme Report — {datetime.now().strftime('%d %b %Y')}",
            f"`{REPO}` · {len(open_issues)} open · {stale_count} stale · {unassigned_count} unassigned"
        )
        + ai_body
        + comment_footer()
    )

    if POST_AS_ISSUE:
        title = f"📊 Weekly Programme Report — {datetime.now().strftime('%d %b %Y')}"
        create_issue(title, full_body, labels=["ai-report"])
    elif ISSUE_NUMBER:
        post_comment(ISSUE_NUMBER, full_body)
    else:
        print(full_body)

    print("✅ Done.")


if __name__ == "__main__":
    run()
