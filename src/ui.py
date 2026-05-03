"""Cutaway's UI registration in Fusion.

Adds one button to the DESIGN workspace's MODIFY panel. Clicking it opens a
file dialog to pick a Cutaway zip; the importer takes it from there.

If a newer release is available (set by ``updater``), the button tooltip gets
an "Update available — v0.X.Y" suffix and a second small button appears that
opens the GitHub release page in the user's browser.
"""

import webbrowser

import adsk.core

from . import importer, updater


CMD_IMPORT_ID = 'cutaway_import_sections'
CMD_IMPORT_NAME = 'Cutaway: Import Sections'
CMD_UPDATE_ID = 'cutaway_open_release'
CMD_UPDATE_NAME = 'Cutaway: Update Available'
PANEL_ID = 'SolidModifyPanel'
WORKSPACE_ID = 'FusionSolidEnvironment'

_handlers: list = []  # keep refs so Fusion's GC doesn't drop them mid-callback


class _ImportCommandCreated(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface

            dlg = ui.createFileDialog()
            dlg.title = 'Cutaway — pick a section export zip'
            dlg.filter = 'Cutaway zip (*.zip)'
            dlg.isMultiSelectEnabled = False
            if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
                return

            importer.import_zip(dlg.filename)
        except Exception:
            import traceback
            adsk.core.Application.get().userInterface.messageBox(
                'Cutaway import failed:\n{}'.format(traceback.format_exc())
            )


class _UpdateCommandCreated(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        pending = updater.get_pending_update()
        if pending and pending.get('url'):
            webbrowser.open(pending['url'])


def _register_button(ui, cmd_id: str, cmd_name: str, tooltip: str, handler):
    existing = ui.commandDefinitions.itemById(cmd_id)
    if existing:
        existing.deleteMe()
    cmd_def = ui.commandDefinitions.addButtonDefinition(cmd_id, cmd_name, tooltip)
    cmd_def.commandCreated.add(handler)
    _handlers.append(handler)
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    panel.controls.addCommand(cmd_def)
    return cmd_def


def start():
    app = adsk.core.Application.get()
    ui = app.userInterface

    _register_button(
        ui,
        CMD_IMPORT_ID,
        CMD_IMPORT_NAME,
        'Pick a Cutaway zip (one DXF per section) — each becomes a sketch on its own plane.',
        _ImportCommandCreated(),
    )

    # Fire the update probe — non-blocking. If a newer release lands later in
    # this Fusion session the user will see the affordance next time they
    # restart Fusion (we stash state in module-level memory only).
    updater.check_in_background()

    pending = updater.get_pending_update()
    if pending:
        _register_button(
            ui,
            CMD_UPDATE_ID,
            f'Cutaway: Update to {pending["version"]}',
            f'A newer Cutaway release is available ({pending["version"]}). Opens the GitHub release page.',
            _UpdateCommandCreated(),
        )


def _remove_button(ui, cmd_id: str):
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace:
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        if panel:
            ctrl = panel.controls.itemById(cmd_id)
            if ctrl:
                ctrl.deleteMe()
    cmd_def = ui.commandDefinitions.itemById(cmd_id)
    if cmd_def:
        cmd_def.deleteMe()


def stop():
    ui = adsk.core.Application.get().userInterface
    _remove_button(ui, CMD_IMPORT_ID)
    _remove_button(ui, CMD_UPDATE_ID)
    _handlers.clear()
