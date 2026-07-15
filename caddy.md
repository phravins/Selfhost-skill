# Caddy Reverse Proxy — Reference

## When to choose Caddy

Best default for a single self-hosted app and a user who wants HTTPS to work with the least amount of manual certificate management. Caddy requests and renews its own Let's Encrypt certificate automatically the first time it starts — there is no Certbot, no cron job, no separate renewal step to explain or verify.

Caddy also upgrades WebSocket connections transparently with zero extra configuration, which matters for any app with real-time collaboration, chat, or live updates.

## Installation approach

Run Caddy as a Docker container alongside the app's own containers, on the same Docker network. Do not install Caddy as a host package unless the user specifically wants it managing multiple unrelated projects outside Docker — inside a docker-compose.yml is simpler to reason about and matches how the rest of a self-hosted app stack is usually deployed.

```yaml
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - app_net
```

`caddy_data` must be a persistent volume (or host bind mount) — it holds the issued certificate and Caddy's ACME account state. Losing it means re-issuing a new certificate on next start, which is safe but avoidable.

## Config template — single domain, path-based routing

Use this when the app splits frontend/API/websocket by URL path on one domain (the common modern pattern):

```
draw.example.com {
    encode zstd gzip

    @api    path /api/*
    @socket path /socket.io/*

    reverse_proxy @api    api:8080
    reverse_proxy @socket room:80

    reverse_proxy frontend:80

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        -Server
    }
}
```

**Ordering rule (always call this out explicitly in the generated guide):** the unmatched, catch-all `reverse_proxy` line must be the LAST reverse_proxy directive in the block. Caddy evaluates directives top-down; a catch-all placed first will swallow every request, including the ones meant for the API or WebSocket matchers.

## Config template — multiple subdomains

Use this only when the app genuinely needs separate origins (e.g. a document-editing sidecar):

```
cloud.example.com {
    reverse_proxy app:9200
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}

office.example.com {
    reverse_proxy office:9980
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}
```

Each block gets its own automatic certificate — no extra config needed for multiple domains in one Caddyfile.

## SSL / certificates

Nothing to configure. Caddy obtains a certificate via HTTP-01 (or TLS-ALPN-01) the moment it can reach the domain on port 80/443 and DNS resolves. State the two preconditions plainly in the guide:
1. DNS A record already points at the server.
2. Ports 80 and 443 are reachable from the public internet (not just open in the host firewall — also check any cloud provider security group).

## Maintenance commands specific to Caddy

```
docker compose logs caddy              # check for ACME/certificate errors
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
docker compose restart caddy
```

## Troubleshooting rows to include

| Symptom | Likely cause | Resolution |
|---|---|---|
| Caddy never obtains a certificate | DNS not propagated yet, or port 80/443 blocked by a cloud firewall in front of the host firewall | Confirm `ping <domain>` resolves; check the cloud provider's security group, not just `ufw` |
| Site loads but API/websocket calls 404 or hang | Catch-all `reverse_proxy` line is not last | Reorder the Caddyfile so path-matched blocks come before the unmatched catch-all |
| Certificate re-issues on every restart | `caddy_data` volume isn't persistent | Mount it as a named volume or host bind mount, not an anonymous volume |
