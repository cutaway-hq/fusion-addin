"""Regenerate the Cutaway toolbar PNG icons from pure stdlib.

Run this from the repo root:

    python resources/generate_icons.py

Writes three PNGs into ``resources/cutaway/``:

    16x16.png   — Fusion's smallest button size
    32x32.png   — default button size
    64x64.png   — large button / panel icon

The design is intentionally simple: a rounded-square Cutaway-brand
background with two horizontal "section line" strokes, evoking a side-cut
view through a part. Replace this script (or the PNGs it produces) with
real brand artwork when the logo is finalised. No external dependencies —
uses only ``struct`` and ``zlib`` from the stdlib so anyone with vanilla
Python can rebuild the icons.
"""

import os
import struct
import zlib


# Cutaway brand palette (RGBA, 0-255).
BG_DARK    = (10, 14, 23, 255)     # near-black panel background
BG_PRIMARY = (56, 189, 248, 255)   # Cutaway accent (matches web-app `--accent`)
INK        = (245, 245, 250, 255)  # near-white "section lines"
TRANSPARENT = (0, 0, 0, 0)


def _draw_icon(size: int) -> bytes:
    """Return raw RGBA bytes (size*size*4) for one icon."""
    w = h = size
    pix = bytearray(w * h * 4)

    # Geometry as fractions of `size` so it scales cleanly.
    corner_r = max(2, size // 5)
    margin = max(1, size // 16)
    inner = size - 2 * margin

    # First fill background-shape (rounded square) with the accent colour.
    for y in range(h):
        for x in range(w):
            # distance to the rounded-square boundary
            dx = max(margin + corner_r - x, x - (w - margin - corner_r - 1), 0)
            dy = max(margin + corner_r - y, y - (h - margin - corner_r - 1), 0)
            in_rect = margin <= x < w - margin and margin <= y < h - margin
            in_corner = (dx * dx + dy * dy) <= corner_r * corner_r
            color = BG_PRIMARY if in_rect and in_corner else TRANSPARENT
            i = (y * w + x) * 4
            pix[i:i + 4] = bytes(color)

    # Two section-line strokes through the upper third of the icon, evoking
    # a cut profile. Stroke thickness scales with size; lines stop short of
    # the edges to look like a proper section indicator.
    stroke = max(1, size // 12)
    line_inset = margin + max(2, inner // 6)
    line_x0 = line_inset
    line_x1 = w - line_inset
    line_ys = [int(h * 0.36), int(h * 0.56)]
    for ly in line_ys:
        for y in range(ly, ly + stroke):
            if y < 0 or y >= h:
                continue
            for x in range(line_x0, line_x1):
                i = (y * w + x) * 4
                pix[i:i + 4] = bytes(INK)

    # A short vertical stub on the right end of each line — small visual
    # detail that reads as "this is a cut", even at 16px.
    stub_h = max(2, size // 4)
    stub_w = stroke
    for ly in line_ys:
        for y in range(ly - stub_h // 2, ly + stroke + stub_h // 2):
            if y < 0 or y >= h:
                continue
            for x in range(line_x1 - stub_w, line_x1):
                if 0 <= x < w:
                    i = (y * w + x) * 4
                    pix[i:i + 4] = bytes(INK)

    # Dark dot in the lower portion — represents the cut "interior" — gives
    # the icon a clear focal point distinct from the section lines above.
    dot_cx, dot_cy = w // 2, int(h * 0.74)
    dot_r = max(2, size // 6)
    for y in range(h):
        for x in range(w):
            dx = x - dot_cx
            dy = y - dot_cy
            if dx * dx + dy * dy <= dot_r * dot_r:
                i = (y * w + x) * 4
                pix[i:i + 4] = bytes(BG_DARK)

    return bytes(pix)


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    length = struct.pack('>I', len(data))
    crc = struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF)
    return length + typ + data + crc


def _write_png(path: str, size: int) -> None:
    pixels = _draw_icon(size)
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # filter byte 0 (None) per scanline
        raw.extend(pixels[y * size * 4:(y + 1) * size * 4])
    idat = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA

    sig = b'\x89PNG\r\n\x1a\n'
    with open(path, 'wb') as f:
        f.write(sig)
        f.write(_png_chunk(b'IHDR', ihdr))
        f.write(_png_chunk(b'IDAT', idat))
        f.write(_png_chunk(b'IEND', b''))


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, 'cutaway')
    os.makedirs(out_dir, exist_ok=True)
    for size in (16, 32, 64):
        path = os.path.join(out_dir, f'{size}x{size}.png')
        _write_png(path, size)
        print(f'wrote {path}')


if __name__ == '__main__':
    main()
