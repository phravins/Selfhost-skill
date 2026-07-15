# House Document Format — Self-Host Installation Guides

This defines the standard shape every guide this skill produces should follow, regardless of which app or reverse proxy is involved. Consistency here is what makes the output feel like a single trustworthy product rather than an improvised one-off.

## Title page

A plain metadata table, not a decorative cover — this is a working technical document, not a brochure. Fields, in this order:

| Field | Example |
|---|---|
| Server | `draw.example.com (YOUR_SERVER_IP)` |
| Operating System | `Debian 13 (Trixie)` |
| Provider | `Any VPS / Cloud Droplet` |
| `<App>` Source | link to the upstream repo, plus a one-line note on its release maturity if relevant (e.g. "actively developed alpha") |
| Reverse Proxy | which one, plus "(automatic HTTPS)" or "(Certbot)" etc. |
| SSL Certificate | how it's obtained/renewed |
| Date | month + year |
| Prepared by | attribution line |

Follow the metadata table with one NOTE box if the guide's reverse proxy choice differs from the app's official/documented one — state the substitution plainly and why it's reasonable, the way past guides in this workspace have done ("the official stack uses Traefik; this guide substitutes Caddy because...").

## Section order

1. **Overview** — one paragraph on what the app is and what this document covers, plus:
   - **1.1 Architecture** — a table of every component (frontend, API, database, object storage, proxy, etc.) with its internal port and one-line role.
   - **1.2 Domain Structure** — one domain or several, and why; a table of subdomain(s) and purpose if more than one is needed.
   - **1.3 Prerequisites** — bullet list: VPS/OS, SSH access, domain + DNS access, ports open, anything app-specific (e.g. an OIDC provider if SSO is planned).
2. **DNS Configuration** — the exact A record(s) needed, plus a NOTE about propagation delay and how to verify with `ping` or `dig`.
3. **System Preparation** — update packages, install prerequisite utilities, configure the firewall (ufw allow rules for SSH/80/443 only).
4. **Install Docker** — official convenience-script or apt-repository method; always verify Compose plugin version afterward; call out any Debian/Ubuntu-codename gotchas currently relevant (check whether Docker's repo natively supports the target release before reaching for an older workaround).
5. **Clone the app / prepare secrets** — clone the repo, generate secrets with `openssl rand`, create persistent host-side storage directories with a table explaining what each one holds.
6. **Configure the environment file** — copy the template, then a table of which variables to set and why; flag anything that can only be set correctly before first start (e.g. an initial admin password) with an IMPORTANT box.
7. **docker-compose.yml** — the full file, every service, with the reverse proxy already wired in. This is usually the longest code block in the document.
8. **Reverse proxy configuration** — the actual Nginx/Caddy/Traefik config, sourced from the matching `references/<proxy>.md` file. Always include the one ordering/priority rule that proxy needs (see each reference file) as its own IMPORTANT box, not buried in prose.
9. **Starting the app** — pull images, start, expected success output, verify running/healthy status.
10. **First login** — what URL to open, how to create the first admin account, and the very next thing to do afterward if a setup-only flag (like open registration) needs to be turned back off.
11. **Ongoing maintenance** — a table of useful day-2 commands, an update procedure, and how certificate renewal is handled for the chosen proxy.
12. **Troubleshooting** — a table: Symptom / Likely cause / Resolution. Merge in the proxy-specific rows from the reference file plus any app-specific ones from research.
13. **Installation Summary** — a checklist table (✔ / component / one-line note) confirming everything that's now running, ending with a short "sources" line pointing back to the upstream docs and a note if the software is pre-1.0/alpha/actively changing.

Don't skip sections just because they seem obvious for a given app — a non-technical reader benefits from the repetition of structure across different guides more than from a shorter document.

## Callout boxes

Two kinds only, used consistently:
- **NOTE** — helpful context, not required for success (e.g. why a design choice was made, what a term means).
- **IMPORTANT** — something that will break the deployment or lose data if skipped or done out of order (ordering rules, must-set-before-first-start variables, don't-commit-secrets warnings).

Don't invent additional callout types (tip/caution/danger/etc.) — two is enough and keeps the document scannable.

## Code blocks

Every command the reader needs to run goes in its own copy-pasteable block, in the exact order they run them. Where a command's output matters (e.g. confirming `docker compose version` shows v2.x, or the expected `docker compose up -d` success listing), show the expected output in its own block immediately after, so the reader has something concrete to compare against before moving to the next step.

Long files (docker-compose.yml, proxy config) get their own labelled code block with a small caption above it giving the file's path, e.g. `/opt/app/deploy/docker-compose.yml`.

## Tone

Write for a first-time self-hoster. The first time a piece of jargon appears (DNS propagation, WebSocket, reverse proxy, ACME, healthcheck), give it a short plain-language aside in the same sentence rather than assuming it or footnoting it elsewhere. Keep sentences short. Never assume the reader knows what "the stack" or "the upstream" means without having introduced it.

## What NOT to do

- Don't guess a port, image name, or environment variable to fill a gap — go back to Step 1 of SKILL.md and verify it.
- Don't silently drop the "official proxy differs" disclosure just because it's a minor detail — it belongs in the title-page NOTE box every time it's true.
- Don't invent a fabricated troubleshooting "incident" (a specific error message you didn't actually encounter) to pad out Section 12 — real, plausible, general failure modes only.
