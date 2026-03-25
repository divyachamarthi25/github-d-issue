"""
ai_router_slash.py
──────────────────
Routes /ai slash commands to the correct script.
Called from the GitHub Actions workflow instead of inline Python heredoc.
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(__file__))
from utils import REPO, ISSUE_NUMBER, GITHUB_TOKEN, gh_post, comment_header, comment_footer

SCRIPTS = os.path.dirname(__file__)


def post_help():
    body = comment_header("🤖", "GitHub AI PM — Available Commands") + """
| Command | What it does |
|---|---|
| `/ai summary` | AI summary of this issue — status, blockers, next actions, ETA |
| `/ai template` | Blank structured update template for this issue |
| `/ai template [your notes]` | Auto-structure free-form notes into a template |
| `/ai triage` | Bulk triage of all open issues in this repo |
| `/ai migration` | Migration programme status dashboard |
| `/ai report` | Executive programme health report |
| `/ai help` | Show this help message |
""" + comment_footer()

    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    gh_post(url, {"body": body})
    print("✅ Help message posted.")


def run():
    cmd = os.environ.get("COMMENT_BODY", "").strip().lower()
    print(f"📨 Slash command received: {cmd!r}")

    if cmd.startswith("/ai summary"):
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_summary.py"], check=True)

    elif cmd.startswith("/ai template"):
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_template.py"], check=True)

    elif cmd.startswith("/ai triage"):
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_triage.py"], check=True)

    elif cmd.startswith("/ai migration"):
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_migration.py"], check=True)

    elif cmd.startswith("/ai report"):
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_executive.py"], check=True)

    elif cmd.startswith("/ai help"):
        post_help()

    else:
        print(f"Unknown command: {cmd!r}")
        print("Try /ai help for available commands.")
        post_help()


if __name__ == "__main__":
    run()
