#!/usr/bin/env bash
set -euo pipefail

# One-shot installer for Oracle Cloud Always Free VM.
# Run as root (or with sudo) on a fresh Ubuntu 22.04/24.04 instance.
#
# Optional: pass keys as env vars to write .env automatically:
#   sudo GEMINI_API_KEY=... WHATSAPP_API_TOKEN=... bash install.sh
# Otherwise a template is created and you edit it manually.

APP_USER="whatsapp"
APP_DIR="/opt/whatsapp_agent"
REPO_URL="https://github.com/ullahhafeez321/whatsapp_agent.git"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root:  sudo bash install.sh" >&2
  exit 1
fi

echo "==> Updating apt..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "==> Creating dedicated service user '${APP_USER}'..."
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd -r -m -d "/home/${APP_USER}" -s /bin/bash "${APP_USER}"
fi

echo "==> Cloning the repo to ${APP_DIR}..."
rm -rf "${APP_DIR}"
git clone "${REPO_URL}" "${APP_DIR}"

echo "==> Creating Python virtualenv and installing dependencies..."
sudo -u "${APP_USER}" -H python3 -m venv "${APP_DIR}/venv"
sudo -u "${APP_USER}" -H "${APP_DIR}/venv/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" -H "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "==> Setting up .env..."
if [[ -n "${GEMINI_API_KEY:-}" && -n "${WHATSAPP_API_TOKEN:-}" ]]; then
  cat > "${APP_DIR}/.env" <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
WHATSAPP_API_TOKEN=${WHATSAPP_API_TOKEN}
WHATSAPP_BASE_URL=https://api.whatsapp.com/agent/v1
EOF
  echo "    .env written from the keys you provided."
else
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
  echo "    Template created — edit it with your keys before starting:"
  echo "      nano ${APP_DIR}/.env"
fi
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "==> Installing systemd service..."
cp "${APP_DIR}/deploy/whatsapp-agent.service" /etc/systemd/system/whatsapp-agent.service
systemctl daemon-reload
systemctl enable whatsapp-agent.service

if [[ -n "${GEMINI_API_KEY:-}" || -f "${APP_DIR}/.env" ]]; then
  if systemctl start whatsapp-agent.service; then
    echo "    Service started successfully."
  else
    echo "    Service enabled but failed to start (check keys in ${APP_DIR}/.env)."
    echo "    Fix keys, then:  systemctl restart whatsapp-agent"
  fi
fi

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo ""
echo "=============================================================="
echo "Done! Useful commands:"
echo "  sudo systemctl status whatsapp-agent     # check status"
echo "  sudo journalctl -u whatsapp-agent -f     # live logs"
echo "  sudo systemctl restart whatsapp-agent    # restart"
echo "  sudo systemctl stop whatsapp-agent       # stop"
echo "=============================================================="