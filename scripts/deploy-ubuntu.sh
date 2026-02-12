#!/usr/bin/env bash
# =============================================================================
# Telegram Client Copier - Ubuntu VPS Deployment Script
# =============================================================================
# Deploys PyTelegramClientCopier from GitHub with:
#   - Python venv, backend API (systemd)
#   - Frontend built and served via nginx reverse proxy
#   - Optional SSL via Let's Encrypt
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sammirzagharcheh/PyTelegramClientCopier/main/scripts/deploy-ubuntu.sh | bash
#   # Or: ./scripts/deploy-ubuntu.sh
#
# Prerequisites: Ubuntu 20.04/22.04/24.04, sudo access
#
# Requirements for Let's Encrypt (USE_SSL=true):
#   - Domain name pointing to this VPS (DNS A record)
#   - Ports 80 and 443 open (allow in firewall if using ufw)
#   - CERTBOT_EMAIL for certificate expiry notifications
#
# Env vars: UPDATE_ONLY=true (quick redeploy), NON_INTERACTIVE=true,
#   ADMIN_EMAIL, ADMIN_PASSWORD, API_ID, API_HASH, JWT_SECRET
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration (override via environment or edit below)
# -----------------------------------------------------------------------------
INSTALL_DIR="${INSTALL_DIR:-/opt/telegram-copier}"
APP_USER="${APP_USER:-tgcopier}"
REPO_URL="${REPO_URL:-https://github.com/sammirzagharcheh/PyTelegramClientCopier.git}"
DOMAIN="${DOMAIN:-}"             # e.g. telegram-copier.example.com (optional, for SSL)
USE_SSL="${USE_SSL:-false}"      # Set to 'true' to enable Let's Encrypt
SKIP_DEPS="${SKIP_DEPS:-false}"  # Skip system package install (if already installed)
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}" # Email for Let's Encrypt (default: admin@$DOMAIN)
UPDATE_ONLY="${UPDATE_ONLY:-false}" # Pull, rebuild, restart only (skip deps, env, ssl)
NON_INTERACTIVE="${NON_INTERACTIVE:-false}" # Use env vars only, no prompts

# Example: DOMAIN=copier.example.com USE_SSL=true CERTBOT_EMAIL=you@example.com bash deploy-ubuntu.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${GREEN}==>${NC} $*"; }

die() { log_error "$*"; exit 1; }

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------
check_root() {
  if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
    die "This script needs sudo. Run: sudo bash $0"
  fi
}

get_sudo() {
  if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
    RUN_AS="sudo -u $APP_USER"
  else
    SUDO=""
    RUN_AS="runuser -u $APP_USER --"
  fi
  export SUDO RUN_AS
}

# -----------------------------------------------------------------------------
# Interactive SSL/domain prompts (when env vars not set)
# -----------------------------------------------------------------------------
prompt_ssl_config() {
  [[ "$NON_INTERACTIVE" == "true" ]] && return
  [[ ! -t 0 ]] && return

  echo
  if [[ -z "$DOMAIN" ]]; then
    read -rp "Enter domain (or Enter to skip): " DOMAIN
    DOMAIN="${DOMAIN// /}"
  fi
  if [[ -n "$DOMAIN" ]] && [[ "$USE_SSL" != "true" ]]; then
    read -rp "Enable HTTPS with Let's Encrypt? (y/n): " use_ssl_ans
    [[ "${use_ssl_ans,,}" == "y" || "${use_ssl_ans,,}" == "yes" ]] && USE_SSL=true || USE_SSL=false
  fi
  if [[ "$USE_SSL" == "true" ]] && [[ -z "$CERTBOT_EMAIL" ]]; then
    read -rp "Email for Let's Encrypt: " CERTBOT_EMAIL
  fi
  export DOMAIN USE_SSL CERTBOT_EMAIL
}

# -----------------------------------------------------------------------------
# Install system dependencies
# -----------------------------------------------------------------------------
install_deps() {
  log_step "Installing system dependencies..."
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq \
    curl \
    git \
    nginx \
    build-essential \
    python3-venv \
    python3-dev \
    libffi-dev \
    ca-certificates \
    certbot \
    python3-certbot-nginx \
    software-properties-common

  # Ensure Python 3.11+ (Ubuntu 22.04+ has 3.10/3.12; 20.04 may need deadsnakes)
  local pyver
  pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0")
  if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    log_info "Python $pyver OK"
    export PYTHON_CMD="python3"
  else
    log_warn "Python 3.11+ recommended. Installing from deadsnakes PPA..."
    $SUDO add-apt-repository -y ppa:deadsnakes/ppa
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
    export PYTHON_CMD="python3.11"
  fi

  # Node.js 20.x LTS
  if ! command -v node &>/dev/null || [[ $(node -v 2>/dev/null | cut -d. -f1 | tr -d 'v') -lt 18 ]]; then
    log_info "Installing Node.js 20.x..."
    local _ns="/tmp/nodesource-setup.sh"
    curl -fsSL https://deb.nodesource.com/setup_20.x -o "$_ns"
    $SUDO bash "$_ns"
    rm -f "$_ns"
    $SUDO apt-get install -y -qq nodejs
  fi
  log_info "Node $(node -v) OK"
}

# -----------------------------------------------------------------------------
# Create app user and directory
# -----------------------------------------------------------------------------
setup_app_user() {
  log_step "Creating app user and directory..."
  if ! id "$APP_USER" &>/dev/null; then
    $SUDO useradd -r -s /bin/false -d "$INSTALL_DIR" "$APP_USER" || true
  fi
  $SUDO mkdir -p "$INSTALL_DIR"
  $SUDO chown "$APP_USER:" "$INSTALL_DIR"
}

# -----------------------------------------------------------------------------
# Clone and build
# -----------------------------------------------------------------------------
clone_repo() {
  log_step "Cloning repository..."
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log_info "Repository exists, pulling latest..."
    $RUN_AS git -C "$INSTALL_DIR" fetch origin
    $RUN_AS git -C "$INSTALL_DIR" reset --hard origin/main
  else
    $RUN_AS git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi
}

setup_python() {
  log_step "Setting up Python environment..."
  [[ ! -d "$INSTALL_DIR/.venv" ]] && $RUN_AS bash -c "cd $INSTALL_DIR && ${PYTHON_CMD:-python3} -m venv .venv"
  $RUN_AS bash -c "cd $INSTALL_DIR && .venv/bin/pip install -e ."
}

build_frontend() {
  log_step "Building frontend..."
  $RUN_AS bash -c "cd $INSTALL_DIR/frontend && npm ci && npm run build"
}

# -----------------------------------------------------------------------------
# Write a single .env key=value (add or replace)
# -----------------------------------------------------------------------------
set_env_var() {
  local env_file="$1" key="$2" val="$3"
  val="${val//\\/\\\\}"
  val="${val//&/\\&}"
  if $SUDO grep -q "^${key}=" "$env_file" 2>/dev/null; then
    $SUDO sed -i "s|^${key}=.*|${key}=${val}|" "$env_file"
  else
    $SUDO bash -c "echo \"$key=$val\" >> $env_file"
  fi
}

# -----------------------------------------------------------------------------
# Environment and database
# -----------------------------------------------------------------------------
setup_env() {
  log_step "Configuring .env..."
  local env_file="$INSTALL_DIR/.env"
  if [[ ! -f "$env_file" ]]; then
    if [[ -f "$INSTALL_DIR/.env.example" ]]; then
      $RUN_AS cp "$INSTALL_DIR/.env.example" "$env_file"
    else
      $RUN_AS touch "$env_file"
    fi
  else
    local backup_ts
    backup_ts=$(date +%Y%m%d%H%M%S)
    $SUDO cp "$env_file" "$env_file.backup.$backup_ts"
    log_info "Backed up .env to .env.backup.$backup_ts"
  fi

  local api_id api_hash jwt_secret admin_email admin_pass
  local use_env=false

  if [[ "$NON_INTERACTIVE" == "true" ]] || [[ ! -t 0 ]]; then
    api_id="${API_ID:-}"
    api_hash="${API_HASH:-}"
    jwt_secret="${JWT_SECRET:-}"
    admin_email="${ADMIN_EMAIL:-}"
    admin_pass="${ADMIN_PASSWORD:-}"
    if [[ -n "$api_id" && -n "$api_hash" && -n "$admin_email" && -n "$admin_pass" ]]; then
      use_env=true
    fi
  fi

  if [[ "$use_env" == "true" ]]; then
    [[ -n "$api_id" ]] && set_env_var "$env_file" "API_ID" "$api_id"
    [[ -n "$api_hash" ]] && set_env_var "$env_file" "API_HASH" "$api_hash"
    if [[ -z "$jwt_secret" ]]; then
      jwt_secret=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom 2>/dev/null | xxd -p)
      [[ -n "$jwt_secret" ]] && set_env_var "$env_file" "JWT_SECRET" "$jwt_secret" && log_info "Generated JWT_SECRET"
    else
      set_env_var "$env_file" "JWT_SECRET" "$jwt_secret"
    fi
    $SUDO chown "$APP_USER:" "$env_file"
    log_info "Initializing database and creating admin..."
    $RUN_AS bash -c "cd $INSTALL_DIR && .venv/bin/tg-copier db init-db"
    $RUN_AS bash -c "cd $INSTALL_DIR && .venv/bin/tg-copier db create-admin \"$admin_email\" \"$admin_pass\""
    return
  fi

  if [[ -t 0 ]]; then
    echo
    read -rp "API_ID (from my.telegram.org): " api_id
    read -rp "API_HASH: " api_hash
    read -rp "JWT_SECRET (or Enter to auto-generate): " jwt_secret
    read -rp "Admin email: " admin_email
    read -sp "Admin password: " admin_pass
    echo

    [[ -n "$api_id" ]] && set_env_var "$env_file" "API_ID" "$api_id"
    [[ -n "$api_hash" ]] && set_env_var "$env_file" "API_HASH" "$api_hash"
    if [[ -z "$jwt_secret" ]]; then
      jwt_secret=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom 2>/dev/null | xxd -p)
      [[ -n "$jwt_secret" ]] && set_env_var "$env_file" "JWT_SECRET" "$jwt_secret" && log_info "Generated JWT_SECRET"
    else
      [[ -n "$jwt_secret" ]] && set_env_var "$env_file" "JWT_SECRET" "$jwt_secret"
    fi

    $SUDO chown "$APP_USER:" "$env_file"

    if [[ -n "$admin_email" && -n "$admin_pass" ]]; then
      log_info "Initializing database and creating admin..."
      $RUN_AS bash -c "cd $INSTALL_DIR && .venv/bin/tg-copier db init-db"
      $RUN_AS bash -c "cd $INSTALL_DIR && .venv/bin/tg-copier db create-admin \"$admin_email\" \"$admin_pass\""
    fi
  else
    log_warn "Non-interactive: configure $env_file manually, then run:"
    echo "  cd $INSTALL_DIR && .venv/bin/tg-copier db init-db"
    echo "  cd $INSTALL_DIR && .venv/bin/tg-copier db create-admin your@email.com yourpassword"
  fi
}

# -----------------------------------------------------------------------------
# Production readiness check
# -----------------------------------------------------------------------------
check_production_ready() {
  local env_file="$INSTALL_DIR/.env"
  if [[ -f "$env_file" ]] && $SUDO grep -q "JWT_SECRET=change-me-in-production" "$env_file" 2>/dev/null; then
    log_warn "JWT_SECRET is still the default 'change-me-in-production'. Set a strong secret in $env_file"
  fi
}

# -----------------------------------------------------------------------------
# Fix permissions for all files and folders
# -----------------------------------------------------------------------------
fix_permissions() {
  log_step "Setting file and folder permissions..."
  $SUDO chown -R "$APP_USER:" "$INSTALL_DIR"

  # .env and backups: owner read/write only (secrets)
  [[ -f "$INSTALL_DIR/.env" ]] && $SUDO chmod 600 "$INSTALL_DIR/.env"
  for f in "$INSTALL_DIR"/.env.backup.*; do
    [[ -f "$f" ]] && $SUDO chmod 600 "$f"
  done

  # data/ and data/sessions/: app user only (DB, Telegram sessions)
  $SUDO mkdir -p "$INSTALL_DIR/data/sessions"
  $SUDO chmod 700 "$INSTALL_DIR/data"
  $SUDO chmod 700 "$INSTALL_DIR/data/sessions"
  [[ -f "$INSTALL_DIR/data/app.db" ]] && $SUDO chmod 600 "$INSTALL_DIR/data/app.db"

  # frontend/dist: nginx (www-data) needs read access for static files
  if [[ -d "$INSTALL_DIR/frontend/dist" ]]; then
    if id www-data &>/dev/null; then
      $SUDO chown -R "$APP_USER:www-data" "$INSTALL_DIR/frontend/dist"
      $SUDO chmod -R 750 "$INSTALL_DIR/frontend/dist"
    else
      $SUDO chmod -R 755 "$INSTALL_DIR/frontend/dist"
    fi
  fi

  # .venv: ensure dirs executable
  [[ -d "$INSTALL_DIR/.venv" ]] && $SUDO chmod -R u+rX "$INSTALL_DIR/.venv"

  # Source and config: readable by app user
  [[ -d "$INSTALL_DIR/src" ]] && $SUDO chmod -R u+rX "$INSTALL_DIR/src"

  log_info "Permissions set: .env 600, data 700, frontend/dist 750 (or 755)"
}

# -----------------------------------------------------------------------------
# Systemd service
# -----------------------------------------------------------------------------
install_systemd() {
  log_step "Installing systemd service..."
  $SUDO tee /etc/systemd/system/telegram-copier.service >/dev/null <<EOF
[Unit]
Description=Telegram Client Copier API
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/.venv/bin/tg-copier api --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable telegram-copier
  $SUDO systemctl restart telegram-copier
  log_info "Service telegram-copier enabled and started"
}

# -----------------------------------------------------------------------------
# Nginx reverse proxy
# -----------------------------------------------------------------------------
install_nginx() {
  log_step "Configuring nginx..."
  local server_name="${DOMAIN:-_}"

  $SUDO tee /etc/nginx/sites-available/telegram-copier >/dev/null <<EOF
server {
    listen 80;
    server_name $server_name;

    root $INSTALL_DIR/frontend/dist;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
  $SUDO ln -sf /etc/nginx/sites-available/telegram-copier /etc/nginx/sites-enabled/
  $SUDO rm -f /etc/nginx/sites-enabled/default
  $SUDO nginx -t && $SUDO systemctl reload nginx
  log_info "Nginx configured and reloaded"
}

# -----------------------------------------------------------------------------
# Firewall (ufw)
# -----------------------------------------------------------------------------
setup_firewall() {
  if ! command -v ufw &>/dev/null; then return; fi
  if $SUDO ufw status 2>/dev/null | grep -q "Status: active"; then return; fi
  if [[ "$NON_INTERACTIVE" == "true" ]]; then return; fi
  if [[ -t 0 ]]; then
    read -rp "Allow Nginx (80/443) and enable ufw? (y/n): " ans
    if [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]; then
      $SUDO ufw allow 'Nginx Full'
      $SUDO ufw --force enable
      log_info "ufw enabled, Nginx ports allowed"
    fi
  fi
}

# -----------------------------------------------------------------------------
# Pre-check: domain DNS points to this server
# -----------------------------------------------------------------------------
check_dns_points_here() {
  [[ "$USE_SSL" != "true" || -z "$DOMAIN" ]] && return
  local domain_ip server_ip
  domain_ip=$(dig +short "$DOMAIN" 2>/dev/null | head -1)
  [[ -z "$domain_ip" ]] && domain_ip=$(getent hosts "$DOMAIN" 2>/dev/null | awk '{print $1}')
  [[ -z "$domain_ip" ]] && domain_ip=$(host "$DOMAIN" 2>/dev/null | grep "has address" | awk '{print $NF}')
  [[ -z "$domain_ip" ]] && return
  server_ip=$(curl -sf --max-time 5 https://ifconfig.me 2>/dev/null || curl -sf --max-time 5 https://icanhazip.com 2>/dev/null)
  [[ -z "$server_ip" ]] && return
  if [[ "$domain_ip" != "$server_ip" ]]; then
    log_warn "Domain $DOMAIN resolves to $domain_ip, this server is $server_ip. Certbot may fail."
    if [[ -t 0 ]] && [[ "$NON_INTERACTIVE" != "true" ]]; then
      read -rp "Continue anyway? (y/n): " ans
      [[ "${ans,,}" != "y" && "${ans,,}" != "yes" ]] && die "Aborted."
    fi
  fi
}

# -----------------------------------------------------------------------------
# SSL (Let's Encrypt)
# -----------------------------------------------------------------------------
setup_ssl() {
  if [[ "$USE_SSL" != "true" || -z "$DOMAIN" ]]; then
    return
  fi
  check_dns_points_here
  log_step "Obtaining SSL certificate (Let's Encrypt)..."
  log_info "Requirements: Domain $DOMAIN must point to this VPS, ports 80/443 open."
  local email="${CERTBOT_EMAIL:-admin@$DOMAIN}"
  if ! $SUDO certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect \
    --email "${email:-admin@example.com}" 2>&1; then
    log_warn "Certbot failed. Debug: sudo certbot certificates; sudo journalctl -u nginx -n 50"
  fi
}

# -----------------------------------------------------------------------------
# Post-deploy health check
# -----------------------------------------------------------------------------
check_health() {
  sleep 2
  if curl -sf --max-time 5 http://127.0.0.1:8000/health &>/dev/null; then
    log_info "API health check OK"
  else
    log_warn "API may not be ready; check: sudo systemctl status telegram-copier"
  fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
  echo "Telegram Client Copier - Ubuntu Deployment"
  echo "=========================================="
  check_root
  get_sudo
  prompt_ssl_config

  if [[ "$UPDATE_ONLY" == "true" ]]; then
    [[ ! -d "$INSTALL_DIR/.venv" ]] && die "UPDATE_ONLY requires existing install at $INSTALL_DIR"
    get_sudo
    clone_repo
    setup_python
    build_frontend
    fix_permissions
    install_systemd
    $SUDO nginx -t 2>/dev/null && $SUDO systemctl reload nginx
    log_step "Update complete. Restarted services."
    return
  fi

  [[ "$SKIP_DEPS" != "true" ]] && install_deps
  setup_app_user
  clone_repo
  setup_python
  build_frontend
  setup_env
  check_production_ready
  fix_permissions
  install_systemd
  install_nginx
  setup_firewall
  setup_ssl
  check_health

  log_step "Done!"
  echo "  App dir:    $INSTALL_DIR"
  echo "  Service:    sudo systemctl status telegram-copier"
  echo "  Nginx:      sudo systemctl status nginx"
  if [[ -n "$DOMAIN" ]] && [[ "$USE_SSL" == "true" ]]; then
    echo "  URL:        https://$DOMAIN"
  elif [[ -n "$DOMAIN" ]]; then
    echo "  URL:        http://$DOMAIN"
  else
    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo "  URL:        http://${ip:-localhost}"
    echo "  Tip:       DOMAIN=copier.example.com USE_SSL=true for HTTPS"
  fi
  echo "  Firewall:  sudo ufw allow 'Nginx Full' && sudo ufw enable  # if using ufw"
  if [[ "$USE_SSL" == "true" && -n "$DOMAIN" ]]; then
    echo ""
    echo "  SSL: Certbot auto-renews. Verify: sudo certbot renew --dry-run"
  fi
}

main "$@"
