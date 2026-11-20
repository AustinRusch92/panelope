# Panelope

A personal AI assistant and accountability coach with Gmail, Calendar,
and web search access, built with a security-first design.

## Threat Model

### What I'm protecting
- Gmail inbox (job search correspondence, account notifications)
- Calendar
- API keys and OAuth credentials
- Personal task and memory data

### Who/what is the attacker
- **Untrusted email content**: anyone can send me an email with a
  crafted subject line or sender name (prompt injection).
- **Untrusted web content**: search results are external data that
  may contain malicious instructions.
- **Credential leakage**: secrets accidentally committed or exposed.

### Two risk categories
1. **Leak**: can an attacker get data out of the system?
2. **Hijack**: can an attacker make the assistant take actions?

## Design Decisions

| Threat | Mitigation |
|---|---|
| Over-privileged access | **Least-privilege scopes.** Started with gmail.readonly, added gmail.modify only when needed for archiving. Calendar access is limited to calendar.events and writes only to a separate "Panelope" calendar, not the main one. |
| Prompt injection via email | **Headers-only email access.** Panelope reads sender, subject, and date, never message bodies. This shrinks attacker-controlled text to a few short fields. |
| Destructive actions from hijacked instructions | **Human-approved, archive-only actions.** The cleanup script can only remove the INBOX label (no delete, no send). It works from a dry-run list I approve, uses a promos-only query that excludes job-related senders, and is capped at 50 messages per run. Archiving is not exposed as an assistant tool, and the promo-listing tool strips message IDs so the model never sees them. |
| Injection via search results or email | **Taint block (enforced in code) plus prompt rules.** Once web search or an email tool returns untrusted content, state-changing tools (save_memory, add_task, complete_task, create_event) are blocked for the rest of that turn. The system prompt also tells the model to treat this content as data. Tested: an email search followed by add_task in the same turn is blocked. |
| Unwanted calendar writes | **Confirmation gate.** Every created event needs terminal confirmation (y/n). |
| Credential leakage | **Secrets hygiene.** Credentials, tokens, and API keys live in gitignored files. No keys are hardcoded in any script. |

**Tradeoff:** after the assistant reads email or web content, I have to
confirm any follow-up action in a new message. That friction is deliberate.

## Known Gaps

- **Memory writes are ungated.** save_memory has no confirmation prompt.
  A successful injection could persist a false "fact". Planned: y/n gate
  showing the exact note, default no, with rejected notes logged.
- **Email query scope is prompt-level.** search_job_emails accepts a
  free-form Gmail query, so "job-related only" is enforced by the tool
  description and system prompt, not by code.
- **Web search is an outbound channel.** Query text leaves the machine
  and isn't gated or logged.
- **Token scope exceeds exposed tools.** gmail.modify is requested at
  auth time, but no registered tool uses it (archiving runs only from a
  separate script with a dry-run approval).
- **Test-mode OAuth.** Tokens expire after ~7 days and need re-auth.

## Lessons Learned

- **Verify your .gitignore actually works.** My first .gitignore was
  saved as UTF-16 (a PowerShell redirect side effect), which git
  silently ignores. `git status` showed credentials.json, token.json,
  and .env as untracked until I rewrote the file as UTF-8. Always run
  `git status` before the first commit.
- **Test controls empirically.** After extending the taint block to
  email tools, I tested it end to end: an email search followed by
  add_task in the same turn is blocked, and the task isn't created.
- **Audit the code, not just the design.** Reviewing agent.py showed
  the taint block only covered web search and not email. Fixed before
  publishing.
- **Least-privilege is a process.** Scopes started read-only and
  expanded only when a feature needed them.

## Setup

**Requirements:** Python 3.x (developed on Windows), a Google Cloud
project with the Gmail and Calendar APIs enabled, an Anthropic API
key, and a Tavily API key.

1. Clone the repo and create a virtual environment:
   python -m venv venv
   venv\Scripts\activate
2. Install dependencies:
   pip install -r requirements.txt
3. Create an OAuth client in Google Cloud and save it as
   credentials.json in the project root (gitignored).
4. Create a .env file (gitignored) with:
   - ANTHROPIC_API_KEY
   - TAVILY_API_KEY
   - PANELOPE_CAL_ID (ID of a separate "Panelope" calendar)
5. Run: python agent.py
   The first run opens a browser for Google consent.

**Note:** OAuth apps in test mode expire tokens after ~7 days.
If you see invalid_grant, delete token.json and re-run to re-auth.