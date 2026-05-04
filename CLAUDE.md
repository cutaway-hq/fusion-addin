# CLAUDE.md — Cutaway Fusion add-in

This file is the AI handoff doc. Read it before making changes; keep it in
sync when you change anything load-bearing.

## What this repo is

A Fusion 360 add-in (Python) that imports section exports from the
[Cutaway HQ web app](https://cutawayhq.com) into the active design. Each
DXF in the user's zip becomes a sketch on a construction plane positioned
at the section's real-world depth. Distributed via GitHub Releases; users
re-run a small install script to update.

The add-in deliberately does the **minimum** that beats the manual Fusion
"Insert DXF" workflow (which would force the user to dial in an X / Y / Z
offset for every section by hand).

## Where things live

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full file map and
runtime flow. Quick orientation:

- `Cutaway.py` — Fusion's entry point, calls `src/ui.py`.
- `src/ui.py` — registers the **Cutaway: Import Sections** button in the
  DESIGN → MODIFY panel; also registers an **Update available** button if
  one is pending.
- `src/importer.py` — opens the zip, walks the DXFs, drives the import.
- `src/plane_resolver.py` — parses the placement suffix in the filename.
- `src/updater.py` — daemon thread checks GitHub Releases once per session.

## How to read the codebase

Top-down: open `Cutaway.py`, then `src/ui.py`, then follow the button's
handler into `src/importer.py`. Everything is short on purpose; if you find
yourself wanting to factor things out, push back — the value of staying
small is bigger than the value of "clean" abstractions for a 200-line
add-in.

## The contract with the web app

The zip carries a **`cutaway.json` manifest** at its top level. That's the
authoritative source of geometry for every section — origin, normal,
u-axis, v-axis, kind. Reading it is much more robust than parsing
filenames, and it makes face / 3-point / derived / tilted sections
importable (the filename alone can't carry orientation).

Schema is documented in `src/manifest.py`'s module docstring; the writer
side lives in `cad-app/src/viewer/bulkSectionExport.ts`. Keep them in
lockstep — bump `version` and the reader's `SUPPORTED_VERSIONS` together
on breaking changes.

### Filename suffix (legacy fallback)

Older zips (or third-party DXFs) might not have a manifest. For those, the
importer parses the placement suffix in each filename:

```
<sketchName>__<Plane>_<DepthAxis><DepthValue>_dx<X>_dy<Y>_<unit>.dxf
                ^XY|XZ|YZ ^X|Y|Z   signed   signed signed  mm|cm|m|in
```

Only **axis-aligned planar** sections survive this path. Face / 3-point /
derived / tilted sections export with the `__at_X<x>_Y<y>_Z<z>_<unit>`
form which carries no orientation; they get reported as skipped if the
manifest is missing.

The web app currently writes BOTH the manifest AND the placement suffix in
filenames. Filenames stay human-readable; the manifest is what the importer
actually trusts.

## Constraints to respect

- **Stdlib only.** Fusion ships its own Python; no `pip install`. If you
  need an external library, find another way.
- **Never block Fusion's main thread on network I/O.** The updater runs in
  a daemon thread on purpose. Don't replace it with a blocking request.
- **Don't change the manifest `id` UUID.** Fusion uses it to track the
  add-in across versions. Changing it = users see two add-ins.
- **Keep `version.json` and `Cutaway.manifest` in sync.** The release
  workflow has a CI check that fails if they diverge from the tag.
- **Don't add features beyond what's asked.** The user has been explicit
  that scope creep is undesired. Pre-existing code that's "kept but not
  surfaced" (combined 3D DXF import, etc.) is intentional — discuss before
  re-introducing.

## Behavior decisions worth knowing

| Decision | Why |
|----------|-----|
| Update check is in-process, fired once at `start()`, results surface only on next Fusion restart | Predictable; avoids surprise prompts mid-session |
| Update affordance opens GitHub release page in a browser; no auto-download | Keeps install path the same as a fresh install (one path to debug) |
| Per-file failures don't kill the batch; failures are listed in the summary | A bad DXF shouldn't waste the rest of a 50-section import |
| Each section is a separate sketch, no auto-grouping | Fusion's API doesn't merge sketches; matches user mental model |
| File-picker only, no "watch this folder" mode | Simplest possible v1, matches the web app's "Export zip" UX |

## What the user has explicitly said NOT to do

- Don't surface SVG export anywhere (the functions exist in the web app
  but the buttons are removed).
- Don't surface combined 3D DXF (raw or refined) in the web app UI either
  — kept in code for possible future use.
- Don't add the "import combined multi-layer 3D DXF" path to this add-in.
  The user evaluated it and decided the per-plane manual adjustment burden
  in Fusion outweighs the convenience.

## Adding a new feature

1. Read `docs/ARCHITECTURE.md` to find the right module.
2. Add the feature with **as little new structure as possible** (one new
   function, one new button — not a class hierarchy).
3. Update `docs/ARCHITECTURE.md` if the runtime flow changed.
4. Update this file's "Behavior decisions worth knowing" table if the new
   feature has a UX rationale future-readers should understand.
5. Bump the minor version (see `docs/VERSIONING.md`) and follow
   `docs/RELEASE.md`.

## Cutting a release

See `docs/RELEASE.md`. TL;DR: bump version in two files + CHANGELOG, tag
`vX.Y.Z`, push tag, CI builds and publishes.

## Related projects

- **`../cad-app/`** — the Vite + React + Three.js web app at
  cutawayhq.com that produces the zips this add-in consumes. The exporter
  responsible for the filename schema lives in
  `cad-app/src/viewer/SectionViewer.tsx` (`placementSuffix`) and
  `cad-app/src/viewer/bulkSectionExport.ts`.
- **GitHub org:** [cutaway-hq](https://github.com/cutaway-hq).
