"""Cutaway — Fusion 360 add-in entry point.

Fusion calls run() when the add-in is enabled and stop() when disabled.
All real work lives under src/. This file is intentionally thin so the entry
points stay obvious.
"""

import traceback

import adsk.core

from .src import ui


def run(context):
    try:
        ui.start()
    except Exception:
        adsk.core.Application.get().userInterface.messageBox(
            'Cutaway failed to start:\n{}'.format(traceback.format_exc())
        )


def stop(context):
    try:
        ui.stop()
    except Exception:
        adsk.core.Application.get().userInterface.messageBox(
            'Cutaway failed to stop cleanly:\n{}'.format(traceback.format_exc())
        )
