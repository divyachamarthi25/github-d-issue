"""
ai_migration.py
───────────────
Auto-detects migration-related issues using keyword + label matching,
then calls Claude to produce a leadership-ready migration status dashboard.

Called by:
  - Job 2: /ai migration command
  - Job 3: migration / cloud-migration label applied
  - Job 6: workflow_dispatch action=migration_status
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

# Keywords used to identify migration-related issues
MIGRATION_KEYWORDS = [
    "migrat", "cloud", "legacy", "infra", "k8s", "kubernetes",
    "aws", "gcp", "azure", "terraform", "docker", "containeris",
    "refactor", "port ", "move to", "moderniz", "lift", "shift",
    "decommission", "sunset", "deprecat",
]


def is_migration_issue(issue):
    text = (issue["title"] + " " + " ".join(issue["labels"])).lower()
    return any(kw in text for kw in MIGRATION_KEYWORDS)


def build_prompt(all_issues, migration_issues):
    def fmt(issues, limit=20):
        lines = []
        for i in issues[:limit]:
            tag = "🔁 MIG" if is_migration_issue(i) else "📋 BAU"
            lines.append(
                f"{tag} #{i['number']} [{i['state'].upper()}]: {i['title']}\n"
                f"     Labels: {', '.join(i['labels']) or 'none'} | "
                f"Assignee: {', '.join(i['assignees']) or 'NONE'} | "
                f"{i['days_open']}d open | {i['days_since_update']}d since update"
            )
        return "\n".join(lines)

    open_mig   = [i for i in migration_issues if i["state"] == "open"]
    closed_mig = [i for i in migration_issues if i["state"] == "closed"]
    bau        = [i for i in all_issues if not is_migration_issue(i)]

    return f"""Analyse issues from {REPO} and produce a migration programme status report.

OVERVIEW:
- Total issues analysed: {len(all_issues)}
- Migration-related issues: {len(migration_issues)} ({len(open_mig)} open, {len(closed_mig)} closed)
- BAU issues: {len(bau)}
- Date: {datetime.now().strftime('%d %b %Y')}

MIGRATION ISSUES:
{fmt(migration_issues, 25)}

BAU ISSUES (sample):
{fmt(bau[:10], 10)}

Produce a migration status dashboard with EXACTLY these sections:

## 🗺️ Migration Programme Overview
[Executive summary in 2-3 sentences. Overall confidence and trajectory.]

## ✅ Completed / Closed Items
[List closed migration issues with #number and title. If none, say so.]

## 🔄 In Progress
[Active open migration items. For each: #number, title, who owns it, how many days open.]

## 🚧 Blocked / At Risk
[Stale migration items, unassigned ones, or those that look problematic. Be specific.]

## 📊 Migration Health Metrics
| Metric | Value |
|---|---|
| Estimated % complete | X% |
| Open migration items | N |
| Blocked / stale | N |
| Unassigned | N |
| Avg age of open items | X days |

## 📋 BAU vs Migration Split
[What % of the team's visible GitHub work is migration vs BAU? Any imbalance?]

## 🔮 Forecast & Top 3 Unblocking Actions
[Timeline assessment and the 3 most impactful things leadership could do to accelerate the migration.]"""


def run():
    print(f"📖 Fetching all issues from {REPO}…")
    open_raw   = fetch_issues(state="open",   per_page=100)
    closed_raw = fetch_issues(state="closed", per_page=50)
    all_raw    = open_raw + closed_raw

    all_issues       = [enrich_issue(i) for i in all_raw]
    migration_issues = [i for i in all_issues if is_migration_issue(i)]
    open_migration   = [i for i in migration_issues if i["state"] == "open"]

    print(f"   Total: {len(all_issues)} | Migration: {len(migration_issues)} | Open migration: {len(open_migration)}")

    if len(migration_issues) == 0:
        msg = (
            "ℹ️ **No migration-related issues detected** in this repository.\n\n"
            "The scanner looks for keywords: `migrat`, `cloud`, `legacy`, `k8s`, `aws`, `gcp`, "
            "`azure`, `terraform`, `docker`, `refactor`, `containeris`, and more.\n\n"
            "Add these keywords to issue titles or labels to enable migration tracking."
        )
        if ISSUE_NUMBER:
            post_comment(ISSUE_NUMBER, comment_header("☁️", "Migration Status") + msg + comment_footer())
        else:
            print(msg)
        return

    print("🤖 Calling Claude for migration analysis…")
    system = (
        "You are a cloud migration programme manager. "
        "Produce clear, data-driven migration dashboards for engineering leadership. "
        "Be honest about risks and blockers. Use specific issue numbers. "
        "Keep the executive summary punchy — leaders read the first 3 lines."
    )
    ai_body = call_claude(
        system,
        build_prompt(all_issues, migration_issues),
        max_tokens=2500
    )

    # ── Build stats row ────────────────────────────────────────────────────────
    pct = round((len([i for i in migration_issues if i["state"]=="closed"]) / max(len(migration_issues),1)) * 100)
    stats = (
        f"| | |\n|---|---|\n"
        f"| Migration issues | **{len(migration_issues)}** |\n"
        f"| Open migration | **{len(open_migration)}** |\n"
        f"| Completed | **{len(migration_issues)-len(open_migration)}** |\n"
        f"| Est. % complete | **{pct}%** |\n"
        f"| BAU issues | **{len(all_issues)-len(migration_issues)}** |\n"
    )

    full_body = (
        comment_header(
            "☁️", "Migration Status Dashboard",
            f"`{REPO}` · {len(migration_issues)} migration items detected"
        )
        + stats + "\n---\n\n"
        + ai_body
        + comment_footer()
    )

    if POST_AS_ISSUE:
        title = f"☁️ Migration Status Report — {datetime.now().strftime('%d %b %Y')}"
        create_issue(title, full_body, labels=["ai-report", "migration"])
    elif ISSUE_NUMBER:
        post_comment(ISSUE_NUMBER, full_body)
    else:
        print(full_body)

    print("✅ Done.")


if __name__ == "__main__":
    run()
