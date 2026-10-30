#!/usr/bin/env bash
# Provision SAIRA on a fresh Ubuntu 24.04 host. Run as root, on the server:
#
#     bash provision.sh saira.sainith.in you@example.com
#
# Safe to re-run: every step checks before it acts. The second argument is the
# address Let's Encrypt uses for expiry warnings.
set -euo pipefail

DOMAIN="${1:?usage: provision.sh <domain> <admin-email>}"
ADMIN_EMAIL="${2:?usage: provision.sh <domain> <admin-email>}"
APP_DIR=/opt/saira
APP_USER=saira

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

say "System packages"
export DEBIAN_FRONTEND=noninteractive

# Some Ubuntu images ship with only the release pocket enabled. That machine
# gets no security updates, and its installed packages end up newer than
# anything apt can still see, so python3.12-venv and build-essential refuse to
# resolve. Add the missing pockets before anything else depends on them.
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
for f in /etc/apt/sources.list.d/*.sources; do
  [ -e "$f" ] || continue
  if grep -q "^Suites: $CODENAME\$" "$f"; then
    cp -n "$f" "$f.bak" 2>/dev/null || true
    sed -i "s/^Suites: $CODENAME\$/Suites: $CODENAME $CODENAME-updates $CODENAME-security $CODENAME-backports/" "$f"
    echo "   Enabled $CODENAME-updates and -security in $(basename "$f")"
  fi
done

apt-get update -qq
# Versioned, not the python3-* metapackages: those pin an exact python3
# version and break the moment the installed one has moved on.
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
apt-get install -y -qq \
  "python$PYV-venv" "python$PYV-dev" build-essential pkg-config git curl \
  ffmpeg debian-keyring debian-archive-keyring apt-transport-https
# No libav*-dev: PyAV installs a wheel with ffmpeg already inside it.

say "Service account"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"

say "Application code"
# The code is pushed here with deploy/sync.sh rather than cloned: the repo is a
# private monorepo holding several unrelated projects, one of them gigabytes.
[ -f "$APP_DIR/main.py" ] || { echo "No code at $APP_DIR — run deploy/sync.sh first." >&2; exit 1; }
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

say "Python environment"
[ -x "$APP_DIR/.venv/bin/python" ] || sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
# CPU-only torch first: sentence-transformers would otherwise pull the CUDA
# build, which is gigabytes of code this machine has no card to run.
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -q --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -q torch \
  --index-url https://download.pytorch.org/whl/cpu
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
# No Playwright browser: the tools that use it are desktop-only and switched
# off below, so a 400 MB Chromium would never be opened.

say "Speech models"
cd "$APP_DIR"
[ -f kokoro-v1.0.int8.onnx ] || sudo -u "$APP_USER" curl -fsSL -o kokoro-v1.0.int8.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
[ -f voices-v1.0.bin ] || sudo -u "$APP_USER" curl -fsSL -o voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

say "Ollama and the language model"
command -v ollama >/dev/null 2>&1 || curl -fsSL https://ollama.com/install.sh | sh
systemctl enable --now ollama
sleep 5
ollama list | grep -q '^llama3.2' || ollama pull llama3.2

say "Configuration"
if [ ! -f "$APP_DIR/.env" ]; then
  # Generated here and never copied from a laptop: the master key derives every
  # user's encryption key, so it must belong to this machine alone.
  MASTER=$(sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" -c \
    'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
  ADMIN_PW=$(sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" -c \
    'import secrets,string; a=string.ascii_letters+string.digits+"!@#$%^&*-_=+"; print("".join(secrets.choice(a) for _ in range(24)))')
  cat > "$APP_DIR/.env" <<ENV
SAIRA_MASTER_KEY=$MASTER
SAIRA_APP_URL=https://$DOMAIN

# Hosted: the tools that drive a desktop are off, because here "open this app"
# would mean the server's apps.
SAIRA_DESKTOP_TOOLS=off

SAIRA_ADMIN_EMAIL=$ADMIN_EMAIL
SAIRA_ADMIN_NAME=Admin
SAIRA_ADMIN_PASSWORD=$ADMIN_PW

# Fill these in, then: systemctl restart saira
SAIRA_SMTP_HOST=
SAIRA_SMTP_PORT=465
SAIRA_SMTP_USER=
SAIRA_SMTP_PASSWORD=
SAIRA_MAIL_FROM=Saira <no-reply@$DOMAIN>
ENV
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  say "Admin password written to $APP_DIR/.env — read it there, it is not printed."
fi

say "Service"
cat > /etc/systemd/system/saira.service <<UNIT
[Unit]
Description=SAIRA voice assistant
After=network-online.target ollama.service
Wants=network-online.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 3001
Restart=always
RestartSec=5
# The app only ever writes inside its own directory.
ProtectSystem=strict
ReadWritePaths=$APP_DIR
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now saira

say "Reverse proxy"
# A certificate needs the name to point here first. Until it does, serve plain
# HTTP so the box can be checked — but browsers refuse microphone access to a
# page that is not on HTTPS, so the assistant cannot hear anyone until the DNS
# record exists and this script is run again.
SERVER_IP=$(curl -fsS --max-time 10 https://api.ipify.org || hostname -I | awk '{print $1}')
RESOLVED=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)
if [ -n "$RESOLVED" ] && [ "$RESOLVED" = "$SERVER_IP" ]; then
  TLS_READY=yes
else
  TLS_READY=no
  echo "   $DOMAIN resolves to '${RESOLVED:-nothing}', this host is $SERVER_IP."
  echo "   Serving plain HTTP for now; re-run once the A record is in place."
fi

# A certificate is not cosmetic here: browsers refuse microphone access to a
# page that is not on HTTPS, so without it the assistant cannot hear anyone.
if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy
fi
if [ "$TLS_READY" = yes ]; then
  cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
    encode zstd gzip
    # The voice socket is a long-lived stream; don't cut it off mid-sentence.
    reverse_proxy 127.0.0.1:3001 {
        flush_interval -1
    }
}
CADDY
else
  cat > /etc/caddy/Caddyfile <<CADDY
:80 {
    encode zstd gzip
    reverse_proxy 127.0.0.1:3001 {
        flush_interval -1
    }
}
CADDY
fi
systemctl reload caddy || systemctl restart caddy

say "Firewall"
# Only enable the firewall once SSH is explicitly allowed, or this locks
# everyone out of a machine that is reachable only over SSH.
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp  >/dev/null 2>&1 || true
  ufw allow 80/tcp  >/dev/null 2>&1 || true
  ufw allow 443/tcp >/dev/null 2>&1 || true
  if ufw status | grep -q '22/tcp'; then
    yes | ufw enable >/dev/null 2>&1 || true
  else
    echo "   Leaving the firewall off: the SSH rule did not take."
  fi
fi

if [ "$TLS_READY" = yes ]; then
  say "Done — https://$DOMAIN"
else
  say "Done — http://$SERVER_IP (no certificate yet, so no microphone)"
fi
echo "Admin email:    $ADMIN_EMAIL"
echo "Admin password: grep SAIRA_ADMIN_PASSWORD $APP_DIR/.env"
echo
echo "Still to do: put the SMTP settings in $APP_DIR/.env and run"
echo "  systemctl restart saira"
