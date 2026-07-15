---
name: self-host-guide
description: Generate a complete, formal, step-by-step self-hosting installation guide for any application, with a reverse proxy (Nginx, Caddy, or Traefik) chosen to fit the user's requirement. Use this whenever the user asks for a self-hosting guide, installation guide, deployment guide, Docker Compose setup, or "how to self host X" for any open-source or self-hostable application — whether or not they name a specific reverse proxy. Also use when the user asks to switch or compare reverse proxies for an existing self-host guide, wants a PDF/document version of a deployment walkthrough, or references "the OpenCloud-style guide", "the AstraDraw-style guide", or a similarly formatted installation document. Trigger even if the user only names the app and says something like "give me a self-host guide for Immich" or "how do I deploy Paperless-ngx with HTTPS" — reverse proxy choice can be asked or defaulted.
---

# Self-Host Installation Guide Generator

Produces a formal, non-technical-user-friendly, step-by-step self-hosting installation guide for any application, matching an established house style (title metadata table, numbered sections, copy-paste command blocks, NOTE/IMPORTANT callouts, troubleshooting table, installation summary checklist). The reverse proxy layer — Nginx, Caddy, or Traefik — is swappable per user requirement without changing anything else in the guide.

## Why this skill exists

Self-hosting guides fail non-technical readers in two common ways: (1) the reverse-proxy config is wrong or incomplete for the specific app's routing needs (subdomain-per-service vs single-domain-path-routing, WebSocket upgrade headers, SSL cert paths), and (2) the app's own config (ports, environment variables, Docker images, required backing services) is guessed instead of verified against the upstream project. This skill fixes both by separating "which reverse proxy" (references/) from "which app" (always researched fresh) and by using a single proven document structure for every output.

## Workflow

Follow these steps in order. Don't skip the research step even if the app seems familiar — self-hosted project configs (image names, ports, env var names, official architecture) change over time and training data goes stale quickly.

### Step 1 — Identify the application and research its real deployment requirements

Never fabricate ports, environment variable names, Docker image names, or architecture. If you don't already have verified, current information in this conversation:

- Web search the application's official GitHub repository, README, and any `docs/deployment` folder.
- Confirm: official Docker image name(s) and tags, internal ports each service listens on, required environment variables (and which are mandatory vs optional), required backing services (database, object storage, cache), and — critically — the **official reverse proxy routing rules**: does the app split traffic by path (e.g. `/api/*` to one container, everything else to another) or does it need separate subdomains per component (e.g. a WOPI/office-editing sidecar, a separate collaboration/websocket service)?
- Note what reverse proxy the project officially ships (Traefik, Nginx, Caddy, none) — this doesn't dictate what you build, but any deviation from it should be called out transparently in the finished guide, the same way past guides in this workspace have flagged "official proxy is Traefik, this guide substitutes Caddy."
- If the app is genuinely unfamiliar or details can't be confirmed, say so plainly rather than guessing plausible-sounding values — a wrong port or env var name in a document like this wastes a non-technical user's time at the worst possible step.

### Step 2 — Determine the reverse proxy

If the user named one (Nginx, Caddy, or Traefik), use it. If they didn't, pick the best default for the situation and say why, or ask if it's genuinely ambiguous:

| Proxy | Best fit | Trade-off to mention |
|---|---|---|
| **Caddy** | First-time self-hosters, single app, want HTTPS to "just work" | Fewer people already know it; less common in existing tutorials |
| **Nginx** | User already runs Nginx for other sites, wants full manual control, most existing tutorials use it | Needs a separate Certbot step and manual renewal verification |
| **Traefik** | Multiple self-hosted apps on one host, want new services to get routing + HTTPS automatically via Docker labels | Label-based config is a different mental model; steeper first-time learning curve |

Read the matching reference file now — `references/caddy.md`, `references/nginx.md`, or `references/traefik.md` — for that proxy's installation commands, config template, certificate handling, and proxy-specific troubleshooting entries. Read more than one if the user wants a comparison or wants to migrate between them.

### Step 3 — Read the house document format

Read `references/document-format.md`. It defines the exact section order, title-page metadata table, callout box conventions, and tone this skill always produces, so every guide this skill generates feels like the same product regardless of which app or proxy is involved.

### Step 4 — Decide single-domain vs multi-domain routing

Based on Step 1's research:
- If the app's official architecture routes everything through URL paths on one domain (common for modern SPA + API + WebSocket stacks) → one DNS record, one certificate. This is simpler and should be preferred when the app supports it.
- If the app genuinely requires separate services on separate subdomains (e.g. a document-editing sidecar that must be reachable on its own origin) → use multiple DNS records/subdomains, exactly as the OpenCloud + Collabora reference guide does, and make the redirect/routing behavior explicit in a table.

Don't default to multi-subdomain out of habit — check whether the app actually needs it first.

### Step 5 — Generate the guide

Build the document following `references/document-format.md`'s structure, using the proxy-specific material from Step 2 and the app-specific facts from Step 1. Use `scripts/build_guide_pdf.py` to render it as a PDF (see that script's docstring for its small helper API — it already implements the header/footer, title-metadata table, callout boxes, and safe code-block chunking that long docker-compose.yml / config-file listings need to avoid page-overflow errors). Markdown or docx output is also acceptable if the user asks for those instead — apply the same section structure and tone either way.

Before finalizing, re-read the generated content once against Step 1's research and check every port, image name, and environment variable is exactly what the upstream project documents — not a plausible-looking placeholder.

### Step 6 — Deliver

Save the file to the outputs directory and present it. Mention, once, if anything upstream is unverified, alpha/actively-changing software, or if the official proxy differs from the one used — the same transparency pattern used in this workspace's existing AstraDraw guides.

## Switching or comparing reverse proxies later

If the user asks to convert an existing guide to a different proxy ("now give me the Traefik version" / "what would this look like with Nginx instead"):
- Keep every app-specific fact (images, ports, env vars, volumes, domain structure) identical.
- Only the reverse-proxy install section, its config file, the SSL/certificate section, and the proxy-specific troubleshooting rows change.
- Read the newly-requested proxy's reference file and swap those sections in; don't regenerate the whole document from scratch unless asked to.

## Notes on tone

Write for someone who has never used a terminal before, without being condescending: every command should be copy-pasteable exactly as shown, every step should say what "success" looks like before moving on, and jargon (DNS propagation, WebSocket upgrade, reverse proxy itself) gets a short plain-language aside the first time it appears. This mirrors the standard already set by the OpenCloud and AstraDraw guides in this workspace.
