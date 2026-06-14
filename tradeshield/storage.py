from __future__ import annotations

import os
import uuid
from pathlib import Path

from tradeshield.config import get_settings

settings = get_settings()


def save_upload(content: bytes, original_filename: str) -> tuple[str, str]:
    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = original_filename.replace("/", "_").replace("\\", "_")
    name = f"{uuid.uuid4().hex}_{safe_name}"
    path = storage_dir / name
    path.write_bytes(content)
    return str(path), name
