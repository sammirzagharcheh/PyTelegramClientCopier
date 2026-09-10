# Multi-environment Docker deploy (GHCR images)

Pull pre-built images and run isolated stacks for **dev**, **tst**, **uat**, and **prod**.

| Doc | Purpose |
|-----|---------|
| [docs/docker-multi-env.md](../docs/docker-multi-env.md) | Env files, ports, `deploy-env.sh` |
| [docs/github-actions-ci-cd.md](../docs/github-actions-ci-cd.md) | CI, GHCR publish, GitHub Environment deploy |

Quick start:

```bash
cp deploy/env/docker.env.uat.example deploy/env/docker.env.uat
# edit secrets…
chmod +x deploy/scripts/deploy-env.sh
./deploy/scripts/deploy-env.sh uat
```
