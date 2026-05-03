"""Import a Cutaway zip of DXF sections into the active Fusion design.

Flow:
  1. User picks the zip.
  2. We extract it to a temp dir.
  3. For every .dxf file, parse the placement suffix → target plane.
  4. Create a ConstructionPlane in the root component at the right offset.
  5. Use Fusion's ImportManager to import the DXF onto that plane as a sketch.
  6. Report the count and any skipped files.

Edge cases handled:
  - No active design → friendly message, abort.
  - Filename without the placement suffix → reported as skipped.
  - Single DXF inside the zip is fine; many DXFs is the normal case.
  - Per-file failures don't kill the whole batch.
"""

import os
import tempfile
import traceback
import zipfile

import adsk.core
import adsk.fusion

from . import plane_resolver


def import_zip(zip_path: str) -> None:
    app = adsk.core.Application.get()
    ui = app.userInterface

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox('Cutaway: please open a Fusion design before importing.')
        return

    root = design.rootComponent
    import_mgr = app.importManager

    imported = 0
    skipped: list[str] = []

    with tempfile.TemporaryDirectory(prefix='cutaway_') as tmpdir:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipFile:
            ui.messageBox(f'Cutaway: "{os.path.basename(zip_path)}" is not a valid zip file.')
            return

        # Walk the temp dir recursively in case the zip has a top-level folder.
        dxf_paths: list[str] = []
        for dirpath, _, filenames in os.walk(tmpdir):
            for fname in filenames:
                if fname.lower().endswith('.dxf'):
                    dxf_paths.append(os.path.join(dirpath, fname))
        dxf_paths.sort()

        if not dxf_paths:
            ui.messageBox('Cutaway: no .dxf files found in the zip.')
            return

        for full_path in dxf_paths:
            fname = os.path.basename(full_path)
            info = plane_resolver.parse_filename(fname)
            if not info:
                skipped.append(f'{fname} — no placement suffix (face/derived/tilted not supported in v1)')
                continue

            try:
                target_plane = plane_resolver.create_offset_plane(root, info)
                opts = import_mgr.createDXF2DImportOptions(full_path, target_plane)
                import_mgr.importToTarget(opts, design)
                imported += 1
            except Exception:
                skipped.append(f'{fname} — {traceback.format_exc().splitlines()[-1]}')

    summary = f'Cutaway: imported {imported} section{"s" if imported != 1 else ""}.'
    if skipped:
        head = '\n'.join(skipped[:10])
        more = f'\n…and {len(skipped) - 10} more' if len(skipped) > 10 else ''
        summary += f'\n\nSkipped {len(skipped)}:\n{head}{more}'
    ui.messageBox(summary)
