"""Cutaway's UI registration in Fusion.

Surfaces:
  - One toolbar button in DESIGN → MODIFY (icon from ``resources/cutaway/``)
    that toggles the Cutaway HTML Palette open/closed.
  - The Cutaway Palette itself (``resources/palette/index.html``), which
    hosts the actual import action and is the home for future features
    (e.g. "Publish to Cutaway" marketplace upload).
  - A second toolbar button — "Cutaway: Update to vX.Y.Z" — that appears
    only when ``updater`` has detected a newer release.

Historical note: pre-v0.2.x the toolbar button opened Fusion's native file
dialog directly. We swapped that for the Palette to give Cutaway a branded
surface inside Fusion and a place to host follow-on features. The importer
itself is unchanged. See CLAUDE.md "Migration history" for the full
rationale and how to revert if needed.
"""

import json
import os
import pathlib
import traceback
import webbrowser

import adsk.core

from . import importer, updater


# Toolbar / palette identifiers. The IDs are stable strings so Fusion
# recognises the buttons/palette across sessions even when the user is on
# an older install.
CMD_LAUNCH_ID = 'cutaway_launch'
CMD_LAUNCH_NAME = 'Cutaway'
CMD_UPDATE_ID = 'cutaway_open_release'
CMD_UPDATE_NAME = 'Cutaway: Update Available'
PALETTE_ID = 'cutaway_palette'
PALETTE_NAME = 'Cutaway'
PANEL_ID = 'SolidModifyPanel'
WORKSPACE_ID = 'FusionSolidEnvironment'

# Filesystem paths to bundled resources. Computed relative to this file so
# it works regardless of where the user installed the add-in.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_ADDIN_ROOT = os.path.dirname(_SRC_DIR)
_ICON_DIR = os.path.join(_ADDIN_ROOT, 'resources', 'cutaway')

# Fusion's Palettes API expects a URL (not a Windows path). pathlib turns
# `D:\...\index.html` into `file:///D:/.../index.html` with forward slashes,
# which Chromium (the embedded browser) accepts.
_PALETTE_URL = pathlib.Path(
    _ADDIN_ROOT, 'resources', 'palette', 'index.html'
).as_uri()

# Keep handler references alive — Fusion's GC drops them otherwise.
_handlers: list = []


# ──────────────────────────────────────────────────────────────────────────
# Toolbar-button command handlers
# ──────────────────────────────────────────────────────────────────────────

class _LaunchCommandCreated(adsk.core.CommandCreatedEventHandler):
    """Toolbar button click → toggle the Cutaway Palette open/closed."""

    def notify(self, args):
        try:
            ui = adsk.core.Application.get().userInterface
            palette = ui.palettes.itemById(PALETTE_ID)
            if not palette:
                palette = _create_palette(ui)
            # Toggle: showing → hide; hidden → show.
            palette.isVisible = not palette.isVisible
            if palette.isVisible:
                # The HTML loads while the palette is hidden (created at
                # start()), and the embedded Chromium skips painting hidden
                # views — so the first reveal shows a blank panel until
                # something forces a layout pass (users found minimize/
                # restore "fixed" it). A 1px size nudge forces that pass
                # invisibly. Best-effort: a failure here must not break
                # the toggle.
                try:
                    palette.height = palette.height + 1
                    palette.height = palette.height - 1
                except Exception:
                    pass
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                'Cutaway failed to open the panel:\n{}'.format(traceback.format_exc())
            )


class _UpdateCommandCreated(adsk.core.CommandCreatedEventHandler):
    """Toolbar button click → open the GitHub release page in a browser."""

    def notify(self, args):
        try:
            pending = updater.get_pending_update()
            if pending and pending.get('url'):
                webbrowser.open(pending['url'])
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                'Cutaway failed to open the release page:\n{}'.format(
                    traceback.format_exc()
                )
            )


# ──────────────────────────────────────────────────────────────────────────
# Palette event handling (JS → Python actions)
# ──────────────────────────────────────────────────────────────────────────

# These two handlers cooperate to translate `adsk.fusionSendData(action,
# data)` calls from index.html's JS into Python work. `HTMLEvent` fires
# once per JS-side post; we route on the `action` string.

class _PaletteHTMLEvent(adsk.core.HTMLEventHandler):
    def notify(self, args):
        try:
            event_args = adsk.core.HTMLEventArgs.cast(args)
            action = event_args.action
            # We accept JSON payloads from JS but don't need any data yet.
            try:
                _ = json.loads(event_args.data) if event_args.data else {}
            except ValueError:
                pass

            if action == 'import':
                _run_import_flow()
            elif action == 'open-help':
                webbrowser.open('https://cutawayhq.com')
            # Future: 'publish' → export current design as STL → upload.
            # Add the branch here, keep the JS side declarative
            # (just another data-action button in index.html).
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(
                'Cutaway palette action failed:\n{}'.format(traceback.format_exc())
            )


class _PaletteClosedHandler(adsk.core.UserInterfaceGeneralEventHandler):
    """No-op for now, but reserved so we can persist palette state later
    (e.g. remember docked position) without a second registration pass."""

    def notify(self, args):
        pass


def _run_import_flow():
    """The original toolbar-click behaviour — pick a zip and import it.
    Triggered now by the Palette's "Import sections" button instead of the
    toolbar button directly.
    """
    app = adsk.core.Application.get()
    ui = app.userInterface

    dlg = ui.createFileDialog()
    dlg.title = 'Cutaway — pick a section export zip'
    dlg.filter = 'Cutaway zip (*.zip)'
    dlg.isMultiSelectEnabled = False
    if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
        return

    importer.import_zip(dlg.filename)


# ──────────────────────────────────────────────────────────────────────────
# Palette + toolbar wiring
# ──────────────────────────────────────────────────────────────────────────

def _create_palette(ui):
    """Register the Cutaway Palette so Fusion knows about it.

    Width / height are starting dimensions; the user can resize and dock.
    `isVisible=False` because callers (the toolbar button) set visibility
    themselves — keeps the create-vs-show split clean.
    """
    palette = ui.palettes.add(
        PALETTE_ID,
        PALETTE_NAME,
        _PALETTE_URL,
        False,   # isVisible — create hidden; callers decide when to show.
                 # Creating visible broke the toolbar toggle when the palette
                 # had to be recreated inside the click handler: it appeared
                 # visible and the toggle immediately hid it (click did
                 # "nothing"; second click worked).
        True,    # showCloseButton
        True,    # isResizable
        400,     # initial width (px) — comfortable but not dominating.
        400,     # initial height (px) — leaves room for future buttons
                 # (e.g. "Publish to Cutaway") without immediate resize.
    )
    # Float by default — when docked to a Fusion edge the palette is
    # forced to full available height, which leaves the compact UI
    # swimming in empty space. Floating respects our initial 400×400
    # dimensions. User can drag it onto an edge to dock it themselves.
    palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateFloating

    html_handler = _PaletteHTMLEvent()
    palette.incomingFromHTML.add(html_handler)
    _handlers.append(html_handler)

    closed_handler = _PaletteClosedHandler()
    palette.closed.add(closed_handler)
    _handlers.append(closed_handler)

    return palette


def _register_button(ui, cmd_id, cmd_name, tooltip, handler, icon_folder=None):
    """Add a toolbar button to the DESIGN → MODIFY panel."""
    existing = ui.commandDefinitions.itemById(cmd_id)
    if existing:
        existing.deleteMe()
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        cmd_id, cmd_name, tooltip, icon_folder or '',
    )
    cmd_def.commandCreated.add(handler)
    _handlers.append(handler)
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    panel.controls.addCommand(cmd_def)
    return cmd_def


def start():
    app = adsk.core.Application.get()
    ui = app.userInterface

    # Create the Palette eagerly but hide it until the user clicks the
    # toolbar button. Eager creation means the first click is instant.
    palette = ui.palettes.itemById(PALETTE_ID)
    if not palette:
        palette = _create_palette(ui)
    palette.isVisible = False

    _register_button(
        ui,
        CMD_LAUNCH_ID,
        CMD_LAUNCH_NAME,
        'Open the Cutaway panel — import section exports from cutawayhq.com.',
        _LaunchCommandCreated(),
        icon_folder=_ICON_DIR,
    )

    # Fire the update probe in a daemon thread. Its result lands after this
    # function has returned, so the button below is driven by the CACHED
    # result of a previous session's check (updater persists it next to
    # version.json) — a newer release found now surfaces on the next restart.
    updater.check_in_background()

    pending = updater.get_pending_update()
    if pending:
        _register_button(
            ui,
            CMD_UPDATE_ID,
            f'Cutaway: Update to {pending["version"]}',
            f'A newer Cutaway release is available ({pending["version"]}). '
            'Opens the GitHub release page.',
            _UpdateCommandCreated(),
        )


# ──────────────────────────────────────────────────────────────────────────
# Teardown
# ──────────────────────────────────────────────────────────────────────────

def _remove_button(ui, cmd_id):
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
    _remove_button(ui, CMD_LAUNCH_ID)
    _remove_button(ui, CMD_UPDATE_ID)
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.deleteMe()
    _handlers.clear()
