# Deploying Modelia on one cloud VM

Docker Compose + Caddy (automatic HTTPS) + a free DuckDNS domain. Files:
`docker-compose.prod.yml` (repo root), `deploy/Caddyfile`, `env.example` (repository root).

What runs: `caddy` (only ports 80/443 published), `frontend`, `backend`, `runner`,
`socket-proxy` (the only container with the Docker socket), `db`, `redis`.
Caddy routes `/gen/*` to the runner, `/api/*` and `/ws/*` to the backend, the rest to the frontend.

## 1. VM

- Ubuntu 22.04/24.04, **4 GB RAM, 2 vCPU, 30 GB disk** (Gradle builds need the RAM; add 2 GB swap if you can).
- Firewall / security group: allow **22, 80, 443 only** (443/udp optional, HTTP/3).
  Ports **8090 (runner), 8000 (backend), 5432 (db), 6379 (redis), 2375 (docker proxy) must NOT be open.**
  With UFW: `sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`.
  (Docker bypasses UFW for published ports, which is why the compose file publishes only 80/443.)

## 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out and back in
```

## 3. DuckDNS domain

1. Sign in at https://www.duckdns.org, create a subdomain (e.g. `modelia` -> `modelia.duckdns.org`), set its IP to the VM's public IP (use a static/elastic IP).
2. Keep it updated (only needed if the IP can change). `crontab -e`:

```
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=modelia&token=YOUR_DUCKDNS_TOKEN&ip=" >/dev/null
```

## 4. Configure and start

```bash
git clone <your-repo-url> modelia && cd modelia
cp env.example .env
# edit the root .env: APP_DOMAIN, and fill SECRET_KEY / POSTGRES_PASSWORD / RUNNER_TOKEN
# with `openssl rand -hex 32` (one value each). .env is git-ignored.

# Optional but saves time on the first "Generate backend" (~1 GB of images):
docker pull gradle:9.7.1-jdk21 && docker pull eclipse-temurin:21-jre && docker pull postgres:16-alpine

docker compose -f docker-compose.prod.yml up -d --build
```

Open `https://<APP_DOMAIN>`. The first request may take a few seconds while Caddy gets the
Let's Encrypt certificate (needs 80/443 reachable and the DNS record already pointing at the VM).
Register the first user in the app. Verification emails go to `docker compose ... logs backend`
until you configure SMTP in the root `.env`.

## 5. Operate

Short alias for the commands below: `alias mc='docker compose -f docker-compose.prod.yml'`

| Task | Command |
|---|---|
| Update to latest code | `git pull && mc up -d --build` |
| Status | `mc ps` |
| Logs (all / one) | `mc logs -f --tail=100` / `mc logs -f backend` (also `runner`, `caddy`, `socket-proxy`) |
| Restart one service | `mc restart backend` |
| Stop (keeps data) | `mc stop` |
| Running generated backends | `docker ps --filter label=modelia.managed=true` |

Data lives in the named volumes `postgres_data` (database) and `caddy_data` (certificates). Do not
delete them casually; never run `mc down -v`. Generated backends are removed after
`RUNNER_MAX_LIFETIME_SECONDS` (6 h by default) and on every runner restart.

## Notes and limits

- Django admin (`/admin`) is intentionally not routed by Caddy.
- The socket proxy limits which Docker API sections the runner can call, not what it puts in a
  container (it cannot read request bodies). The runner enforces the image allowlist, no
  privileged mode, no host mounts, resource limits and an internal-only network per deployment.
- Backups are not set up: `docker compose ... exec db pg_dump -U app app > backup.sql` is the manual way.
