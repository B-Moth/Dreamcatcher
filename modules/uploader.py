"""
uploader.py — Audio upload module for DreamCatcher
- Sends recorded audio to Sandman via HTTP POST
- Manages a local queue for offline uploads
- Retries automatically when Sandman is back online
- Updates meta.json after successful upload
"""

import json
import logging
import os
import queue
import threading
import time
from pathlib import Path

import requests
import yaml

# ── Logging ────────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path.home() / "dreamjournal" / "config.yaml"
QUEUE_DIR   = Path.home() / "dreamjournal" / "queue"


def _load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


class Uploader:
    """
    Manages uploading audio entries to Sandman.

    Usage:
        u = Uploader(on_status=my_callback)
        u.start()
        u.enqueue(Path("/home/sandman/dreamjournal/queue/2024-03-01_06h12"))

    on_status(status, entry_path) is called with:
        status = "uploading" | "success" | "error" | "queued"
    """

    def __init__(self, on_status=None):
        self.on_status      = on_status
        self._queue         = queue.Queue()
        self._thread        = threading.Thread(target=self._worker, daemon=True)
        self._active        = False   # True while uploading
        self._sandman_up    = False   # Last known Sandman status

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Start the background upload worker thread."""
        self._thread.start()
        log.info("Uploader thread started")

    def enqueue(self, entry_path: Path):
        """Add an entry to the upload queue."""
        self._queue.put(entry_path)
        log.info(f"Queued for upload: {entry_path.name}")

    def resume_pending(self):
        """
        On startup, scan queue/ for any entries not yet uploaded and re-queue them.
        Call once at app start for crash recovery.
        """
        if not QUEUE_DIR.exists():
            return
        for entry in sorted(QUEUE_DIR.iterdir()):
            if not entry.is_dir():
                continue
            meta = _read_meta(entry)
            if meta and not meta.get("uploaded", False):
                audio = entry / "audio.wav"
                if audio.exists():
                    log.info(f"Resuming pending upload: {entry.name}")
                    self.enqueue(entry)

    @property
    def is_active(self):
        """True while an upload is in progress."""
        return self._active

    @property
    def sandman_reachable(self):
        """Last known Sandman reachability status."""
        return self._sandman_up

    # ── Internal ───────────────────────────────────────────────────────────────

    def _worker(self):
        """Background worker — processes upload queue."""
        while True:
            entry_path = self._queue.get()
            try:
                self._active = True
                self._upload_entry(entry_path)
            except Exception as e:
                log.error(f"Upload failed for {entry_path.name}: {e}")
                _update_meta(entry_path, {"upload_error": str(e)})
                if self.on_status:
                    self.on_status("error", entry_path)
                # Re-queue for retry after delay
                threading.Timer(60, self.enqueue, args=[entry_path]).start()
            finally:
                self._active = False
                self._queue.task_done()

    def _upload_entry(self, entry_path: Path):
        """Upload a single entry to Sandman."""
        config  = _load_config()
        sandman = config.get("sandman", {})
        host    = sandman.get("host", "sandman")
        port    = sandman.get("port", 8765)
        api_key = sandman.get("api_key", "")
        url     = f"http://{host}:{port}/upload"

        audio_file = entry_path / "audio.wav"
        meta       = _read_meta(entry_path) or {}

        if not audio_file.exists():
            log.warning(f"No audio.wav in {entry_path.name}, skipping")
            return

        if meta.get("uploaded"):
            log.info(f"{entry_path.name} already uploaded, skipping")
            return

        log.info(f"Uploading {entry_path.name} to {url}")

        if self.on_status:
            self.on_status("uploading", entry_path)

        with open(audio_file, "rb") as f:
            response = requests.post(
                url,
                files={"audio": (audio_file.name, f, "audio/wav")},
                data={
                    "timestamp":        meta.get("timestamp", entry_path.name),
                    "duration_seconds": meta.get("duration_seconds", 0),
                },
                headers={"X-API-Key": api_key},
                timeout=120   # large files on slow Wi-Fi need time
            )

        if response.status_code == 200:
            self._sandman_up = True
            log.info(f"Upload successful: {entry_path.name}")
            _update_meta(entry_path, {
                "uploaded":    True,
                "uploaded_at": _now_iso(),
            })
            if self.on_status:
                self.on_status("success", entry_path)
        else:
            raise RuntimeError(
                f"Sandman returned {response.status_code}: {response.text}"
            )


class ConnectionMonitor:
    """
    Background thread that periodically pings Sandman's /health endpoint.
    Updates connection status and flushes the upload queue on reconnection.

    Usage:
        monitor = ConnectionMonitor(uploader=uploader, on_status=my_callback)
        monitor.start()

    on_status(connected: bool) is called whenever connection state changes.
    """

    PING_INTERVAL   = 30   # seconds between pings
    RETRY_INTERVAL  = 60   # seconds between retries when offline

    def __init__(self, uploader: Uploader, on_status=None):
        self._uploader      = uploader
        self.on_status      = on_status
        self._connected     = False
        self._thread        = threading.Thread(target=self._monitor, daemon=True)

    def start(self):
        self._thread.start()
        log.info("Connection monitor started")

    @property
    def connected(self):
        return self._connected

    def _monitor(self):
        while True:
            reachable = self._ping()

            if reachable and not self._connected:
                # Just came back online
                log.info("Sandman is back online — flushing upload queue")
                self._connected = True
                if self.on_status:
                    self.on_status(True)
                self._uploader.resume_pending()

            elif not reachable and self._connected:
                # Just went offline
                log.warning("Sandman is unreachable")
                self._connected = False
                if self.on_status:
                    self.on_status(False)

            interval = self.PING_INTERVAL if reachable else self.RETRY_INTERVAL
            time.sleep(interval)

    def _ping(self):
        """Ping Sandman's health endpoint. Returns True if reachable."""
        config  = _load_config()
        sandman = config.get("sandman", {})
        host    = sandman.get("host", "sandman")
        port    = sandman.get("port", 8765)
        url     = f"http://{host}:{port}/health"
        try:
            r = requests.get(url, timeout=5)
            return r.status_code == 200
        except Exception:
            return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_meta(entry_path: Path):
    meta_file = entry_path / "meta.json"
    if not meta_file.exists():
        return None
    with open(meta_file) as f:
        return json.load(f)

def _update_meta(entry_path: Path, updates: dict):
    meta_file = entry_path / "meta.json"
    meta = _read_meta(entry_path) or {}
    meta.update(updates)
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=2)

def _now_iso():
    from datetime import datetime
    return datetime.now().isoformat()


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Quick test: attempts to upload the most recent queue entry to Sandman.
    Usage: python3 uploader.py
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [uploader] %(message)s"
    )

    def on_status(status, path):
        print(f"\n→ Status: {status} — {path.name}")

    u = Uploader(on_status=on_status)
    u.start()
    u.resume_pending()

    # Keep alive long enough for upload to complete
    time.sleep(30)
    print("Done.")
