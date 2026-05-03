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

import re
from typing import Optional, TypedDict


PLANAR_RE = re.compile(
    r'__(?P<plane>XY|XZ|YZ)_'
    r'(?P<depth_axis>[XYZ])(?P<depth>-?\d+(?:\.\d+)?)'
    r'_dx(?P<dx>-?\d+(?:\.\d+)?)'
    r'_dy(?P<dy>-?\d+(?:\.\d+)?)'
    r'_(?P<unit>mm|cm|m|in)\.dxf$',
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
