# Changelog

All notable changes to Cutaway. Format inspired by
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org).

## Unreleased

_Nothing yet._

## v0.1.0 — 2026-05-03

### Added
- Initial scaffold of the Fusion 360 add-in.
- **Cutaway: Import Sections** button in the DESIGN → MODIFY panel.
- Bulk DXF zip importer: each axis-aligned planar section becomes a sketch
  on its own construction plane at the correct depth.
- Background update check against GitHub Releases — surfaces an
  **Update available** button when a newer tag exists.
- Windows + macOS install / uninstall scripts.
- GitHub Actions release workflow: tag push → builds zip → publishes
  GitHub Release with auto-generated notes.
- Architecture, release, versioning, install, and Fusion-API-gotchas docs.
- `CLAUDE.md` AI handoff doc.

### Known limitations
- Face / 3-point / derived / tilted sections are skipped (no plane info in
  the filename suffix). Re-export as axis-aligned planes.
