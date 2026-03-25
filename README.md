# GitHub AI Project Manager — GitHub Action

AI-powered project management that lives **entirely inside GitHub**.
No external tools. No dashboards to switch between.
Engineers stay in GitHub — the AI comes to them.

---

## ✨ What It Does

| Trigger | Action | Where result appears |
|---|---|---|
| Issue opened | Auto AI summary posted | Comment on the issue |
| `/ai summary` | AI summary on demand | Comment on the issue |
| `/ai template` | Blank structured update template | Comment on the issue |
| `/ai template [text]` | Auto-structure free-form update | Comment on the issue |
| `/ai triage` | Bulk triage of all open issues | Comment on the issue |
| `/ai migration` | Migration status dashboard | Comment on the issue |
| `/ai report` | Executive programme health report | Comment on the issue |
| `/ai help` | Command reference | Comment on the issue |
| Label: `needs-summary` | AI summary | Comment on the issue |
| Label: `migration` | Migration analysis | Comment on the issue |
| Every Monday 08:00 UTC | Weekly triage + executive report | New issue created |
| Every day 08:00 UTC | Stale issue alert | New issue created |
| `workflow_dispatch` | Any action, on demand | New issue or comment |

---

## 🚀 Setup — 3 Steps

### Step 1 — Copy the files into your repo

```
your-repo/
└── .github/
    ├── workflows/
    │   └── ai-pm.yml           ← The workflow
    └── scripts/
        ├── utils.py            ← Shared helpers
        ├── ai_summary.py       ← Issue summarisation
        ├── ai_triage.py        ← Bulk triage
        ├── ai_migration.py     ← Migration dashboard
        ├── ai_executive.py     ← Executive report
        ├── ai_template.py      ← Structured templates
        ├── ai_stale.py         ← Daily stale check
        └── requirements.txt
```

### Step 2 — Add your API key as a secret

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your key from [console.anthropic.com](https://console.anthropic.com)

> **Note:** `GITHUB_TOKEN` is provided automatically by GitHub Actions — you do not need to add it.

### Step 3 — Push and test

```bash
git add .github/
git commit -m "feat: add GitHub AI PM workflow"
git push
```

Then go to **Actions** → **AI Project Manager** → **Run workflow** → select `triage` → **Run**.

That's it. The AI is live.

---

## 💬 Slash Commands

Type any of these as a comment on any GitHub issue:

```
/ai summary          → Structured summary of this issue
/ai template         → Blank update template to fill in
/ai template [text]  → Auto-structure your free-form notes
/ai triage           → Triage all open issues in this repo
/ai migration        → Migration programme status
/ai report           → Executive weekly health report
/ai help             → Show all commands
```

**Example — auto-structuring a free-form update:**
```
/ai template fixed the auth token issue, waiting on @alice to review the DB schema,
should be done by Thursday unless we hit the rate limit problem again
```
Claude will convert this into a proper structured update comment.

---

## 🏷️ Label Triggers

Apply these labels to automatically trigger AI actions:

| Label | Action triggered |
|---|---|
| `needs-summary` | AI summary posted as comment |
| `ai-summarise` | AI summary posted as comment |
| `needs-template` | Blank update template posted |
| `migration` | Migration analysis triggered |
| `cloud-migration` | Migration analysis triggered |

---

## ⏱️ Scheduled Jobs

| Schedule | Job | Result |
|---|---|---|
| Every Monday 08:00 UTC | Triage + Executive Report | New issues created with `ai-report` label |
| Every day 08:00 UTC | Stale issue check | New issue if stale/unassigned issues exist |

To change the schedule, edit the `cron` lines in `ai-pm.yml`:
```yaml
schedule:
  - cron: "0 8 * * 1"   # Monday morning — change to your timezone offset
  - cron: "0 8 * * *"   # Daily morning
```

---

## 🔧 Configuration

All configuration is done via environment variables in the workflow file:

| Variable | Where to set | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Repository secret | Your Claude API key (required) |
| `STALE_DAYS` | Workflow env | Days before issue flagged stale (default: 3) |
| `POST_AS_ISSUE` | Workflow env | `true` = create new issue, `false` = comment |

To change the stale threshold, edit `ai-pm.yml`:
```yaml
STALE_DAYS: "5"   # Flag as stale after 5 days instead of 3
```

---

## 🏗️ Architecture

```
GitHub event (issue / comment / label / schedule)
        │
        ▼
GitHub Actions runner (ubuntu-latest)
        │
        ├── .github/scripts/utils.py       ← GitHub API + Claude API
        ├── .github/scripts/ai_summary.py  ← Called for new issues + /ai summary
        ├── .github/scripts/ai_triage.py   ← Called for /ai triage + weekly
        ├── .github/scripts/ai_migration.py← Called for /ai migration + label
        ├── .github/scripts/ai_executive.py← Called for /ai report + weekly
        ├── .github/scripts/ai_template.py ← Called for /ai template + label
        └── .github/scripts/ai_stale.py    ← Called daily
        │
        ▼
Anthropic Claude API (claude-sonnet-4-6)
        │
        ▼
GitHub Issues API → comment or new issue posted
```

**No external server. No database. No deployment.**
Everything runs inside GitHub's infrastructure.

---

## 💰 Cost Estimate

| Usage | Est. Claude cost/month |
|---|---|
| 50 new issues summarised | ~$0.50 |
| 4 weekly triage reports | ~$0.40 |
| 20 daily stale checks | ~$0.20 |
| 30 slash commands | ~$0.30 |
| **Total** | **~$1.40/month** |

GitHub Actions minutes (public repos: free, private: 2,000 min/month free):
- Each job run: ~30–60 seconds → ~1 minute
- 100 runs/month → ~100 minutes

---

## 🔒 Security Notes

- `ANTHROPIC_API_KEY` is stored as a GitHub secret — never visible in logs
- `GITHUB_TOKEN` is auto-generated per run with minimum required permissions
- The workflow requests only `issues: write` and `contents: read`
- No data is stored anywhere — each run is stateless
- The action only reads/writes issues in the repo it's installed on

---

## 🐛 Troubleshooting

**Workflow not triggering?**
- Check `Actions` tab is enabled for your repo (Settings → Actions → Allow all actions)
- Ensure the YAML file is valid: paste into [yaml.org/spec](https://yaml-online-parser.appspot.com/)

**"ANTHROPIC_API_KEY secret is not set" message?**
- Go to Settings → Secrets → Actions → add `ANTHROPIC_API_KEY`

**Slash command not working?**
- The comment must start with `/ai` (no leading spaces)
- The workflow must have `issues: write` permission (already set in the yml)

**Rate limit errors from GitHub?**
- Add a `GITHUB_TOKEN` from a machine account to increase limits
- The built-in `GITHUB_TOKEN` allows 5,000 requests/hour per repo

**Want to disable auto-summarising new issues?**
Remove or comment out the `summarise-new-issue` job in `ai-pm.yml`.

---

## 📄 Licence

MIT — free to use, modify, and deploy in your organisation.
