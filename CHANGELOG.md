# Changelog

All notable changes to Cutaway. Format inspired by
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org).

## v0.2.1 — 2026-07-12

### Fixed
- Palette no longer shows blank on its first open. The HTML loads while the
  palette is hidden (created eagerly at `start()`), and the embedded
  Chromium skips painting hidden views — the first reveal stayed unpainted
  until a resize (minimize/restore "fixed" it). The toggle handler now
  nudges the palette height by 1px right after showing it, forcing the
  missing layout pass invisibly. Found by Davud in the first production
  install test.

## v0.2.0 — 2026-07-12

### Fixed
- **The "Update available" button can now actually appear.** The update
  check stored its result only in module memory, but `ui.start()` reads the
  pending state immediately after firing the check (the network result
  lands too late) and module memory dies with Fusion — so the button was
  unreachable on any normal launch. The worker now also persists its result
  to `.update_check.json` next to `version.json`; the next session's
  `start()` reads that cache. The cache re-validates against the current
  local version (and is deleted once the local version catches up), so a
  stale prompt can't outlive the update.
- Manifest entries without placement fields (the fitter's `kind:
  "imported"` — DXFs loaded standalone, never cut from a mesh) are skipped
  with an explicit "no 3D placement in manifest" message instead of falling
  through to the tilted path's default normal and a misleading "normal has
  no XY component" error.
- Removed the explicit `tiltU`/`tiltV` check from
  `planar_info_from_manifest` — a real tilt already shows in the normal,
  and the check diverged from the web app in the sub-tolerance window
  (tilt < ~0.06°): the app exported such sections as axis-aligned but the
  add-in rejected them from both paths and skipped them entirely.
- `install.bat` now clears `src/` and `resources/` before copying (matching
  `install.sh`), so files renamed or deleted by a newer version don't
  linger from the previous install on Windows.
- The Update button's click handler got the same try/except + messageBox
  wrapper as every other handler.
- Unknown manifest `unit` values (e.g. the fitter's `"unitless"`) are now
  normalized to `mm` — the same default as a missing unit — instead of
  falling through the unit table as factor 1.0 (centimetres, Fusion's
  internal unit), which silently placed every plane at 10× the correct
  depth for mm parts. (The fitter side was also fixed to write a real unit
  whenever one is known.)
- Palette is now created hidden. Creating it visible broke the toolbar
  toggle when the palette had to be recreated inside the click handler
  (it appeared visible and the toggle immediately hid it — first click did
  nothing, second worked).
- Updater worker: the whole response handling now sits inside the
  try/except, so an unexpected JSON shape (non-dict body) can't traceback
  in the daemon thread ("failures are silent" contract).
- Import temp dir switched to `mkdtemp` + best-effort `rmtree`: a Windows
  cleanup failure (AV holding a handle on an extracted DXF) after a
  successful import no longer replaces the summary dialog with a raw
  traceback.
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
- Docs refreshed to match the code: `INSTALL.md` no longer describes the
  pre-palette flow ("Cutaway: Import Sections" opening a file dialog
  directly) and its troubleshooting section reflects the manifest-era
  importer; `ARCHITECTURE.md` no longer claims tilted planes use
  "three-point construction" (it's `setByAngle` + a shared helper sketch).

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
