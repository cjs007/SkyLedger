#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${SKYLEDGER_APP_DIR:-/opt/skyledger}"
CONFIG_DIR="${SKYLEDGER_CONFIG_DIR:-/etc/skyledger}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Installing SkyLedger to ${APP_DIR}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

sudo mkdir -p "${APP_DIR}" "${CONFIG_DIR}"
sudo rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "venv" \
  --exclude "__pycache__" \
  ./ "${APP_DIR}/"
sudo chown -R "${USER}:${USER}" "${APP_DIR}"

cd "${APP_DIR}"
"${PYTHON_BIN}" -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt

if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
  sudo cp config.example.yaml "${CONFIG_DIR}/config.yaml"
  echo "Created ${CONFIG_DIR}/config.yaml"
fi

SKYLEDGER_CONFIG="${CONFIG_DIR}/config.yaml" ./venv/bin/python - <<'PY'
from skyledger.config import load_config
from skyledger.db import Database

config = load_config()
Database(config.database_path).init()
print(f"Initialized SQLite database at {config.database_path}")
PY

if [ "${INSTALL_SERVICE:-0}" = "1" ]; then
  sudo cp skyledger.service /etc/systemd/system/skyledger.service
  sudo systemctl daemon-reload
  sudo systemctl enable skyledger.service
  echo "Installed systemd service. Start it with: sudo systemctl start skyledger"
else
  echo "Service not installed. Run with INSTALL_SERVICE=1 ./install.sh to install it."
fi

cat <<EOF

Next steps:
1. Edit ${CONFIG_DIR}/config.yaml with home_lat, home_lon, ADS-B JSON path, and optional Discord webhook.
2. Start manually:
   cd ${APP_DIR}
   SKYLEDGER_CONFIG=${CONFIG_DIR}/config.yaml ./venv/bin/python -m skyledger
3. Open:
   http://localhost:8000
EOF
