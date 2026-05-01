#!/usr/bin/env bash
# Run on the VPS (after SSH) as a user who can sudo. Does not print DB passwords.
# Usage: sudo bash scripts/diagnose-prod-login.sh
#    or: bash /opt/telegram-copier/scripts/diagnose-prod-login.sh

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/telegram-copier}"
APP_USER="${APP_USER:-tgcopier}"

echo "=== systemd: telegram-copier ==="
systemctl status telegram-copier --no-pager -l || true

echo ""
echo "=== health (local) ==="
curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/health || echo "curl failed"

echo ""
echo "=== git tip ==="
if [[ -d "$INSTALL_DIR/.git" ]]; then
  sudo -u "$APP_USER" git -C "$INSTALL_DIR" log -1 --oneline
else
  echo "No git at $INSTALL_DIR"
fi

echo ""
echo "=== tg-copier config (no secrets) ==="
sudo -u "$APP_USER" bash -lc "cd $INSTALL_DIR && set -a && [[ -f .env ]] && . ./.env && set +a && .venv/bin/tg-copier db show-config"

echo ""
echo "=== users (safe fields; bcrypt_ok must be true for password login) ==="
sudo -u "$APP_USER" bash -lc "cd $INSTALL_DIR && set -a && [[ -f .env ]] && . ./.env && set +a && .venv/bin/tg-copier db inspect-auth-users"

echo ""
echo "=== recent app logs (errors) ==="
journalctl -u telegram-copier -n 40 --no-pager 2>/dev/null || true
