from __future__ import annotations

import os
import tempfile
from pathlib import Path


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def render_env(template: str, values: dict[str, str]) -> str:
    rendered = []
    for raw_line in template.splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#") and "=" in raw_line:
            key = raw_line.split("=", 1)[0].strip()
            if key in values:
                raw_line = f"{key}={values[key]}"
        rendered.append(raw_line)
    return "\n".join(rendered) + "\n"


def write_private(path: Path, text: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", text=True
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
