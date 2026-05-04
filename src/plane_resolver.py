"""Filename → target sketch plane.

The Cutaway web app exports DXFs with a placement suffix encoding the
section's 3D origin. For axis-aligned planar sections that suffix is:

    __<Plane>_<DepthAxis><DepthValue>_dx<X>_dy<Y>_<unit>.dxf

e.g. ``Top__XY_Z12.34_dx0_dy0_mm.dxf`` means the XY plane offset +12.34 mm
along Z, with the sketch's local X and Y starting at world (0, 0).

For face / derived / tilted sections the suffix is ``__at_X<x>_Y<y>_Z<z>``
and we don't try to reconstruct the plane in v1 — those get reported as
skipped so the user knows.
"""

import math
import re
from typing import Optional, TypedDict


PLANAR_RE = re.compile(
    r'__(?P<plane>XY|XZ|YZ)_'
    r'(?P<depth_axis>[XYZ])(?P<depth>-?\d+(?:\.\d+)?)'
    r'_dx(?P<dx>-?\d+(?:\.\d+)?)'
    r'_dy(?P<dy>-?\d+(?:\.\d+)?)'
    r'_(?P<unit>mm|cm|m|in)(?=[._]|$)',  # unit must be followed by `.`,
                                          # `_<modifier>`, or end of string —
                                          # accepts `_mm.dxf`, `_mm_refined.dxf`,
                                          # `_mm_refined_2.dxf`, etc.
    re.IGNORECASE,
)


class PlanarInfo(TypedDict):
    plane: str          # 'XY' | 'XZ' | 'YZ'
    depth_axis: str     # 'X' | 'Y' | 'Z'
    depth: float        # signed offset in source unit
    dx: float           # local sketch-X offset in source unit
    dy: float           # local sketch-Y offset in source unit
    unit: str           # 'mm' | 'cm' | 'm' | 'in'


def parse_filename(filename: str) -> Optional[PlanarInfo]:
    """Return parsed planar info, or None if the filename isn't recognised."""
    m = PLANAR_RE.search(filename)
    if not m:
        return None
    return PlanarInfo(
        plane=m.group('plane').upper(),
        depth_axis=m.group('depth_axis').upper(),
        depth=float(m.group('depth')),
        dx=float(m.group('dx')),
        dy=float(m.group('dy')),
        unit=m.group('unit').lower(),
    )


# Fusion's API works in centimetres internally, regardless of the active
# document's display unit. Anything that crosses into the API has to be in cm.
_TO_CM = {'mm': 0.1, 'cm': 1.0, 'm': 100.0, 'in': 2.54}


def to_cm(value: float, unit: str) -> float:
    return value * _TO_CM.get(unit, 1.0)


def create_offset_plane(component, info: PlanarInfo):
    """Build a ConstructionPlane offset from the component's base XY/XZ/YZ.

    ``component`` is a ``adsk.fusion.Component``. Returns the new
    ``ConstructionPlane``.
    """
    import adsk.core
    import adsk.fusion  # noqa: F401  (caller has these — keeps the type hints honest)

    base = {
        'XY': component.xYConstructionPlane,
        'XZ': component.xZConstructionPlane,
        'YZ': component.yZConstructionPlane,
    }[info['plane']]

    depth_cm = to_cm(info['depth'], info['unit'])

    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(base, adsk.core.ValueInput.createByReal(depth_cm))
    return planes.add(plane_input)


class ArbitraryPlaneNotSupported(Exception):
    """Raised when a tilted-plane construction can't proceed for some reason
    (degenerate normal, etc.). The importer catches this and skips cleanly."""


# How long to draw each helper sketch line, in cm. The line just has to be
# long enough that Fusion accepts it as a "linear entity" — actual length
# doesn't affect the resulting plane orientation. 10 cm is comfortable.
_HELPER_LINE_HALF_LENGTH_CM = 10.0


def create_tilted_plane(component, origin, normal, unit, sketch_provider):
    """Build a ConstructionPlane through ``origin`` with the given ``normal``,
    when the plane is NOT parallel to any base XY/XZ/YZ plane.

    Strategy: every non-XY-parallel plane intersects the XY plane along a
    line. Draw that intersection line in a shared helper sketch on XY, then
    use ``setByAngle`` to rotate the XY plane around it by the right angle.

      1. Compute intersection-line direction = perpendicular to the normal's
         XY projection, lying in XY.
      2. Compute a point on the intersection line — the foot of perpendicular
         from world origin to the line within XY.
      3. Add a SketchLine to the helper sketch, centered on that foot point.
      4. Compute the rotation angle = atan2(|N_xy|, N_z).
      5. Call ``setByAngle(line, angle, xYConstructionPlane)``.

    All sections share one helper sketch (created lazily by ``sketch_provider``)
    so the timeline grows by 1 sketch + 1 plane per tilted section, not 13.

    ``sketch_provider`` is a zero-arg callable that returns the shared
    helper sketch, creating it on first call.
    """
    import adsk.core
    import adsk.fusion  # noqa: F401

    nx, ny, nz = (float(c) for c in normal[:3])
    # Magnitude of the horizontal (XY) component of the normal.
    nxy = math.hypot(nx, ny)
    if nxy < _AXIS_TOL:
        raise ArbitraryPlaneNotSupported(
            'normal has no XY component — should have been handled by axis-aligned path'
        )

    # Origin in cm (Fusion API unit).
    ox, oy, oz = (to_cm(c, unit) for c in origin)

    # Plane equation: nx*x + ny*y + nz*z = D, where D = N · O (in cm).
    plane_d_cm = nx * ox + ny * oy + nz * oz

    # Foot of perpendicular from world origin to the intersection line,
    # within the XY plane (z=0).
    # Solve nx*x + ny*y = D, with (x, y) closest to origin → (x, y) = (nx, ny) * (D / (nx²+ny²)).
    t = plane_d_cm / (nxy * nxy)
    foot_x = nx * t
    foot_y = ny * t

    # Direction of the intersection line within XY: perpendicular to (nx, ny),
    # normalised. Using (-ny, nx) / |xy| (left perpendicular, consistent with
    # the angle-direction convention below).
    dir_x = -ny / nxy
    dir_y = nx / nxy

    # Two endpoints of the helper sketch line, centred on the foot point.
    half = _HELPER_LINE_HALF_LENGTH_CM
    p1 = adsk.core.Point3D.create(foot_x - dir_x * half, foot_y - dir_y * half, 0)
    p2 = adsk.core.Point3D.create(foot_x + dir_x * half, foot_y + dir_y * half, 0)

    helper_sketch = sketch_provider()
    sketch_line = helper_sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2)

    # Rotation angle from XY plane (normal Z=(0,0,1)) to target plane around
    # the chosen line direction. With our left-perpendicular line direction,
    # rotating by +angle = atan2(nxy, nz) takes Z to (nx, ny, nz)/|N|.
    angle_rad = math.atan2(nxy, nz)

    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByAngle(
        sketch_line,
        adsk.core.ValueInput.createByReal(angle_rad),
        component.xYConstructionPlane,
    )
    return planes.add(plane_input)


def make_helper_sketch_provider(component):
    """Returns a zero-arg callable that lazily creates a single hidden
    helper sketch on the XY plane and returns it. Used to share one helper
    sketch across many tilted sections so the timeline stays clean.

    Notes for future-you:
    - DON'T set ``isComputeDeferred = True`` — the deferred compute keeps
      newly added SketchLines in a pending state that doesn't render in the
      viewport, even though the entity exists. setByAngle still consumes
      them, but visually the sketch looks empty.
    - The visibility flag for sketches is ``isVisible`` (the property
      ``isLightBulbOn`` is for ConstructionPlanes — assigning it to a
      Sketch silently throws).
    - API-added sketch geometry doesn't fire auto-constraints, so we don't
      need to defer compute to keep our independent helper lines apart.
    """
    state = {'sketch': None}

    def provider():
        if state['sketch'] is None:
            sketch = component.sketches.add(component.xYConstructionPlane)
            sketch.name = 'Cutaway helpers (do not delete)'
            try:
                sketch.isVisible = False
            except Exception:
                pass
            state['sketch'] = sketch
        return state['sketch']

    return provider


# Tolerance for "is this normal axis-aligned?" — components below this are
# treated as zero. Generous enough to absorb the floating-point noise that
# falls out of computing a face/3-point section's normal from a cross product
# (real measured noise: ~2e-4 from a 3-point section through coplanar points).
# 1e-3 corresponds to ~0.06° of true tilt — well below anything intentional.
_AXIS_TOL = 1e-3


def axis_aligned_plane(normal) -> Optional[str]:
    """If ``normal`` points along ±X, ±Y, or ±Z (within tolerance), return
    the corresponding base plane label ('YZ' for X-normal, 'XZ' for Y, 'XY'
    for Z). Otherwise return None.

    The base-plane label is what the section's geometry is *parallel to* —
    a section whose normal points along Z lies in (a plane parallel to) XY.
    """
    if not normal or len(normal) < 3:
        return None
    nx, ny, nz = (abs(float(c)) for c in normal[:3])
    if nx > _AXIS_TOL and ny < _AXIS_TOL and nz < _AXIS_TOL:
        return 'YZ'
    if ny > _AXIS_TOL and nx < _AXIS_TOL and nz < _AXIS_TOL:
        return 'XZ'
    if nz > _AXIS_TOL and nx < _AXIS_TOL and ny < _AXIS_TOL:
        return 'XY'
    return None


def planar_info_from_manifest(section: dict, unit: str) -> Optional[PlanarInfo]:
    """Map a manifest section to the PlanarInfo shape that
    ``create_offset_plane`` expects. Works for ANY section kind whose
    normal is axis-aligned — planar XY/XZ/YZ from the planar tool, AND
    face / 3-point / derived sections that happen to have an axis-aligned
    normal (very common: any section on a flat top/bottom/side face).
    Returns None for genuinely off-axis normals (caller should fall back
    to ``create_arbitrary_plane``).
    """
    # Reject sections with explicit tilt — those have non-cardinal normals
    # even when kind == 'plane'.
    if section.get('kind') == 'plane' and (
        float(section.get('tiltU', 0) or 0) != 0
        or float(section.get('tiltV', 0) or 0) != 0
    ):
        return None

    plane = axis_aligned_plane(section.get('normal'))
    if plane is None:
        return None

    origin = section.get('origin') or [0, 0, 0]
    depth_axis = {'XY': 'Z', 'XZ': 'Y', 'YZ': 'X'}[plane]
    depth_index = {'X': 0, 'Y': 1, 'Z': 2}[depth_axis]
    return PlanarInfo(
        plane=plane,
        depth_axis=depth_axis,
        depth=float(origin[depth_index]),
        dx=0.0,
        dy=0.0,
        unit=unit,
    )
