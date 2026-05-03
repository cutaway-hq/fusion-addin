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
│   ├── importer.py         # zip → loop DXFs → import each onto its plane
│   ├── plane_resolver.py   # filename → ConstructionPlane
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
   - Walks every `.dxf`, calls `plane_resolver.parse_filename()` to extract
     `{plane, depth_axis, depth, dx, dy, unit}`.
   - For each parsed file: creates a `ConstructionPlane` offset from the
     base XY/XZ/YZ at the right depth (in cm — Fusion's API unit), then uses
     `ImportManager.createDXF2DImportOptions(file, plane)` +
     `ImportManager.importToTarget(...)` to land the sketch.
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
| `src/importer.py` | Pure import logic. Easy to read top-to-bottom. Per-file failures don't kill the batch; everything funnels into a single summary message. |
| `src/plane_resolver.py` | Filename schema is the contract with the Cutaway web app. If the web app's suffix format changes, this is the only file that needs updating. |
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

- **Web app changes the filename suffix** → `src/plane_resolver.py`
  (`PLANAR_RE` and `PlanarInfo`).
- **Need to change which Fusion panel hosts the button** → `src/ui.py`
  (`PANEL_ID` / `WORKSPACE_ID`).
- **Need to add a new format (e.g. STL marketplace download)** → new module
  in `src/`, register a new button in `ui.py`, document in `CLAUDE.md`.
- **Need to bump version** → `version.json` + `Cutaway.manifest` (keep them
  in sync) + tag and push (`vX.Y.Z`) — see `docs/RELEASE.md`.
