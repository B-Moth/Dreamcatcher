# Dreamcatcher

The DreamCatcher is the physical bedside device in the DreamJournal system. It sits on your nightstand, records your voice each morning, and uploads the recording to DreamServer for transcription.
You can find the repo for DreamServer here : https://github.com/B-Moth/Dreamserver_source_public

---

## Hardware

| Component | Details |
|---|---|
| Board | Raspberry Pi Zero 2 W |
| Display | 2.42" OLED SSD1309 128x64 — I2C at 0x3C |
| Input | EC11 rotary encoder with push button |
| Microphone | USB mic via Waveshare USB HUB HAT (B) |
| Power | 5V USB power supply (always-on) |

---

## How it works

1. DreamCatcher boots and displays an animated idle screen depending on the weather of the current location with a clock and connection status
2. You rotate the encoder to select an action (settings, recording,...) press to confirm
3. When recording starts — the screen switches to a recording animation
4. You press again to stop — the file is queued for upload
5. DreamCatcher if connect to network automatically attempts to upload to DreamServer every 60 seconds until it succeeds
6. That's it — transcription and everything else happens on DreamServer

---

## Software

```
~/dreamjournal/
├── main.py              # Entry point — main loop
├── config.yaml          # Configuration
├── modules/
│   ├── recorder.py      # Audio recording + watchdog
│   └── uploader.py      # Upload queue + retry logic
├── assets/
│   └── animations/      # PNG spritesheets for OLED animations
├── queue/               # Pending recordings (YYYY-MM-DD_HHhMM/)
└── logs/                # Upload and error logs
```

Standalone modules to build:
- `display.py` — OLED rendering (clock face, status screens, animations)
- `buttons.py` — Encoder rotation and button events with debounce
- `menu.py` — State machine (IDLE → RECORDING → UPLOADING → ERROR)
- `connection.py` — Background Sandman health monitor

---

## Setup

### Requirements

```bash
pip install luma.oled pillow gpiozero requests pyyaml
```

### I2C

```bash
sudo raspi-config  # Interface Options → I2C → Enable
sudo i2cdetect -y 1  # Should show 3c
```

### USB hub auto-detection on boot

The Waveshare USB HUB HAT requires a reset after boot. A systemd service handles this:

```bash
# /etc/systemd/system/usb-hub-reset.service
# Runs /usr/local/bin/usb-hub-init.sh after boot
# Unbinds and rebinds USB port after 10s delay
sudo systemctl enable usb-hub-reset
```

### Auto-start

```bash
sudo systemctl enable dreamcatcher
sudo systemctl start dreamcatcher

# Stop for testing
sudo systemctl stop dreamcatcher
python3 ~/dreamjournal/main.py
```

---

## Configuration

```yaml
DreamServer:
  host: "DreamServer"
  port: 8765
  api_key: "your-key-here"

recording:
  sample_rate: 16000
  channels: 1
  format: "S16_LE"
  max_duration_minutes: 10

display:
  brightness: 200
  idle_dim_after_seconds: 60

gpio:
  encoder_a: 17
  encoder_b: 18
  encoder_button: 27
```

---

## Network

DreamCatcher connects to DreamServer over Tailscale. It is tagged `recorder` in the Tailscale ACL and can only reach DreamServer on port 8765. SSH access from personal devices is allowed on port 22.

```bash
ssh dreamcatcher  # Direct via Tailscale
```

---

## Current status

| Module | Status |
|---|---|
| USB mic + hub | ✅ Working |
| OLED display | ✅ Detected, rendering working |
| Rotary encoder | ✅ Working |
| recorder.py | ✅ Built and tested |
| uploader.py | ✅ Built and tested |
| display.py | 🔨 In progress |
| buttons.py | ⬜ To build |
| menu.py | ⬜ To build |
| connection.py | ⬜ To build |
| main.py | 🔨 In progress |
