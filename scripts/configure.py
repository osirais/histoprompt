#!/usr/bin/env python3
from __future__ import annotations

import getpass
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from histoprompt.setup_config import parse_env, render_env, write_private  # noqa: E402


def ask(label: str, current: str = "", secret: bool = False) -> str:
    suffix = " [already set]" if current and secret else f" [{current}]" if current else ""
    prompt = f"{label}{suffix}: "
    value = getpass.getpass(prompt) if secret else input(prompt)
    return value.strip() or current


def main() -> None:
    template_path = ROOT / ".env.example"
    output_path = ROOT / ".env.local"
    template = template_path.read_text(encoding="utf-8")
    values = parse_env(template)
    if output_path.exists():
        values.update(parse_env(output_path.read_text(encoding="utf-8")))

    print("Configure HistoPrompt. Secrets are written only to ignored .env.local.")
    mode = ask("MUSK mode (remote or local)", values.get("MUSK_BACKEND", "remote")).lower()
    if mode not in {"remote", "local"}:
        raise SystemExit("MUSK mode must be remote or local.")
    values["MUSK_BACKEND"] = mode
    values["LUMEN_API_KEY"] = ask(
        "Lumen API key", values.get("LUMEN_API_KEY", ""), secret=True
    )
    if mode == "remote":
        values["DELTA_USERNAME"] = ask(
            "NCSA/Delta username", values.get("DELTA_USERNAME", "")
        )
        values["MUSK_API_KEY"] = ask(
            "Shared MUSK bearer key", values.get("MUSK_API_KEY", ""), secret=True
        )
        required = ("LUMEN_API_KEY", "DELTA_USERNAME", "MUSK_API_KEY")
    else:
        values["HF_TOKEN"] = ask(
            "Hugging Face token with MUSK access", values.get("HF_TOKEN", ""), secret=True
        )
        required = ("LUMEN_API_KEY", "HF_TOKEN")

    conch_mode = ask(
        "CONCH mode (remote or disabled)", values.get("CONCH_BACKEND", "disabled")
    ).lower()
    if conch_mode not in {"remote", "disabled"}:
        raise SystemExit("CONCH mode must be either remote or disabled.")
    values["CONCH_BACKEND"] = conch_mode
    if conch_mode == "remote":
        values["DELTA_CONCH_HOST"] = ask(
            "NCSA CONCH host", values.get("DELTA_CONCH_HOST", "")
        )
        values["CONCH_API_KEY"] = ask(
            "Shared CONCH bearer key", values.get("CONCH_API_KEY", ""), secret=True
        )
        required = (*required, "DELTA_CONCH_HOST", "CONCH_API_KEY")

    missing = [key for key in required if not values.get(key)]
    if missing:
        raise SystemExit(f"Missing required values: {', '.join(missing)}")
    write_private(output_path, render_env(template, values))
    print("Saved private configuration to .env.local.")


if __name__ == "__main__":
    main()
