# Documentation index

Simple guides for installing and running **Telegram Client Copier**.

## Deploy / install

| Guide | When to use |
|-------|-------------|
| [Git clone & private GitHub repos](git-clone-and-private-repo.md) | Clone the project; SSH deploy keys / PAT for **private** repos. |
| [Deploy on Ubuntu 22.04+](deploy-ubuntu.md) | Native install on a Linux VPS (systemd + nginx). No Docker required. |
| [Docker — production](docker-production.md) | Full stack in containers (backend + frontend + **MongoDB**), build on the host. |
| [Docker — production without Mongo](docker-production-no-mongo.md) | Backend + frontend only; no Mongo container (optional external Mongo). |
| [Docker — development](docker-development.md) | Hot-reload coding with Docker (Vite + API reload). |
| [Docker — multi-env (dev/tst/uat/prod)](docker-multi-env.md) | Pull GHCR images; separate env files + ports per environment. |
| [GitHub Actions CI/CD](github-actions-ci-cd.md) | Tests → GHCR images → optional SSH deploy per environment. |

## Operations

| Guide | When to use |
|-------|-------------|
| [Worker troubleshooting](WORKER_TROUBLESHOOTING.md) | Workers won’t start, session locks, Mongo worker logs. |
| [Developer cheat sheet](dev-cheatsheet.md) | Feature → files → tests map for day-to-day coding. |

## What you need before any install

1. **Clone the repo** (public HTTPS, or SSH/PAT if private) — [git-clone-and-private-repo.md](git-clone-and-private-repo.md)
2. **Telegram API credentials** from [my.telegram.org](https://my.telegram.org): `API_ID` and `API_HASH`
3. A strong **`JWT_SECRET`** for production (example: `openssl rand -hex 32`)
4. Ubuntu **22.04 / 24.04** (or Docker Engine on any host)

## Pick a path (quick)

- **First time / private GitHub:** start with [Git clone & private repos](git-clone-and-private-repo.md)
- **VPS, simple, one server:** start with [Deploy on Ubuntu](deploy-ubuntu.md)
- **Containers + Mongo in Docker:** start with [Docker — production](docker-production.md)
- **Containers without Mongo container:** start with [Docker — production without Mongo](docker-production-no-mongo.md)
- **CI images + separate dev/tst/uat/prod:** start with [GitHub Actions CI/CD](github-actions-ci-cd.md) then [multi-env Docker](docker-multi-env.md)
- **Develop on your machine with Docker:** start with [Docker — development](docker-development.md)
