# Deploy on Ubuntu 22.04+ (native)

Install Telegram Client Copier on a Linux server **without Docker**.  
Uses: Python 3.11+, Node.js 20, nginx, systemd. MongoDB is optional (needed for message/worker logs).

**Supported:** Ubuntu 22.04 and 24.04 (script also works on 20.04 with Python 3.11).

---

## Quick start (recommended)

### A) Clone the repo first (public or private)

```bash
sudo apt-get update && sudo apt-get install -y git

# Public:
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private (SSH after deploy key — see docs/git-clone-and-private-repo.md):
# git clone git@github.com:OWNER/REPO.git
# cd REPO
```

Then run the local deploy script:

```bash
sudo bash scripts/deploy-ubuntu.sh
```

### B) One-line install (public repo only)

```bash
curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

> **Private GitHub repo:** do **not** use the curl one-liner (raw files are not public). Clone with SSH/PAT, then run `sudo bash scripts/deploy-ubuntu.sh`. Full guide: [git-clone-and-private-repo.md](git-clone-and-private-repo.md).

Then:

```bash
# 1) Edit secrets
sudo nano /opt/telegram-copier/.env
# Set API_ID, API_HASH, JWT_SECRET

# 2) Init DB + create admin (as app user)
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db init-db"
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db create-admin you@example.com 'YourStrongPassword'"

# 3) Restart
sudo systemctl restart telegram-copier

# 4) Open in browser
# http://YOUR_SERVER_IP
```

With HTTPS (domain DNS A record must already point to the VPS):

```bash
DOMAIN=copier.example.com USE_SSL=true CERTBOT_EMAIL=you@example.com \
  sudo bash scripts/deploy-ubuntu.sh
```

(Or the curl one-liner if the repo is public.)

---

## Step-by-step (detailed)

### Step 0 — Server checklist

- Fresh or clean Ubuntu 22.04 / 24.04 VPS
- SSH access with `sudo`
- Ports **80** (and **443** if using SSL) open
- Get `API_ID` + `API_HASH` from [my.telegram.org](https://my.telegram.org)
- Git installed; for a **private** repo, auth ready ([git-clone-and-private-repo.md](git-clone-and-private-repo.md))

Optional firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # 80 + 443
sudo ufw enable
```

### Step 1 — Clone the repository

```bash
sudo apt-get update
sudo apt-get install -y git

# Public HTTPS
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git
cd PyTelegramClientCopier

# Private SSH (recommended on VPS)
# git clone git@github.com:OWNER/REPO.git && cd REPO
```

Verify:

```bash
ls scripts/deploy-ubuntu.sh docker-compose.yml
```

### Step 2 — Run the deploy script

**Option A — from your clone** (works for public and private)

```bash
sudo bash scripts/deploy-ubuntu.sh
```

Private repo: tell the script which URL to pull into `/opt/telegram-copier`:

```bash
sudo REPO_URL=git@github.com:OWNER/REPO.git bash scripts/deploy-ubuntu.sh
```

(`tgcopier` must be able to use the SSH deploy key — see private-repo guide.)

**Option B — one-liner** (public repo only)

```bash
curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

**Option C — clone to `/tmp` then run** (public HTTPS or private SSH)

```bash
git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git /tmp/tgc
sudo bash /tmp/tgc/scripts/deploy-ubuntu.sh
```

The script will:

- Install packages (nginx, Python, Node 20, build tools, certbot)
- Clone the app to `/opt/telegram-copier` (default)
- Create user `tgcopier`
- Create Python venv and install the backend
- Build the frontend
- Configure nginx + systemd service `telegram-copier`
- Create `.env` if missing (prompts when interactive)

### Step 3 — Configure `.env`

```bash
sudo nano /opt/telegram-copier/.env
```

Minimum:

```env
API_ID=12345678
API_HASH=your_api_hash_here
JWT_SECRET=paste_a_long_random_secret
```

Generate a secret:

```bash
openssl rand -hex 32
```

Optional MongoDB (message / worker logs):

```env
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB=telegram_copier
```

If you use Mongo, install it separately (example):

```bash
# Follow MongoDB’s Ubuntu install guide for 22.04/24.04, then:
sudo systemctl enable --now mongod
```

Secure the file:

```bash
sudo chmod 600 /opt/telegram-copier/.env
sudo chown tgcopier:tgcopier /opt/telegram-copier/.env
```

### Step 4 — Initialize database and admin

```bash
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db init-db"
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db create-admin you@example.com 'YourStrongPassword'"
```

### Step 5 — Start / verify service

```bash
sudo systemctl enable --now telegram-copier
sudo systemctl status telegram-copier
curl -s http://127.0.0.1:8000/health
# expect: {"status":"ok"}
```

Open:

- Panel: `http://YOUR_SERVER_IP` (or `https://your-domain` if SSL)
- API health via nginx: `http://YOUR_SERVER_IP/health`

### Step 6 — First login in the UI

1. Log in with the admin email/password
2. Add a Telegram account (login flow in the panel)
3. Create a mapping (source → destination)
4. Start a worker for that account

---

## Manual install (no deploy script)

Use this if you prefer full control.

### 1) System packages

```bash
sudo apt-get update
sudo apt-get install -y curl git nginx build-essential python3-venv python3-dev \
  libffi-dev ca-certificates software-properties-common
```

Install Node.js 20:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v   # should be v20.x
python3 --version   # need 3.11+
```

### 2) App user and directory

```bash
sudo useradd --system --create-home --home-dir /opt/telegram-copier --shell /usr/sbin/nologin tgcopier || true
sudo mkdir -p /opt/telegram-copier
sudo chown -R tgcopier:tgcopier /opt/telegram-copier
```

### 3) Clone and install backend

```bash
# Public:
sudo -u tgcopier git clone https://github.com/sammirzagharcheh/PyTelegramClientCopier.git /opt/telegram-copier

# Private (SSH; deploy key must exist for user tgcopier):
# sudo -u tgcopier git clone git@github.com:OWNER/REPO.git /opt/telegram-copier

cd /opt/telegram-copier
sudo -u tgcopier python3 -m venv .venv
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/pip install -U pip && .venv/bin/pip install -e ."
```

> Private repo auth: [git-clone-and-private-repo.md](git-clone-and-private-repo.md)
### 4) Env, DB, admin

```bash
sudo -u tgcopier cp /opt/telegram-copier/.env.example /opt/telegram-copier/.env
sudo -u tgcopier nano /opt/telegram-copier/.env
sudo chmod 600 /opt/telegram-copier/.env
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db init-db"
sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db create-admin you@example.com 'YourStrongPassword'"
```

### 5) Build frontend

```bash
sudo -u tgcopier bash -c "cd /opt/telegram-copier/frontend && npm ci && npm run build"
```

### 6) systemd unit

Create `/etc/systemd/system/telegram-copier.service`:

```ini
[Unit]
Description=Telegram Client Copier API
After=network.target

[Service]
Type=simple
User=tgcopier
Group=tgcopier
WorkingDirectory=/opt/telegram-copier
EnvironmentFile=/opt/telegram-copier/.env
ExecStart=/opt/telegram-copier/.venv/bin/tg-copier api --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-copier
```

### 7) nginx reverse proxy

Create `/etc/nginx/sites-available/telegram-copier`:

```nginx
server {
    listen 80;
    server_name _;   # or your domain

    root /opt/telegram-copier/frontend/dist;
    index index.html;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/telegram-copier /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Optional HTTPS:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

---

## Update the app

On the VPS:

```bash
sudo bash /opt/telegram-copier/scripts/update-vps.sh
```

Or re-run deploy in update mode:

```bash
UPDATE_ONLY=true curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

---

## Useful commands

| Task | Command |
|------|---------|
| Service status | `sudo systemctl status telegram-copier` |
| API logs | `sudo journalctl -u telegram-copier -f` |
| Restart API | `sudo systemctl restart telegram-copier` |
| Show config | `sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db show-config"` |
| Test Mongo | `sudo -u tgcopier bash -c "cd /opt/telegram-copier && .venv/bin/tg-copier db test-mongo"` |
| nginx reload | `sudo nginx -t && sudo systemctl reload nginx` |

Data lives under `/opt/telegram-copier/data/` (SQLite DB, Telethon sessions, media assets). Keep backups of this folder.

---

## Production checklist

- [ ] Strong `JWT_SECRET` (not the example value)
- [ ] `API_ID` / `API_HASH` kept private; `.env` mode `600`
- [ ] HTTPS with a real domain when public
- [ ] Firewall allows only SSH + HTTP/HTTPS
- [ ] Backup `data/` regularly (sessions = login state)
- [ ] MongoDB installed if you need message/worker logs in the UI

---

## Non-interactive / CI deploy

```bash
API_ID=123 \
API_HASH=abc \
JWT_SECRET="$(openssl rand -hex 32)" \
ADMIN_EMAIL=admin@example.com \
ADMIN_PASSWORD='strong-password' \
NON_INTERACTIVE=true \
curl -fsSL "https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh" | sudo bash
```

Prefer CI secrets or a local env file over putting passwords in shell history.

### Script env vars

| Variable | Default | Meaning |
|----------|---------|---------|
| `INSTALL_DIR` | `/opt/telegram-copier` | Install path |
| `REPO_URL` | public GitHub HTTPS URL | Clone URL (use `git@github.com:OWNER/REPO.git` for private) |
| `DOMAIN` | empty | Domain for nginx / SSL |
| `USE_SSL` | `false` | Let's Encrypt |
| `CERTBOT_EMAIL` | empty | Certbot contact email |
| `SKIP_DEPS` | `false` | Skip apt installs |
| `UPDATE_ONLY` | `false` | Pull + rebuild + restart only |
| `NON_INTERACTIVE` | `false` | No prompts |
| `API_ID` / `API_HASH` / `JWT_SECRET` | — | Written into `.env` when provided |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | — | Creates admin when provided |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `curl \| bash` errors like `-u: command not found` | Use clone-and-run (Option B) instead of piping curl |
| Port 80 in use | `sudo ss -tlnp \| grep ':80'` and stop the other service |
| Health fails | `sudo journalctl -u telegram-copier -n 100 --no-pager` |
| Permission errors under `data/` | `sudo chown -R tgcopier:tgcopier /opt/telegram-copier/data` |
| Worker won’t start | See [WORKER_TROUBLESHOOTING.md](WORKER_TROUBLESHOOTING.md) |

---

## Related docs

- [Git clone & private GitHub repos](git-clone-and-private-repo.md)
- [Docker — production](docker-production.md)
- [Docker — development](docker-development.md)
- [Worker troubleshooting](WORKER_TROUBLESHOOTING.md)
