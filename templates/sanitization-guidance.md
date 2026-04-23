# Sanitization guidance for transferable skills

> Reference for the `sanitize-transferable` skill (and human reviewers). Not a regex enforcement list — sanitization in this framework is judgment-based, applied by an LLM that can read context. Use this doc as a rubric, not a checklist to grep against.

## What "sanitized" means

A transferable skill ships in the open-source master repo and gets cloned by anyone who installs the framework. Once a leak lands here, it can't be retracted from clones. **Sanitized = no detail in the prose that ties the skill to one specific project, company, person, or deployment.**

The proprietary counterpart is allowed to know everything; the transferable should know only the *method*.

## Categories of leak

### 1. Identity and ownership

- Project names (the codename, internal name, or repo name of any specific project)
- Company names, brand names, product names
- Personal names, email addresses, handles
- Domain names tied to a specific deployment (anything under a `.com` / `.ai` / etc. that names a real service or person)
- IP addresses, port numbers used by a specific deployment

These are the most obvious leaks. They almost never have a legitimate reason to appear in a transferable skill.

### 2. Stack and OS specifics

- Specific init-system names ("use rc.d" / "use systemd" / "use launchd") — generalize to "the project's service manager."
- Specific reverse-proxy paths (`/usr/local/etc/nginx/conf.d/myproject.conf`) — generalize to "the reverse-proxy config the project uses."
- Specific Linux / BSD distro names — only mention if the skill genuinely behaves differently on different OSes; otherwise drop.
- VPS provider names — generalize to "the production host."
- Specific service names baked into command examples (`sudo service <projectname> stop`) — use placeholders.

Exception: when the skill is *teaching what to avoid*, naming these in inline backticks is fine. "Don't hand-roll a `systemctl` call; use the project's service manager wrapper" is acceptable.

### 3. Secrets and credentials

- Real API keys, tokens, passwords, payment hashes (obviously).
- Specific env-var names of secrets (`<VENDOR>_KEY`, `STRIPE_SECRET`, `<FEATURE>_ROOT_KEY`) — generalize to `<service>_API_KEY` or "the project's payment-API key env var."
- Test-account credentials (anything of the form `<internal-test-handle>@example.com / <password>`) — even when the domain is a placeholder, the handle and password convention leak the project's test-account setup.
- SSH key paths, hostnames, port-forwarded ports.

### 4. Filesystem and infrastructure

- Absolute paths under `/home/<user>/`, `/opt/<project>/`, `/var/log/<project>/`.
- Project-specific module names (`leads_orchestrator.py`, `agent_job_runner.py`).
- Database names (`createdb <projectname>`).
- Specific service / daemon names (`gunicorn.pid`, `<projectname>_worker`).
- SSH config aliases (`ssh <host-alias>`).

Generalize to "the project's primary database," "the worker daemon," "your project root."

### 5. Architectural assumptions baked in as universal

If your skill says "the deploy step is `ssh <host-alias> && git pull`," it has assumed every project SSHes into one host and uses git-pull for deploys. Plenty don't. Generalize: "the project's deploy command (look it up in the project's CLAUDE.md or deploy/ dir)."

### 6. Hardcoded values that pretend to be limits

`max_length: 254` in a transferable that's *about* email addresses is OK (it's the RFC limit). `timeout: 30` because that's what your project happens to use is not — the next user has different latencies. Generalize or omit.

## Acceptable references in transferable skills

These are NOT leaks; the framework is built around them:

- The harness vendor (`Claude Code`, `anthropic.com`) — the framework explicitly supports the Claude Code harness as its only MVP implementation.
- The framework's own paths (`~/Dev/skill-set/skills/`, `~/.claude/state/`).
- Industry-standard tools, languages, formats (`pytest`, `git`, `JSON`, `Markdown`).
- RFC-defined values (port 80, port 443, TLS, RFC 5321 email length).
- Standard placeholder TLDs (RFC 2606: `example.com`, `example.org`, `example.net`).

## How the sanitize-transferable skill uses this doc

1. Reads this guidance plus the proposed/current transferable SKILL.md body.
2. Reads any per-project banned-terms list maintained by the proprietary supervisor (e.g. the "Banned terms" section of `<project>/.claude/skills/<persona>-supervisor/SKILL.md`).
3. Walks the SKILL.md prose section by section, applying judgment per category above.
4. Flags every candidate leak with its category, severity, and a suggested abstraction.
5. Optionally writes a sanitized rewrite to a sibling file (`<skill>.sanitized.md`) for human review and (separate) promotion via `/promote-skill-proposal`.

The skill never writes silently; it always produces a diff for the user to review.

## Severity tiering (advisory, no automatic gating)

- **must-fix** — names a specific project/person/secret that has zero legitimate reason to be in a transferable. Will leak unambiguously.
- **should-fix** — references a stack/OS specific that's borderline. The author probably had a generalization in mind that didn't get written down.
- **nit** — a wording choice that *implies* a specific stack but doesn't name it. Refactor if convenient; ignore if not.

The sanitize skill reports all three; the human reviewer decides what blocks promotion.
