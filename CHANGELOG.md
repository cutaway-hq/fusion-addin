# Changelog

All notable changes to Cutaway. Format inspired by
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org).

## Unreleased

### Added
- `cutaway.json` manifest support — the importer now reads full section
  metadata (origin, normal, u-axis, v-axis, kind) from a manifest at the
  top of the zip. **Face, 3-point, derived, and tilted sections are now
  importable** (previously skipped because filenames carry no orientation).
- **Tilted plane construction** via `setByAngle` with a shared hidden helper
  sketch. The helper sketch is created lazily on the first tilted section
  and reused across all tilted sections in one import — 1 sketch + 1 plane
  per tilted section instead of 13 entities each. Works for any section
  whose plane intersects XY (every plane that isn't parallel to it).
- **Axis-aligned dispatch by normal vector**, not section kind. A face / 3-
  point / derived section whose normal happens to be along ±X / ±Y / ±Z
  now takes the cleaner `setByOffset` path and lands at the correct world
  position with correct rotation — same as a planar tool section.
- `install/dev-link.bat` — creates a junction from Fusion's AddIns folder
  to the source repo so iterative dev doesn't need re-running install.bat.
- `docs/COORDINATE_SYSTEMS.md` — captures the chain of coordinate
  transformations between web app, manifest, DXF, and Fusion's sketch frame.
  Read this before changing anything in the import pipeline.

### Changed
- Importer summary now reports which path it took: "imported N sections via
  manifest" vs. "via filename (no cutaway.json)".
- Per-step error reporting in the importer (plane construction vs. DXF
  import) so failures point to the right Fusion API call instead of a
  generic "InternalValidationError".
- Tolerance for "is this normal axis-aligned?" bumped from `1e-6` to `1e-3`
  in both the web app (`axisAlignedWorldFrame`, `tiltedWorldFrame`) and
  the add-in (`_AXIS_TOL`). Tight tolerance was misclassifying 3-point
  sections through coplanar points (whose normal carries floating-point
  noise from the cross-product) as "tilted", routing them to the
  setByAngle path with weird rotations. The three values must stay in
  lockstep.

### Fixed
- Bulk-export filenames now include the placement suffix (was just
  `Section_5_refined.dxf`, now `Section_5__YZ_X87.49_dx-2.9_dy38.25_mm_refined.dxf`).
- Placement-suffix regex no longer requires the unit to be immediately
  followed by `.dxf` — now accepts `_refined`, `_2`, etc. between unit and
  extension.
- `ImportManager.importToTarget()` now receives the root Component instead
  of the Design (Fusion required a Component target).
- Helper sketch is hidden via `isVisible = False` (the property is
  `isVisible` on Sketch; `isLightBulbOn` is for ConstructionPlane only and
  silently throws when assigned to a Sketch).
- `isComputeDeferred = True` on the helper sketch was preventing newly-added
  sketch lines from rendering — removed.

### Known limitations
- The tilted-section path empirically matches Fusion's `setByAngle` sketch
  convention (sketch X = line direction, etc.) on the version we tested. If
  Fusion ever changes that convention, all genuinely tilted sections will
  land mis-rotated within their plane. Fallback fix is documented in
  `docs/COORDINATE_SYSTEMS.md` — a post-import sketch transform that walks
  `sketchPoints` and moves each one to its intended world position.

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
