"""Read ``cutaway.json`` from an extracted Cutaway zip.

The manifest is the authoritative source for section placement — much more
robust than parsing filenames. Filename parsing is kept as a fallback for
older zips (and anything we receive without a manifest).

Schema (version 1):

    {
      "version": 1,
      "exporter": {"name": "cutaway-web", "url": "https://cutawayhq.com"},
      "exported_at": "2026-05-03T...",
      "unit": "mm" | "cm" | "m" | "in",
      "sections": [
        {
          "file": "<filename inside the zip>",
          "name": "<section name>",
          "kind": "plane" | "face" | "derived",
          "origin": [x, y, z],
          "normal": [nx, ny, nz],
          "uAxis": [ux, uy, uz],
          "vAxis": [vx, vy, vz],
          "plane": "XY" | "XZ" | "YZ" | null,
          "tiltU": <number>,
          "tiltV": <number>
        },
        ...
      ]
    }

When bumping the schema version, keep this reader backward-compatible: old
add-in versions will still receive newer zips and shouldn't crash on extra
fields.
"""

import json
import os
from typing import Optional, TypedDict, List


SUPPORTED_VERSIONS = {1}


class ManifestSection(TypedDict, total=False):
    file: str
    name: str
    kind: str           # 'plane' | 'face' | 'derived'
    origin: List[float] # [x, y, z]
    normal: List[float]
    uAxis: List[float]
    vAxis: List[float]
    plane: Optional[str]
    tiltU: float
    tiltV: float


class Manifest(TypedDict, total=False):
    version: int
    unit: str
    sections: List[ManifestSection]


def read_from_dir(extracted_dir: str) -> Optional[Manifest]:
    """Look for ``cutaway.json`` at the top level of an extracted zip.

    Returns the parsed manifest (with a couple of light validation checks),
    or ``None`` if the file is missing / malformed / unsupported version.
    Never raises — the importer falls back to filename parsing on None.
    """
    path = os.path.join(extracted_dir, 'cutaway.json')
    if not os.path.isfile(path):
        # Walk one level deeper in case the zip nests under a folder.
        for entry in os.listdir(extracted_dir):
            candidate = os.path.join(extracted_dir, entry, 'cutaway.json')
            if os.path.isfile(candidate):
                path = candidate
                break
        else:
            return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None

    if not isinstance(data, dict):
        return None
    version = data.get('version')
    if version not in SUPPORTED_VERSIONS:
        return None
    sections = data.get('sections')
    if not isinstance(sections, list):
        return None

    return data  # type: ignore[return-value]
