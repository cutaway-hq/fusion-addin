# Coordinate systems & conventions

The hardest thing about this codebase isn't any single function — it's the
chain of coordinate transformations between the web app, the manifest, the
DXF, and Fusion's sketch frame. This doc captures the mental model so
future-you (or a future AI) doesn't have to rediscover it from code alone.

## The big picture

```
   Web app (Three.js)           Zip on disk           Fusion 360
 ┌────────────────────┐    ┌──────────────────┐    ┌──────────────────┐
 │  3D contour points │    │  cutaway.json    │    │  ConstructionPlane│
 │  in WORLD coords   │ → │  + per-section   │ → │  + Sketch + DXF  │
 │                    │    │  *.dxf files     │    │  geometry        │
 │  Section frame:    │    │                  │    │                  │
 │   origin / N /     │    │  DXF coords =    │    │  Sketch axes are │
 │   U axis / V axis  │    │  contour pt      │    │  picked by Fusion│
 │                    │    │  projected onto  │    │  based on plane  │
 │                    │    │  (U, V) frame    │    │  construction    │
 └────────────────────┘    └──────────────────┘    └──────────────────┘
```

Each box is its own coordinate system. The whole pipeline is about making
sure they line up so the imported geometry lands at the right world
position with the right orientation.

## The contract: cutaway.json

The manifest is the **single source of truth** for plane reconstruction.
Schema is documented in `src/manifest.py`'s docstring; the writer side is
in `slice-app/src/viewer/bulkSectionExport.ts`. Per-section entry:

```json
{
  "file":   "Section_5__XY_Z12.34_dx0_dy0_mm_refined.dxf",
  "name":   "Section 5",
  "kind":   "plane" | "face" | "derived",
  "origin": [x, y, z],            // 3D point on the section plane (in mm/cm/m/in)
  "normal": [nx, ny, nz],         // unit vector
  "uAxis":  [ux, uy, uz],         // unit vector, in the section plane (sketch X)
  "vAxis":  [vx, vy, vz],         // unit vector, in the section plane (sketch Y)
  "plane":  "XY" | "XZ" | "YZ" | null,  // hint, planar tool only
  "tiltU":  0,                    // hint, planar tool only
  "tiltV":  0
}
```

A contour point's 3D world position is reconstructed as:

```
P_world = origin + dxf_x * uAxis + dxf_y * vAxis
```

where `(dxf_x, dxf_y)` is what's in the DXF.

If the manifest schema ever changes, bump `version` in `manifest.py`'s
`SUPPORTED_VERSIONS` AND in the web app's writer in lockstep.

## Two flavours of section, two export overrides

The DXF coords aren't always written using the section's natural U/V
frame. The web app applies one of two overrides at export time so that
when Fusion later imports the DXF onto a construction plane, the
geometry lands aligned without a post-import transform.

### AXIS_ALIGNED_WORLD_FRAME

Triggers when the section's normal is along ±X / ±Y / ±Z (within
tolerance — see "The 1e-3 lesson" below). Per-plane DXF axes:

| Section plane (normal) | DXF X      | DXF Y       | DXF origin                |
|------------------------|------------|-------------|---------------------------|
| XY (normal ±Z)         | world +X   | world +Y    | (0, 0, depth_z)           |
| XZ (normal ±Y)         | world +X   | world **−Z**| (0, depth_y, 0)           |
| YZ (normal ±X)         | world +Y   | world +Z    | (depth_x, 0, 0)           |

The XY and YZ rows are intuitive — DXF coords match world coords within
the plane. **The XZ row has a sign flip on V** because Fusion's
`xZConstructionPlane` sketches with sketch Y = world **−Z** (right-hand
rule: the plane normal is +Y and X × −Z = +Y, so sketch Y must point
along world −Z to keep things right-handed). Without this flip, every
axis-aligned XZ-parallel section lands mirrored across Z=0 in Fusion —
contours appear "below" the geometry by 2× their world Z. The flip
cancels Fusion's sign so the contour ends up at its true world Z; **no
visible mirror in world space**.

(YZ is left intuitive on the assumption Fusion's `yZConstructionPlane`
follows sketch X = world Y, sketch Y = world Z — typical CAD
convention. If a YZ section ever lands mirrored across the Y axis, flip
its V the same way.)

When Fusion creates the sketch via `setByOffset(base_plane, depth)`,
its default sketch axes line up with the table above — the geometry
lands at its correct world position with no further work.

The override fires regardless of section kind (planar tool, face,
3-point, derived), so a face section on a top face becomes equivalent
to a planar XY section.

### TILTED_WORLD_FRAME

Triggers when the normal is *not* axis-aligned. For these:

- DXF X axis = `(-Ny, Nx, 0) / |Nxy|` — the direction of the section
  plane's intersection with the XY plane
- DXF Y axis = `N × DXF_X` — perpendicular within the section plane
- DXF origin = `N · (N · sectionOrigin)` — projection of world origin
  onto the section plane (Fusion's natural pick for `setByAngle` planes)

This is the *guess* at what Fusion will pick when it builds the plane
via `setByAngle(line, angle, XY)`. Empirically verified to work on
Fusion 2026.x but undocumented — see "The fragility" section.

## Plane construction in Fusion

Mirrors the export overrides. For each manifest entry:

### Axis-aligned → `setByOffset`

```python
plane_input.setByOffset(base, ValueInput.createByReal(depth_cm))
```

`base` is one of `xYConstructionPlane / xZConstructionPlane /
yZConstructionPlane`. 0 helper entities. The resulting sketch's axes
match world axes (because base planes do).

### Tilted → `setByAngle` with a helper sketch line

```python
sketch_line = helper_sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2)
plane_input.setByAngle(sketch_line, ValueInput.createByReal(angle), xYConstructionPlane)
```

The helper sketch is **shared across all tilted sections** in one import,
created lazily on the first tilted section. It lives at name "Cutaway
helpers (do not delete)" and is hidden via `isVisible = False`. Cost: 1
shared sketch + 1 plane per tilted section, instead of 13 entities each
(see `FUSION_API_NOTES.md` for the construction-points alternative we
rejected).

The intersection-line direction comes from `axis = z × n`, the angle
from `atan2(|Nxy|, Nz)`. Both math-checked: rotating the XY plane by
that angle around that axis lands its normal at N.

## The 1e-3 lesson

A face section through three coplanar points (e.g., 3 points all on a
top face) *should* have a normal of exactly `(0, 0, 1)` in theory. In
practice, the cross-product computation produces a normal like
`(0.000146, 0.00155, 0.99999...)` — accurate but not bit-exact.

When we use a strict tolerance (1e-6) for "axis-aligned?", the noise
fails the check and the section gets routed to the tilted path with a
weird helper-line direction `(-Ny, Nx, 0)/|Nxy|` that depends entirely
on the noise direction. Result: import lands rotated by some
unpredictable angle.

Tolerance of **1e-3** absorbs the noise. The cost is treating sections
with up to ~0.06° of true tilt as axis-aligned — well below anything
intentional in CAD work. Detection thresholds:
- `slice-app/src/viewer/sectionFrame.ts` (axisAlignedWorldFrame, tiltedWorldFrame)
- `fusion-addin/src/plane_resolver.py` (`_AXIS_TOL`)

These three values must stay in lockstep.

## The fragility (and the fallback if it ever bites)

The tilted path bets on Fusion's `setByAngle` sketch convention being
exactly what `TILTED_WORLD_FRAME` assumes:

- Sketch X = the line direction we passed (P1 → P2)
- Sketch Y = `N × sketch_X`
- Sketch origin = `N · (N · point_on_plane)`

This is empirically true on Fusion 2026.x but undocumented. If a future
Fusion release changes any of those choices, all genuinely tilted
sections will land mis-rotated or mis-translated within their plane.

**Fallback if that happens** — a post-import sketch transform:

1. After each tilted import, find the new sketch
2. Query its `origin`, `xDirection`, `yDirection`
3. For each `SketchPoint sp` at 2D coords `(sx, sy)`:
   - Current world position: `f_origin + sx * f_xDir + sy * f_yDir`
   - Intended world position: `intended_origin + sx * intended_U + sy * intended_V`
     (intended frame = section's natural frame from the manifest, *without*
     `tiltedWorldFrame` override)
   - `sp.move(Vector3D.create(dx, dy, dz))` with the delta
4. Lines / arcs / circles transform automatically because they're built
   on top of `SketchPoint`s

This decouples us from Fusion's convention entirely. If we ever
implement it, also remove `tiltedWorldFrame` on the web app side
(manifest carries the natural frame; add-in does all alignment).

## Quick reference: where each piece lives

| What | File |
|------|------|
| Manifest schema (writer) | `slice-app/src/viewer/bulkSectionExport.ts` |
| Manifest schema (reader) | `fusion-addin/src/manifest.py` |
| Section frame computation (web app) | `slice-app/src/viewer/sectionFrame.ts` |
| Axis-aligned export override | `slice-app/src/viewer/sectionFrame.ts` (`axisAlignedWorldFrame`) |
| Tilted export override | `slice-app/src/viewer/sectionFrame.ts` (`tiltedWorldFrame`) |
| Axis-aligned plane construction | `fusion-addin/src/plane_resolver.py` (`create_offset_plane`) |
| Tilted plane construction | `fusion-addin/src/plane_resolver.py` (`create_tilted_plane`) |
| Helper-sketch lifecycle | `fusion-addin/src/plane_resolver.py` (`make_helper_sketch_provider`) |
| Tolerance for "axis-aligned?" | both files, search `1e-3` or `_AXIS_TOL` |
| Import dispatch | `fusion-addin/src/importer.py` (`_build_plane_from_manifest`) |
