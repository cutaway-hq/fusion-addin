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
│   ├── ui.py               # registers the MODIFY-panel button + HTML Palette
│   ├── importer.py         # zip → manifest or filename → plane → import
│   ├── manifest.py         # cutaway.json reader (preferred metadata source)
│   ├── plane_resolver.py   # builds construction planes (offset / setByAngle)
│   └── updater.py          # background GitHub Releases poll
├── resources/
│   ├── cutaway/            # toolbar button PNG icons (16/32/64)
│   ├── palette/            # HTML/CSS/JS for the Cutaway Palette
│   └── generate_icons.py   # regenerates the PNGs from pure stdlib
├── install/                # per-platform install scripts
└── docs/                   # this folder
```

## Runtime flow

1. **Fusion starts** (with the add-in enabled in *Run on Startup*).
2. Fusion calls `Cutaway.py:run()`, which delegates to `ui.start()`.
3. `ui.start()`:
   - Registers the `Cutaway` toolbar button in the MODIFY panel, with the
     icon from `resources/cutaway/`.
   - Registers (but does not show) the Cutaway HTML Palette, sourcing
     `resources/palette/index.html`.
   - Wires the toolbar button to toggle the Palette open/closed.
   - Registers an HTMLEvent handler on the Palette so its JS can call into
     Python (e.g., the "Import sections" button posts an `import` action).
   - Calls `updater.check_in_background()` — a daemon thread hits the GitHub
     Releases API and, if a newer version exists, stashes a record in module
     state and in a small cache file (`.update_check.json`, next to
     `version.json`) so the result survives the Fusion restart.
   - Looks up `updater.get_pending_update()` — on a fresh launch this reads
     the cache written by a *previous* session's check (this session's probe
     hasn't finished yet). If non-null, also registers a second toolbar
     button: `Cutaway: Update to vX.Y.Z`.
4. **User clicks the Cutaway button** → Palette opens (or closes if it was already open).
5. **User clicks "Import sections" inside the Palette** → JS posts `import`
   to Python → Python opens the file dialog → user picks a `.zip`.
6. `importer.import_zip(path)`:
   - Extracts the zip into a temp dir.
   - Tries `manifest.read_from_dir()`. If `cutaway.json` exists, take the
     **manifest path**: walk every entry, build the right plane per normal
     (axis-aligned → offset from base; tilted → `setByAngle` around a helper
     sketch line), then `ImportManager.createDXF2DImportOptions(file, plane)`
     + `ImportManager.importToTarget(opts, root_component)`.
   - If no manifest, fall back to the **filename path**: `plane_resolver.parse_filename()`
     on each `.dxf`. Only axis-aligned planar sections are recoverable that
     way — face / 3-point / derived / tilted are reported as skipped.
   - Aggregates a summary message and shows it in a `messageBox`.
7. **User clicks Update** (only if visible) → `webbrowser.open(release_url)`.
8. **Fusion stops the add-in** → `stop()` → `ui.stop()` removes the Palette,
   removes both toolbar buttons, and clears the handlers list.

## Why each piece exists

| File | Reason |
|------|--------|
| `Cutaway.py` | Fusion expects a top-level module with `run()` / `stop()`. Keep it thin so the entry surface is obvious. |
| `Cutaway.manifest` | Required by Fusion. The `id` UUID identifies this add-in across versions; **don't change it** between releases or Fusion treats it as a new add-in. |
| `version.json` | Single source of truth for the running version. The release workflow fails the build if it diverges from the tag; the updater compares it against the GitHub `tag_name`. |
| `src/ui.py` | All Fusion-UI plumbing lives here. The handlers are kept in a module-level list so Fusion's GC doesn't drop them mid-callback (a known Fusion gotcha). |
| `src/importer.py` | Pure import logic. Easy to read top-to-bottom. Per-file failures don't kill the batch; everything funnels into a single summary message. Two paths: manifest-based (preferred, supports every section kind) and filename-based (legacy fallback for axis-aligned planar only). |
| `src/manifest.py` | `cutaway.json` reader. Validates schema version, returns a parsed dict or `None`. Never raises — falling back to filename parsing is the right behaviour on malformed manifests. |
| `src/plane_resolver.py` | Builds Fusion `ConstructionPlane`s. Two construction methods: offset-from-base (axis-aligned normals) and `setByAngle` around a line in a shared hidden helper sketch (tilted normals). The web app pre-aligns each DXF's coordinates to the sketch frame Fusion picks for these constructions — see `docs/COORDINATE_SYSTEMS.md`. |
| `src/updater.py` | Network I/O is in a daemon thread on purpose — a slow/unreachable GitHub must never block Fusion startup or the importer. |
| `resources/cutaway/` | PNG icons (16/32/64) shown next to the toolbar button. Fusion finds them by convention: it looks in the `resourceFolder` path for files named `16x16.png`, `32x32.png`, `64x64.png`. |
| `resources/palette/` | HTML/CSS/JS for the Cutaway Palette. Inline single-file `index.html` for simplicity — no build step needed. The JS calls `adsk.fusionSendData(action, jsonStr)` to message Python; Python handles those actions in an `HTMLEventHandler`. |
| `resources/generate_icons.py` | Regenerates the PNGs from scratch using pure stdlib (`struct` + `zlib`). Lets a maintainer change the icon style without needing Pillow or graphics tooling. |

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
  module docstring — keep it in sync with `slice-app/src/viewer/bulkSectionExport.ts`.
- **Web app changes the filename suffix** (only matters for the legacy
  fallback path now) → `src/plane_resolver.py` (`PLANAR_RE` and `PlanarInfo`).
- **Need to change which Fusion panel hosts the button** → `src/ui.py`
  (`PANEL_ID` / `WORKSPACE_ID`).
- **Need to add a new format (e.g. STL marketplace download)** → new module
  in `src/`, register a new button in `ui.py`, document in `CLAUDE.md`.
- **Need to bump version** → `version.json` + `Cutaway.manifest` (keep them
  in sync) + tag and push (`vX.Y.Z`) — see `docs/RELEASE.md`.
