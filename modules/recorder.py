"""
recorder.py — Audio recording module for DreamCatcher
- Records audio via arecord (ALSA)
- Saves to ~/dreamjournal/queue/ with timestamp
- Creates meta.json alongside each recording
- Auto-stops after max_duration_minutes (configurable)
- Calls on_complete callback when recording stops
"""

import os
import json
import subprocess
import threading
import logging
from datetime import datetime
from pathlib import Path

import yaml

# ── Logging ────────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path.home() / "dreamjournal" / "config.yaml"
QUEUE_DIR   = Path.home() / "dreamjournal" / "queue"


def _load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


class Recorder:
    """
    Manages audio recording via arecord.

    Usage:
        r = Recorder(on_complete=my_callback)
        r.start()   # begin recording
        r.stop()    # stop recording → triggers on_complete
        r.discard() # stop and delete the file

    on_complete(entry_path: Path) is called with the queue entry folder
    when recording stops cleanly.
    """

    def __init__(self, on_complete=None, on_start=None, on_timeout=None):
        self.on_complete  = on_complete
        self.on_start     = on_start
        self.on_timeout   = on_timeout  # called when auto-stop triggers
        self._process     = None
        self._active      = False
        self._entry_path  = None
        self._start_time  = None
        self._watchdog    = None
        self._lock        = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────────────

    def toggle(self):
        """Start recording if idle, stop if recording."""
        if self._active:
            self.stop()
        else:
            self.start()

    def start(self):
        """Begin a new recording."""
        with self._lock:
            if self._active:
                log.warning("Already recording, ignoring start")
                return

            config = _load_config()
            rec    = config.get("recording", {})

            # Create a timestamped entry folder in queue/
            timestamp        = datetime.now().strftime("%Y-%m-%d_%Hh%M")
            self._entry_path = QUEUE_DIR / timestamp
            self._entry_path.mkdir(parents=True, exist_ok=True)

            audio_file = self._entry_path / "audio.wav"

            # Find the correct ALSA device
            device = _find_mic_device()
            if device is None:
                log.error("No microphone found — is the USB mic plugged in?")
                return

            cmd = [
                "arecord",
                "-D", device,
                "-f", rec.get("format", "S16_LE"),
                "-r", str(rec.get("sample_rate", 16000)),
                "-c", str(rec.get("channels", 1)),
                str(audio_file)
            ]

            log.info(f"Recording to {audio_file} via {device}")
            self._process    = subprocess.Popen(cmd)
            self._active     = True
            self._start_time = datetime.now()

            # Write initial meta.json
            _write_meta(self._entry_path, {
                "timestamp":  timestamp,
                "started_at": self._start_time.isoformat(),
                "uploaded":   False,
                "status":     "recording"
            })

            # Auto-stop watchdog
            max_seconds      = rec.get("max_duration_minutes", 10) * 60
            self._watchdog   = threading.Timer(max_seconds, self._timeout_stop)
            self._watchdog.start()
            log.info(f"Recording watchdog set for {max_seconds}s")

            if self.on_start:
                self.on_start(self._entry_path)

    def stop(self):
        """Stop recording and trigger on_complete."""
        with self._lock:
            if not self._active:
                log.warning("Not recording, ignoring stop")
                return

            # Cancel watchdog if still running
            if self._watchdog is not None:
                self._watchdog.cancel()
                self._watchdog = None

            self._process.terminate()
            self._process.wait()

            duration = (datetime.now() - self._start_time).seconds
            log.info(f"Recording stopped — duration: {duration}s")

            # Update meta.json
            _write_meta(self._entry_path, {
                "timestamp":        self._entry_path.name,
                "started_at":       self._start_time.isoformat(),
                "stopped_at":       datetime.now().isoformat(),
                "duration_seconds": duration,
                "uploaded":         False,
                "status":           "pending"
            })

            entry            = self._entry_path
            self._active     = False
            self._process    = None
            self._entry_path = None
            self._start_time = None

        # Check recording has actual content
        audio_file = entry / "audio.wav"
        if not audio_file.exists() or audio_file.stat().st_size < 1000:
            log.warning("Recording too short or empty, discarding")
            import shutil
            shutil.rmtree(entry)
            return

        if self.on_complete:
            self.on_complete(entry)

    def discard(self):
        """Stop recording and delete the file."""
        with self._lock:
            if not self._active:
                return

            # Cancel watchdog if still running
            if self._watchdog is not None:
                self._watchdog.cancel()
                self._watchdog = None

            self._process.terminate()
            self._process.wait()

            import shutil
            shutil.rmtree(self._entry_path)
            log.info("Recording discarded")

            self._active     = False
            self._process    = None
            self._entry_path = None
            self._start_time = None

    def _timeout_stop(self):
        """Called automatically when max recording duration is reached."""
        log.warning("Max recording duration reached — auto-stopping")
        if self.on_timeout:
            self.on_timeout()
        self.stop()

    @property
    def is_active(self):
        """True while recording is in progress."""
        return self._active

    @property
    def duration(self):
        """Current recording duration in seconds, or 0 if not recording."""
        if not self._active or self._start_time is None:
            return 0
        return (datetime.now() - self._start_time).seconds


# ── ALSA device detection ──────────────────────────────────────────────────────

def _find_mic_device():
    """
    Find the USB microphone ALSA device automatically.
    Returns a device string like 'plughw:1,0' or None if not found.
    """
    try:
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True, text=True
        )
        lines = result.stdout.splitlines()
        for line in lines:
            if "card" in line.lower() and ("usb" in line.lower() or "USB" in line):
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "card":
                        card_num = parts[i+1].rstrip(":")
                        return f"plughw:{card_num},0"
        log.warning("USB mic not found by name, falling back to plughw:1,0")
        return "plughw:1,0"
    except Exception as e:
        log.error(f"Error detecting mic: {e}")
        return "plughw:1,0"


# ── meta.json helper ───────────────────────────────────────────────────────────

def _write_meta(entry_path: Path, data: dict):
    with open(entry_path / "meta.json", "w") as f:
        json.dump(data, f, indent=2)


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Quick test: records then auto-stops via watchdog.
    Usage: python3 recorder.py
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    def on_complete(path):
        print(f"\n✓ Recording saved to: {path}")
        print(f"  Files: {list(path.iterdir())}")

    def on_timeout():
        print("\n⚠ Auto-stopped: max duration reached")

    r = Recorder(on_complete=on_complete, on_timeout=on_timeout)

    print("Recording — will auto-stop after max_duration_minutes...")
    r.start()

    import time
    time.sleep(60)  # Keep script alive while watchdog does its job

    print("Done.")
