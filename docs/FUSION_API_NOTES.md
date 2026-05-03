# Fusion API gotchas

Things that bit us during development. Read before changing
`src/importer.py` or `src/plane_resolver.py`.

## Units

- **Fusion's API works in centimetres internally**, regardless of the
  active document's display unit. Anything you pass to `ValueInput.createByReal()`
  has to be in cm. Our exports use mm/cm/m/in; `plane_resolver.to_cm()`
  does the conversion at the boundary.
- The display unit in the Fusion UI is independent of API units — a sketch
  imported with cm-based offsets will still display in whatever unit the
  document is set to.

## Construction planes

- The base planes are `component.xYConstructionPlane`,
  `component.xZConstructionPlane`, `component.yZConstructionPlane`.
- `setByOffset(base, ValueInput)` is the simplest path for axis-aligned
  offsets. Negative distance flips to the other side.
- For tilted / non-axis-aligned planes you'd need
  `setByThreePoints(p1, p2, p3)` or `setByPlane(planarEntity)`. We don't do
  that in v1 — the web app's filename suffix doesn't carry enough info to
  reconstruct an arbitrary orientation, and the *correct* fix is to write a
  richer manifest into the zip (a JSON sibling per DXF) rather than parse
  filenames.

## ImportManager

- `ImportManager.createDXF2DImportOptions(filepath, planarEntity)` —
  `planarEntity` accepts a `ConstructionPlane`, a `BRepFace`, or a sketch
  plane. We use construction planes.
- `importToTarget(options, target)` — `target` is the active product
  (`adsk.fusion.Design.cast(app.activeProduct)`).
- The DXF importer creates a single new sketch per import. There's no API
  to merge into an existing sketch — each section is its own sketch.
- It does **not** join coincident endpoints between different sketches, so
  even if two sections share a plane and an endpoint, they're separate
  sketches. That's fine for our use case (each section = its own
  reference).

## Event handlers and GC

- Fusion's Python wrapper uses weak references for event handlers. If you
  do `cmd_def.commandCreated.add(MyHandler())` without keeping a strong
  reference, Python's GC may reap the handler before Fusion calls it,
  silently breaking the button.
- `ui.py` keeps a module-level `_handlers: list` and appends every handler
  it creates. **Don't remove that list without understanding the
  consequences.**

## Workspace and panel IDs

- `FusionSolidEnvironment` is the DESIGN workspace.
- `SolidModifyPanel` is the MODIFY panel inside DESIGN.
- IDs are stable across Fusion versions but Autodesk has been known to
  change them. If the button ever fails to appear after a Fusion update,
  log the available panel IDs:

  ```python
  for ws in ui.workspaces:
      print(ws.id)
      for p in ws.toolbarPanels:
          print('  ', p.id)
  ```

## Threading

- The Fusion API is **not thread-safe**. Don't call `adsk.core.Application`
  / `adsk.fusion` methods from worker threads.
- `updater.check_in_background()` is OK because it only does network I/O
  and writes to a Python module-level variable. The UI reads that variable
  from the main thread when `start()` runs.

## Known limitations we accept

- **No incremental import.** Re-running the importer always creates new
  sketches; it doesn't replace ones from a prior import. The user can
  delete old sketches manually if they want a clean slate.
- **No sketch naming.** We let Fusion's auto-naming take over. If we want
  named sketches in a future version, we'd have to look up the most-recently
  created sketch after each `importToTarget` call and rename it (the API
  doesn't return the new sketch directly).
- **No undo grouping.** Each import is a separate undo step. Wrapping the
  whole batch in a single undo step requires a custom feature, which is
  more complex than v1 needs.
