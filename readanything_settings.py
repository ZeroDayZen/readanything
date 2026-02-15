import json
import os
from pathlib import Path


DEFAULT_SETTINGS: dict = {
    "piper_bin_path": "",
}


def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "readanything"
    return Path.home() / ".config" / "readanything"


def settings_path() -> Path:
    return _config_dir() / "settings.json"


def load_settings() -> dict:
    path = settings_path()
    data: dict = {}
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
    except Exception:
        data = {}

    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def save_settings(settings: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Only save known keys for forward compatibility/safety
    out = {k: settings.get(k, DEFAULT_SETTINGS.get(k, "")) for k in DEFAULT_SETTINGS.keys()}
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

