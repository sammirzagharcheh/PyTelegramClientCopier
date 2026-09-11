# Git clone and private GitHub repos

How to get the project onto a server or laptop, including when the GitHub repo is **private**.

Replace `OWNER/REPO` with your real path (example: `sammirzagharcheh/PyTelegramClientCopier`).

---

## Quick start — public repo

```bash
sudo apt-get update && sudo apt-get install -y git   # Ubuntu/Debian if needed
git clone https://github.com/OWNER/REPO.git
cd REPO
```

Clone into a specific folder:

```bash
git clone https://github.com/OWNER/REPO.git TelegramClientCopier
cd TelegramClientCopier
```

Shallow clone (faster, less history — good for servers):

```bash
git clone --depth 1 https://github.com/OWNER/REPO.git
cd REPO
```

---

## Quick start — private repo (pick one)

| Method | Best for | Command shape |
|--------|----------|-----------------|
| **SSH + deploy key** | Servers / VPS (recommended) | `git clone git@github.com:OWNER/REPO.git` |
| **HTTPS + Personal Access Token (PAT)** | Quick one-off / CI | `git clone https://github.com/OWNER/REPO.git` (token as password) |
| **GitHub CLI (`gh`)** | Interactive machines | `gh auth login` then `gh repo clone OWNER/REPO` |

Details below.

---

## Step-by-step: clone (public or private)

### 1) Install Git

```bash
# Ubuntu 22.04+
sudo apt-get update
sudo apt-get install -y git

git --version
```

### 2) Choose destination

```bash
# Example locations
mkdir -p ~/apps && cd ~/apps          # your user home
# or
sudo mkdir -p /opt && cd /opt         # system path (needs sudo for later chown)
```

### 3) Clone

**Public HTTPS:**

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
```

**Private — use SSH (after setup in the next section):**

```bash
git clone git@github.com:OWNER/REPO.git
cd REPO
```

**Private — use HTTPS + token (after creating a PAT):**

```bash
git clone https://github.com/OWNER/REPO.git
# Username: your GitHub username
# Password: paste the PAT (not your GitHub account password)
cd REPO
```

### 4) Confirm

```bash
pwd
git remote -v
git status
ls
```

You should see files like `docker-compose.yml`, `README.md`, `docs/`.

### 5) Later updates

```bash
cd /path/to/REPO
git pull
```

For private repos, the same auth method (SSH key or stored credential) must still work.

---

## Private repo solutions (explained)

Anonymous `git clone https://github.com/...` **fails** on private repos (`Repository not found` or auth required). Use one of these.

### Option A — SSH deploy key (recommended on servers)

A **deploy key** is an SSH key tied to **one repo** (read-only is enough for deploy). Safer than putting a full personal token on a VPS.

**On the server:**

```bash
# 1) Create a key (no passphrase is common for unattended deploy; protect the server instead)
ssh-keygen -t ed25519 -C "deploy-telegram-copier" -f ~/.ssh/github_deploy_copier -N ""

# 2) Show the public key — copy this entire line
cat ~/.ssh/github_deploy_copier.pub
```

**On GitHub:**

1. Open the repo → **Settings** → **Deploy keys** → **Add deploy key**
2. Title: e.g. `vps-production`
3. Paste the `.pub` contents
4. Leave **Allow write access** unchecked (read-only)
5. Save

**On the server — use that key for GitHub:**

```bash
# SSH config so git uses this key
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_deploy_copier
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

# Test
ssh -T git@github.com
# Expect: Hi OWNER/REPO! You've successfully authenticated...

# Clone
git clone git@github.com:OWNER/REPO.git
cd REPO
```

**App user note (Ubuntu native install):** if the service user is `tgcopier`, either:

- Clone as your admin user then `chown -R tgcopier:tgcopier /opt/telegram-copier`, or  
- Create the deploy key in `/home/tgcopier/.ssh/` and run `git` as `tgcopier`.

Deploy script with private SSH URL:

```bash
REPO_URL=git@github.com:OWNER/REPO.git \
  sudo -E bash scripts/deploy-ubuntu.sh
```

Ensure the user that runs `git clone` inside the script (`tgcopier`) can use the SSH key (copy key + `config` into that user’s `~/.ssh`).

---

### Option B — HTTPS + Personal Access Token (PAT)

Good for laptops or short-lived servers. Prefer a **fine-grained** or classic PAT with **Contents: Read** only.

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens**
2. Create token with repo read access
3. Clone:

```bash
git clone https://github.com/OWNER/REPO.git
# Username: your-github-username
# Password: ghp_xxxxxxxx   (the token)
```

**Avoid saving the token in shell history:**

```bash
# Prompt-based (token not in the command line)
git clone https://github.com/OWNER/REPO.git
```

Or use a credential helper once:

```bash
git config --global credential.helper store   # stores in ~/.git-credentials (protect this file!)
git clone https://github.com/OWNER/REPO.git
```

**CI / non-interactive:**

```bash
git clone "https://x-access-token:${GITHUB_TOKEN}@github.com/OWNER/REPO.git"
```

Use a secrets manager / CI secret — never commit the token or put it in docs/chat logs.

Deploy script:

```bash
REPO_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/OWNER/REPO.git" \
  NON_INTERACTIVE=true \
  sudo -E bash -c 'curl -fsSL ... | bash'
```

Prefer SSH deploy keys over embedding tokens in `REPO_URL` on long-lived VPS.

---

### Option C — GitHub CLI

```bash
sudo apt-get install -y gh    # or see https://cli.github.com/
gh auth login                 # follow prompts (HTTPS or SSH)
gh repo clone OWNER/REPO
cd REPO
```

---

### Option D — Machine user / collaborator

Add a dedicated GitHub user as a **read-only collaborator**, then authenticate that user with SSH or PAT on the server. Heavier than a deploy key; use when one identity must access **many** private repos.

---

## Which method should I use?

| Situation | Use |
|-----------|-----|
| Public repo | HTTPS clone (no auth) |
| Private repo on a VPS | **Deploy key (SSH)** |
| Private repo on your laptop | SSH key for your user, or `gh auth login` |
| GitHub Actions / CI | `GITHUB_TOKEN` or deploy key / machine PAT in secrets |
| One-time test | HTTPS + PAT |

---

## Common errors

| Error | Meaning / fix |
|-------|----------------|
| `Repository not found` | Private repo + no auth, or wrong URL / no access |
| `Permission denied (publickey)` | SSH key missing, wrong `IdentityFile`, or key not added as deploy/user key |
| `Authentication failed` (HTTPS) | Used account password instead of **PAT**, or token expired / missing `repo` scope |
| `curl \| bash` can’t see private script | Don’t curl raw private files without a token; clone with SSH/PAT then run `scripts/deploy-ubuntu.sh` locally |

**Private repo + Ubuntu one-liner:** the public `curl … raw.githubusercontent.com/…/deploy-ubuntu.sh` URL **will not work** if the repo is private. Instead:

```bash
git clone git@github.com:OWNER/REPO.git /tmp/tgc
sudo REPO_URL=git@github.com:OWNER/REPO.git bash /tmp/tgc/scripts/deploy-ubuntu.sh
```

(SSH auth must work for the account that performs the clone inside the script.)

---

## Related docs

- [Deploy on Ubuntu](deploy-ubuntu.md)
- [Docker — production](docker-production.md)
- [Docker — production without Mongo](docker-production-no-mongo.md)
- [Docker — development](docker-development.md)
