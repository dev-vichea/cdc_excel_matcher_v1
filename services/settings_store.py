"""Settings and persistent master data storage."""

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).parent.parent
DEFAULTS_DIR = ROOT / "data" / "defaults"
DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DEFAULTS_DIR / "settings.json"
DEFAULT_TEMPLATE_PATH = ROOT / "services" / "templates" / "permit_template_default.xlsx"
DEFAULT_CDC_PATH = DEFAULTS_DIR / "default_cdc_master.xlsx"

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "company_name": "XIN CAI FU (CAMBODIA) CO., LTD.",
    "qip_reference": "211/26",
    "vat_number": "LO01-902303477",
    "consignee_address_1": "PHUM DOMNAK TROYEOUNG, SANGKAT CHOM CHAO II,",
    "consignee_address_2": "KHAN POR SEN CHEY PHNOM PENH,",
    "consignee_address_3": "KINGDOM OF CAMBODIA.",
    "shipping_mode": "BY TRUCK",
    "origin": "JIANGSU, CHINA",
    "destination": "PHNOM PENH, CAMBODIA",
    "template_filename": "permit_template_default.xlsx",
    "cdc_filename": "default_cdc_master.xlsx",
}


def get_settings() -> Dict[str, Any]:
    """Retrieve saved preferences, merging with defaults."""
    if not SETTINGS_FILE.is_file():
        save_settings(DEFAULT_PREFERENCES)
        return dict(DEFAULT_PREFERENCES)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_PREFERENCES)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_PREFERENCES)


def save_settings(settings: Dict[str, Any]) -> None:
    """Save preferences to disk."""
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


def get_default_template_path() -> Path:
    """Return path to active default permit template."""
    if DEFAULT_TEMPLATE_PATH.is_file():
        return DEFAULT_TEMPLATE_PATH
    fallback = ROOT / "reference" / "shipping_work" / "02_import_TK164" / "permit_application" / "1-26TKYM164.xlsx"
    return fallback


def get_default_template_bytes() -> bytes:
    """Return bytes of active default permit template."""
    return get_default_template_path().read_bytes()


def save_default_template(data: bytes, filename: str) -> None:
    """Save new default permit template."""
    DEFAULT_TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_TEMPLATE_PATH.write_bytes(data)
    settings = get_settings()
    settings["template_filename"] = filename
    save_settings(settings)


def get_default_cdc_path() -> Path:
    """Return path to active default CDC master list."""
    if DEFAULT_CDC_PATH.is_file():
        return DEFAULT_CDC_PATH
    fallback = ROOT / "reference" / "shipping_work" / "03_cdc_master_and_approval" / "needs_verification" / "XIN CAI FU-CDC Master List-2026-CUT STOCK ( QIP # 211-26  ).xlsx"
    return fallback


def get_default_cdc_bytes() -> bytes:
    """Return bytes of active default CDC master list."""
    return get_default_cdc_path().read_bytes()


def save_default_cdc(data: bytes, filename: str) -> None:
    """Save new default CDC master list."""
    DEFAULT_CDC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CDC_PATH.write_bytes(data)
    settings = get_settings()
    settings["cdc_filename"] = filename
    save_settings(settings)
