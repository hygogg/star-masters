#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_images.py — all sprite/background PNGs for the 8-bit vertical shmup.

Standard library only. PNGs are written by hand (RGBA8, single IDAT,
filter byte 0 per scanline). Deterministic: every random element uses
random.Random(fixed_seed).

Sprites are authored as list-of-strings pixel grids at BASE resolution
('.' = transparent), mirrored for symmetry, then nearest-neighbor
upscaled x2 into the deliverable sheets (1 art dot = 2 final px).
Animation frames are laid out horizontally.

Re-runnable: overwrites everything, then verifies every PNG's IHDR
against the size contract and exits non-zero on any mismatch.
"""

import math
import os
import struct
import sys
import zlib
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG_DIR = os.path.join(ROOT, "assets", "img")
# 拡大プレビューの出力先(目視確認用)。環境変数で差し替え可。
PREVIEW_DIR = os.environ.get("PREVIEW_DIR",
                             os.path.join(ROOT, "_preview", "img"))

T = (0, 0, 0, 0)  # transparent

# ----------------------------------------------------------------------------
# PNG writer (stdlib only)
# ----------------------------------------------------------------------------

def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, pixels):
    """pixels: list of rows, each row a list of (r,g,b,a) tuples."""
    h = len(pixels)
    w = len(pixels[0])
    raw = bytearray()
    for row in pixels:
        assert len(row) == w, "ragged pixel row"
        raw.append(0)  # filter type 0
        for (r, g, b, a) in row:
            raw += bytes((r, g, b, a))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" +
           _chunk(b"IHDR", ihdr) +
           _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
           _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def read_png_size(path):
    with open(path, "rb") as f:
        d = f.read(33)
    assert d[:8] == b"\x89PNG\r\n\x1a\n" and d[12:16] == b"IHDR", path
    return struct.unpack(">II", d[16:24])


# ----------------------------------------------------------------------------
# grid helpers
# ----------------------------------------------------------------------------

def upscale(pixels, n):
    out = []
    for row in pixels:
        big = []
        for p in row:
            big.extend([p] * n)
        for _ in range(n):
            out.append(list(big))
    return out


def hstack(frames):
    h = len(frames[0])
    for f in frames:
        assert len(f) == h, "frame heights differ"
    out = []
    for y in range(h):
        row = []
        for f in frames:
            row.extend(f[y])
        out.append(row)
    return out


def mirror(half_rows):
    """left half -> full width (center at the right end of each half row)."""
    return [r + r[::-1] for r in half_rows]


def pad_left(rows, width):
    out = []
    for i, r in enumerate(rows):
        assert len(r) <= width, "row %d too long (%d > %d): %r" % (i, len(r), width, r)
        out.append("." * (width - len(r)) + r)
    return out


def render(grid, legend, name):
    """grid: list of equal-length strings. legend: char -> RGBA or None(=T)."""
    w = len(grid[0])
    px = []
    for i, line in enumerate(grid):
        assert len(line) == w, "%s: row %d width %d != %d" % (name, i, len(line), w)
        row = []
        for ch in line:
            if ch not in legend:
                raise KeyError("%s: unknown char %r in row %d" % (name, ch, i))
            c = legend[ch]
            row.append(c if c else T)
        px.append(row)
    return px


def leg(base, **over):
    """copy base legend, apply overrides (name=None means transparent)."""
    d = dict(base)
    d.update(over)
    d["."] = None
    return d


# ----------------------------------------------------------------------------
# 1. PLAYER — 16x16 base, 2 frames (engine flame flickers)
# ----------------------------------------------------------------------------

PLAYER_HALF = [
    ".......W",
    ".......C",
    "......CC",
    "......CB",
    "......CB",
    ".....CBW",
    ".....CBW",
    ".....CBB",
    "....CBBB",
    "...CCBBB",
    "..CCBBBB",
    ".CCB.BBB",
    "CCB...CB",
    "......yy",
    "......2y",
    ".......2",
]

def player_frames():
    grid = mirror(PLAYER_HALF)
    base = {
        "C": (80, 210, 235, 255),   # cyan hull edge
        "B": (40, 100, 210, 255),   # blue hull
        "W": (235, 245, 255, 255),  # white cockpit / nose
        "y": (255, 210, 80, 255),   # flame
    }
    f1 = leg(base, **{"2": None})                       # short flame
    f2 = leg(base, **{"2": (255, 160, 50, 255)})        # long, hotter flame
    return [render(grid, f1, "player f1"), render(grid, f2, "player f2")]


# ----------------------------------------------------------------------------
# 2. ENEMY1 — green crab invader, claw/leg wiggle
# ----------------------------------------------------------------------------

ENEMY1_HALF = [
    "........",
    "11......",
    "1G......",
    "2G.GLLGG",
    "2GGGGGGG",
    ".GGooGGG",
    ".GGooGGG",
    ".GGGGGGG",
    "..GGLLLL",
    "...GGGGG",
    "....GGGG",
    "...G.G.G",
    "...G.G.G",
    "..212121",
    "........",
    "........",
]

def enemy1_frames():
    grid = mirror(ENEMY1_HALF)
    G = (70, 190, 70, 255)
    base = {
        "G": G,
        "L": (150, 235, 130, 255),  # light green highlight
        "o": (8, 32, 12, 255),      # dark eye sockets
    }
    f1 = leg(base, **{"1": G, "2": None})
    f2 = leg(base, **{"1": None, "2": G})
    return [render(grid, f1, "enemy1 f1"), render(grid, f2, "enemy1 f2")]


# ----------------------------------------------------------------------------
# 3. ENEMY2 — purple bat-wing drone, wing flap
# ----------------------------------------------------------------------------

ENEMY2_HALF = [
    "........",
    "uuu.....",
    "uuuu....",
    ".uuuukkk",
    "..uuukPP",
    "...uukPP",
    "...ddkPP",
    "..dddkPP",
    ".ddddkPP",
    ".ddd.kRP",
    "ddd..kRP",
    "dd...kPP",
    "......kP",
    ".......k",
    "........",
    "........",
]

def enemy2_frames():
    grid = mirror(ENEMY2_HALF)
    WING = (150, 70, 210, 255)      # purple wings
    base = {
        "k": (40, 10, 70, 255),     # dark outline
        "P": (190, 130, 240, 255),  # light lavender body
        "R": (255, 80, 80, 255),    # red eyes
    }
    f1 = leg(base, u=WING, d=None)
    f2 = leg(base, u=None, d=WING)
    return [render(grid, f1, "enemy2 f1"), render(grid, f2, "enemy2 f2")]


# ----------------------------------------------------------------------------
# 4. ENEMY3 — orange spiky orb mech with lens eye (procedural radial)
# ----------------------------------------------------------------------------

def enemy3_grid():
    n = 16
    c = (n - 1) / 2.0
    rows = []
    for y in range(n):
        line = ""
        for x in range(n):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            spike = (abs(dx) <= 0.9 or abs(dy) <= 0.9 or
                     abs(abs(dx) - abs(dy)) <= 0.9)
            if r <= 1.6:
                ch = "e"                       # lens eye (pulses)
            elif r <= 2.5:
                ch = "k"                       # lens rim
            elif r <= 4.1:
                ch = "O"                       # orange shell
            elif r <= 4.9:
                ch = "D"                       # dark shell edge
            elif spike and r <= 6.6:
                ch = "Y"                       # spike (both frames)
            elif spike and r <= 7.7:
                ch = "2"                       # longer spike tip, frame 2
            else:
                ch = "."
            line += ch
        rows.append(line)
    return rows


def enemy3_frames():
    grid = enemy3_grid()
    base = {
        "O": (240, 140, 50, 255),
        "D": (160, 60, 16, 255),
        "Y": (255, 210, 90, 255),
        "k": (60, 20, 8, 255),
    }
    f1 = leg(base, e=(210, 255, 255, 255), **{"2": None})
    f2 = leg(base, e=(120, 220, 245, 255), **{"2": (255, 210, 90, 255)})
    return [render(grid, f1, "enemy3 f1"), render(grid, f2, "enemy3 f2")]


# ----------------------------------------------------------------------------
# 5. MIDENEMY — 24x24 red heavy gunship, turret light blinks
# ----------------------------------------------------------------------------

MIDENEMY_HALF = pad_left([
    "",
    "",
    "kkkkk",
    "kDDDD",
    "kDRRRRRRRR",
    "kkDRRRRRRRRR",
    "kDDRRRRRRRRR",
    "kDRRRRRRRRRR",
    "kDRRRRRRkkkk",
    "kDRRRRRRkDLL",
    "kDRRRRRRkDLL",
    "kDRRRRRRkDLL",
    "kDRRRRRRkkkk",
    "kDkGGkRRRRRR",
    "kDkGGkRRRRRR",
    ".kkGGkDRRRRR",
    "..kGGk.kDDDD",
    "..kGGk..kkkk",
    "..kGGk......",
    "..kGGk......",
    "..kkkk......",
    "",
    "",
    "",
], 12)

def midenemy_frames():
    grid = mirror(MIDENEMY_HALF)
    base = {
        "k": (30, 6, 10, 255),      # outline
        "R": (206, 52, 56, 255),    # red hull
        "D": (118, 16, 28, 255),    # dark red
        "G": (184, 188, 198, 255),  # gray cannons
    }
    f1 = leg(base, L=(255, 244, 150, 255))   # turret light on
    f2 = leg(base, L=(118, 16, 28, 255))     # turret light off
    return [render(grid, f1, "midenemy f1"), render(grid, f2, "midenemy f2")]


# ----------------------------------------------------------------------------
# 6. BOSS1 "GUARDIAN" — 48x48 steel-blue battleship, core glow blinks
# ----------------------------------------------------------------------------

def boss1_half():
    """angular battleship: stepped shoulders, straight plateau sides with
    protruding fins, twin chunky cannon pods, glowing central core."""
    rows = []
    rows.append("kkkkkkkkkk")                 # 0  stern edge
    rows.append("kSDDSDDSDD")                 # 1  exhaust vents
    rows.append("kSDDSDDSDD")                 # 2
    rows.append("kkkkkkkkkk")                 # 3
    rows.append("k" * 14)                     # 4  step ledge
    rows.append("kD" + "S" * 12)              # 5
    rows.append("kDSS" + "H" * 8 + "SS")      # 6  highlight band
    rows.append("kD" + "S" * 12)              # 7
    rows.append("k" * 18)                     # 8  step ledge
    rows.append("kD" + "S" * 16)              # 9
    rows.append("kDSHH" + "S" * 13)           # 10
    rows.append("kDSHH" + "S" * 13)           # 11
    rows.append("k" * 22)                     # 12 step to main plateau

    def body(tail, pod=False):
        left = "kkDSkSSSkSSSSSk" if pod else "kDSHSSSSkSSSSSk"
        return left + "S" * (22 - len(left) - len(tail)) + tail

    core_tails = {16: "kk", 17: "kgg", 18: "kggg", 19: "kgggg", 20: "kgggg",
                  21: "kggggg", 22: "kggghh", 23: "kggghh", 24: "kggggg",
                  25: "kgggg", 26: "kgggg", 27: "kggg", 28: "kk"}
    for r in range(13, 33):
        b = body(core_tails.get(r, ""), pod=(r >= 26))
        if 16 <= r <= 24:                     # protruding side fin
            b = ("kk" if r in (16, 24) else "kS") + b
        rows.append(b)

    pod = "kDSk"
    for _ in range(33, 37):
        rows.append("..." + pod + "." + "kD" + "S" * 14)
    for _ in range(37, 39):
        rows.append("..." + pod + ".." + "kD" + "S" * 13)
    rows.append("..." + "kkkk" + ".." + "kD" + "S" * 13)          # 39 muzzle
    rows.append("...." + "kk" + "....." + "kD" + "S" * 9 + "HH")  # 40
    rows.append("kDSSSSSSSSHH")               # 41  prow V with light keel
    rows.append("kDSSSSSSHH")                 # 42
    rows.append("kDSSSSSHH")                  # 43
    rows.append("kDSSSHH")                    # 44
    rows.append("kDSSHH")                     # 45
    rows.append("kDHH")                       # 46
    rows.append("kkk")                        # 47
    return pad_left(rows, 24)


def boss1_frames():
    grid = mirror(boss1_half())
    base = {
        "k": (10, 14, 24, 255),      # outline
        "D": (44, 58, 82, 255),      # dark steel
        "S": (88, 112, 146, 255),    # steel
        "H": (158, 180, 210, 255),   # light steel
    }
    f1 = leg(base, g=(110, 235, 255, 255), h=(225, 255, 255, 255))  # core ON
    f2 = leg(base, g=(45, 120, 160, 255), h=(45, 120, 160, 255))    # core dim
    return [render(grid, f1, "boss1 f1"), render(grid, f2, "boss1 f2")]


# ----------------------------------------------------------------------------
# 7. BOSS2 "CRIMSON TWIN" — 48x48 crimson bio-mech, twin heads + big wings
#    (procedural half: head pod pasted, wing computed, auto outline pass)
# ----------------------------------------------------------------------------

BOSS2_HEAD = [  # 10 cols, pasted at col 3 (one horned head; mirrored -> twin)
    ".kk....kk.",
    ".kDk..kDk.",
    "..kCkkCk..",
    ".kCCCCCCk.",
    "kCCCCCCCCk",
    "kCDDDDDDCk",
    "kCDggggDCk",
    "kCCCCCCCCk",
    ".kFCCCCFk.",
    ".kFkCCkFk.",
    "..kkFFkk..",
    "...kkkk...",
]

def boss2_half():
    W, H = 24, 48
    g = [["."] * W for _ in range(H)]

    # --- wing: solid triangle (root at spine, tip out-left, back corner low)
    A = (19.0, 11.0)   # root (x=col, y=row)
    B = (0.0, 26.0)    # outer tip
    C = (16.0, 40.0)   # trailing corner

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
            for t in (1.0 / 3, 2.0 / 3)]
    for r in range(H):
        for c in range(20):
            p = (float(c), float(r))
            if not inside(p):
                continue
            dedge = min(seg_dist(p, A, B), seg_dist(p, B, C), seg_dist(p, C, A))
            drib = min(seg_dist(p, A, q) for q in ribs)
            if drib <= 0.7:
                g[r][c] = "D"                      # bone rib
            elif dedge > 2.0 and drib > 1.8:
                g[r][c] = "g"                      # membrane glow cell
            else:
                g[r][c] = "C"

    # --- claws hanging from the wing's lower edge (connected)
    for cc in (3, 9):
        bot = max(r for r in range(H) if g[r][cc] != ".")
        for i in range(5):
            rr = bot + 1 + i
            if rr >= H:
                break
            for c2 in range(cc, cc + (2 if i < 3 else 1)):
                g[rr][c2] = "C" if i == 0 else "D"

    # --- spine / central body (cols 18-23), ribbed
    for r in range(2, 44):
        seg = "kDCCCC" if (r // 3) % 2 == 0 else "kDDCCC"
        for i, ch in enumerate(seg):
            g[r][18 + i] = ch
    for r, seg in ((44, "kDCC"), (45, "kDC"), (46, "kDC"), (47, "kD")):
        for i, ch in enumerate(seg):
            g[r][24 - len(seg) + i] = ch

    # --- thick neck band from head to spine
    for i in range(6):
        col = 13 + i
        top = 4 + (i * 5) // 6
        for rr in range(top, top + 5):
            if g[rr][col] == ".":
                g[rr][col] = "C"

    # --- head pod (twin via mirror)
    for r, line in enumerate(BOSS2_HEAD):
        for i, ch in enumerate(line):
            if ch != ".":
                g[r][3 + i] = ch

    # --- auto outline: colored cells 4-adjacent to transparency become 'k'
    out = [row[:] for row in g]
    for r in range(H):
        for c in range(W):
            if g[r][c] in (".", "k", "g"):
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if cc == W:                      # mirror seam is not an edge
                    continue
                if not (0 <= rr < H) or not (0 <= cc < W) or g[rr][cc] == ".":
                    out[r][c] = "k"
                    break
    return ["".join(row) for row in out]


def boss2_frames():
    grid = mirror(boss2_half())
    base = {
        "k": (26, 4, 14, 255),      # outline
        "C": (198, 44, 66, 255),    # crimson
        "D": (112, 10, 34, 255),    # dark crimson
        "F": (246, 158, 148, 255),  # pale bone/flesh
    }
    f1 = leg(base, g=(255, 150, 80, 255))   # membrane glow hot
    f2 = leg(base, g=(150, 44, 52, 255))    # membrane glow dim
    return [render(grid, f1, "boss2 f1"), render(grid, f2, "boss2 f2")]


# ----------------------------------------------------------------------------
# 8. BOSS3 "OMEGA CORE" — 48x48 dark-purple fortress core, giant baleful eye
#    (procedural radial rings + slit-pupil eye)
# ----------------------------------------------------------------------------

def boss3_grid():
    n = 48
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
            if r <= 7.4:
                if abs(dx) <= 1.3 and abs(dy) <= 5.8:
                    ch = "p"                                  # slit pupil
                else:
                    ch = "g"                                  # baleful iris
            elif r <= 9.0:
                ch = "k"                                      # eye rim
            elif r <= 13.5:
                ch = "P"                                      # inner disc
                if angdist(a, math.pi / 4) * r <= 0.9:
                    ch = "D"                                  # radial seams
                if abs(r - 11.5) <= 0.8 and angdist(a, math.pi / 4, math.pi / 8) * r <= 0.9:
                    ch = "L"                                  # rivet lights
            elif r <= 14.8:
                ch = "D"                                      # recessed gap
                if r <= 14.2 and angdist(a, math.pi / 8) * r <= 0.7:
                    ch = "P"                                  # inward teeth
            elif r <= 15.8:
                ch = "k"
            elif r <= 20.2:
                ch = "P"                                      # outer armor ring
                if r <= 16.9 and dy < 0:
                    ch = "L"                                  # top highlight
                if r > 19.0:
                    ch = "D"                                  # bottom shade of ring
                if angdist(a, math.pi / 4, math.pi / 8) * r <= 1.1:
                    ch = "k"                                  # segment gaps
            elif r <= 21.2:
                ch = "k"
            else:
                # 8 spikes at the diagonals/cardinals (offset 22.5 deg)
                d = angdist(a, math.pi / 4, math.pi / 8) * r
                reach = (23.8 - r) * 0.7
                if r <= 23.8 and d <= reach:
                    ch = "D" if d <= reach - 1.1 else "k"
            # brow: hood the eye from above for menace
            if 4.8 <= r <= 10.2 and dy <= -2.8 and ch in ("g", "k", "P"):
                ch = "D"
            # 4 warning lights on the inner disc (frame-toggled)
            for la in (0, math.pi / 2, math.pi, -math.pi / 2):
                lx, ly = 11.0 * math.cos(la), 11.0 * math.sin(la)
                if math.hypot(dx - lx, dy - ly) <= 1.5:
                    ch = "h"
            line += ch
        rows.append(line)
    return rows


def boss3_frames():
    grid = boss3_grid()
    base = {
        "k": (14, 6, 24, 255),       # outline / near-black
        "p": (8, 2, 8, 255),         # pupil slit
        "P": (120, 70, 170, 255),    # mid purple armor
        "D": (60, 26, 92, 255),      # dark purple
        "L": (180, 150, 220, 255),   # lavender highlight
    }
    f1 = leg(base, g=(255, 66, 48, 255), h=(255, 88, 88, 255))    # red glare
    f2 = leg(base, g=(255, 196, 70, 255), h=(60, 26, 92, 255))    # amber flare
    return [render(grid, f1, "boss3 f1"), render(grid, f2, "boss3 f2")]


# ----------------------------------------------------------------------------
# 9/10. bullets
# ----------------------------------------------------------------------------

BULLET_PLAYER = [
    ".YY.",
    "YWWY",
    "YWWY",
    "YWWY",
    "YWWY",
    ".YY.",
    ".yy.",
    ".yy.",
]

def bullet_player_frames():
    lg = leg({
        "Y": (255, 220, 60, 255),
        "W": (255, 255, 235, 255),
        "y": (220, 150, 40, 255),
    })
    return [render(BULLET_PLAYER, lg, "bullet_player")]


BULLET_ENEMY = [
    ".MMMM.",
    "MMPPMM",
    "MPWWPM",
    "MPWWPM",
    "MMPPMM",
    ".MMMM.",
]

def bullet_enemy_frames():
    lg = leg({
        "M": (235, 40, 170, 255),
        "P": (255, 140, 220, 255),
        "W": (255, 255, 255, 255),
    })
    return [render(BULLET_ENEMY, lg, "bullet_enemy")]


# ----------------------------------------------------------------------------
# 11. EXPLOSION — 4 frames, 16x16 base each (procedural, seeded)
# ----------------------------------------------------------------------------

def explosion_frames():
    n = 16
    c = (n - 1) / 2.0
    W = (255, 255, 240, 255)
    Y = (255, 220, 70, 255)
    O = (255, 140, 40, 255)
    R = (210, 60, 40, 255)
    G1 = (80, 80, 86, 255)
    G2 = (50, 50, 56, 255)
    E = (110, 40, 30, 255)

    def h(x, y):  # deterministic per-pixel hash
        return (x * 7 + y * 13 + (x * y) % 5) % 97

    frames = []

    # frame 1: white/yellow flash star
    f = [[T] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            if (abs(dx) <= 0.8 and abs(dy) <= 5.5) or (abs(dy) <= 0.8 and abs(dx) <= 5.5):
                f[y][x] = W
            elif abs(abs(dx) - abs(dy)) <= 0.8 and r <= 3.8:
                f[y][x] = Y
            if r <= 1.8:
                f[y][x] = W
    frames.append(f)

    # frame 2: full orange fireball
    f = [[T] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            r = math.hypot(x - c, y - c)
            if r <= 6.4:
                if 5.2 < r and h(x, y) % 3 == 0:
                    continue  # ragged edge
                if r <= 2.0:
                    f[y][x] = W
                elif r <= 4.2:
                    f[y][x] = Y
                else:
                    f[y][x] = O
    frames.append(f)

    # frame 3: red debris ring
    f = [[T] * n for _ in range(n)]
    rng = random.Random(7)
    for y in range(n):
        for x in range(n):
            r = math.hypot(x - c, y - c)
            if 4.6 <= r <= 7.0 and h(x, y) % 4 != 0:
                f[y][x] = O if (5.0 < r <= 6.0 and h(x, y) % 5 == 0) else R
    for _ in range(14):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(2.5, 7.4)
        x = int(c + rr * math.cos(a))
        y = int(c + rr * math.sin(a))
        if 0 <= x < n and 0 <= y < n:
            f[y][x] = Y if rng.random() < 0.3 else R
    frames.append(f)

    # frame 4: sparse dark smoke + dying embers
    f = [[T] * n for _ in range(n)]
    rng = random.Random(11)
    for _ in range(22):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(2.0, 7.4)
        x = int(c + rr * math.cos(a))
        y = int(c + rr * math.sin(a))
        if 0 <= x < n and 0 <= y < n:
            f[y][x] = G1 if rng.random() < 0.5 else G2
    for _ in range(5):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(1.5, 5.5)
        x = int(c + rr * math.cos(a))
        y = int(c + rr * math.sin(a))
        if 0 <= x < n and 0 <= y < n:
            f[y][x] = E
    frames.append(f)

    return frames


# ----------------------------------------------------------------------------
# 12. POWERUP — 8x8 gold chip with 'P'; frame 2 flashes bright
# ----------------------------------------------------------------------------

POWERUP = [
    ".kkkkkk.",
    "kLLLLLGk",
    "kLpppGGk",
    "kLpGpGGk",
    "kGpppGGk",
    "kGpGGGGk",
    "kGpGGGGk",
    ".kkkkkk.",
]

def powerup_frames():
    f1 = leg({
        "k": (92, 58, 8, 255),
        "G": (235, 180, 45, 255),
        "L": (255, 230, 130, 255),
        "p": (54, 32, 4, 255),
    })
    f2 = leg({
        "k": (120, 84, 20, 255),
        "G": (255, 226, 110, 255),
        "L": (255, 255, 235, 255),
        "p": (54, 32, 4, 255),
    })
    return [render(POWERUP, f1, "powerup f1"), render(POWERUP, f2, "powerup f2")]


# ----------------------------------------------------------------------------
# backgrounds — 320x480, opaque, vertically seamless (all features wrap mod H)
# ----------------------------------------------------------------------------

BG_W, BG_H = 320, 480

def gen_bg1():
    """deep space starfield."""
    rng = random.Random(101)
    base = (7, 9, 26, 255)
    px = [[base] * BG_W for _ in range(BG_H)]
    px = [list(r) for r in px]

    # faint nebula wisps
    for _ in range(7):
        cx = rng.uniform(0, BG_W)
        cy = rng.uniform(0, BG_H)
        rx = rng.uniform(24, 60)
        ry = rng.uniform(40, 95)
        col = rng.choice([(15, 13, 44), (22, 14, 50), (11, 17, 46)])
        for dy in range(-int(ry), int(ry) + 1):
            for dx in range(-int(rx), int(rx) + 1):
                d = (dx / rx) ** 2 + (dy / ry) ** 2
                if d < 1 and rng.random() > d * 1.15:
                    x = int(cx + dx) % BG_W
                    y = int(cy + dy) % BG_H
                    px[y][x] = (col[0], col[1], col[2], 255)

    # stars: 3 brightness tiers
    for _ in range(150):
        x, y = rng.randrange(BG_W), rng.randrange(BG_H)
        px[y % BG_H][x] = (70, 80, 122, 255)
    for _ in range(55):
        x, y = rng.randrange(BG_W), rng.randrange(BG_H)
        px[y % BG_H][x] = (150, 160, 200, 255)
    for _ in range(20):
        x, y = rng.randrange(BG_W), rng.randrange(BG_H)
        px[y % BG_H][x] = (240, 244, 255, 255)
        # tiny twinkle cross on the brightest tier
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            px[(y + dy) % BG_H][(x + dx) % BG_W] = (120, 128, 170, 255)
    return px


def gen_bg2():
    """red nebula sector."""
    rng = random.Random(202)
    base = (34, 10, 16, 255)
    px = [[base] * BG_W for _ in range(BG_H)]
    px = [list(r) for r in px]

    def h2(x, y):
        return (x * 31 + y * 57 + (x ^ y) * 13) % 100

    # drifting nebula bands (wrap-safe via modular distance), soft + irregular
    bands = []
    for _ in range(5):
        bands.append((
            rng.uniform(0, BG_H),                       # y0
            rng.uniform(10, 20),                        # amplitude 1
            rng.uniform(4, 9),                          # amplitude 2
            rng.uniform(0, 2 * math.pi),                # phase 1
            rng.uniform(0, 2 * math.pi),                # phase 2
            rng.uniform(14, 30),                        # thickness
            rng.choice([(46, 14, 22), (56, 18, 28), (44, 16, 30)]),
        ))
    for x in range(BG_W):
        for (y0, a1, a2, p1, p2, th, col) in bands:
            cy = (y0 + a1 * math.sin(2 * math.pi * x / BG_W + p1)
                     + a2 * math.sin(4 * math.pi * x / BG_W + p2))
            for yy in range(int(cy - th), int(cy + th) + 1):
                y = yy % BG_H
                fall = abs(yy - cy) / th
                if fall < 0.45 or h2(x, y) > fall * 110:
                    c2 = col
                    if fall < 0.22 and h2(x, y) % 3:
                        c2 = (col[0] + 9, col[1] + 3, col[2] + 4)  # soft core
                    px[y][x] = (c2[0], c2[1], c2[2], 255)

    # asteroid silhouettes with a faint rim light
    for _ in range(13):
        cx = rng.uniform(8, BG_W - 8)
        cy = rng.uniform(0, BG_H)
        rr = rng.uniform(3.0, 8.0)
        for dy in range(-int(rr) - 1, int(rr) + 2):
            for dx in range(-int(rr) - 1, int(rr) + 2):
                d = math.hypot(dx, dy)
                if d <= rr:
                    x = int(cx + dx) % BG_W
                    y = int(cy + dy) % BG_H
                    if d > rr - 1.4 and dx <= 0 and dy <= 0:
                        px[y][x] = (72, 38, 42, 255)   # rim light (upper-left)
                    else:
                        px[y][x] = (14, 5, 9, 255)     # silhouette
    return px


def gen_bg3():
    """enemy fortress interior: metal panels, rivets, pipes, hazard stripes."""
    P = 40  # panel size; 320/40=8, 480/40=12 -> tiles both ways
    def phash(px_, py_):
        return (px_ * 73856093 ^ py_ * 19349663) % 1000

    tints = [(27, 33, 29), (29, 36, 31), (25, 31, 28), (31, 38, 33)]
    rows = []
    for y in range(BG_H):
        row = []
        pyi = y // P
        ly = y % P
        for x in range(BG_W):
            pxi = x // P
            lx = x % P
            hsh = phash(pxi, pyi)
            c = tints[hsh % 4]
            # hazard stripe panels (sparse)
            if hsh % 17 == 0:
                if 6 <= lx <= 33 and 6 <= ly <= 33:
                    c = (54, 50, 24) if ((x + y) // 5) % 2 == 0 else (24, 26, 20)
                elif 4 <= lx <= 35 and 4 <= ly <= 35:
                    c = (18, 22, 19)
            # vent grille panels
            elif hsh % 13 == 0 and 10 <= lx <= 29 and 12 <= ly <= 27:
                c = (16, 20, 18) if ly % 4 < 2 else (33, 40, 35)
            # panel seams + bevel
            if lx == 0 or ly == 0:
                c = (14, 18, 16)
            elif lx == 1 or ly == 1:
                c = (36, 44, 39)
            elif lx == 39 or ly == 39:
                c = (20, 25, 22)
            # rivets near corners
            if (lx, ly) in ((4, 4), (35, 4), (4, 35), (35, 35)):
                c = (52, 62, 54)
            elif (lx, ly) in ((5, 5), (36, 5), (5, 36), (36, 36)):
                c = (15, 19, 17)
            row.append((c[0], c[1], c[2], 255))
        rows.append(row)

    # two vertical pipes running the full height (inherently seamless)
    for x0 in (96, 216):
        for y in range(BG_H):
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
                # couplings every 60px (480/60=8 -> wraps)
                if y % 60 < 4:
                    c = (18, 23, 20) if i in (0, 7) else (50, 60, 52)
                rows[y][x] = (c[0], c[1], c[2], 255)
    return rows


# ----------------------------------------------------------------------------
# assembly / output
# ----------------------------------------------------------------------------

CONTRACT = {
    "player.png": (64, 32),
    "enemy1.png": (64, 32),
    "enemy2.png": (64, 32),
    "enemy3.png": (64, 32),
    "midenemy.png": (96, 48),
    "boss1.png": (192, 96),
    "boss2.png": (192, 96),
    "boss3.png": (192, 96),
    "bullet_player.png": (8, 16),
    "bullet_enemy.png": (12, 12),
    "explosion.png": (128, 32),
    "powerup.png": (32, 16),
    "bg1.png": (320, 480),
    "bg2.png": (320, 480),
    "bg3.png": (320, 480),
}

SPRITES = [
    ("player.png", player_frames),
    ("enemy1.png", enemy1_frames),
    ("enemy2.png", enemy2_frames),
    ("enemy3.png", enemy3_frames),
    ("midenemy.png", midenemy_frames),
    ("boss1.png", boss1_frames),
    ("boss2.png", boss2_frames),
    ("boss3.png", boss3_frames),
    ("bullet_player.png", bullet_player_frames),
    ("bullet_enemy.png", bullet_enemy_frames),
    ("explosion.png", explosion_frames),
    ("powerup.png", powerup_frames),
]

BACKGROUNDS = [
    ("bg1.png", gen_bg1),
    ("bg2.png", gen_bg2),
    ("bg3.png", gen_bg3),
]


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    for name, fn in SPRITES:
        frames = fn()
        sheet = hstack(frames)
        final = upscale(sheet, 2)          # 1 art dot = 2 px
        write_png(os.path.join(IMG_DIR, name), final)
        write_png(os.path.join(PREVIEW_DIR, name), upscale(sheet, 12))  # 6x final
        print("wrote", name)

    for name, fn in BACKGROUNDS:
        px = fn()
        write_png(os.path.join(IMG_DIR, name), px)
        # preview: two tiles stacked so the wrap seam is visible mid-image
        write_png(os.path.join(PREVIEW_DIR, name), px + px)
        print("wrote", name)

    # ---- verification -------------------------------------------------------
    print()
    print("%-22s %-12s %-12s %s" % ("file", "expected", "actual", "status"))
    print("-" * 56)
    ok = True
    for name, (ew, eh) in sorted(CONTRACT.items()):
        path = os.path.join(IMG_DIR, name)
        try:
            aw, ah = read_png_size(path)
        except Exception as e:
            print("%-22s %-12s %-12s FAIL (%s)" % (name, "%dx%d" % (ew, eh), "-", e))
            ok = False
            continue
        status = "OK" if (aw, ah) == (ew, eh) else "FAIL"
        if status == "FAIL":
            ok = False
        print("%-22s %-12s %-12s %s" % (name, "%dx%d" % (ew, eh), "%dx%d" % (aw, ah), status))
    print("-" * 56)
    print("ALL OK" if ok else "SIZE CONTRACT VIOLATED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
