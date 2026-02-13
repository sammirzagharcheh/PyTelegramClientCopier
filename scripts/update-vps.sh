#!/usr/bin/env bash
# =============================================================================
# Telegram Client Copier - VPS Update Script
# =============================================================================
# Updates an existing deployment: pull latest, reinstall deps, rebuild frontend,
# restart services. Run on the VPS after SSH.
#
# Usage:
#   sudo bash scripts/update-vps.sh
#   # Or from any directory:
#   sudo bash /opt/telegram-copier/scripts/update-vps.sh
#
# Env vars: INSTALL_DIR (default /opt/telegram-copier), APP_USER (default tgcopier)
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/telegram-copier}"
APP_USER="${APP_USER:-tgcopier}"

if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
  echo "This script needs sudo. Run: sudo bash $0"
  exit 1
fi

SUDO=""
RUN_AS=""
if [[ $EUID -ne 0 ]]; then
  SUDO="sudo"
  RUN_AS="sudo -u $APP_USER"
else
  RUN_AS="runuser -u $APP_USER --"
fi

[[ ! -d "$INSTALL_DIR/.venv" ]] && { echo "No existing install at $INSTALL_DIR. Run deploy-ubuntu.sh first."; exit 1; }

echo "==> Pulling latest code..."
$RUN_AS bash -c "cd $INSTALL_DIR && git fetch origin && git reset --hard origin/main"

echo "==> Reinstalling Python dependencies..."
$RUN_AS bash -c "cd $INSTALL_DIR && .venv/bin/pip install -e ."

echo "==> Building frontend..."
$RUN_AS bash -c "cd $INSTALL_DIR/frontend && npm ci && npm run build"

echo "==> Fixing permissions..."
$SUDO chown -R "$APP_USER:" "$INSTALL_DIR"
if [[ -d "$INSTALL_DIR/frontend/dist" ]]; then
  if id www-data &>/dev/null; then
    $SUDO chown -R "$APP_USER:www-data" "$INSTALL_DIR/frontend/dist"
    $SUDO chmod -R 750 "$INSTALL_DIR/frontend/dist"
  else
    $SUDO chmod -R 755 "$INSTALL_DIR/frontend/dist"
  fi
fi

echo "==> Restarting telegram-copier service..."
$SUDO systemctl daemon-reload
$SUDO systemctl restart telegram-copier

if $SUDO nginx -t 2>/dev/null; then
  $SUDO systemctl reload nginx
  echo "==> Nginx reloaded."
fi

echo ""
echo "Update complete. Verify:"
echo "  sudo systemctl status telegram-copier"
echo "  curl -s http://127.0.0.1:8000/health"
echo ""
