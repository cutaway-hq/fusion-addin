# Architecture

Cutaway is intentionally tiny. There are four files in `src/` and a thin
`Cutaway.py` entry point that Fusion calls. Everything else is docs and
distribution scaffolding.

## File layout

```
fusion-addin/
├── Cutaway.py              # Fusion calls run() / stop() here
├── Cutaway.manifest        # add-in metadata (name, author, id, version)
├── version.json            # source of truth for the running version
├── src/
│   ├── ui.py               # registers the MODIFY-panel button(s)
│   ├── importer.py         # zip → manifest or filename → plane → import
│   ├── manifest.py         # cutaway.json reader (preferred metadata source)
│   ├── plane_resolver.py   # builds construction planes (offset / 3-point)
│   └── updater.py          # background GitHub Releases poll
├── install/                # per-platform install scripts
└── docs/                   # this folder
```

## Runtime flow

1. **Fusion starts** (with the add-in enabled in *Run on Startup*).
2. Fusion calls `Cutaway.py:run()`, which delegates to `ui.start()`.
3. `ui.start()`:
   - Registers the `Cutaway: Import Sections` button in the MODIFY panel.
   - Calls `updater.check_in_background()` — a daemon thread hits the GitHub
     Releases API and stashes a "newer version exists" record if it finds one.
   - Looks up `updater.get_pending_update()`. If non-null, also registers a
     second button: `Cutaway: Update to vX.Y.Z`.
4. **User clicks Import** → file dialog → user picks a `.zip`.
5. `importer.import_zip(path)`:
   - Extracts the zip into a temp dir.
   - Tries `manifest.read_from_dir()`. If `cutaway.json` exists, take the
     **manifest path**: walk every entry, build the right plane per kind
     (axis-aligned planar → offset from base; everything else → three-point
     construction), then `ImportManager.createDXF2DImportOptions(file, plane)`
     + `ImportManager.importToTarget(opts, root_component)`.
   - If no manifest, fall back to the **filename path**: `plane_resolver.parse_filename()`
     on each `.dxf`. Only axis-aligned planar sections are recoverable that
     way — face / 3-point / derived / tilted are reported as skipped.
   - Aggregates a summary message and shows it in a `messageBox`.
6. **User clicks Update** (only if visible) → `webbrowser.open(release_url)`.
7. **Fusion stops the add-in** → `stop()` → `ui.stop()` removes both buttons
   and clears the handlers list.

## Why each piece exists

| File | Reason |
|------|--------|
| `Cutaway.py` | Fusion expects a top-level module with `run()` / `stop()`. Keep it thin so the entry surface is obvious. |
| `Cutaway.manifest` | Required by Fusion. The `id` UUID identifies this add-in across versions; **don't change it** between releases or Fusion treats it as a new add-in. |
| `version.json` | Single source of truth for the running version. The release workflow can rewrite it in CI; the updater compares against the GitHub `tag_name`. |
| `src/ui.py` | All Fusion-UI plumbing lives here. The handlers are kept in a module-level list so Fusion's GC doesn't drop them mid-callback (a known Fusion gotcha). |
| `src/importer.py` | Pure import logic. Easy to read top-to-bottom. Per-file failures don't kill the batch; everything funnels into a single summary message. Two paths: manifest-based (preferred, supports every section kind) and filename-based (legacy fallback for axis-aligned planar only). |
| `src/manifest.py` | `cutaway.json` reader. Validates schema version, returns a parsed dict or `None`. Never raises — falling back to filename parsing is the right behaviour on malformed manifests. |
| `src/plane_resolver.py` | Builds Fusion `ConstructionPlane`s. Two construction methods: offset-from-base (axis-aligned planar) and three-point (anything else — pins both plane orientation AND in-plane rotation so the imported sketch lands aligned with the section's original U/V frame). |
| `src/updater.py` | Network I/O is in a daemon thread on purpose — a slow/unreachable GitHub must never block Fusion startup or the importer. |

## What's intentionally NOT here

- **No bundled dependencies.** Fusion ships its own Python; we use only the
  stdlib (`urllib`, `zipfile`, `tempfile`, `re`, `json`, `threading`,
  `webbrowser`). Adding a wheel makes installation much harder.
- **No background polling on a timer.** `check_in_background()` runs once per
  Fusion session (when `start()` is called). Picks the new release up the
  next time the user restarts Fusion. Simple, predictable.
- **No telemetry.** Nothing leaves the user's machine besides the one
  unauthenticated GitHub Releases request.
- **No 3D / multi-plane single-DXF import.** That path was deliberately
  parked — see `docs/FUSION_API_NOTES.md` for why.

## Where to edit when…

- **Web app changes the manifest schema** → bump `SUPPORTED_VERSIONS` in
  `src/manifest.py`, update field handling in `src/importer.py`'s
  `_build_plane_from_manifest`. The schema is documented in `manifest.py`'s
  module docstring — keep it in sync with `cad-app/src/viewer/bulkSectionExport.ts`.
- **Web app changes the filename suffix** (only matters for the legacy
  fallback path now) → `src/plane_resolver.py` (`PLANAR_RE` and `PlanarInfo`).
- **Need to change which Fusion panel hosts the button** → `src/ui.py`
  (`PANEL_ID` / `WORKSPACE_ID`).
- **Need to add a new format (e.g. STL marketplace download)** → new module
  in `src/`, register a new button in `ui.py`, document in `CLAUDE.md`.
- **Need to bump version** → `version.json` + `Cutaway.manifest` (keep them
  in sync) + tag and push (`vX.Y.Z`) — see `docs/RELEASE.md`.
