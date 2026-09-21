#!/usr/bin/env python3
"""Generate the low-res dithered site images from the originals in src/.

    python3 tools/pixelize.py            # default block size
    python3 tools/pixelize.py --scale 2  # half-size blocks (twice the resolution)

Needs: pip install pillow numpy

Every image gets two versions: *-px-s for phones (<= 600px wide) and
*-px-l for larger screens. Widths are chosen so one image pixel is about
2 CSS px on a 390px-wide phone and about 3 CSS px on a 1920px desktop.
--scale multiplies those widths, so --scale 2 halves the block size.

Colours are snapped to LEVELS per channel with a 4x4 Bayer ordered dither,
alpha is snapped to on/off with the same threshold map (fades become a
pixel dissolve). The scarf ad gets a fully transparent frame held for
HOLD_MS after each play so nothing shows between plays.

Icons are rasterised separately by tools/rasterize-icons.js (needs a
browser) at 32 * scale px; this script then dithers those PNGs.
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageSequence

LEVELS = 4           # colour levels per channel
HOLD_MS = 3000       # pause between scarf ad plays
FRAME_MS = 100       # scarf ad frame duration

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (source, output stem, phone width, desktop width, opaque?)
STILLS = [
    ('src/bg.jpg',     'images/bg-px',     320, 640, True),
    ('src/logo.png',   'images/logo-px',   136, 192, False),
    ('src/portal.png', 'images/portal-px', 196, 640, False),
]
ANIMATIONS = [
    ('src/scarf-ad.gif', 'images/scarf-px', 196, 640),
]
ICONS = ['web', 'shopping-bag', 'music', 'game-controller', 'instagram']
ICON_PX = 32


def threshold_map(h, w):
    t = (BAYER + 0.5) / 16.0
    return np.tile(t, (h // 4 + 1, w // 4 + 1))[:h, :w]


def dither(img):
    """Ordered-dither an RGBA image: colour to LEVELS per channel, alpha to on/off."""
    a = np.asarray(img.convert('RGBA'), dtype=np.float32) / 255.0
    h, w = a.shape[:2]
    t = threshold_map(h, w)[..., None]
    rgb = a[..., :3] + (t - 0.5) * (1.0 / LEVELS)
    q = np.clip(np.floor(rgb * LEVELS), 0, LEVELS - 1) / (LEVELS - 1)
    alpha = (a[..., 3:4] > t).astype(np.float32)
    out = np.concatenate([q, alpha], axis=-1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def shrink(img, width):
    img = img.convert('RGBA')
    h = max(1, round(img.height * width / img.width))
    return img.resize((width, h), Image.LANCZOS)


def report(path):
    im = Image.open(path)
    n = getattr(im, 'n_frames', 1)
    print(f'{path:28s} {im.size[0]}x{im.size[1]}' + (f' x{n}' if n > 1 else '') + f'  {os.path.getsize(path) // 1024} KB')


def make_still(src, dst, width, opaque):
    im = dither(shrink(Image.open(src), width))
    if opaque:
        im = im.convert('RGB').quantize(colors=256, dither=Image.Dither.NONE)
    im.save(dst, 'PNG', optimize=True)
    report(dst)


def make_animation(src, dst, width):
    frames = [dither(shrink(f, width)) for f in ImageSequence.Iterator(Image.open(src))]
    durations = [FRAME_MS] * len(frames)
    frames.append(Image.new('RGBA', frames[0].size, (0, 0, 0, 0)))
    durations.append(HOLD_MS)
    frames[0].save(dst, 'WEBP', save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, lossless=True, method=6)
    report(dst)


def make_icon(name, px):
    src = f'tools/build/icons/{name}.png'
    if not os.path.exists(src):
        print(f'skip icon {name}: run tools/rasterize-icons.js first')
        return
    a = np.asarray(Image.open(src).convert('RGBA'), dtype=np.float32) / 255.0
    if a.shape[0] != px:
        a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((px, px), Image.LANCZOS), dtype=np.float32) / 255.0
    alpha = (a[..., 3] > threshold_map(px, px)).astype(np.uint8) * 255
    out = np.zeros((px, px, 4), np.uint8)
    out[..., 3] = alpha                      # solid black glyph
    dst = f'icons/{name}.png'
    Image.fromarray(out, 'RGBA').save(dst, optimize=True)
    report(dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scale', type=float, default=1.0, help='resolution multiplier; 2 = half-size blocks')
    args = ap.parse_args()
    os.chdir(ROOT)
    s = args.scale
    for src, stem, ws, wl, opaque in STILLS:
        make_still(src, f'{stem}-s.png', round(ws * s), opaque)
        make_still(src, f'{stem}-l.png', round(wl * s), opaque)
    for src, stem, ws, wl in ANIMATIONS:
        make_animation(src, f'{stem}-s.webp', round(ws * s))
        make_animation(src, f'{stem}-l.webp', round(wl * s))
    for name in ICONS:
        make_icon(name, round(ICON_PX * s))


if __name__ == '__main__':
    main()
