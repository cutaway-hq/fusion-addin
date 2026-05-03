# Installing Cutaway

For end users. If you're a developer working on the add-in itself, see
[ARCHITECTURE.md](ARCHITECTURE.md).

## Requirements

- Fusion 360 (any reasonably recent version — Cutaway uses only the stable
  Python API surface).
- Windows 10/11 or macOS.

## Install

### Windows

1. Download the latest `cutaway-X.Y.Z.zip` from the
   [Releases page](https://github.com/cutaway-hq/fusion-addin/releases).
2. Unzip it anywhere (Downloads is fine).
3. Double-click `install/install.bat`. A console window appears, copies the
   files, and waits for you to press a key.

### macOS

1. Download the latest `cutaway-X.Y.Z.zip` from the
   [Releases page](https://github.com/cutaway-hq/fusion-addin/releases).
2. Unzip it anywhere.
3. Open Terminal in the unzipped folder and run:

   ```bash
   chmod +x install/install.sh
   ./install/install.sh
   ```

## Enable in Fusion

After running the installer:

1. Open Fusion 360. (If it was already running, restart it.)
2. Go to **UTILITIES** → **Add-Ins** → **Scripts and Add-Ins…**.
3. Switch to the **Add-Ins** tab.
4. Find **Cutaway** in the *My Add-Ins* list.
5. Click **Run**. Tick **Run on Startup** so it loads automatically next time.

You should now see **Cutaway: Import Sections** in the **MODIFY** panel of
the DESIGN workspace.

## Use

1. Export sections from [cutawayhq.com](https://cutawayhq.com) using the
   **Refined 2D DXF (zipped)** option in the Sections panel.
2. In Fusion, click **MODIFY → Cutaway: Import Sections**.
3. Pick the zip you just downloaded.
4. Each `.dxf` becomes a sketch on its own construction plane at the
   correct depth.

## Update

When a newer release is available, an extra button appears in the MODIFY
panel:

> **Cutaway: Update to vX.Y.Z**

Click it — your browser opens the GitHub release page. Download the new
zip and re-run the install script. (Reinstalling overwrites the old files;
no need to uninstall first.)

## Uninstall

### Windows

```cmd
install\uninstall.bat
```

### macOS

```bash
./install/uninstall.sh
```

Then restart Fusion to clear the add-in from the *Scripts and Add-Ins*
list.

## Troubleshooting

- **"Cutaway: please open a Fusion design before importing"** — open or
  create a design first; the importer needs a target document.
- **"no .dxf files found in the zip"** — the zip might be the `.svg`
  export (we hide that in the UI but old exports may still exist). Use the
  Refined 2D DXF export.
- **Some sections show as "skipped — no placement suffix"** — those are
  face / 3-point / derived / tilted sections, which the v1 importer doesn't
  handle yet (we couldn't reconstruct an exact plane from the suffix
  alone). Re-export the sections as axis-aligned planes.
- **Nothing happens when I click the button** — check Fusion's TEXT
  COMMANDS pane (View → Show Text Commands) for any error output.
