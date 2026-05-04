"""Import a Cutaway zip of DXF sections into the active Fusion design.

Two paths:

  1. **Manifest path** (preferred). The zip carries a ``cutaway.json``
     manifest with full geometric metadata for every section: origin,
     normal, u-axis, v-axis, kind. We use this to build the right
     ConstructionPlane for ANY section type — planar / face / 3-point /
     derived / tilted — and import each DXF onto its plane.

  2. **Filename-fallback path** (legacy). For zips without a manifest, we
     fall back to parsing the placement suffix in each DXF's filename.
     Only axis-aligned planar sections (XY/XZ/YZ) are recoverable that way;
     anything else is reported as skipped.

In both paths, per-file failures don't kill the batch, and the user gets a
single summary message at the end.
"""

import os
import tempfile
import traceback
import zipfile
from typing import Optional

import adsk.core
import adsk.fusion

from . import manifest, plane_resolver


def import_zip(zip_path: str) -> None:
    app = adsk.core.Application.get()
    ui = app.userInterface

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox('Cutaway: please open a Fusion design before importing.')
        return

    root = design.rootComponent
    import_mgr = app.importManager

    with tempfile.TemporaryDirectory(prefix='cutaway_') as tmpdir:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipFile:
            ui.messageBox(f'Cutaway: "{os.path.basename(zip_path)}" is not a valid zip file.')
            return

        manifest_data = manifest.read_from_dir(tmpdir)
        if manifest_data:
            imported, skipped = _import_with_manifest(
                tmpdir, manifest_data, root, import_mgr, design,
            )
            method = 'manifest'
        else:
            imported, skipped = _import_with_filenames(
                tmpdir, root, import_mgr, design,
            )
            method = 'filename (no cutaway.json)'

    summary = f'Cutaway: imported {imported} section{"s" if imported != 1 else ""} via {method}.'
    if skipped:
        head = '\n'.join(skipped[:10])
        more = f'\n…and {len(skipped) - 10} more' if len(skipped) > 10 else ''
        summary += f'\n\nSkipped {len(skipped)}:\n{head}{more}'
    ui.messageBox(summary)


def _import_with_manifest(extracted_dir, manifest_data, root, import_mgr, design):
    """Walk every entry in cutaway.json, build its plane, import the DXF."""
    unit = manifest_data.get('unit', 'mm')
    skipped: list[str] = []
    imported = 0

    # Lazy: we only create the helper sketch on the first tilted section. If
    # every section is axis-aligned, no helper sketch appears at all.
    helper_sketch_provider = plane_resolver.make_helper_sketch_provider(root)

    for entry in manifest_data.get('sections', []):
        fname = entry.get('file')
        if not fname:
            skipped.append('<missing file field in manifest entry>')
            continue
        full_path = _find_in_dir(extracted_dir, fname)
        if not full_path:
            skipped.append(f'{fname} — file referenced in manifest is missing from zip')
            continue

        # Split into per-step try/except so the skip message tells the user
        # exactly where it failed (plane construction vs. DXF import) — both
        # surfaces of Fusion's API throw the same generic
        # "InternalValidationError" so without this we're flying blind.
        try:
            target_plane = _build_plane_from_manifest(root, entry, unit, helper_sketch_provider)
        except plane_resolver.ArbitraryPlaneNotSupported as e:
            skipped.append(f'{fname} — {e}')
            continue
        except Exception:
            last = traceback.format_exc().strip().splitlines()[-1]
            skipped.append(f'{fname} — plane construction failed: {last}')
            continue

        try:
            opts = import_mgr.createDXF2DImportOptions(full_path, target_plane)
            import_mgr.importToTarget(opts, root)
            imported += 1
        except Exception:
            last = traceback.format_exc().strip().splitlines()[-1]
            skipped.append(f'{fname} — DXF import failed: {last}')

    return imported, skipped


def _build_plane_from_manifest(component, entry, unit, helper_sketch_provider):
    """Pick the cleanest construction method per entry:

      - axis-aligned (normal along ±X / ±Y / ±Z, regardless of section kind)
        → ``setByOffset`` from the matching base plane. 0 helper entities.
      - tilted (normal not aligned to a base axis) → draw a sketch line at
        the intersection of the target plane with XY in a SHARED hidden
        helper sketch, then ``setByAngle``. 1 sketch (shared, lazily
        created) + 1 plane per tilted section.
    """
    info = plane_resolver.planar_info_from_manifest(entry, unit)
    if info is not None:
        return plane_resolver.create_offset_plane(component, info)

    origin = entry.get('origin') or [0, 0, 0]
    normal = entry.get('normal') or [0, 0, 1]
    return plane_resolver.create_tilted_plane(
        component, origin, normal, unit, helper_sketch_provider,
    )


def _import_with_filenames(extracted_dir, root, import_mgr, design):
    """Legacy path — parse the placement suffix from each DXF's filename.
    Only axis-aligned planar sections are recoverable this way."""
    skipped: list[str] = []
    imported = 0

    dxf_paths: list[str] = []
    for dirpath, _, filenames in os.walk(extracted_dir):
        for fname in filenames:
            if fname.lower().endswith('.dxf'):
                dxf_paths.append(os.path.join(dirpath, fname))
    dxf_paths.sort()

    if not dxf_paths:
        return 0, ['no .dxf files found in the zip']

    for full_path in dxf_paths:
        fname = os.path.basename(full_path)
        info = plane_resolver.parse_filename(fname)
        if not info:
            skipped.append(
                f'{fname} — no placement suffix and no cutaway.json '
                '(face/derived/tilted not recoverable from filename)'
            )
            continue
        try:
            target_plane = plane_resolver.create_offset_plane(root, info)
            opts = import_mgr.createDXF2DImportOptions(full_path, target_plane)
            import_mgr.importToTarget(opts, root)
            imported += 1
        except Exception:
            last = traceback.format_exc().strip().splitlines()[-1]
            skipped.append(f'{fname} — {last}')

    return imported, skipped


def _find_in_dir(root_dir: str, relative_or_basename: str) -> Optional[str]:
    """Resolve a manifest 'file' value to an actual path on disk.

    Manifest filenames are flat (no subfolders) but the zip might have been
    extracted under a wrapper directory, so we walk and match basename.
    """
    direct = os.path.join(root_dir, relative_or_basename)
    if os.path.isfile(direct):
        return direct
    target = os.path.basename(relative_or_basename)
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname == target:
                return os.path.join(dirpath, fname)
    return None
