#!/usr/bin/env bash
# Push the application to the server. Source of truth is this working tree.
#
#     deploy/sync.sh root@74.91.31.50
#
# SAIRA_SSH_KEY picks the private key when it is not one of ssh's defaults.
#
# Sends only what the server runs. Secrets are excluded on purpose: the server
# keeps its own .env and its own master key, generated there, so a copy of this
# laptop is never enough to read anyone's stored conversations.
set -euo pipefail

TARGET="${1:?usage: sync.sh user@host [path]}"
REMOTE_DIR="${2:-/opt/saira}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new)
[ -n "${SAIRA_SSH_KEY:-}" ] && SSH_OPTS+=(-i "$SAIRA_SSH_KEY")

ssh "${SSH_OPTS[@]}" "$TARGET" "mkdir -p $REMOTE_DIR"
rsync -az --delete --stats -e "ssh ${SSH_OPTS[*]}" \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'web/node_modules/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude '.master.key' \
  --exclude '*.enc' \
  --exclude '.*.key' \
  --exclude 'saira.db*' \
  --exclude '*.log' \
  --exclude 'data/' \
  --exclude 'YTBlock/' \
  --exclude 'hydrate-buddy/' \
  --exclude 'hydrate-buddy-app/' \
  "$HERE/" "$TARGET:$REMOTE_DIR/"

echo "Synced to $TARGET:$REMOTE_DIR"
