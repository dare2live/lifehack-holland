"""Download IPIP source files declared in config/source_registry.json."""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_REGISTRY = PROJECT_ROOT / "config" / "source_registry.json"


def _load_source() -> dict:
    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    return registry["sources"]["ipip_jungian_seed"]


def _project_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def download_file(url: str, dest_path: Path) -> None:
    print(f"Downloading {url} ...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        dest_path.write_bytes(response.read())
    print(f"Saved to {dest_path} ({os.path.getsize(dest_path)} bytes)")


def fetch_ipip_data() -> None:
    source = _load_source()
    for item in source.get("files", []):
        download_file(item["url"], _project_path(item["output_path"]))
    print(f"IPIP source data fetched: {source['source_name']} {source['source_version']}")


if __name__ == "__main__":
    fetch_ipip_data()
