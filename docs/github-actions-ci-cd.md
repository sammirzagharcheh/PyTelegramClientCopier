# GitHub Actions CI/CD (tests → GHCR images → per-env Docker deploy)

This project’s pipeline:

1. **CI** — backend pytest + frontend lint/test/build + Docker build smoke  
2. **Publish** — push **backend** and **frontend** images to **GitHub Container Registry (GHCR)** after CI succeeds on `main`/`master` (also on `v*.*.*` tags)  
3. **Deploy** — pull those images and run Docker Compose for **dev / tst / uat / prod**, each with its own env file and ports

Related guide: [Docker multi-environment deploy](docker-multi-env.md)

---

## Workflows

| File | Trigger | What it does |
|------|---------|----------------|
| `.github/workflows/ci.yml` | PR / push to `main`/`master` / manual | Tests + Docker build (no push) |
| `.github/workflows/publish-images.yml` | After successful CI on `main`/`master`; tag `v*.*.*`; manual | Build & push GHCR images |
| `.github/workflows/deploy-environment.yml` | Manual (`workflow_dispatch`) | SSH to a host and run `deploy-env.sh` for one environment |

---

## Image names (GHCR)

Images are published as (owner/repo lowercased):

```text
ghcr.io/<owner>/<repo>/backend:<tag>
ghcr.io/<owner>/<repo>/frontend:<tag>
```

For this repository that is typically:

```text
ghcr.io/sammirzagharcheh/pytelegramclientcopier/backend:latest
ghcr.io/sammirzagharcheh/pytelegramclientcopier/frontend:latest
```

**Tags:**

| Source | Tags |
|--------|------|
| Successful CI on `main`/`master` | `sha-<7char>` and `latest` |
| Git tag `v1.2.3` | `v1.2.3` and `latest` |
| Manual publish | Custom tag you enter (or short SHA + `latest`) |

### First-time GHCR setup

1. Push to `main` (or run **Publish images** manually) so packages exist.  
2. In GitHub → **Packages**, open each package → **Package settings** → set visibility (private for private repos is typical).  
3. Grant the repo **write** access to the packages if GitHub does not link them automatically.  
4. On deploy hosts, log in when packages are private:

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

PAT needs at least `read:packages` (and `write:packages` only for pushing).  
`GITHUB_TOKEN` in Actions already has package write for this repo’s workflows.

---

## CI details

**Backend**

- Python 3.11  
- `pip install -e ".[dev]"`  
- `pytest` with `TESTING=1`  
- Live Telethon test is ignored in CI (`tests/integration/test_telethon_live.py`)

**Frontend**

- Node 20  
- `npm ci` → `lint` → `test` → `build`

**Docker smoke**

- Builds `Dockerfile.backend` and `Dockerfile.frontend` (no registry push)

---

## Manual publish

GitHub → **Actions** → **Publish images** → **Run workflow**  
Optional input: custom image tag.

---

## Deploy from GitHub Actions (optional)

Create four GitHub **Environments**: `dev`, `tst`, `uat`, `prod`  
(Settings → Environments).

### Required secrets (per environment)

| Secret | Purpose |
|--------|---------|
| `DEPLOY_HOST` | Server hostname or IP |
| `DEPLOY_USER` | SSH user |
| `DEPLOY_SSH_KEY` | Private SSH key (full PEM) |
| `DEPLOY_PATH` | Absolute path on the server (repo or deploy root), e.g. `/opt/telegram-copier` |
| `DOCKER_ENV_FILE` | **Full contents** of that env’s `docker.env.*` (same keys as `deploy/env/docker.env.<env>.example`) |

### Host requirements

- Docker Engine + Compose plugin  
- SSH access for `DEPLOY_USER` (docker group or root as you prefer)  
- Outbound HTTPS to `ghcr.io`

### Run a deploy

Actions → **Deploy environment** → choose `environment` + `image_tag` (e.g. `latest` or `sha-abc1234`).

---

## Deploy from the server (recommended simple path)

On the host (after cloning the repo or copying `deploy/`):

```bash
cd /opt/telegram-copier   # or your clone path

# One-time per environment
cp deploy/env/docker.env.uat.example deploy/env/docker.env.uat
nano deploy/env/docker.env.uat   # API_ID, API_HASH, JWT_SECRET, …

# Login to GHCR if private
echo "$CR_PAT" | docker login ghcr.io -u YOUR_USER --password-stdin

chmod +x deploy/scripts/deploy-env.sh
./deploy/scripts/deploy-env.sh uat          # pulls :latest
./deploy/scripts/deploy-env.sh prod v1.2.3  # specific release tag
```

Without Mongo container (external Mongo / Atlas):

```bash
NO_MONGO=1 ./deploy/scripts/deploy-env.sh uat
# Set MONGO_URI in deploy/env/docker.env.uat to your external URI
```

First boot — create admin:

```bash
docker compose -p tgc-uat \
  -f deploy/compose/docker-compose.yml \
  -f deploy/compose/docker-compose.uat.yml \
  --env-file deploy/env/docker.env.uat \
  exec backend tg-copier db create-admin you@example.com 'YourStrongPassword'
```

---

## Environments at a glance

| Env | Compose project | Panel port | API port | Mongo port | Env file |
|-----|-----------------|------------|----------|------------|----------|
| dev | `tgc-dev` | 8080 | 8001 | 27018 | `deploy/env/docker.env.dev` |
| tst | `tgc-tst` | 8081 | 8002 | 27019 | `deploy/env/docker.env.tst` |
| uat | `tgc-uat` | 8082 | 8003 | 27020 | `deploy/env/docker.env.uat` |
| prod | `tgc-prod` | 80 | *(not published)* | *(not published)* | `deploy/env/docker.env.prod` |

Each environment has its own Docker volumes (`tgc-<env>_app_data`, `tgc-<env>_mongo_data`) and should use a **different** `JWT_SECRET` and `MONGO_DB`.

Full Docker details: [docker-multi-env.md](docker-multi-env.md)

---

## Local development (unchanged)

Building from source on your laptop still uses the root compose files:

```bash
cp docker.env.example docker.env
docker compose up --build -d
```

CI/CD images are for **server / multi-env** deploys, not a replacement for [Docker development](docker-development.md).

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Publish skipped after CI | `workflow_run` only publishes when CI **succeeds** on `main`/`master` |
| `denied` pulling from GHCR | `docker login ghcr.io`; package visibility; PAT scopes |
| Deploy Action fails on secrets | All five environment secrets set for that GitHub Environment |
| Wrong config in a container | Confirm `deploy/env/docker.env.<env>` exists on the host and matches the overlay |
| Port already allocated | Another stack using 80/808x — stop it or change the overlay ports |
| CI pytest failures | Run `pytest -q --ignore=tests/integration/test_telethon_live.py` locally with `TESTING=1` |

---

## Security notes

- Never commit real `docker.env.*` files (only `*.example`).  
- Prefer unique `JWT_SECRET` per environment.  
- Production overlay does **not** publish Mongo or the API port on the host; put TLS (nginx/Caddy/Cloudflare) in front of port 80 as needed.  
- Rotate deploy SSH keys and GitHub PATs if leaked.
