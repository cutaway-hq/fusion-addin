# Cutaway — Fusion 360 add-in

Imports section exports from [cutawayhq.com](https://cutawayhq.com) into
Fusion 360 as sketches placed on construction planes at their real-world
3D positions. One DXF in your zip → one sketch on its own plane. No
manual offset typing.

## Install

See [docs/INSTALL.md](docs/INSTALL.md). TL;DR: download the latest
`cutaway-X.Y.Z.zip` from
[Releases](https://github.com/cutaway-hq/fusion-addin/releases), unzip,
run `install/install.bat` (Windows) or `install/install.sh` (macOS), then
enable **Cutaway** in Fusion's *Scripts and Add-Ins* dialog.

## Use

1. In Cutaway HQ, export your sections with **Refined 2D DXF (zipped)**.
2. In Fusion: **DESIGN → MODIFY → Cutaway: Import Sections**.
3. Pick the zip. Each `.dxf` becomes a sketch on its own plane.

## Update

When a newer version is on GitHub, an extra **Cutaway: Update to vX.Y.Z**
button appears in the MODIFY panel. Click it to open the release page;
re-run the install script.

## Status

v0.1.0 — first scaffold. Imports axis-aligned planar sections (XY / XZ /
YZ + offset). Face / 3-point / derived / tilted sections are reported as
skipped — re-export those as axis-aligned planes for now.

## Repo layout

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[CLAUDE.md](CLAUDE.md).

## Related

- **[cutawayhq.com](https://cutawayhq.com)** — the web app that produces
  the zips this add-in consumes.

## License

MIT — see [LICENSE](LICENSE).
