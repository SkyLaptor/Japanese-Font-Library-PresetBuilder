from pathlib import Path
from typing import Any

import yaml

from const import DEFAULT_LANG_CODE, DEFAULT_LANG_FILE, ENCODE, LANG_DIR

_current_lang_code = DEFAULT_LANG_CODE
_current_lang_data: dict[str, Any] = {}


def _read_lang_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding=ENCODE) as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def set_language(lang_code: str | None = None) -> str:
    global _current_lang_code, _current_lang_data

    next_lang = (lang_code or DEFAULT_LANG_CODE).strip().lower()
    target_file = LANG_DIR / f"{next_lang}.yml"

    data = _read_lang_file(target_file)
    if not data:
        next_lang = DEFAULT_LANG_CODE
        data = _read_lang_file(DEFAULT_LANG_FILE)

    _current_lang_code = next_lang
    _current_lang_data = data
    return _current_lang_code


def get_language() -> str:
    return _current_lang_code


def tr(key: str, default: str | None = None, **kwargs) -> str:
    if not _current_lang_data:
        set_language(DEFAULT_LANG_CODE)

    node: Any = _current_lang_data
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            node = None
            break

    text = default if default is not None else key
    if isinstance(node, str):
        text = node

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
