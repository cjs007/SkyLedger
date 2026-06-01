# SkyLedger

SkyLedger is a local ADS-B flight command center for a Raspberry Pi 4, RTL-SDR Blog V4, and 1090 MHz antenna. It reads local `readsb`/`tar1090` aircraft JSON, runs a FastAPI backend, shows a full-screen outdoor-TV dashboard, logs flyovers to SQLite, and can send Discord webhook alerts.

Core behavior does not require paid APIs or cloud services. Optional enrichment is intentionally modular and off by default.

## What It Includes

- FastAPI backend with WebSocket live updates.
- SQLite schema for aircraft, flyover events, daily stats, enrichment cache, and raw positions.
- Configurable ADS-B source path or URL.
- Distance calculation from your configured home location.
- Active flyover tracking with alert cooldowns.
- Altitude guessing countdown and reveal mode.
- Discord webhook alerts when enabled.
- TV-friendly dashboard, history page, aircraft page, and settings/status page.
- Raspberry Pi install script, systemd unit, and kiosk instructions.

## Quick Start On Raspberry Pi

Install `readsb` and `tar1090` first, then verify one of these data sources exists:

```bash
ls /run/readsb/aircraft.json
ls /var/run/readsb/aircraft.json
ls /run/dump1090-fa/aircraft.json
curl http://localhost/tar1090/data/aircraft.json
```

Install SkyLedger:

```bash
cd /path/to/SkyLedger
chmod +x install.sh
./install.sh
```

Edit configuration:

```bash
sudo nano /etc/skyledger/config.yaml
```

Set at least:

```yaml
home_lat: 41.000000
home_lon: -87.000000
home_name: "Gazebo"
adsb_json_path: "/run/readsb/aircraft.json"
```

Start manually:

```bash
cd /opt/skyledger
SKYLEDGER_CONFIG=/etc/skyledger/config.yaml ./venv/bin/python -m skyledger
```

Open [http://localhost:8000](http://localhost:8000).

## Install As A Service

The provided service assumes the Raspberry Pi user is `pi` and the app lives in `/opt/skyledger`.

```bash
cd /path/to/SkyLedger
INSTALL_SERVICE=1 ./install.sh
sudo systemctl start skyledger
sudo systemctl status skyledger
```

Logs:

```bash
journalctl -u skyledger -f
```

If your Pi username is not `pi`, edit `/etc/systemd/system/skyledger.service` and change `User=` and `Group=`.

## Local Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m skyledger --config config.yaml
```

For a local test countdown, open [http://localhost:8000/settings](http://localhost:8000/settings) and press `Test Countdown`.

## Configuration

Use `config.example.yaml` as the reference. Important fields:

- `home_lat`, `home_lon`: Your antenna/home position.
- `adsb_json_path`: File path or HTTP URL for `aircraft.json`.
- `alert_radius_miles`: Discord alert radius.
- `guess_trigger_radius_miles`: Countdown trigger radius.
- `max_alert_altitude_ft`: Ignore high aircraft for alerts/countdowns.
- `countdown_seconds`: Guess countdown duration.
- `reveal_duration_seconds`: Reveal screen duration.
- `raw_position_retention_days`: Retention for raw position samples.
- `enable_discord_alerts`, `discord_webhook_url`: Optional Discord notifications.
- `enable_enrichment`: Reserved for cache-first free/public enrichment.

## Kiosk Mode

On Raspberry Pi OS Desktop, disable screen blanking:

```bash
xset s off
xset -dpms
xset s noblank
```

Launch Chromium:

```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:8000
```

To auto-start on boot, create:

```bash
mkdir -p ~/.config/lxsession/LXDE-pi
nano ~/.config/lxsession/LXDE-pi/autostart
```

Add:

```text
@xset s off
@xset -dpms
@xset s noblank
@chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:8000
```

## Dashboard Routes

- `/`: Outdoor TV dashboard.
- `/history`: Flyover history.
- `/aircraft/{hex}`: Aircraft history.
- `/settings`: Status, config, and test controls.

API:

- `GET /api/status`
- `GET /api/aircraft/live`
- `GET /api/events/recent`
- `GET /api/stats/today`
- `GET /api/aircraft/{hex}`
- `GET /api/history`
- `POST /api/test-discord`
- `POST /api/test-countdown`
- `WS /ws/live`

## Notes

SkyLedger treats local ADS-B data as the source of truth. If the ADS-B JSON file is missing, malformed, or empty, the dashboard stays up and reports receiver status instead of crashing.
