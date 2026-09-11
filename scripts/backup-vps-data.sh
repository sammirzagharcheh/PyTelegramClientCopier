#!/usr/bin/env bash
# =============================================================================
# Telegram Client Copier - VPS data backup
# =============================================================================
# Snapshots SQLite, sessions, media, and .env before updates.
#
# Usage:
#   sudo bash scripts/backup-vps-data.sh
#   INSTALL_DIR=/opt/telegram-copier bash scripts/backup-vps-data.sh
#   SKIP_BACKUP=1 bash scripts/backup-vps-data.sh   # no-op success
#   BACKUP_MONGO=1 ...                              # optional mongodump
#
# Env:
#   INSTALL_DIR   default /opt/telegram-copier
#   BACKUP_DIR    default $INSTALL_DIR/backups
#   BACKUP_KEEP   default 5 (number of pre-update-* dirs to retain)
#   SKIP_BACKUP   set to 1 to skip
#   BACKUP_MONGO  set to 1 to attempt mongodump when mongo tools exist
# =============================================================================

set -euo pipefail

tgc_env_get() {
  # Read KEY=value from .env without sourcing (no export side effects).
  local env_file="$1" key="$2"
  [[ -f "$env_file" ]] || return 0
  local line
  line="$(grep -E "^[[:space:]]*${key}=" "$env_file" | tail -n1 || true)"
  [[ -n "$line" ]] || return 0
  line="${line#*=}"
  line="${line%%$'\r'}"
  line="${line#\"}"
  line="${line%\"}"
  line="${line#\'}"
  line="${line%\'}"
  printf '%s' "$line"
}

tgc_backup_vps_data() {
  local install_dir="${INSTALL_DIR:-/opt/telegram-copier}"
  local backup_root="${BACKUP_DIR:-$install_dir/backups}"
  local keep="${BACKUP_KEEP:-5}"
  local env_file="$install_dir/.env"

  if [[ "${SKIP_BACKUP:-0}" == "1" ]]; then
    echo "==> SKIP_BACKUP=1 — skipping data backup."
    return 0
  fi

  local sqlite_path sessions_dir media_dir
  sqlite_path="$(tgc_env_get "$env_file" SQLITE_PATH)"
  sessions_dir="$(tgc_env_get "$env_file" SESSIONS_DIR)"
  media_dir="$(tgc_env_get "$env_file" MEDIA_ASSETS_DIR)"

  [[ -n "$sqlite_path" ]] || sqlite_path="$install_dir/data/app.db"
  [[ -n "$sessions_dir" ]] || sessions_dir="$install_dir/data/sessions"
  [[ -n "$media_dir" ]] || media_dir="$install_dir/data/media_assets"

  # Prefer absolute paths; if relative, resolve under install_dir.
  [[ "$sqlite_path" = /* ]] || sqlite_path="$install_dir/$sqlite_path"
  [[ "$sessions_dir" = /* ]] || sessions_dir="$install_dir/$sessions_dir"
  [[ "$media_dir" = /* ]] || media_dir="$install_dir/$media_dir"

  local stamp
  # Include pid + random so same-second runs (tests / rapid updates) do not collide.
  stamp="$(date +%Y%m%d-%H%M%S)-$$-${RANDOM:-0}"
  local dest="$backup_root/pre-update-$stamp"
  if [[ -e "$dest" ]]; then
    echo "ERROR: backup destination already exists: $dest" >&2
    return 1
  fi

  echo "==> Backing up durable data to $dest ..."
  mkdir -p "$dest"

  if [[ -f "$sqlite_path" ]]; then
    mkdir -p "$dest/sqlite"
    cp -a "$sqlite_path" "$dest/sqlite/$(basename "$sqlite_path")"
    # SQLite sidecars when present
    [[ -f "${sqlite_path}-wal" ]] && cp -a "${sqlite_path}-wal" "$dest/sqlite/" || true
    [[ -f "${sqlite_path}-shm" ]] && cp -a "${sqlite_path}-shm" "$dest/sqlite/" || true
  else
    echo "    (no SQLite file at $sqlite_path)"
  fi

  if [[ -d "$sessions_dir" ]]; then
    mkdir -p "$dest/sessions"
    cp -a "$sessions_dir/." "$dest/sessions/" 2>/dev/null || cp -a "$sessions_dir" "$dest/sessions-dir"
  else
    echo "    (no sessions dir at $sessions_dir)"
  fi

  if [[ -d "$media_dir" ]]; then
    mkdir -p "$dest/media_assets"
    cp -a "$media_dir/." "$dest/media_assets/" 2>/dev/null || true
  else
    echo "    (no media_assets dir at $media_dir)"
  fi

  if [[ -f "$env_file" ]]; then
    cp -a "$env_file" "$dest/dotenv.env"
    chmod 600 "$dest/dotenv.env" 2>/dev/null || true
  else
    echo "    (no .env at $env_file)"
  fi

  # Also snapshot whole data/ when it exists (covers worker logs under data/, etc.)
  if [[ -d "$install_dir/data" ]]; then
    mkdir -p "$dest/data_tree"
    cp -a "$install_dir/data/." "$dest/data_tree/" 2>/dev/null || true
  fi

  if [[ "${BACKUP_MONGO:-0}" == "1" ]]; then
    local mongo_uri mongo_db
    mongo_uri="$(tgc_env_get "$env_file" MONGO_URI)"
    mongo_db="$(tgc_env_get "$env_file" MONGO_DB)"
    if command -v mongodump >/dev/null 2>&1; then
      mkdir -p "$dest/mongo"
      local dump_args=()
      [[ -n "$mongo_uri" ]] && dump_args+=(--uri="$mongo_uri")
      [[ -n "$mongo_db" ]] && dump_args+=(--db="$mongo_db")
      if mongodump "${dump_args[@]}" --out="$dest/mongo" 2>/dev/null; then
        echo "    Mongo dump written under $dest/mongo"
      else
        echo "    WARNING: mongodump failed (continuing; SQLite/sessions backed up)."
      fi
    else
      echo "    WARNING: BACKUP_MONGO=1 but mongodump not found; skipping Mongo."
    fi
  fi

  chmod -R go-rwx "$dest" 2>/dev/null || true
  echo "==> Backup complete: $dest"

  tgc_prune_backups "$backup_root" "$keep"
}

tgc_prune_backups() {
  local backup_root="$1"
  local keep="$2"
  [[ -d "$backup_root" ]] || return 0
  local i=0
  local dir
  # Newest first; delete after the first $keep entries.
  while IFS= read -r dir; do
    [[ -n "$dir" ]] || continue
    i=$((i + 1))
    if (( i > keep )); then
      echo "==> Pruning old backup: $dir"
      rm -rf "$dir"
    fi
  done < <(ls -1dt "$backup_root"/pre-update-* 2>/dev/null || true)
}

# Run when executed (not when sourced for tests).
if [[ "${BASH_SOURCE[0]:-}" == "${0}" ]]; then
  tgc_backup_vps_data
fi
