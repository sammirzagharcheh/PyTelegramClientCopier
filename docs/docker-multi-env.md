# Docker — multi-environment deploy (dev / tst / uat / prod)

Deploy the **same GHCR images** to isolated stacks. Each environment has:

- Its own **compose overlay** (ports / exposure)
- Its own **env file** (`EnvironmentFile`-style config for the backend container)
- Its own **Compose project name** (`tgc-dev`, `tgc-tst`, …) so volumes and containers never clash

Images are produced by CI/CD — see [GitHub Actions CI/CD](github-actions-ci-cd.md).  
For a single local production-like build from source, see [Docker — production](docker-production.md).

---

## Layout

```text
deploy/
  compose/
    docker-compose.yml              # GHCR images (no local build)
    docker-compose.dev.yml
    docker-compose.tst.yml
    docker-compose.uat.yml
    docker-compose.prod.yml
    docker-compose.no-mongo.yml     # optional overlay
  env/
    docker.env.dev.example          # templates (committed)
    docker.env.tst.example
    docker.env.uat.example
    docker.env.prod.example
    docker.env.dev                  # real secrets (gitignored)
    docker.env.tst
    docker.env.uat
    docker.env.prod
  scripts/
    deploy-env.sh                   # pull + up for one env
```

---

## One-time setup per environment

```bash
cd /path/to/PyTelegramClientCopier

cp deploy/env/docker.env.dev.example  deploy/env/docker.env.dev
cp deploy/env/docker.env.tst.example  deploy/env/docker.env.tst
cp deploy/env/docker.env.uat.example  deploy/env/docker.env.uat
cp deploy/env/docker.env.prod.example deploy/env/docker.env.prod
```

Edit each file and set at least:

| Variable | Notes |
|----------|--------|
| `API_ID` / `API_HASH` | From [my.telegram.org](https://my.telegram.org) |
| `JWT_SECRET` | **Different** strong secret per env (`openssl rand -hex 32`) |
| `MONGO_DB` | Defaults already differ (`telegram_copier_dev`, `_tst`, …) |
| `LOG_LEVEL` | `DEBUG` (dev) → `WARNING` (prod) |
| `MONGO_URI` | Keep `mongodb://mongodb:27017` with in-compose Mongo; or Atlas / external URI with `NO_MONGO=1` |

---

## Deploy / update

```bash
chmod +x deploy/scripts/deploy-env.sh

# Pull :latest (or IMAGE_TAG) and start
./deploy/scripts/deploy-env.sh dev
./deploy/scripts/deploy-env.sh tst
./deploy/scripts/deploy-env.sh uat
./deploy/scripts/deploy-env.sh prod

# Pin a release or CI SHA
./deploy/scripts/deploy-env.sh uat v1.2.3
./deploy/scripts/deploy-env.sh prod sha-a1b2c3d
```

Optional environment variables:

| Variable | Meaning |
|----------|---------|
| `IMAGE_TAG` | Tag if not passed as 2nd argument (default `latest`) |
| `BACKEND_IMAGE` / `FRONTEND_IMAGE` | Full image refs (override defaults) |
| `GHCR_OWNER_REPO` | Override `owner/repo` used in default image names |
| `NO_MONGO=1` | Apply `docker-compose.no-mongo.yml` |

---

## Ports

| Env | Panel (HTTP) | Backend API | MongoDB |
|-----|--------------|-------------|---------|
| **dev** | `8080` | `8001` | `27018` |
| **tst** | `8081` | `8002` | `27019` |
| **uat** | `8082` | `8003` | `27020` |
| **prod** | `80` | not published | not published |

You can run **dev + tst + uat** on one host at the same time. Prefer a dedicated host (or firewall) for **prod**.

---

## Useful Compose commands

Replace `uat` with your env; project is always `tgc-<env>`:

```bash
ENV=uat
PROJECT=tgc-$ENV
FILES="-f deploy/compose/docker-compose.yml -f deploy/compose/docker-compose.$ENV.yml"
ENVFILE="deploy/env/docker.env.$ENV"

docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" ps
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" logs -f backend
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" exec backend tg-copier db create-admin admin@example.com 'Secret'
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" pull
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" up -d
docker compose -p "$PROJECT" $FILES --env-file "$ENVFILE" down
```

`down` does **not** delete named volumes. To wipe data for one env:

```bash
docker compose -p tgc-uat $FILES --env-file "$ENVFILE" down -v
```

---

## How this maps to “EnvironmentFile”

On systemd installs, Ubuntu docs use an `EnvironmentFile=` pointing at `.env`.  
In Docker multi-env deploys, the equivalent is:

```text
deploy/env/docker.env.<env>  →  backend service env_file in docker-compose.<env>.yml
```

Compose injects those variables into the backend container the same way systemd would inject an EnvironmentFile into a unit.

---

## Same host as local `docker compose` (root)

Root `docker-compose.yml` uses project name from the directory (often `telegramclientcopier`) and ports **80 / 8000 / 27017**.

Multi-env stacks use `tgc-*` and alternate ports (except prod `:80`).  
**Do not** run root prod-like compose and `tgc-prod` together on the same host without changing ports — both want host port 80.

---

## Checklist

- [ ] GHCR images exist (`backend` + `frontend`)
- [ ] `docker login ghcr.io` on the host (if private packages)
- [ ] Real `deploy/env/docker.env.<env>` created from examples
- [ ] Unique `JWT_SECRET` / `MONGO_DB` per env
- [ ] `./deploy/scripts/deploy-env.sh <env>` succeeds
- [ ] Admin user created
- [ ] Panel opens on the env’s HTTP port
- [ ] `/health` OK (via panel proxy or published API port on non-prod)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Missing env file` | Copy the matching `*.example` to `docker.env.<env>` |
| Image pull denied | GHCR login + package permissions |
| Port is already allocated | Stop conflicting compose project or edit the overlay |
| App uses wrong DB/secret | Confirm the overlay’s `env_file` path and file contents |
| Workers / sessions lost after recreate | Normal if you removed volumes (`down -v`); otherwise data lives in `tgc-<env>_app_data` |
