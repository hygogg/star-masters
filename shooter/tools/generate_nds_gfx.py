#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_nds_gfx.py — Nintendo DS graphics data for the NDS port of the shmup.

Reuses tools/generate_images.py (same directory) for all base art, the grid
helpers (mirror/pad_left/render/leg) and the PNG writer used by the debug
previews. Does NOT touch generate_images.py or anything under assets/.

Emits:
    ../../shooter-nds/source/gfx_data.c
    ../../shooter-nds/include/gfx_data.h

Sprites    : 8bpp, 1D-mapped 8x8 tiles (left-to-right, top-to-bottom across
             the frame; 64 row-major pixels per tile), all frames contiguous,
             ONE shared 256-colour BGR555 palette, index 0 = transparent.
Backgrounds: three 256x256 vertically seamless stage backgrounds, regenerated
             at 256x256 in the style of gen_bg1/2/3 (NOT resampled), emitted
             as flip-deduped 8bpp tiles + 32x32 u16 text-BG map + own
             256-entry palette (no pixel ever maps to index 0).
Font       : 5x7-in-8x8 4bpp tiles, ASCII 32..95 (glyph index = c - 32),
             16-entry palette (0 = transparent, 1..7 = UI colours).

midenemy (24x24) and the three bosses (48x48) are re-authored at 32x32 /
64x64 in the same visual language so they FILL the DS hardware sprite frame.

After emitting, the script verifies everything in memory, re-parses the
emitted C, writes round-trip preview PNGs (decoded from the emitted tile
bytes + palettes) and exits non-zero on any failure.
"""

import math
import os
import re
import sys
import random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_images as GI  # noqa: E402

MASTERS = os.path.dirname(os.path.dirname(HERE))
NDS_ROOT = os.path.join(MASTERS, "shooter-nds")
SRC_DIR = os.path.join(NDS_ROOT, "source")
INC_DIR = os.path.join(NDS_ROOT, "include")
# 出力したタイルデータから復元した確認用プレビューの出力先。環境変数で差し替え可。
PREVIEW_DIR = os.environ.get("NDS_PREVIEW_DIR",
                             os.path.join(MASTERS, "shooter", "_preview", "nds"))

T = (0, 0, 0, 0)
NBG = 256  # background side


def bgr555(r, g, b):
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def rgb888(v):
    r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
    return ((r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2))


def center_pad(frame, W, H):
    h, w = len(frame), len(frame[0])
    assert w <= W and h <= H, "art %dx%d does not fit frame %dx%d" % (w, h, W, H)
    ox, oy = (W - w) // 2, (H - h) // 2
    out = [[T] * W for _ in range(H)]
    for y in range(h):
        for x in range(w):
            out[oy + y][ox + x] = frame[y][x]
    return out


# ============================================================================
# EXPANDED ART — midenemy 24->32, bosses 48->64 (same language, fills frame)
# ============================================================================

# ---- MIDENEMY 32x32: red heavy gunship. Wider hull, tail engine vents,
#      bigger 12-wide turret with blinking light bank, FOUR gun barrels
#      (outer pair + longer inner pair), pointed prow. ----
MIDENEMY32_HALF = GI.pad_left([
    "",
    "kkkkk",
    "kDDGG",
    "kDDGG",
    "kkkkkkkkk",
    "kDDDDDDDD",
    "kDRRRRRRRR",
    "kkDRRRRRRRRR",
    "kDDRRRRRRRRRRR",
    "kDRRRRRRRRRRRRR",
    "kDRRRRRRRRkkkkkk",
    "kDRRRRRRRRkDLLLL",
    "kDRRRRRRRRkDLLLL",
    "kDRRRRRRRRkDLLLL",
    "kDRRRRRRRRkkkkkk",
    "kDRRRRRRRRRRRRRR",
    "kDkGGkRRRRRRRRRR",
    "kDkGGkRRRRRRRRRR",
    "kDkGGkRkGGkRRRRR",
    "kDkGGkRkGGkRRRRR",
    "kkkGGkRkGGkRRRRR",
    ".kkGGkDkGGkRRRRR",
    "..kGGkkkGGkDRRRR",
    "..kGGk.kGGkDRRRR",
    "..kGGk.kGGkkDRRR",
    "..kkkk.kGGk.kDRR",
    ".......kGGk..kDR",
    ".......kGGk...kD",
    ".......kGGk....k",
    ".......kkkk.....",
    "",
    "",
], 16)


def midenemy32_frames():
    grid = GI.mirror(MIDENEMY32_HALF)
    base = {
        "k": (30, 6, 10, 255),      # outline
        "R": (206, 52, 56, 255),    # red hull
        "D": (118, 16, 28, 255),    # dark red
        "G": (184, 188, 198, 255),  # gray cannons / vents
    }
    f1 = GI.leg(base, L=(255, 244, 150, 255))   # turret light on
    f2 = GI.leg(base, L=(118, 16, 28, 255))     # turret light off
    return [GI.render(grid, f1, "midenemy32 f1"),
            GI.render(grid, f2, "midenemy32 f2")]


# ---- BOSS1 "GUARDIAN" 64x64: steel-blue battleship. More armor steps,
#      wider vent bank, protruding side fins, TWIN cannon pods per side,
#      bigger diamond core with hot center, long keel-lit prow. ----
def boss1_half64():
    rows = []
    rows.append("k" * 14)                            # 0  stern edge
    for _ in range(3):                               # 1-3 exhaust vents
        rows.append("k" + "SDD" * 4 + "S")
    rows.append("k" * 14)                            # 4
    rows.append("k" * 18)                            # 5  step ledge
    rows.append("kD" + "S" * 16)                     # 6
    rows.append("kDSS" + "H" * 10 + "SSSS")          # 7  highlight band
    rows.append("kD" + "S" * 16)                     # 8
    rows.append("k" * 24)                            # 9  step ledge
    rows.append("kD" + "S" * 22)                     # 10
    for _ in range(3):                               # 11-13
        rows.append("kDSHH" + "S" * 19)
    rows.append("k" * 28)                            # 14 step ledge
    rows.append("kD" + "S" * 26)                     # 15
    rows.append("kDS" + "H" * 8 + "S" * 17)          # 16 highlight band
    rows.append("kD" + "S" * 26)                     # 17
    rows.append("k" * 30)                            # 18 step to main plateau

    core_tails = {22: "kk", 23: "kgg", 24: "kggg", 25: "kgggg",
                  26: "kggggg", 27: "kgggggg", 28: "kgggggg",
                  29: "kggghhh", 30: "kgghhhh", 31: "kgghhhh",
                  32: "kggghhh", 33: "kgggggg", 34: "kgggggg",
                  35: "kggggg", 36: "kgggg", 37: "kggg", 38: "kgg",
                  39: "kk"}

    def body(tail, pod=False):
        left = "kkDSkSSSSkSSSSSSk" if pod else "kDSHSSSSSkSSSSSSk"
        return left + "S" * (30 - len(left) - len(tail)) + tail

    for r in range(19, 44):                          # 19-43 main plateau
        b = body(core_tails.get(r, ""), pod=(r >= 37))
        if 24 <= r <= 36:                            # protruding side fin
            b = ("kk" if r in (24, 36) else "kS") + b
        rows.append(b)
    rows.append("k" * 30)                            # 44 plateau bottom edge

    for _ in range(45, 51):                          # 45-50 twin cannon pods
        rows.append("..." + "kDSk" + "." + "kDSk" + "." + "kD" + "S" * 17)
    for _ in range(51, 53):                          # 51-52 hull narrows
        rows.append("..." + "kDSk" + "." + "kDSk" + ".." + "kD" + "S" * 16)
    rows.append("..." + "kkkk" + "." + "kDSk" + ".." + "kD" + "S" * 16)  # 53
    rows.append("...." + "kk" + ".." + "kkkk" + "..." + "kD" + "S" * 13 + "HH")  # 54
    rows.append("kD" + "S" * 13 + "HH")              # 55 prow V, keel light
    rows.append("kD" + "S" * 11 + "HH")              # 56
    rows.append("kD" + "S" * 9 + "HH")               # 57
    rows.append("kD" + "S" * 7 + "HH")               # 58
    rows.append("kD" + "S" * 5 + "HH")               # 59
    rows.append("kD" + "S" * 3 + "HH")               # 60
    rows.append("kD" + "S" + "HH")                   # 61
    rows.append("kDHH")                              # 62
    rows.append("kkk")                               # 63
    return GI.pad_left(rows, 32)


def boss1_64_frames():
    grid = GI.mirror(boss1_half64())
    base = {
        "k": (10, 14, 24, 255),      # outline
        "D": (44, 58, 82, 255),      # dark steel
        "S": (88, 112, 146, 255),    # steel
        "H": (158, 180, 210, 255),   # light steel
    }
    f1 = GI.leg(base, g=(110, 235, 255, 255), h=(225, 255, 255, 255))  # core ON
    f2 = GI.leg(base, g=(45, 120, 160, 255), h=(45, 120, 160, 255))    # core dim
    return [GI.render(grid, f1, "boss1_64 f1"), GI.render(grid, f2, "boss1_64 f2")]


# ---- BOSS2 "CRIMSON TWIN" 64x64: crimson bio-mech. Bigger horned heads,
#      wider wing with THREE bone ribs and more glow membrane cells,
#      three claws per wing, thicker ribbed spine with long tail. ----
BOSS2_HEAD64 = [  # 13 cols, pasted at col 4 (one head; mirrored -> twin)
    ".kk.......kk.",
    ".kDk.....kDk.",
    "..kDk...kDk..",
    "..kCkkkkkCk..",
    ".kCCCCCCCCCk.",
    "kCCCCCCCCCCCk",
    "kCDDDDDDDDDCk",
    "kCDgggggggDCk",
    "kCDgggggggDCk",
    "kCCCCCCCCCCCk",
    "kCCCCCCCCCCCk",
    ".kFCCCCCCCFk.",
    ".kFkkCCCkkFk.",
    "..kkFFFFFkk..",
    "....kkkkk....",
]


def boss2_half64():
    W, H = 32, 64
    g = [["."] * W for _ in range(H)]

    # --- wing: solid triangle (root at spine, tip out-left, back corner low)
    A = (25.0, 14.0)   # root (x=col, y=row)
    B = (0.0, 34.0)    # outer tip
    C = (21.0, 53.0)   # trailing corner

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p):
        d1, d2, d3 = cross(A, B, p), cross(B, C, p), cross(C, A, p)
        neg = d1 < 0 or d2 < 0 or d3 < 0
        pos = d1 > 0 or d2 > 0 or d3 > 0
        return not (neg and pos)

    def seg_dist(p, a, b):
        px_, py_ = p
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        t = ((px_ - ax) * dx + (py_ - ay) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return math.hypot(px_ - (ax + dx * t), py_ - (ay + dy * t))

    ribs = [(B[0] + (C[0] - B[0]) * t, B[1] + (C[1] - B[1]) * t)
            for t in (0.25, 0.5, 0.75)]
    for r in range(H):
        for c in range(24):
            p = (float(c), float(r))
            if not inside(p):
                continue
            dedge = min(seg_dist(p, A, B), seg_dist(p, B, C), seg_dist(p, C, A))
            drib = min(seg_dist(p, A, q) for q in ribs)
            if drib <= 0.8:
                g[r][c] = "D"                      # bone rib
            elif dedge > 2.4 and drib > 2.0:
                g[r][c] = "g"                      # membrane glow cell
            else:
                g[r][c] = "C"

    # --- claws hanging from the wing's lower edge (connected)
    for cc in (4, 11, 18):
        bot = max(r for r in range(H) if g[r][cc] != ".")
        for i in range(6):
            rr = bot + 1 + i
            if rr >= H:
                break
            for c2 in range(cc, min(W, cc + (2 if i < 4 else 1))):
                g[rr][c2] = "C" if i == 0 else "D"

    # --- spine / central body (cols 24-31), ribbed
    for r in range(3, 59):
        seg = "kDCCCCCC" if (r // 3) % 2 == 0 else "kDDCCCCC"
        for i, ch in enumerate(seg):
            g[r][24 + i] = ch
    for r, seg in ((59, "kDCCC"), (60, "kDCC"), (61, "kDC"),
                   (62, "kDC"), (63, "kD")):
        for i, ch in enumerate(seg):
            g[r][32 - len(seg) + i] = ch

    # --- segmented dorsal glow vein down the spine (pulses with the frames)
    for r in range(6, 54):
        if (r // 3) % 2 == 0:
            g[r][30] = "g"
            g[r][31] = "g"

    # --- solid shoulder block joining head to spine
    for col in range(17, 24):
        for rr in range(6, 16):
            if g[rr][col] == ".":
                g[rr][col] = "C"

    # --- head pod (twin via mirror)
    for r, line in enumerate(BOSS2_HEAD64):
        for i, ch in enumerate(line):
            if ch != ".":
                g[r][6 + i] = ch

    # --- auto outline: colored cells 4-adjacent to transparency become 'k'
    out = [row[:] for row in g]
    for r in range(H):
        for c in range(W):
            if g[r][c] in (".", "k", "g"):
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if cc == W:                          # mirror seam is not an edge
                    continue
                if not (0 <= rr < H) or not (0 <= cc < W) or g[rr][cc] == ".":
                    out[r][c] = "k"
                    break
    return ["".join(row) for row in out]


def boss2_64_frames():
    grid = GI.mirror(boss2_half64())
    base = {
        "k": (26, 4, 14, 255),      # outline
        "C": (198, 44, 66, 255),    # crimson
        "D": (112, 10, 34, 255),    # dark crimson
        "F": (246, 158, 148, 255),  # pale bone/flesh
    }
    f1 = GI.leg(base, g=(255, 150, 80, 255))   # membrane + eyes glow hot
    f2 = GI.leg(base, g=(150, 44, 52, 255))    # membrane + eyes dim
    return [GI.render(grid, f1, "boss2_64 f1"), GI.render(grid, f2, "boss2_64 f2")]


# ---- BOSS3 "OMEGA CORE" 64x64: dark-purple fortress core. Bigger eye with
#      taller slit pupil, inner disc, recessed toothed gap, a NEW wide
#      segmented armor ring, 12 spikes reaching the frame edge, 8 blinking
#      warning lights (4 inner + 4 on the ring). ----
def boss3_grid64():
    n = 64
    c = (n - 1) / 2.0
    rows = []

    def angdist(a, step, offset=0.0):
        d = (a - offset) % step
        return min(d, step - d)

    for y in range(n):
        line = ""
        for x in range(n):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            ch = "."
            if r <= 9.8:
                if abs(dx) <= 1.7 and abs(dy) <= 7.6:
                    ch = "p"                                  # slit pupil
                else:
                    ch = "g"                                  # baleful iris
            elif r <= 11.8:
                ch = "k"                                      # eye rim
            elif r <= 17.8:
                ch = "P"                                      # inner disc
                if angdist(a, math.pi / 4) * r <= 1.1:
                    ch = "D"                                  # radial seams
                if abs(r - 15.2) <= 0.9 and angdist(a, math.pi / 4, math.pi / 8) * r <= 1.1:
                    ch = "L"                                  # rivet lights
            elif r <= 19.6:
                ch = "D"                                      # recessed gap
                if r <= 18.9 and angdist(a, math.pi / 8) * r <= 0.8:
                    ch = "P"                                  # inward teeth
            elif r <= 20.8:
                ch = "k"
            elif r <= 26.4:
                ch = "P"                                      # big outer armor ring
                if r <= 22.3 and dy < 0:
                    ch = "L"                                  # top highlight
                if r > 25.0:
                    ch = "D"                                  # bottom shade of ring
                if angdist(a, math.pi / 4, math.pi / 8) * r <= 1.3:
                    ch = "k"                                  # segment gaps
            elif r <= 27.6:
                ch = "k"
            else:
                # 12 spikes (offset 15 deg, every 30 deg), tips reach the edge
                d = angdist(a, math.pi / 6, math.pi / 12) * r
                reach = (32.4 - r) * 1.0
                if r <= 32.4 and d <= reach:
                    ch = "D" if d <= reach - 1.3 else "k"
            # brow: hood the eye from above for menace
            if 6.4 <= r <= 13.6 and dy <= -3.7 and ch in ("g", "k", "P"):
                ch = "D"
            # 8 warning lights (frame-toggled): 4 inner disc + 4 on armor ring
            for lr, langs in ((14.6, (0.0, math.pi / 2, math.pi, -math.pi / 2)),
                              (23.6, (math.pi / 4, 3 * math.pi / 4,
                                      -math.pi / 4, -3 * math.pi / 4))):
                for la in langs:
                    lx, ly = lr * math.cos(la), lr * math.sin(la)
                    if math.hypot(dx - lx, dy - ly) <= 1.8:
                        ch = "h"
            line += ch
        rows.append(line)
    return rows


def boss3_64_frames():
    grid = boss3_grid64()
    base = {
        "k": (14, 6, 24, 255),       # outline / near-black
        "p": (8, 2, 8, 255),         # pupil slit
        "P": (120, 70, 170, 255),    # mid purple armor
        "D": (60, 26, 92, 255),      # dark purple
        "L": (180, 150, 220, 255),   # lavender highlight
    }
    f1 = GI.leg(base, g=(255, 66, 48, 255), h=(255, 88, 88, 255))    # red glare
    f2 = GI.leg(base, g=(255, 196, 70, 255), h=(60, 26, 92, 255))    # amber flare
    return [GI.render(grid, f1, "boss3_64 f1"), GI.render(grid, f2, "boss3_64 f2")]


# ============================================================================
# BACKGROUNDS — regenerated at 256x256, vertically seamless, same style
# ============================================================================

def nds_bg1():
    """deep space starfield (style of gen_bg1, seed 101)."""
    rng = random.Random(101)
    base = (7, 9, 26, 255)
    px = [[base] * NBG for _ in range(NBG)]
    px = [list(r) for r in px]

    # faint nebula wisps
    for _ in range(4):
        cx = rng.uniform(0, NBG)
        cy = rng.uniform(0, NBG)
        rx = rng.uniform(20, 48)
        ry = rng.uniform(30, 70)
        col = rng.choice([(15, 13, 44), (22, 14, 50), (11, 17, 46)])
        for dy in range(-int(ry), int(ry) + 1):
            for dx in range(-int(rx), int(rx) + 1):
                d = (dx / rx) ** 2 + (dy / ry) ** 2
                if d < 1 and rng.random() > d * 1.15:
                    px[int(cy + dy) % NBG][int(cx + dx) % NBG] = \
                        (col[0], col[1], col[2], 255)

    # stars: 3 brightness tiers (counts scaled to the smaller canvas)
    for _ in range(64):
        x, y = rng.randrange(NBG), rng.randrange(NBG)
        px[y][x] = (70, 80, 122, 255)
    for _ in range(24):
        x, y = rng.randrange(NBG), rng.randrange(NBG)
        px[y][x] = (150, 160, 200, 255)
    for _ in range(9):
        x, y = rng.randrange(NBG), rng.randrange(NBG)
        px[y][x] = (240, 244, 255, 255)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            px[(y + dy) % NBG][(x + dx) % NBG] = (120, 128, 170, 255)
    return px


def nds_bg2():
    """red nebula sector (style of gen_bg2, seed 202)."""
    rng = random.Random(202)
    base = (34, 10, 16, 255)
    px = [list(r) for r in [[base] * NBG for _ in range(NBG)]]

    def h2(x, y):
        return (x * 31 + y * 57 + (x ^ y) * 13) % 100

    bands = []
    for _ in range(3):
        bands.append((
            rng.uniform(0, NBG),
            rng.uniform(8, 16),
            rng.uniform(3, 7),
            rng.uniform(0, 2 * math.pi),
            rng.uniform(0, 2 * math.pi),
            rng.uniform(12, 24),
            rng.choice([(46, 14, 22), (56, 18, 28), (44, 16, 30)]),
        ))
    for x in range(NBG):
        for (y0, a1, a2, p1, p2, th, col) in bands:
            cy = (y0 + a1 * math.sin(2 * math.pi * x / NBG + p1)
                     + a2 * math.sin(4 * math.pi * x / NBG + p2))
            for yy in range(int(cy - th), int(cy + th) + 1):
                y = yy % NBG
                fall = abs(yy - cy) / th
                if fall < 0.45 or h2(x, y) > fall * 110:
                    c2 = col
                    if fall < 0.22 and h2(x, y) % 3:
                        c2 = (col[0] + 9, col[1] + 3, col[2] + 4)
                    px[y][x] = (c2[0], c2[1], c2[2], 255)

    # asteroid silhouettes with a faint rim light
    for _ in range(6):
        cx = rng.uniform(8, NBG - 8)
        cy = rng.uniform(0, NBG)
        rr = rng.uniform(2.5, 7.0)
        for dy in range(-int(rr) - 1, int(rr) + 2):
            for dx in range(-int(rr) - 1, int(rr) + 2):
                d = math.hypot(dx, dy)
                if d <= rr:
                    x = int(cx + dx) % NBG
                    y = int(cy + dy) % NBG
                    if d > rr - 1.4 and dx <= 0 and dy <= 0:
                        px[y][x] = (72, 38, 42, 255)
                    else:
                        px[y][x] = (14, 5, 9, 255)
    return px


def nds_bg3():
    """fortress interior (style of gen_bg3): 32px panels so 256 tiles evenly."""
    P = 32

    def phash(px_, py_):
        return (px_ * 73856093 ^ py_ * 19349663) % 1000

    tints = [(27, 33, 29), (29, 36, 31), (25, 31, 28), (31, 38, 33)]
    rows = []
    for y in range(NBG):
        row = []
        pyi = y // P
        ly = y % P
        for x in range(NBG):
            pxi = x // P
            lx = x % P
            hsh = phash(pxi, pyi)
            c = tints[hsh % 4]
            # hazard stripe panels (sparse)
            if hsh % 17 == 0:
                if 5 <= lx <= 26 and 5 <= ly <= 26:
                    c = (54, 50, 24) if ((x + y) // 4) % 2 == 0 else (24, 26, 20)
                elif 3 <= lx <= 28 and 3 <= ly <= 28:
                    c = (18, 22, 19)
            # vent grille panels
            elif hsh % 13 == 0 and 8 <= lx <= 23 and 10 <= ly <= 21:
                c = (16, 20, 18) if ly % 4 < 2 else (33, 40, 35)
            # panel seams + bevel
            if lx == 0 or ly == 0:
                c = (14, 18, 16)
            elif lx == 1 or ly == 1:
                c = (36, 44, 39)
            elif lx == 31 or ly == 31:
                c = (20, 25, 22)
            # rivets near corners
            if (lx, ly) in ((3, 3), (28, 3), (3, 28), (28, 28)):
                c = (52, 62, 54)
            elif (lx, ly) in ((4, 4), (29, 4), (4, 29), (29, 29)):
                c = (15, 19, 17)
            row.append((c[0], c[1], c[2], 255))
        rows.append(row)

    # two vertical pipes running the full height (couplings every 64 -> wraps)
    for x0 in (72, 176):
        for y in range(NBG):
            for i in range(8):
                x = x0 + i
                if i in (0, 7):
                    c = (13, 17, 15)
                elif i in (1, 6):
                    c = (30, 38, 33)
                elif i == 2:
                    c = (56, 66, 58)   # highlight strip
                else:
                    c = (42, 52, 46)
                if y % 64 < 4:
                    c = (18, 23, 20) if i in (0, 7) else (50, 60, 52)
                rows[y][x] = (c[0], c[1], c[2], 255)
    return rows


# ============================================================================
# FONT — 5x7 in 8x8, ASCII 32..95 (glyph pixels use palette index 1)
# ============================================================================
# Glyph data for ASCII 32..95 is taken verbatim from Pimoroni's microdot-phat
# font (column bytes, LSB = top row):
#   https://github.com/pimoroni/microdot-phat/blob/47f9cc35e6ed3523d02b9d5c6453cd7ad3eb73fc/library/microdotphat/font.py
#
#   MIT License
#   Copyright (c) 2017 Pimoroni Ltd.
#   Full license text: THIRD-PARTY-NOTICES.md (repository root) and
#   https://github.com/pimoroni/microdot-phat/blob/master/LICENSE
FONT57 = [
    (0x00, 0x00, 0x00, 0x00, 0x00),  # 32 space
    (0x00, 0x00, 0x5F, 0x00, 0x00),  # 33 !
    (0x00, 0x07, 0x00, 0x07, 0x00),  # 34 "
    (0x14, 0x7F, 0x14, 0x7F, 0x14),  # 35 #
    (0x24, 0x2A, 0x7F, 0x2A, 0x12),  # 36 $
    (0x23, 0x13, 0x08, 0x64, 0x62),  # 37 %
    (0x36, 0x49, 0x55, 0x22, 0x50),  # 38 &
    (0x00, 0x05, 0x03, 0x00, 0x00),  # 39 '
    (0x00, 0x1C, 0x22, 0x41, 0x00),  # 40 (
    (0x00, 0x41, 0x22, 0x1C, 0x00),  # 41 )
    (0x08, 0x2A, 0x1C, 0x2A, 0x08),  # 42 *
    (0x08, 0x08, 0x3E, 0x08, 0x08),  # 43 +
    (0x00, 0x50, 0x30, 0x00, 0x00),  # 44 ,
    (0x08, 0x08, 0x08, 0x08, 0x08),  # 45 -
    (0x00, 0x60, 0x60, 0x00, 0x00),  # 46 .
    (0x20, 0x10, 0x08, 0x04, 0x02),  # 47 /
    (0x3E, 0x51, 0x49, 0x45, 0x3E),  # 48 0
    (0x00, 0x42, 0x7F, 0x40, 0x00),  # 49 1
    (0x42, 0x61, 0x51, 0x49, 0x46),  # 50 2
    (0x21, 0x41, 0x45, 0x4B, 0x31),  # 51 3
    (0x18, 0x14, 0x12, 0x7F, 0x10),  # 52 4
    (0x27, 0x45, 0x45, 0x45, 0x39),  # 53 5
    (0x3C, 0x4A, 0x49, 0x49, 0x30),  # 54 6
    (0x01, 0x71, 0x09, 0x05, 0x03),  # 55 7
    (0x36, 0x49, 0x49, 0x49, 0x36),  # 56 8
    (0x06, 0x49, 0x49, 0x29, 0x1E),  # 57 9
    (0x00, 0x36, 0x36, 0x00, 0x00),  # 58 :
    (0x00, 0x56, 0x36, 0x00, 0x00),  # 59 ;
    (0x00, 0x08, 0x14, 0x22, 0x41),  # 60 <
    (0x14, 0x14, 0x14, 0x14, 0x14),  # 61 =
    (0x41, 0x22, 0x14, 0x08, 0x00),  # 62 >
    (0x02, 0x01, 0x51, 0x09, 0x06),  # 63 ?
    (0x32, 0x49, 0x79, 0x41, 0x3E),  # 64 @
    (0x7E, 0x11, 0x11, 0x11, 0x7E),  # 65 A
    (0x7F, 0x49, 0x49, 0x49, 0x36),  # 66 B
    (0x3E, 0x41, 0x41, 0x41, 0x22),  # 67 C
    (0x7F, 0x41, 0x41, 0x22, 0x1C),  # 68 D
    (0x7F, 0x49, 0x49, 0x49, 0x41),  # 69 E
    (0x7F, 0x09, 0x09, 0x01, 0x01),  # 70 F
    (0x3E, 0x41, 0x41, 0x51, 0x32),  # 71 G
    (0x7F, 0x08, 0x08, 0x08, 0x7F),  # 72 H
    (0x00, 0x41, 0x7F, 0x41, 0x00),  # 73 I
    (0x20, 0x40, 0x41, 0x3F, 0x01),  # 74 J
    (0x7F, 0x08, 0x14, 0x22, 0x41),  # 75 K
    (0x7F, 0x40, 0x40, 0x40, 0x40),  # 76 L
    (0x7F, 0x02, 0x04, 0x02, 0x7F),  # 77 M
    (0x7F, 0x04, 0x08, 0x10, 0x7F),  # 78 N
    (0x3E, 0x41, 0x41, 0x41, 0x3E),  # 79 O
    (0x7F, 0x09, 0x09, 0x09, 0x06),  # 80 P
    (0x3E, 0x41, 0x51, 0x21, 0x5E),  # 81 Q
    (0x7F, 0x09, 0x19, 0x29, 0x46),  # 82 R
    (0x46, 0x49, 0x49, 0x49, 0x31),  # 83 S
    (0x01, 0x01, 0x7F, 0x01, 0x01),  # 84 T
    (0x3F, 0x40, 0x40, 0x40, 0x3F),  # 85 U
    (0x1F, 0x20, 0x40, 0x20, 0x1F),  # 86 V
    (0x7F, 0x20, 0x18, 0x20, 0x7F),  # 87 W
    (0x63, 0x14, 0x08, 0x14, 0x63),  # 88 X
    (0x03, 0x04, 0x78, 0x04, 0x03),  # 89 Y
    (0x61, 0x51, 0x49, 0x45, 0x43),  # 90 Z
    (0x00, 0x00, 0x7F, 0x41, 0x41),  # 91 [
    (0x02, 0x04, 0x08, 0x10, 0x20),  # 92 backslash
    (0x41, 0x41, 0x7F, 0x00, 0x00),  # 93 ]
    (0x04, 0x02, 0x01, 0x02, 0x04),  # 94 ^
    (0x40, 0x40, 0x40, 0x40, 0x40),  # 95 _
]

FONT_FIRST_CHAR = 32
FONT_CHARS = 64

FONT_PAL_RGB = [
    (0, 0, 0),          # 0 transparent (value unused by HW)
    (255, 255, 255),    # 1 TXT_WHITE
    (255, 200, 64),     # 2 TXT_GOLD
    (255, 64, 64),      # 3 TXT_RED
    (64, 224, 96),      # 4 TXT_GREEN
    (80, 200, 255),     # 5 TXT_CYAN
    (152, 160, 176),    # 6 TXT_GREY
    (255, 144, 32),     # 7 TXT_ORANGE
] + [(255, 255, 255)] * 8   # 8..15 spare = white


def build_font_tiles():
    """4bpp tiles: 32 bytes/glyph, low nibble = left pixel, pixel value 1."""
    data = bytearray()
    for glyph in FONT57:
        vals = [[0] * 8 for _ in range(8)]
        for cx in range(5):
            colbits = glyph[cx]
            for cy in range(7):
                if (colbits >> cy) & 1:
                    vals[cy][cx + 1] = 1    # 1px left margin, rows 0..6
        for y in range(8):
            for x in range(0, 8, 2):
                data.append(vals[y][x] | (vals[y][x + 1] << 4))
    return bytes(data)


# ============================================================================
# encoders / decoders
# ============================================================================

def encode_sprite_frame(frame, pal_map):
    """RGBA grid -> 8bpp 1D tiles (LtR, TtB; 64 row-major px per tile)."""
    H, W = len(frame), len(frame[0])
    out = bytearray()
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            for y in range(ty, ty + 8):
                for x in range(tx, tx + 8):
                    r, g, b, a = frame[y][x]
                    assert a in (0, 255), "unexpected alpha %d" % a
                    out.append(0 if a == 0 else pal_map[bgr555(r, g, b)])
    return bytes(out)


def decode_sprite_frame(data, off, W, H):
    """inverse of encode_sprite_frame -> grid of palette indices."""
    px = [[0] * W for _ in range(H)]
    i = off
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            for y in range(8):
                for x in range(8):
                    px[ty + y][tx + x] = data[i]
                    i += 1
    return px


def flip_tile(t, fh, fv):
    out = bytearray(64)
    for y in range(8):
        for x in range(8):
            sx = 7 - x if fh else x
            sy = 7 - y if fv else y
            out[y * 8 + x] = t[sy * 8 + sx]
    return bytes(out)


def encode_bg(pxgrid, name):
    """opaque 256x256 RGBA -> (tiles, map_entries, pal256_u16, idx_grid)."""
    pal = []
    pal_map = {}
    idxg = [[0] * NBG for _ in range(NBG)]
    for y in range(NBG):
        for x in range(NBG):
            r, g, b, a = pxgrid[y][x]
            assert a == 255, "%s: bg pixel not opaque" % name
            v = bgr555(r, g, b)
            if v not in pal_map:
                if len(pal) >= 255:
                    print("FATAL: %s exceeds 255 colours" % name)
                    sys.exit(1)
                pal_map[v] = len(pal) + 1          # indices from 1: 0 never used
                pal.append(v)
            idxg[y][x] = pal_map[v]

    tiles = []
    lookup = {}
    mapent = []
    for ty in range(32):
        for tx in range(32):
            t = bytes(idxg[ty * 8 + y][tx * 8 + x]
                      for y in range(8) for x in range(8))
            ent = None
            for fh in (0, 1):
                for fv in (0, 1):
                    v = flip_tile(t, fh, fv)
                    if v in lookup:
                        ent = lookup[v] | (fh << 10) | (fv << 11)
                        break
                if ent is not None:
                    break
            if ent is None:
                lookup[t] = len(tiles)
                ent = len(tiles)
                tiles.append(t)
            mapent.append(ent)
    pal256 = [0] * 256
    for i, v in enumerate(pal):
        pal256[i + 1] = v
    return tiles, mapent, pal256, idxg


def decode_bg(tiles, mapent):
    """rebuild 256x256 index grid from tiles + map (honouring flip bits)."""
    idxg = [[0] * NBG for _ in range(NBG)]
    for ti, ent in enumerate(mapent):
        tidx = ent & 0x3FF
        fh, fv = (ent >> 10) & 1, (ent >> 11) & 1
        shown = flip_tile(tiles[tidx], fh, fv)
        ty, tx = (ti // 32) * 8, (ti % 32) * 8
        for y in range(8):
            for x in range(8):
                idxg[ty + y][tx + x] = shown[y * 8 + x]
    return idxg


# ============================================================================
# C emission
# ============================================================================

def fmt_u8(data):
    lines = []
    for i in range(0, len(data), 16):
        lines.append("  " + ",".join("0x%02X" % b for b in data[i:i + 16]) + ",")
    return "\n".join(lines)


def fmt_u16(data):
    lines = []
    for i in range(0, len(data), 8):
        lines.append("  " + ",".join("0x%04X" % v for v in data[i:i + 8]) + ",")
    return "\n".join(lines)


def emit_header(sprites, bgs, total_vram):
    L = []
    L.append("#ifndef GFX_DATA_H")
    L.append("#define GFX_DATA_H")
    L.append("#include <nds.h>")
    L.append("")
    L.append("// AUTO-GENERATED by shooter/tools/generate_nds_gfx.py -- do not edit.")
    L.append("//")
    L.append("// total sprite VRAM needed: %d bytes of 8bpp tile data "
             "(shared palette spr_pal)" % total_vram)
    for name, tiles, mapent, pal, idxg in bgs:
        L.append("// %s: %d unique 8x8 tiles (%d bytes tile data, "
                 "%d bytes map)" % (name, len(tiles), len(tiles) * 64,
                                    len(mapent) * 2))
    L.append("")
    L.append("// ---- shared sprite palette (index 0 = transparent) ----")
    L.append("extern const u16 spr_pal[256];")
    L.append("")
    L.append("// ---- per sprite: tile data + metrics ----")
    L.append("// SPR_<NAME>_TILES = 8x8 tiles per frame; data length = TILES*64*FRAMES")
    for (name, W, H, frames, data) in sprites:
        up = name.upper()
        tiles = (W // 8) * (H // 8)
        L.append("extern const u8 spr_%s[];" % name)
        L.append("#define SPR_%s_W %d" % (up, W))
        L.append("#define SPR_%s_H %d" % (up, H))
        L.append("#define SPR_%s_FRAMES %d" % (up, len(frames)))
        L.append("#define SPR_%s_TILES %d" % (up, tiles))
        L.append("#define SPR_%s_SIZE SpriteSize_%dx%d" % (up, W, H))
        L.append("")
    L.append("// ---- backgrounds (index 0..2 == stage 1..3) ----")
    L.append("typedef struct {")
    L.append("    const u8  *tiles;      // 8bpp, 64 bytes per tile")
    L.append("    u32        tiles_len;  // bytes")
    L.append("    const u16 *map;        // 32*32 entries")
    L.append("    const u16 *pal;        // 256 entries")
    L.append("} BgData;")
    L.append("extern const BgData bg_data[3];")
    L.append("")
    L.append("// ---- font ----")
    L.append("extern const u8  font_tiles[];   // 4bpp, 32 bytes per glyph")
    L.append("extern const u16 font_pal[16];")
    L.append("#define FONT_FIRST_CHAR %d" % FONT_FIRST_CHAR)
    L.append("#define FONT_CHARS %d" % FONT_CHARS)
    L.append("// palette index constants for text colour")
    L.append("#define TXT_WHITE 1")
    L.append("#define TXT_GOLD 2")
    L.append("#define TXT_RED 3")
    L.append("#define TXT_GREEN 4")
    L.append("#define TXT_CYAN 5")
    L.append("#define TXT_GREY 6")
    L.append("#define TXT_ORANGE 7")
    L.append("#endif")
    L.append("")
    return "\n".join(L)


def emit_source(spr_pal256, sprites, bgs, font_tiles, font_pal16):
    L = []
    L.append("// AUTO-GENERATED by shooter/tools/generate_nds_gfx.py -- do not edit.")
    L.append('#include "gfx_data.h"')
    L.append("")
    L.append("const u16 spr_pal[256] ALIGN(4) = {")
    L.append(fmt_u16(spr_pal256))
    L.append("};")
    L.append("")
    for (name, W, H, frames, data) in sprites:
        L.append("// %s: %dx%d, %d frame(s), %d bytes" %
                 (name, W, H, len(frames), len(data)))
        L.append("const u8 spr_%s[%d] ALIGN(4) = {" % (name, len(data)))
        L.append(fmt_u8(data))
        L.append("};")
        L.append("")
    for name, tiles, mapent, pal, idxg in bgs:
        tdata = b"".join(tiles)
        L.append("// %s: %d unique tiles" % (name, len(tiles)))
        L.append("static const u8 %s_tiles[%d] ALIGN(4) = {" % (name, len(tdata)))
        L.append(fmt_u8(tdata))
        L.append("};")
        L.append("static const u16 %s_map[%d] ALIGN(4) = {" % (name, len(mapent)))
        L.append(fmt_u16(mapent))
        L.append("};")
        L.append("static const u16 %s_pal[256] ALIGN(4) = {" % name)
        L.append(fmt_u16(pal))
        L.append("};")
        L.append("")
    L.append("const BgData bg_data[3] = {")
    for name, tiles, mapent, pal, idxg in bgs:
        L.append("    { %s_tiles, sizeof(%s_tiles), %s_map, %s_pal }," %
                 (name, name, name, name))
    L.append("};")
    L.append("")
    # The glyphs come from a third-party MIT font: keep its notice with the data.
    L.append("// Font glyphs (ASCII 32..95): Pimoroni microdot-phat font.py")
    L.append("// https://github.com/pimoroni/microdot-phat")
    L.append("// MIT License, Copyright (c) 2017 Pimoroni Ltd.")
    L.append("// Full license text: THIRD-PARTY-NOTICES.md / shooter-nds/licenses/")
    L.append("const u8 font_tiles[%d] ALIGN(4) = {" % len(font_tiles))
    L.append(fmt_u8(font_tiles))
    L.append("};")
    L.append("")
    L.append("const u16 font_pal[16] ALIGN(4) = {")
    L.append(fmt_u16(font_pal16))
    L.append("};")
    L.append("")
    return "\n".join(L)


# ============================================================================
# previews (round-trip: decoded from the emitted bytes + palettes)
# ============================================================================

BACKDROP = (28, 28, 36, 255)
SEP = (55, 55, 70, 255)


def preview_sprite(name, data, W, H, nframes, pal_u16):
    frames_px = []
    fsize = (W // 8) * (H // 8) * 64
    for f in range(nframes):
        idx = decode_sprite_frame(data, f * fsize, W, H)
        px = [[BACKDROP if idx[y][x] == 0 else
               (rgb888(pal_u16[idx[y][x]]) + (255,))
               for x in range(W)] for y in range(H)]
        frames_px.append(px)
        if f != nframes - 1:
            frames_px.append([[SEP] * 2 for _ in range(H)])
    sheet = GI.hstack(frames_px)
    GI.write_png(os.path.join(PREVIEW_DIR, "spr_%s.png" % name),
                 GI.upscale(sheet, 6))


def preview_bg(name, tiles, mapent, pal_u16):
    idxg = decode_bg(tiles, mapent)
    px = [[rgb888(pal_u16[idxg[y][x]]) + (255,) for x in range(NBG)]
          for y in range(NBG)]
    GI.write_png(os.path.join(PREVIEW_DIR, "%s.png" % name), px)
    GI.write_png(os.path.join(PREVIEW_DIR, "%s_x2.png" % name), px + px)


def preview_font(font_tiles, pal_u16):
    cols, rows = 16, 4
    W, H = cols * 8, rows * 8
    px = [[(16, 16, 24, 255)] * W for _ in range(H)]
    for gi in range(FONT_CHARS):
        gx, gy = (gi % cols) * 8, (gi // cols) * 8
        base = gi * 32
        for y in range(8):
            for xb in range(4):
                b = font_tiles[base + y * 4 + xb]
                for sub, v in ((0, b & 0xF), (1, b >> 4)):
                    if v:
                        px[gy + y][gx + xb * 2 + sub] = \
                            rgb888(pal_u16[v]) + (255,)
    GI.write_png(os.path.join(PREVIEW_DIR, "font.png"), GI.upscale(px, 6))


# ============================================================================
# main
# ============================================================================

def main():
    os.makedirs(SRC_DIR, exist_ok=True)
    os.makedirs(INC_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        return cond

    # ---- gather sprite frames at final DS sizes -----------------------------
    specs = [
        ("player",        GI.player_frames,        16, 16),
        ("enemy1",        GI.enemy1_frames,        16, 16),
        ("enemy2",        GI.enemy2_frames,        16, 16),
        ("enemy3",        GI.enemy3_frames,        16, 16),
        ("midenemy",      midenemy32_frames,       32, 32),
        ("boss1",         boss1_64_frames,         64, 64),
        ("boss2",         boss2_64_frames,         64, 64),
        ("boss3",         boss3_64_frames,         64, 64),
        ("bullet_player", GI.bullet_player_frames,  8, 16),
        ("bullet_enemy",  GI.bullet_enemy_frames,   8,  8),
        ("explosion",     GI.explosion_frames,     16, 16),
        ("powerup",       GI.powerup_frames,        8,  8),
        # ground installations + two-piece mid-boss (appended LAST so the
        # shared palette indices of all pre-existing sprites are unchanged)
        ("gturret",       GI.gturret_frames,       16, 16),
        ("gradar",        GI.gradar_frames,        16, 16),
        ("midcore",       GI.midcore_frames,       32, 32),
        ("midpart",       GI.midpart_frames,       16, 16),
    ]
    gathered = []
    for name, fn, W, H in specs:
        frames = [center_pad(f, W, H) for f in fn()]
        gathered.append((name, W, H, frames))

    # ---- shared sprite palette ----------------------------------------------
    spr_pal_map = {}     # bgr555 -> index (>= 1)
    spr_pal = []         # list of bgr555 in index order
    for name, W, H, frames in gathered:
        for f in frames:
            for row in f:
                for (r, g, b, a) in row:
                    if a == 0:
                        continue
                    v = bgr555(r, g, b)
                    if v not in spr_pal_map:
                        spr_pal_map[v] = len(spr_pal) + 1
                        spr_pal.append(v)
    if len(spr_pal) > 255:
        print("FATAL: sprite palette needs %d colours (max 255)" % len(spr_pal))
        sys.exit(1)
    spr_pal256 = [0] * 256
    for i, v in enumerate(spr_pal):
        spr_pal256[i + 1] = v

    # ---- encode sprites ------------------------------------------------------
    sprites = []
    for name, W, H, frames in gathered:
        data = b"".join(encode_sprite_frame(f, spr_pal_map) for f in frames)
        sprites.append((name, W, H, frames, data))

    # ---- backgrounds ---------------------------------------------------------
    bgs = []
    for name, fn in (("bg1", nds_bg1), ("bg2", nds_bg2), ("bg3", nds_bg3)):
        pxgrid = fn()
        tiles, mapent, pal256, idxg = encode_bg(pxgrid, name)
        bgs.append((name, tiles, mapent, pal256, idxg))

    # ---- font ----------------------------------------------------------------
    font_tiles = build_font_tiles()
    font_pal16 = [bgr555(*c) for c in FONT_PAL_RGB]
    font_pal16[0] = 0

    # ---- emit ----------------------------------------------------------------
    total_vram = sum(len(d) for (_, _, _, _, d) in sprites)
    hdr = emit_header(sprites, bgs, total_vram)
    src = emit_source(spr_pal256, sprites, bgs, font_tiles, font_pal16)
    hdr_path = os.path.join(INC_DIR, "gfx_data.h")
    src_path = os.path.join(SRC_DIR, "gfx_data.c")
    with open(hdr_path, "w") as f:
        f.write(hdr)
    with open(src_path, "w") as f:
        f.write(src)
    print("wrote %s (%d bytes)" % (hdr_path, len(hdr)))
    print("wrote %s (%d bytes)" % (src_path, len(src)))
    print()

    # ==========================================================================
    # VERIFICATION
    # ==========================================================================
    print("%-14s %-7s %6s %6s %8s  %-6s %-8s %-9s" %
          ("sprite", "size", "frames", "tiles", "bytes", "lenOK", "idx0OK", "roundtrip"))
    print("-" * 76)
    for name, W, H, frames, data in sprites:
        tiles = (W // 8) * (H // 8)
        len_ok = check(len(data) == tiles * 64 * len(frames),
                       "%s: data length %d != %d" %
                       (name, len(data), tiles * 64 * len(frames)))
        idx0_ok = True
        rt_ok = True
        fsize = tiles * 64
        for fi, f in enumerate(frames):
            idx = decode_sprite_frame(data, fi * fsize, W, H)
            for y in range(H):
                for x in range(W):
                    r, g, b, a = f[y][x]
                    if a == 0:
                        if idx[y][x] != 0:
                            rt_ok = False
                    else:
                        if idx[y][x] == 0:
                            idx0_ok = False
                        elif spr_pal256[idx[y][x]] != bgr555(r, g, b):
                            rt_ok = False
        check(idx0_ok, "%s: opaque pixel maps to palette index 0" % name)
        check(rt_ok, "%s: tile round-trip mismatch" % name)
        print("%-14s %-7s %6d %6d %8d  %-6s %-8s %-9s" %
              (name, "%dx%d" % (W, H), len(frames), tiles, len(data),
               "OK" if len_ok else "FAIL", "OK" if idx0_ok else "FAIL",
               "OK" if rt_ok else "FAIL"))
    print("-" * 76)
    print("sprite palette: %d colours used of 255 (+1 transparent)  total "
          "sprite VRAM: %d bytes" % (len(spr_pal), total_vram))
    print()

    print("%-6s %6s %10s %8s %8s %10s %6s" %
          ("bg", "tiles", "tile bytes", "map<max", "nonzero", "roundtrip", "seam"))
    print("-" * 62)
    for name, tiles, mapent, pal256, idxg in bgs:
        map_ok = check(all((e & 0x3FF) < len(tiles) for e in mapent),
                       "%s: map entry references missing tile" % name)
        nz_ok = check(all(idxg[y][x] != 0 for y in range(NBG) for x in range(NBG)),
                      "%s: a pixel maps to palette index 0" % name)
        rt_ok = check(decode_bg(tiles, mapent) == idxg,
                      "%s: tiles+map round-trip mismatch" % name)
        ncol = sum(1 for v in pal256[1:] if v != 0)
        check(len(tiles) <= 1024, "%s: too many tiles" % name)
        print("%-6s %6d %10d %8s %8s %10s %6s  (%d colours)" %
              (name, len(tiles), len(tiles) * 64,
               "OK" if map_ok else "FAIL", "OK" if nz_ok else "FAIL",
               "OK" if rt_ok else "FAIL", "-", ncol))
    print("-" * 62)
    print()

    font_ok = check(len(font_tiles) == FONT_CHARS * 32,
                    "font: %d bytes != %d" % (len(font_tiles), FONT_CHARS * 32))
    print("font: %d glyphs, %d bytes (4bpp), 16-entry palette -> %s" %
          (FONT_CHARS, len(font_tiles), "OK" if font_ok else "FAIL"))
    print()

    # ---- re-parse the emitted C and cross-check array lengths ---------------
    ctext = open(src_path).read()
    parsed = {}
    for m in re.finditer(
            r"(?:static\s+)?const\s+(u8|u16)\s+(\w+)\[(\d+)\]\s*"
            r"(?:ALIGN\(\d+\)\s*)?=\s*\{(.*?)\};", ctext, re.S):
        vals = re.findall(r"0x[0-9A-Fa-f]+", m.group(4))
        parsed[m.group(2)] = (m.group(1), int(m.group(3)), len(vals))
    expect = {"spr_pal": ("u16", 256), "font_tiles": ("u8", len(font_tiles)),
              "font_pal": ("u16", 16)}
    for name, W, H, frames, data in sprites:
        expect["spr_" + name] = ("u8", len(data))
    for name, tiles, mapent, pal256, idxg in bgs:
        expect[name + "_tiles"] = ("u8", len(tiles) * 64)
        expect[name + "_map"] = ("u16", len(mapent))
        expect[name + "_pal"] = ("u16", 256)
    reparse_ok = True
    for arr, (typ, n) in sorted(expect.items()):
        got = parsed.get(arr)
        ok = got is not None and got[0] == typ and got[1] == n and got[2] == n
        if not ok:
            reparse_ok = False
            failures.append("C re-parse: %s expected %s[%d], got %r" %
                            (arr, typ, n, got))
    print("C re-parse: %d arrays checked -> %s" %
          (len(expect), "OK" if reparse_ok else "FAIL"))
    print()

    # ---- round-trip previews (decoded from emitted data) --------------------
    for name, W, H, frames, data in sprites:
        preview_sprite(name, data, W, H, len(frames), spr_pal256)
    for name, tiles, mapent, pal256, idxg in bgs:
        preview_bg(name, tiles, mapent, pal256)
    preview_font(font_tiles, font_pal16)
    print("previews written to %s" % PREVIEW_DIR)
    print()

    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("ALL CHECKS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
