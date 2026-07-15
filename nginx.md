# Nginx Reverse Proxy — Reference

## When to choose Nginx

Best when the user already runs Nginx for other sites on the same host, wants the most granular manual control over the proxy config, or is following along with existing tutorials (the majority of self-hosting guides on the internet use Nginx + Certbot, so it's the most "found in the wild" combination). The trade-off versus Caddy is an explicit Certbot install and a renewal step that should be verified, not assumed.

## Installation approach

Install Nginx and Certbot on the host directly (not in Docker) — this is the conventional pattern and lets Certbot's Nginx plugin edit the config automatically. The app itself still runs in Docker; Nginx on the host proxies to the containers' published ports.

```
apt install -y nginx certbot python3-certbot-nginx
```

## Step order (always follow this sequence in the generated guide)

1. Create a webroot directory and a temporary Nginx config that only serves the ACME challenge path, so Certbot can verify domain ownership before the real proxy config exists.
2. Request the certificate with Certbot's webroot method.
3. Replace the temporary config with the full production proxy config, referencing the certificate paths Certbot printed.
4. Remove the temporary config and reload Nginx.

This order matters: writing the full proxy config (which references a certificate that doesn't exist yet) before requesting the certificate causes Nginx to fail to start.

### 1. Webroot + temporary config

```
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot

cat > /etc/nginx/sites-available/certbot-challenge << 'EOF'
server {
    listen 80;
    server_name draw.example.com;
    root /var/www/certbot;
    location /.well-known/acme-challenge/ {
        allow all;
        try_files $uri =404;
    }
}
EOF
ln -s /etc/nginx/sites-available/certbot-challenge /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 2. Request certificate

```
certbot certonly --webroot \
  -w /var/www/certbot \
  -d draw.example.com \
  --email you@example.com \
  --agree-tos --no-eff-email
```

Certificates land at `/etc/letsencrypt/live/draw.example.com/fullchain.pem` and `.../privkey.pem`. If a prior partial attempt exists, Certbot appends `-0001` etc. to the directory name — always use the exact path Certbot prints, not an assumed one.

### 3. Production config — single domain, path-based routing

```
rm /etc/nginx/sites-enabled/certbot-challenge

cat > /etc/nginx/sites-available/draw << 'EOF'
server {
    listen 80;
    server_name draw.example.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    http2 on;
    server_name draw.example.com;

    ssl_certificate     /etc/letsencrypt/live/draw.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/draw.example.com/privkey.pem;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    client_max_body_size 20M;

    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -s /etc/nginx/sites-available/draw /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

**Always include the `Upgrade`/`Connection` headers on any location block that proxies a WebSocket path.** This is the single most common Nginx self-hosting mistake — without it, real-time features silently fail to connect while the rest of the app works fine, which is confusing to debug.

`http2 on;` is the current directive syntax (Nginx 1.25+, which ships in current Debian/Ubuntu). The older `listen 443 ssl http2;` combined form is deprecated — don't generate it for a current OS target.

### Multiple subdomains variant

Duplicate the second `server{}` block per subdomain, each with its own `server_name` and its own `location /` proxy_pass target, sharing the same certificate if it was requested with `-d` for all domains, or requesting/mounting separate certificates per subdomain.

## SSL renewal

Certbot installs a systemd timer automatically. State this plainly and give the verification command — don't imply any manual cron setup is needed:

```
systemctl status certbot.timer
certbot renew --dry-run
```

## Maintenance commands specific to Nginx

```
nginx -t                      # test config syntax before reloading
systemctl reload nginx        # apply config changes without dropping connections
journalctl -u nginx -e        # recent Nginx errors
```

## Troubleshooting rows to include

| Symptom | Likely cause | Resolution |
|---|---|---|
| Certbot challenge fails | DNS not propagated, or Nginx not serving the webroot path yet | Wait for DNS, re-check the temporary certbot-challenge config is enabled |
| SSL certificate error / wrong domain in browser | Wrong cert path referenced (missing a `-0001` suffix) | `ls /etc/letsencrypt/live/` and use the exact directory name shown |
| Real-time features don't work but the rest of the app does | Missing `Upgrade`/`Connection` headers on the WebSocket location block | Add `proxy_http_version 1.1;`, `proxy_set_header Upgrade $http_upgrade;`, `proxy_set_header Connection "Upgrade";` |
| 502 Bad Gateway | App container not running or wrong port in `proxy_pass` | `docker ps`, confirm the published host port matches `proxy_pass` |
| Upload fails above a certain size | `client_max_body_size` too low | Raise it in the `server{}` block and reload |
