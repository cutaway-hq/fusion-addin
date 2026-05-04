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
- For arbitrary planes (face / 3-point / derived / tilted sections):
  - `setByThreePoints(p1, p2, p3)` **does NOT accept raw `Point3D`
    arguments** despite what the type signature implies. It throws
    `InternalValidationError : data_->execute(&obj, apiName) && obj`. It
    requires *anchored* construction entities — `ConstructionPoint`,
    `SketchPoint`, or `BRepVertex`. Painful but documented quirk.
  - `setByPlane(planarEntity)` **does NOT accept a math `adsk.core.Plane`**
    despite the type. It wants an existing planar *entity* (face / work
    plane / sketch). Passing a math Plane raises
    `RuntimeError: 3 : Environment is not supported`.
  - **What we do**: create three `ConstructionPoint`s via
    `ConstructionPointInput.setByPoint(Point3D)` (which DOES accept raw
    points), then feed those to `setByThreePoints`. P1 = origin, P2 = origin+u,
    P3 = origin+v — pins both the plane and its in-plane rotation so
    imported DXF sketches land aligned with the section's U/V frame.
  - **Inconsistent collection paths**: construction *points* must be
    created via `component.features.constructionPointFeatures.add(input)`
    — the seemingly-equivalent `component.constructionPoints.add(input)`
    raises `RuntimeError: 3 : Environment is not supported`. Construction
    *planes* accept either path. Don't ask why.
  - The construction points are toggled `isLightBulbOn = False` to hide
    them from the viewport; they remain in the timeline because the plane
    is parametrically dependent on them. Three CPs per non-planar section
    is the cost of correctness here.

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
