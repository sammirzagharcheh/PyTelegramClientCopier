#!/usr/bin/env bash
# =============================================================================
# Telegram Client Copier - prune old VPS backups
# =============================================================================
# Keeps the newest N pre-update-* snapshots under BACKUP_DIR; deletes the rest.
#
# Usage:
#   sudo bash scripts/prune-vps-backups.sh
#   DRY_RUN=1 bash scripts/prune-vps-backups.sh
#   BACKUP_KEEP=3 bash scripts/prune-vps-backups.sh
#
# Keep count (default 10): env BACKUP_KEEP > backup.conf > .env > 10
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=vps-backup-lib.sh
source "$SCRIPT_DIR/vps-backup-lib.sh"

tgc_prune_vps_backups_main() {
  local install_dir="${INSTALL_DIR:-/opt/telegram-copier}"
  local backup_root
  backup_root="$(tgc_resolve_backup_dir "$install_dir")"
  local keep
  keep="$(tgc_resolve_backup_keep "$install_dir")"
  local dry_run="${DRY_RUN:-0}"

  echo "==> Pruning backups under $backup_root (keep=$keep dry_run=$dry_run)"
  tgc_prune_backups "$backup_root" "$keep" "$dry_run"
}

if [[ "${BASH_SOURCE[0]:-}" == "${0}" ]]; then
  tgc_prune_vps_backups_main
fi
