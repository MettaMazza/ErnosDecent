#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-}"
if [[ -z "$repo_root" || ! -d "$repo_root/config/rights" ]]; then
  echo "[RIGHTS RESTORE] invalid repository root" >&2
  exit 1
fi
repo_root="$(cd "$repo_root" && pwd -P)"
marker="$repo_root/config/rights/pending_factory_restore.txt"
[[ -f "$marker" ]] || exit 0

read_field() {
  local key="$1"
  sed -n "s/^${key}=//p" "$marker" | head -n 1
}

bundle_id="$(read_field bundle_id)"
change_id="$(read_field change_id)"
bundle_root="$(read_field root)"
expected_state="$(read_field pre_state_hash)"

[[ "$bundle_id" =~ ^factory_[0-9a-f]{64}$ ]] || { echo "[RIGHTS RESTORE] invalid bundle id" >&2; exit 1; }
[[ "$change_id" =~ ^[0-9a-f]{64}$ ]] || { echo "[RIGHTS RESTORE] invalid change id" >&2; exit 1; }
[[ "$expected_state" =~ ^[0-9a-f]{64}$ ]] || { echo "[RIGHTS RESTORE] invalid pre-state hash" >&2; exit 1; }
expected_root="$repo_root/config/rights/recovery/$bundle_id"
[[ "$bundle_root" == "$expected_root" && -d "$bundle_root/files" ]] || { echo "[RIGHTS RESTORE] bundle path escaped the recovery root" >&2; exit 1; }
restore_map="$bundle_root/restore.tsv"
[[ -f "$restore_map" ]] || { echo "[RIGHTS RESTORE] restore map missing" >&2; exit 1; }
[[ "$(shasum -a 256 "$restore_map" | awk '{print $1}')" == "$expected_state" ]] || { echo "[RIGHTS RESTORE] pre-state manifest hash mismatch" >&2; exit 1; }

data_root="${ERNOS_DATA_DIR:-$HOME/.ernosdecent}"
data_root="$(cd "$data_root" && pwd -P)"
allowed_destination() {
  local destination="$1"
  case "$destination" in
    "$repo_root/config/sessions"/*|"$repo_root/config/workspaces"/*|"$repo_root/config/learning"/*|"$repo_root/config/uploads"/*|"$repo_root/config/changelog"/*|"$repo_root/config/adapters"/*|"$repo_root/config/agent_memory.json"|"$repo_root/config/linked_projects.txt"|"$repo_root/config/agent_persona.txt"|"$data_root/knowledge"/*|"$data_root/discord-images"/*|"$data_root/visual-comparisons"/*|"$data_root/agent_self_sections.json"|"$data_root/active_persona.txt"|"$data_root/node.db")
      return 0
      ;;
  esac
  return 1
}

while IFS=$'\t' read -r expected rel destination; do
  [[ -z "$expected" ]] && continue
  [[ "$expected" =~ ^[0-9a-f]{64}$ && "$rel" =~ ^files/[0-9]+$ ]] || { echo "[RIGHTS RESTORE] malformed restore entry" >&2; exit 1; }
  allowed_destination "$destination" || { echo "[RIGHTS RESTORE] refused destination: $destination" >&2; exit 1; }
  source_file="$bundle_root/$rel"
  [[ -f "$source_file" ]] || { echo "[RIGHTS RESTORE] missing payload: $rel" >&2; exit 1; }
  [[ "$(shasum -a 256 "$source_file" | awk '{print $1}')" == "$expected" ]] || { echo "[RIGHTS RESTORE] payload hash mismatch: $rel" >&2; exit 1; }
done < "$restore_map"

# The daemon is not running when this hook executes. Clear only factory-managed
# agent-state targets so files created after reset cannot make the restored state
# ambiguously differ from the recorded pre-state.
for target in \
  "$repo_root/config/sessions" \
  "$repo_root/config/workspaces" \
  "$repo_root/config/learning" \
  "$repo_root/config/uploads" \
  "$repo_root/config/changelog" \
  "$repo_root/config/adapters" \
  "$data_root/knowledge" \
  "$data_root/discord-images" \
  "$data_root/visual-comparisons"; do
  if [[ -e "$target" ]]; then
    rm -rf -- "$target"
  fi
  mkdir -p -- "$target"
done
rm -f -- "$repo_root/config/agent_memory.json" "$repo_root/config/linked_projects.txt" "$data_root/agent_self_sections.json" "$data_root/active_persona.txt"

while IFS=$'\t' read -r expected rel destination; do
  [[ -z "$expected" ]] && continue
  source_file="$bundle_root/$rel"
  mkdir -p -- "$(dirname "$destination")"
  # A SQLite snapshot is not restored by replacing only node.db while old WAL/SHM
  # sidecars remain. SQLite will replay that stale WAL into the restored main file,
  # producing a state that matches neither snapshot and can fail ledger integrity.
  if [[ "$destination" == "$data_root/node.db" ]]; then
    rm -f -- "$destination-wal" "$destination-shm"
  fi
  cp -p -- "$source_file" "$destination"
  [[ "$(shasum -a 256 "$destination" | awk '{print $1}')" == "$expected" ]] || { echo "[RIGHTS RESTORE] restored hash mismatch: $destination" >&2; exit 1; }
done < "$restore_map"

# Keep the restored SQLite main file authoritative through daemon startup. No
# sidecar belongs to a VACUUM INTO snapshot, and their absence is part of the exact
# recovery boundary.
rm -f -- "$data_root/node.db-wal" "$data_root/node.db-shm"
if command -v sqlite3 >/dev/null 2>&1; then
  [[ "$(sqlite3 "$data_root/node.db" 'PRAGMA integrity_check;' 2>/dev/null)" == "ok" ]] || { echo "[RIGHTS RESTORE] restored SQLite snapshot failed integrity_check" >&2; exit 1; }
fi

result="$repo_root/config/rights/restored_factory_result.txt"
{
  printf 'bundle_id=%s\n' "$bundle_id"
  printf 'change_id=%s\n' "$change_id"
  printf 'restored_hash=%s\n' "$expected_state"
} > "$result"
chmod 600 "$result"
rm -f -- "$marker"
echo "[RIGHTS RESTORE] exact pre-state restored and hash-verified: $expected_state"
