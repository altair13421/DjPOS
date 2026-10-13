import os
from pathlib import Path


def data_dir() -> Path:
    """Return the platform-native directory containing terminal data."""
    configured_root = os.environ.get("DJPOS_DATA_DIR")
    if configured_root:
        return Path(configured_root).expanduser() / ".djpos"
    return Path.home() / ".djpos"
