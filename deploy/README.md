# Multi-environment Docker deploy (GHCR images)

Pull pre-built images and run isolated stacks for **dev**, **tst**, **uat**, and **prod**.

| Doc | Purpose |
|-----|---------|
| [docs/docker-multi-env.md](../docs/docker-multi-env.md) | Env files, ports, **data volumes (SQLite/Mongo)**, `deploy-env.sh` |
| [docs/github-actions-ci-cd.md](../docs/github-actions-ci-cd.md) | CI, GHCR publish, GitHub Environment deploy |

Quick start:

```bash
cp deploy/env/docker.env.uat.example deploy/env/docker.env.uat
# edit secrets…
chmod +x deploy/scripts/deploy-env.sh
./deploy/scripts/deploy-env.sh uat
```

### Where database files live (per env)

| Default (named volumes) | Optional host bind mounts (`BIND_MOUNTS=1`) |
|-------------------------|-----------------------------------------------|
| `tgc-<env>_app_data` → container `/app/data` (SQLite `app.db`, sessions, media) | `<HOST_DATA_ROOT>/<env>/app/…` |
| `tgc-<env>_mongo_data` → container `/data/db` | `<HOST_DATA_ROOT>/<env>/mongo/…` |

Example with bind mounts:

```bash
BIND_MOUNTS=1 HOST_DATA_ROOT=/var/lib/telegram-copier ./deploy/scripts/deploy-env.sh uat
```

**Local machine smoke test (Windows):**

```powershell
.\deploy\scripts\deploy-env.ps1 -Environment dev -LocalBuild -BindMounts
# Panel http://localhost:8080 — SQLite at data\docker-envs\dev\app\app.db
```

Full detail: [Data volumes](../docs/docker-multi-env.md#data-volumes-sqlite-sessions-media-mongodb) · [Local test](../docs/docker-multi-env.md#test-on-a-developer-machine-local-images).
