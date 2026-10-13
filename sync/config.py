# sync/config.py
import json
from config.paths import data_dir
from django.conf import settings


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
