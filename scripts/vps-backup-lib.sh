#!/usr/bin/env bash
# Shared helpers for VPS backup / prune scripts. Source only; do not execute.
# shellcheck shell=bash

tgc_env_get() {
  # Read KEY=value from a conf/.env file without sourcing.
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

tgc_validate_backup_keep() {
  local keep="$1"
  if ! [[ "$keep" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: BACKUP_KEEP must be an integer >= 1 (got: '${keep}')" >&2
    return 1
  fi
  return 0
}

# Resolution: env BACKUP_KEEP (if set) > backup.conf > .env > default 10
tgc_resolve_backup_keep() {
  local install_dir="$1"
  if [[ "${BACKUP_KEEP+set}" == "set" ]]; then
    printf '%s' "$BACKUP_KEEP"
    return 0
  fi
  local conf="${BACKUP_CONF:-$install_dir/backup.conf}"
  local v
  v="$(tgc_env_get "$conf" BACKUP_KEEP)"
  if [[ -n "$v" ]]; then
    printf '%s' "$v"
    return 0
  fi
  v="$(tgc_env_get "$install_dir/.env" BACKUP_KEEP)"
  if [[ -n "$v" ]]; then
    printf '%s' "$v"
    return 0
  fi
  printf '10'
}

tgc_resolve_backup_dir() {
  local install_dir="$1"
  if [[ "${BACKUP_DIR+set}" == "set" && -n "$BACKUP_DIR" ]]; then
    printf '%s' "$BACKUP_DIR"
    return 0
  fi
  local conf="${BACKUP_CONF:-$install_dir/backup.conf}"
  local v
  v="$(tgc_env_get "$conf" BACKUP_DIR)"
  if [[ -n "$v" ]]; then
    [[ "$v" = /* ]] || v="$install_dir/$v"
    printf '%s' "$v"
    return 0
  fi
  v="$(tgc_env_get "$install_dir/.env" BACKUP_DIR)"
  if [[ -n "$v" ]]; then
    [[ "$v" = /* ]] || v="$install_dir/$v"
    printf '%s' "$v"
    return 0
  fi
  printf '%s' "$install_dir/backups"
}

tgc_prune_backups() {
  local backup_root="$1"
  local keep="$2"
  local dry_run="${3:-0}"

  tgc_validate_backup_keep "$keep" || return 1

  if [[ ! -d "$backup_root" ]]; then
    echo "==> No backup directory at $backup_root (nothing to prune)."
    return 0
  fi

  local i=0
  local dir
  local removed=0
  # Newest first; delete after the first $keep entries.
  while IFS= read -r dir; do
    [[ -n "$dir" ]] || continue
    i=$((i + 1))
    if (( i > keep )); then
      if [[ "$dry_run" == "1" ]]; then
        echo "==> DRY_RUN would prune: $dir"
      else
        echo "==> Pruning old backup: $dir"
        rm -rf "$dir"
      fi
      removed=$((removed + 1))
    fi
  done < <(ls -1dt "$backup_root"/pre-update-* 2>/dev/null || true)

  local kept=$i
  if (( kept > keep )); then
    kept=$keep
  fi
  echo "==> Prune summary: keep=$keep retained=$kept removed=$removed dry_run=$dry_run root=$backup_root"
}
