#!/usr/bin/env bash
set -euo pipefail

repo_under_test="$(cd "$(dirname "$0")/.." && pwd -P)"
fixture="$(mktemp -d "${TMPDIR:-/tmp}/ernos-rights-restore.XXXXXX")"
fixture="$(cd "$fixture" && pwd -P)"
cleanup() {
  if [[ -n "${fixture:-}" && "$fixture" == "${TMPDIR:-/tmp}/ernos-rights-restore."* ]]; then
    rm -rf -- "$fixture"
  fi
}
trap cleanup EXIT

fake_repo="$fixture/repo"
fake_data="$fixture/data"
change_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
bundle_id="factory_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
bundle_root="$fake_repo/config/rights/recovery/$bundle_id"
mkdir -p "$bundle_root/files" "$fake_repo/config/sessions" "$fake_data"

printf '%s' 'restored-session-exact-bytes' > "$bundle_root/files/0"
sqlite3 "$bundle_root/files/1" "CREATE TABLE restored_state (value TEXT NOT NULL); INSERT INTO restored_state VALUES ('exact');"
session_hash="$(shasum -a 256 "$bundle_root/files/0" | awk '{print $1}')"
db_hash="$(shasum -a 256 "$bundle_root/files/1" | awk '{print $1}')"
printf '%s\t%s\t%s\n' "$session_hash" 'files/0' "$fake_repo/config/sessions/default.json" > "$bundle_root/restore.tsv"
printf '%s\t%s\t%s\n' "$db_hash" 'files/1' "$fake_data/node.db" >> "$bundle_root/restore.tsv"
state_hash="$(shasum -a 256 "$bundle_root/restore.tsv" | awk '{print $1}')"

printf '%s' 'post-reset-state-that-must-be-cleared' > "$fake_repo/config/sessions/stale.json"
printf '%s' 'stale-wal-must-not-be-replayed' > "$fake_data/node.db-wal"
printf '%s' 'stale-shm-must-not-survive' > "$fake_data/node.db-shm"
printf '%s\n' \
  "bundle_id=$bundle_id" \
  "change_id=$change_id" \
  "root=$bundle_root" \
  "pre_state_hash=$state_hash" > "$fake_repo/config/rights/pending_factory_restore.txt"

ERNOS_DATA_DIR="$fake_data" "$repo_under_test/scripts/rights_restore_pending.sh" "$fake_repo"

[[ ! -e "$fake_repo/config/sessions/stale.json" ]]
[[ "$(shasum -a 256 "$fake_repo/config/sessions/default.json" | awk '{print $1}')" == "$session_hash" ]]
[[ "$(shasum -a 256 "$fake_data/node.db" | awk '{print $1}')" == "$db_hash" ]]
[[ "$(sqlite3 "$fake_data/node.db" 'PRAGMA integrity_check;')" == "ok" ]]
[[ ! -e "$fake_data/node.db-wal" && ! -e "$fake_data/node.db-shm" ]]
[[ ! -e "$fake_repo/config/rights/pending_factory_restore.txt" ]]
grep -Fqx "restored_hash=$state_hash" "$fake_repo/config/rights/restored_factory_result.txt"
printf '%s\n' 'PASS: staged factory recovery restored exact bytes and cleared stale managed state'
