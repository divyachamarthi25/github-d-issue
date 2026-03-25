"""
ai_template.py
──────────────
Generates a structured update template for an issue.
If the comment body contains text after "/ai template",
Claude will structure that free-form text into the template.
Otherwise, posts a blank template to fill in.

Called by:
  - Job 2: /ai template [optional free-form text]
  - Job 3: needs-template or needs-update label
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    REPO, ISSUE_NUMBER, call_claude,
    fetch_issue, enrich_issue,
    post_comment, comment_header, comment_footer
)
from datetime import datetime


BLANK_TEMPLATE = """**📅 Status Update** — {date}

**🔄 Current Status:**
- [ ] 🟢 On Track
- [ ] 🟡 At Risk
- [ ] 🔴 Blocked
- [ ] ✅ Complete

**✅ Progress Since Last Update:**
-  

**🚧 Blockers:**
- [ ] None currently
-  

**⏭️ Next Steps:**
- [ ] 

**📅 ETA:** 

**👤 Owner:** @

**🏷️ Label Updates Needed:**
- [ ] No changes
-  
"""


def build_prompt(issue, free_form_text):
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""Transform this free-form engineer update into a structured status update.

Issue #{issue['number']}: {issue['title']}
Current state: {issue['state']}
Assignees: {', '.join(issue['assignees']) or 'Unassigned'}
Days open: {issue['days_open']}

Engineer wrote:
"{free_form_text}"

Rewrite as a structured update. ONLY use information from the engineer's text.
Do NOT invent details. If something is not mentioned, leave the field blank or say "Not specified".

**📅 Status Update** — {today}

**🔄 Current Status:** [derive from text: On Track / At Risk / Blocked / Complete]

**✅ Progress Since Last Update:**
- [extract from text]

**🚧 Blockers:**
- [extract, or write "None mentioned"]

**⏭️ Next Steps:**
- [extract or infer from text]

**📅 ETA:** [extract, or write "Not specified"]

**👤 Owner:** [extract if mentioned, or write "@[not specified]"]

**🏷️ Suggested Label Updates:**
- [suggest based on content, e.g. "Add: blocked" if blocker mentioned]"""


def run():
    issue_number = ISSUE_NUMBER
    if not issue_number:
        print("❌ ISSUE_NUMBER not set")
        sys.exit(1)

    print(f"📖 Fetching issue #{issue_number}…")
    raw   = fetch_issue(issue_number)
    issue = enrich_issue(raw)

    # Check if there's free-form text after "/ai template"
    comment_body = os.environ.get("COMMENT_BODY", "").strip()
    free_form    = comment_body.replace("/ai template", "").strip()

    if free_form:
        print(f"🤖 Structuring free-form update: '{free_form[:60]}…'")
        system = (
            "You are an engineering project manager who enforces structured GitHub issue updates. "
            "Transform free-form text into clean, structured updates. "
            "Only use information provided — never invent details."
        )
        template_body = call_claude(system, build_prompt(issue, free_form), max_tokens=800)
        subtitle = "Free-form update structured by AI"
    else:
        print("📝 Generating blank template…")
        template_body = BLANK_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
        subtitle = "Fill in the sections below and copy into a new comment"

    comment_body = (
        comment_header("📝", f"Update Template — #{issue_number}", subtitle)
        + template_body
        + "\n\n---\n"
        + "> 💡 **Tip:** Use `/ai template [your update here]` to auto-structure "
        "your free-form notes into this format.\n"
        + "> 📋 **Example:** `/ai template fixed the DB connection issue, ETA Friday, "
        "waiting on @alice to review`"
        + comment_footer()
    )

    post_comment(issue_number, comment_body)
    print("✅ Done.")


if __name__ == "__main__":
    run()
