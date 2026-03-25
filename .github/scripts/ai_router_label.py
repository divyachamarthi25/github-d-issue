"""
ai_router_label.py
──────────────────
Routes label-applied events to the correct AI script.
Called from the GitHub Actions workflow instead of inline Python heredoc.
"""

import os
import sys
import subprocess

SCRIPTS = os.path.dirname(__file__)


def run():
    label = os.environ.get("LABEL_APPLIED", "").strip().lower()
    print(f"🏷️  Label applied: {label!r}")

    if label in ("needs-summary", "ai-summarise", "ai-summarize"):
        print("→ Running AI summary...")
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_summary.py"], check=True)

    elif label in ("needs-template", "needs-update"):
        print("→ Running AI template...")
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_template.py"], check=True)

    elif label in ("migration", "cloud-migration", "legacy"):
        print("→ Running migration analysis...")
        subprocess.run([sys.executable, f"{SCRIPTS}/ai_migration.py"], check=True)

    else:
        print(f"Label '{label}' has no AI action configured — skipping.")


if __name__ == "__main__":
    run()
