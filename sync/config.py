# sync/config.py
import json
import os
from pathlib import Path
from django.conf import settings


def data_dir() -> Path:
    """Where to store the terminal.json and local SQLite DB."""
    if os.environ.get("DJPOS_DATA_DIR"):
        return Path(os.environ["DJPOS_DATA_DIR"] / ".djpos")
    path = Path(os.environ.get("DJPOS_DATA_DIR", Path.home() / ".djpos"))
    return path


def device_config():
    """Env vars win (dev machines); otherwise the paired terminal.json."""
    if settings.DEVICE_ID != "" and settings.DEVICE_KEY != "" and settings.CENTRAL_URL != "":
        return {
            "device_id": settings.DEVICE_ID,
            "device_key": settings.DEVICE_KEY,
            "central_url": settings.CENTRAL_URL,
        }
    f = data_dir() / "terminal.json"
    return json.loads(f.read_text()) if f.exists() else None


def is_paired():
    return device_config() is not None


def save_device_config(cfg):
    data_dir().mkdir(parents=True, exist_ok=True)
    (data_dir() / "terminal.json").write_text(json.dumps(cfg, indent=2))
