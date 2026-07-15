# Traefik Reverse Proxy — Reference

## When to choose Traefik

Best when the user runs (or plans to run) several self-hosted apps on the same Docker host and wants new services to get routing and HTTPS automatically the moment they're added to docker-compose.yml, without touching a shared proxy config file. Many upstream self-hosted projects (including AstraDraw) ship Traefik as their default/official proxy for exactly this reason.

The trade-off: Traefik is configured through Docker labels rather than a single readable config file, which is a different mental model for someone used to Nginx or Caddy syntax. Explain this plainly the first time labels appear in a generated guide.

## Installation approach

Traefik runs as a Docker container and discovers other containers automatically via the Docker provider — it watches the Docker socket and reads routing rules from labels on other services, rather than being told about them in its own config file.

```yaml
  traefik:
    image: traefik:v3.1
    restart: unless-stopped
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--certificatesresolvers.le.acme.email=you@example.com"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_letsencrypt:/letsencrypt
    networks:
      - app_net
```

`--providers.docker.exposedbydefault=false` is important: it means only containers with an explicit `traefik.enable=true` label get routed, so unrelated containers (the database, object storage) stay invisible to the outside world by default rather than needing to be manually excluded.

`traefik_letsencrypt` must be a persistent volume — it holds `acme.json` (the issued certificates and account key). This file requires `600` permissions or Traefik will refuse to use it; if built from scratch, create it and `chmod 600` before first start.

## Config template — single domain, path-based routing

Labels go on each application service, not on Traefik itself:

```yaml
  frontend:
    image: app/frontend:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app-frontend.rule=Host(`draw.example.com`)"
      - "traefik.http.routers.app-frontend.entrypoints=websecure"
      - "traefik.http.routers.app-frontend.tls.certresolver=le"
      - "traefik.http.services.app-frontend.loadbalancer.server.port=80"

  api:
    image: app/api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app-api.rule=Host(`draw.example.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.app-api.entrypoints=websecure"
      - "traefik.http.routers.app-api.tls.certresolver=le"
      - "traefik.http.routers.app-api.priority=10"
      - "traefik.http.services.app-api.loadbalancer.server.port=8080"

  room:
    image: app/room:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app-room.rule=Host(`draw.example.com`) && PathPrefix(`/socket.io`)"
      - "traefik.http.routers.app-room.entrypoints=websecure"
      - "traefik.http.routers.app-room.tls.certresolver=le"
      - "traefik.http.routers.app-room.priority=10"
      - "traefik.http.services.app-room.loadbalancer.server.port=80"
```

**Priority rule (always call this out explicitly in the generated guide):** the more specific `PathPrefix` routers (api, room) need a higher `priority` value than the catch-all `Host`-only router (frontend), or Traefik may match requests to the wrong service. This is the label-based equivalent of Caddy's "catch-all must be last" and Nginx's "more specific location blocks win" rules — same underlying problem, different syntax.

WebSocket upgrades need no special label — Traefik, like Caddy, proxies them transparently once the router/service labels are correct.

## Config template — multiple subdomains

Just give each service its own `Host()` rule — no path-prefix routers needed, and no priority conflicts since each router matches a different domain:

```yaml
  app:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.cloud.rule=Host(`cloud.example.com`)"
      - "traefik.http.routers.cloud.entrypoints=websecure"
      - "traefik.http.routers.cloud.tls.certresolver=le"
      - "traefik.http.services.cloud.loadbalancer.server.port=9200"

  office:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.office.rule=Host(`office.example.com`)"
      - "traefik.http.routers.office.entrypoints=websecure"
      - "traefik.http.routers.office.tls.certresolver=le"
      - "traefik.http.services.office.loadbalancer.server.port=9980"
```

## SSL / certificates

Handled by Traefik's ACME resolver (configured once, in the Traefik service's own `command:` block above) — nothing further to do per-app. Preconditions to state plainly in the guide: DNS must resolve, and ports 80/443 must be reachable (HTTP-01 challenge uses port 80 even though the final site serves on 443).

## Maintenance commands specific to Traefik

```
docker compose logs traefik                     # ACME / routing errors
docker compose exec traefik cat /letsencrypt/acme.json | head -5   # confirm certs were issued (don't share this file's contents)
```

The Traefik dashboard (enable with `--api.dashboard=true` and a router of its own, behind auth) is optional and worth mentioning as a nice-to-have for visually confirming which routers are registered, but isn't required for the guide to work.

## Troubleshooting rows to include

| Symptom | Likely cause | Resolution |
|---|---|---|
| A service returns 404 through Traefik | Missing `traefik.enable=true` label, or `exposedbydefault=false` and no labels at all | Add the label, then `docker compose up -d` to recreate the container |
| Wrong service answers a path-prefixed request | Priority not set, or set backwards | Give `PathPrefix` routers a higher `priority` value than the catch-all `Host()` router |
| Certificate never issues | `acme.json` permissions aren't 600, or DNS/port 80 unreachable | `chmod 600` the file inside the volume; confirm DNS and firewall/security group |
| Traefik container won't start after adding `acme.json` manually | File was created with wrong permissions or as a directory instead of a file | Delete and let Traefik create it fresh with `touch acme.json && chmod 600 acme.json` before first start |
