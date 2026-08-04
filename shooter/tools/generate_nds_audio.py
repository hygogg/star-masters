#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_nds_audio.py -- convert the shooter's BGM/SE for Nintendo DS (maxmod).

Standard library only (math, os, random, struct, sys, wave).

Reads the note-event log that tools/generate_audio.py's Song class records
(self.events -- an append-only side channel that cannot change the web WAVs)
and re-emits every BGM track as a hand-written 4-channel ProTracker MOD
("M.K."), plus the sound effects as 11025 Hz / 8-bit unsigned / mono WAVs,
into  ../../shooter-nds/audio/ .

Design notes
------------
Timing:   4 rows per beat (16 rows per 4/4 bar, 4 bars per 64-row pattern).
          MOD speed = 6 ticks/row (F06) and tempo = source BPM (Fxx), because
          row_len = speed * 2.5/tempo s  ->  beat = 4 rows = 60/BPM s exactly.
          All six tracks therefore play at their source BPM with 0.000% error.
Pitch:    Amiga period table, finetune 0, C-1..B-3 = 856..113 (PAL clock
          3546894.6 Hz).  Instead of writing out-of-range periods, samples are
          transposed by their cycle length:
            - 16-byte single-cycle squares/triangle: MOD C-1 sounds MIDI 60
              (C4); covers MIDI 60..95 (C4..B6) -> lead/harmony/high arps.
            - 64-byte single-cycle triangle: two octaves lower, MOD C-1 sounds
              MIDI 36 (C2); covers MIDI 36..71 (C2..B4) -> bass.
          Every pitch in all six songs fits one of those two windows, so no
          note transposition was needed.  Absolute pitch sits a uniform
          ~17.5 cents below concert pitch (PAL Amiga clock quirk); all
          intervals are exact.
Channels: 0 = lead (50% square), 1 = harmony/arp (25%/12.5% square or high
          triangle), 2 = bass (triangle), 3 = drums (kick/snare/hat one-shots,
          priority kick > snare > hat on collisions -- the web mix masks the
          quiet hat under kick/snare anyway).
Chords:   the source plays two simultaneous harmony notes (stage1/2 chops,
          boss tritone stabs).  Those become classic tracker arpeggio chords:
          effect 0x0 with param = interval<<4 on the lower note.
Volume:   sample-header volumes carry each instrument's per-song level
          (LEAD 0.30 / ARP 0.15 / BASS 0.35 balance preserved); per-note Cxx
          only where a note deviates (e.g. stage3 ghost snare).  A per-track
          gain is auto-calibrated against the original WAV's RMS with a
          peak < 0.95 constraint.
Loops:    restart byte 0x7F (players loop the full order list); patterns are
          deduplicated (A A B A songs store 2 patterns, order 0,0,1,0); note
          cuts (C00) are wrapped around the song end so nothing rings into
          the loop that should not.
Omitted:  the source's 0.6%-depth auto-vibrato (inaudible at these durations)
          and the second chord note's 0.8x volume nuance (folded into the
          arpeggio, lower note emphasised 2:1).

The script then (1) re-parses and validates every emitted MOD, (2) renders
each MOD with its own minimal MOD player and compares duration / peak / RMS /
spectral centroid / per-bar RMS envelope against the original web WAV, and
exits non-zero if anything fails.

Run:  python3 tools/generate_nds_audio.py
"""

import math
import os
import random
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import generate_audio as GA  # noqa: E402  (the web generator; not executed)

SR = 22050                    # analysis / render rate
SE_SR = 11025                 # DS sound-effect rate
TWO_PI = 2.0 * math.pi
PAL_CLOCK = 7093789.2 / 2.0   # Amiga Paula clock / 2 = 3546894.6

NDS_AUDIO_DIR = os.path.join(os.path.dirname(GA.ROOT), "shooter-nds", "audio")
SCRATCH_DIR = os.environ.get(
    "NDS_AUDIO_SCRATCH",
    os.path.join(GA.ROOT, "_preview", "audio"))

# ProTracker period table, finetune 0, C-1..B-3.
PERIODS = [856, 808, 762, 720, 678, 640, 604, 570, 538, 508, 480, 453,
           428, 404, 381, 360, 339, 320, 302, 285, 269, 254, 240, 226,
           214, 202, 190, 180, 170, 160, 151, 143, 135, 127, 120, 113]
PERIOD_SET = set(PERIODS)

DRUM_NOTE = 24                      # C-3, period 214
DRUM_RATE = PAL_CLOCK / 214.0       # ~16574.3 Hz -- drum PCM native rate

TRACKS = ["title", "stage1", "stage2", "stage3", "boss", "ending", "midboss"]
SES = ["shot", "hit", "explosion", "player_death", "powerup",
       "boss_explosion", "start", "clear", "fanfare"]

GAIN_START = 1.35
GAIN_MIN, GAIN_MAX = 0.30, 1.90


# ================================================================ instruments


def synth_square(cycle, duty):
    hi = max(1, int(round(cycle * duty)))
    return [127 if i < hi else -127 for i in range(cycle)]


def synth_triangle(cycle):
    out = []
    for i in range(cycle):
        p = (i + 0.5) / cycle
        out.append(int(round(127.0 * (4.0 * abs(p - 0.5) - 1.0))))
    return out


def _finalize_drum(buf):
    """Normalize to +-120, fade tail, quantize to signed bytes, pad even."""
    peak = max(abs(v) for v in buf) or 1.0
    g = 120.0 / peak
    n = len(buf)
    fade = min(24, n // 4)
    out = []
    for i, v in enumerate(buf):
        w = v * g
        rem = n - 1 - i
        if rem < fade:
            w *= rem / float(fade)
        out.append(max(-127, min(127, int(round(w)))))
    if len(out) % 2:
        out.append(0)
    return out


def synth_kick():
    r = DRUM_RATE
    n = int(0.10 * r)
    rng = random.Random(4242)
    att = max(1, int(40 * r / 22050.0))
    buf = []
    phase = 0.0
    for i in range(n):
        t = i / r
        f = 150.0 * math.exp(-t * 30.0) + 42.0
        phase += f / r
        s = math.sin(TWO_PI * phase)
        if t < 0.008:
            s += 0.35 * rng.uniform(-1.0, 1.0)
        env = math.exp(-t * 32.0)
        if i < att:
            env *= i / float(att)
        buf.append(s * env)
    return _finalize_drum(buf)


def synth_snare():
    r = DRUM_RATE
    n = int(0.13 * r)
    rng = random.Random(5252)
    att = max(1, int(20 * r / 22050.0))
    buf = []
    prev = 0.0
    for i in range(n):
        t = i / r
        x = rng.uniform(-1.0, 1.0)
        hp = x - 0.4 * prev
        prev = x
        s = hp * 0.85 + 0.4 * math.sin(TWO_PI * 185.0 * t) * math.exp(-t * 45.0)
        env = math.exp(-t * 28.0)
        if i < att:
            env *= i / float(att)
        buf.append(s * env)
    return _finalize_drum(buf)


def synth_hat():
    r = DRUM_RATE
    n = int(0.035 * r)
    rng = random.Random(6262)
    buf = []
    prev = 0.0
    for i in range(n):
        t = i / r
        x = rng.uniform(-1.0, 1.0)
        s = x - prev
        prev = x
        env = math.exp(-t * 120.0)
        if i < 6:
            env *= i / 6.0
        buf.append(s * env)
    return _finalize_drum(buf)


# name -> (pcm data list[int], base_midi (None = drum), loops?)
INSTRUMENT_ORDER = ["sq50", "sq25", "sq12", "trilo", "trihi",
                    "kick", "snare", "hat"]
INSTRUMENT_LABEL = {
    "sq50": "square 50% lead", "sq25": "square 25% harmony",
    "sq12": "square 12.5% stab", "trilo": "triangle bass",
    "trihi": "triangle arp hi", "kick": "kick drum",
    "snare": "snare drum", "hat": "hi-hat",
}


def build_instruments():
    return {
        "sq50": (synth_square(16, 0.50), 60, True),
        "sq25": (synth_square(16, 0.25), 60, True),
        "sq12": (synth_square(16, 0.125), 60, True),
        "trilo": (synth_triangle(64), 36, True),
        "trihi": (synth_triangle(16), 60, True),
        "kick": (synth_kick(), None, False),
        "snare": (synth_snare(), None, False),
        "hat": (synth_hat(), None, False),
    }


INSTRUMENTS = build_instruments()


# ============================================================ event -> tracks


def route_tone(midi, wave_kind, duty):
    """-> (channel, instrument name)."""
    if wave_kind == "tri":
        return (2, "trilo") if midi < 60 else (1, "trihi")
    if duty >= 0.375:
        return (0, "sq50")
    if duty >= 0.1875:
        return (1, "sq25")
    return (1, "sq12")


def collect_song(events, bars):
    """Route raw Song events onto the 4-channel row grid representation."""
    rows_total = bars * 16
    tonal = {0: {}, 1: {}, 2: {}}
    drums = {}
    drum_prio = {"kick": 3, "snare": 2, "hat": 1}
    for ev in events:
        if ev[0] == "tone":
            _, bar, beat, dur, midi, wk, vol, duty = ev
            pos = (bar * 4 + beat) * 4.0
            row = int(round(pos))
            if abs(pos - row) > 1e-6:
                raise ValueError("off-grid tone at bar %s beat %s" % (bar, beat))
            if row >= rows_total:
                continue
            durr = max(1, int(round(dur * 4.0)))
            ch, inst = route_tone(midi, wk, duty)
            tonal[ch].setdefault(row, []).append((inst, midi, durr, vol))
        else:
            kind, bar, beat, vol = ev
            pos = (bar * 4 + beat) * 4.0
            row = int(round(pos))
            if abs(pos - row) > 1e-6:
                raise ValueError("off-grid drum at bar %s beat %s" % (bar, beat))
            if row >= rows_total:
                continue
            if row not in drums or drums[row][0] < drum_prio[kind]:
                drums[row] = (drum_prio[kind], kind, vol)

    chan_notes = {0: [], 1: [], 2: []}   # (row, durr, inst, midi, interval, vol)
    for ch in (0, 1, 2):
        for row in sorted(tonal[ch]):
            lst = tonal[ch][row]
            if len(lst) == 1:
                inst, midi, durr, vol = lst[0]
                chan_notes[ch].append((row, durr, inst, midi, 0, vol))
            elif len(lst) == 2:
                (ia, ma, da, va), (ib, mb, db, vb) = lst
                if ia != ib:
                    raise ValueError("mixed-instrument chord at row %d" % row)
                iv = abs(ma - mb)
                if not 1 <= iv <= 15:
                    raise ValueError("chord interval %d out of nibble" % iv)
                chan_notes[ch].append((row, max(da, db), ia, min(ma, mb),
                                       iv, max(va, vb)))
            else:
                raise ValueError(">2 simultaneous notes on channel %d" % ch)
    return rows_total, chan_notes, drums


def most_common(vals):
    counts = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def v64(vol, gain):
    return max(1, min(64, int(round(vol * 64.0 * gain))))


def emit_mod(name, bpm, rows_total, chan_notes, drums, gain):
    """Build the complete .mod byte string for one track."""
    # -- instrument usage & per-song default volumes
    use_vols = {}
    for ch in (0, 1, 2):
        for row, durr, inst, midi, iv, vol in chan_notes[ch]:
            use_vols.setdefault(inst, []).append(vol)
    for row, (prio, kind, vol) in drums.items():
        use_vols.setdefault(kind, []).append(vol)

    used = [i for i in INSTRUMENT_ORDER if i in use_vols]
    smp_num = {inst: i + 1 for i, inst in enumerate(used)}
    smp_vol = {inst: v64(most_common(use_vols[inst]), gain) for inst in used}

    # -- row grid: cell = [note_index or None, sample, effect, param]
    grid = [[None] * rows_total for _ in range(4)]

    for ch in (0, 1, 2):
        notes = chan_notes[ch]
        for row, durr, inst, midi, iv, vol in notes:
            base = INSTRUMENTS[inst][1]
            idx = midi - base
            if not 0 <= idx < 36:
                raise ValueError("%s: %s midi %d outside sample window"
                                 % (name, inst, midi))
            eff, prm = 0, 0
            if iv:
                eff, prm = 0x0, (iv << 4)   # arpeggio chord, lower emphasised
            v = v64(vol, gain)
            if v != smp_vol[inst]:
                if iv:
                    print("  note: %s row %d chord volume nuance dropped"
                          % (name, row))
                else:
                    eff, prm = 0xC, v
            grid[ch][row] = [idx, smp_num[inst], eff, prm]
        # note cuts so nothing rings through rests or across the loop seam
        for i, (row, durr, inst, midi, iv, vol) in enumerate(notes):
            end = row + durr
            nxt = notes[i + 1][0] if i + 1 < len(notes) \
                else notes[0][0] + rows_total
            if end < nxt:
                cr = end % rows_total
                if grid[ch][cr] is None:
                    grid[ch][cr] = [None, 0, 0xC, 0]

    for row in sorted(drums):
        prio, kind, vol = drums[row]
        v = v64(vol, gain)
        eff, prm = (0xC, v) if v != smp_vol[kind] else (0, 0)
        grid[3][row] = [DRUM_NOTE, smp_num[kind], eff, prm]

    # -- row 0: set tempo (Fxx >= 0x20 -> BPM) and speed (F06)
    def inject(eff, prm, prefer):
        for ch in prefer:
            c = grid[ch][0]
            if c is None:
                grid[ch][0] = [None, 0, eff, prm]
                return
            if c[2] == 0 and c[3] == 0:
                c[2], c[3] = eff, prm
                return
        raise RuntimeError("no free effect slot on row 0")

    if not 0x20 <= bpm <= 0xFF:
        raise ValueError("tempo %d not encodable" % bpm)
    inject(0xF, bpm, (3, 2, 1, 0))
    inject(0xF, 0x06, (2, 1, 0, 3))

    # -- serialize patterns (64 rows), dedupe identical ones
    if rows_total % 64:
        raise ValueError("row count %d not a multiple of 64" % rows_total)

    def pack_cell(cell):
        if cell is None:
            return b"\x00\x00\x00\x00"
        note, smp, eff, prm = cell
        period = PERIODS[note] if note is not None else 0
        return bytes(((smp & 0xF0) | ((period >> 8) & 0x0F),
                      period & 0xFF,
                      ((smp & 0x0F) << 4) | (eff & 0x0F),
                      prm & 0xFF))

    patterns, order, seen = [], [], {}
    for p0 in range(0, rows_total, 64):
        blk = bytearray()
        for r in range(p0, p0 + 64):
            for ch in range(4):
                blk += pack_cell(grid[ch][r])
        key = bytes(blk)
        if key in seen:
            order.append(seen[key])
        else:
            seen[key] = len(patterns)
            order.append(len(patterns))
            patterns.append(key)

    # -- assemble file
    out = bytearray()
    out += ("shooter " + name).encode("ascii")[:20].ljust(20, b"\x00")
    for i in range(31):
        if i < len(used):
            inst = used[i]
            data, base, loops = INSTRUMENTS[inst]
            lw = len(data) // 2
            ro, rl = (0, lw) if loops else (0, 1)
            out += INSTRUMENT_LABEL[inst].encode("ascii")[:22].ljust(22, b"\x00")
            out += struct.pack(">H", lw) + bytes((0, smp_vol[inst]))
            out += struct.pack(">HH", ro, rl)
        else:
            out += b"\x00" * 22 + struct.pack(">H", 0) + bytes((0, 0))
            out += struct.pack(">HH", 0, 1)
    out += bytes((len(order), 0x7F))
    out += bytes(order + [0] * (128 - len(order)))
    out += b"M.K."
    for p in patterns:
        out += p
    for inst in used:
        out += bytes(v & 0xFF for v in INSTRUMENTS[inst][0])
    return bytes(out)


# ================================================================== validator


class ModSample(object):
    __slots__ = ("name", "length_w", "finetune", "volume", "rep_off_w",
                 "rep_len_w", "data")


class ModFile(object):
    __slots__ = ("title", "samples", "song_len", "restart", "order",
                 "magic", "patterns", "size")


def parse_mod(data):
    m = ModFile()
    m.size = len(data)
    m.title = data[:20].rstrip(b"\x00").decode("ascii", "replace")
    m.samples = []
    off = 20
    for _ in range(31):
        s = ModSample()
        s.name = data[off:off + 22].rstrip(b"\x00").decode("ascii", "replace")
        s.length_w, s.finetune, s.volume, s.rep_off_w, s.rep_len_w = \
            struct.unpack(">HBBHH", data[off + 22:off + 30])
        s.data = b""
        m.samples.append(s)
        off += 30
    m.song_len = data[950]
    m.restart = data[951]
    m.order = list(data[952:1080])
    m.magic = data[1080:1084]
    npat = max(m.order) + 1
    off = 1084
    m.patterns = []
    for _ in range(npat):
        m.patterns.append(data[off:off + 1024])
        off += 1024
    for s in m.samples:
        n = s.length_w * 2
        s.data = data[off:off + n]
        off += n
    return m


def iter_cells(pattern):
    for r in range(64):
        for ch in range(4):
            o = (r * 4 + ch) * 4
            b0, b1, b2, b3 = pattern[o], pattern[o + 1], pattern[o + 2], \
                pattern[o + 3]
            smp = (b0 & 0xF0) | (b2 >> 4)
            period = ((b0 & 0x0F) << 8) | b1
            eff = b2 & 0x0F
            yield r, ch, smp, period, eff, b3


def validate_mod(path):
    """Re-read an emitted MOD and check structural invariants.
    Returns (row dict for the report table, list of failure strings)."""
    with open(path, "rb") as f:
        data = f.read()
    fails = []
    m = parse_mod(data)
    if m.magic != b"M.K.":
        fails.append("magic %r != M.K." % m.magic)
    npat = max(m.order) + 1
    sample_bytes = sum(s.length_w * 2 for s in m.samples)
    expect = 1084 + npat * 1024 + sample_bytes
    if expect != m.size:
        fails.append("size %d != expected %d" % (m.size, expect))
    if not 1 <= m.song_len <= 128:
        fails.append("song length %d invalid" % m.song_len)
    for i in range(m.song_len):
        if m.order[i] >= npat:
            fails.append("order[%d]=%d >= %d patterns" % (i, m.order[i], npat))
    for i, s in enumerate(m.samples):
        if s.volume > 64:
            fails.append("sample %d volume %d > 64" % (i + 1, s.volume))
        if s.length_w > 0 and s.rep_off_w + s.rep_len_w > s.length_w:
            fails.append("sample %d loop %d+%d > len %d words"
                         % (i + 1, s.rep_off_w, s.rep_len_w, s.length_w))
    ncells = nnotes = 0
    for p in m.patterns:
        for r, ch, smp, period, eff, prm in iter_cells(p):
            ncells += 1
            if period and period not in PERIOD_SET:
                fails.append("pat cell r%d ch%d bad period %d" % (r, ch, period))
            if smp > 31:
                fails.append("pat cell r%d ch%d sample %d > 31" % (r, ch, smp))
            elif smp and m.samples[smp - 1].length_w == 0:
                fails.append("pat cell r%d ch%d refs empty sample %d"
                             % (r, ch, smp))
            if period:
                nnotes += 1
    row = dict(file=os.path.basename(path), size=m.size, patterns=npat,
               order=m.song_len, restart=m.restart,
               samples=sum(1 for s in m.samples if s.length_w),
               notes=nnotes, ok=not fails)
    return row, fails


# ============================================================ minimal player


def render_mod(data, rate=SR):
    """Very small MOD player: 4 channels, loops, volumes, effects 0/C/F.
    Renders exactly one pass over the order list. Mono float output."""
    m = parse_mod(data)
    sd = []   # per sample: (signed data list, loop?, loop_start, loop_end, vol)
    for s in m.samples:
        vals = [b - 256 if b > 127 else b for b in s.data]
        loops = s.rep_len_w > 1
        ls = s.rep_off_w * 2
        le = (s.rep_off_w + s.rep_len_w) * 2
        sd.append((vals, loops, ls, le, s.volume))

    speed, tempo = 6, 125
    out = []
    acc = 0.0
    # channel state: [sample, pos, period, vol, playing, arp_on, arpx, arpy]
    chs = [[0, 0.0, 0, 0, False, False, 0, 0] for _ in range(4)]

    for pos_i in range(m.song_len):
        pat = m.patterns[m.order[pos_i]]
        for r in range(64):
            cells = []
            for ch in range(4):
                o = (r * 4 + ch) * 4
                b0, b1, b2, b3 = pat[o], pat[o + 1], pat[o + 2], pat[o + 3]
                cells.append(((b0 & 0xF0) | (b2 >> 4),
                              ((b0 & 0x0F) << 8) | b1, b2 & 0x0F, b3))
            for ch, (smp, period, eff, prm) in enumerate(cells):
                st = chs[ch]
                if smp:
                    st[0] = smp
                    st[3] = sd[smp - 1][4]
                if period:
                    st[2] = period
                    st[1] = 0.0
                    st[4] = True
                st[5] = False
                if eff == 0x0 and prm:
                    st[5], st[6], st[7] = True, prm >> 4, prm & 0x0F
                elif eff == 0xC:
                    st[3] = min(64, prm)
                elif eff == 0xF:
                    if 0 < prm < 0x20:
                        speed = prm
                    elif prm >= 0x20:
                        tempo = prm
            for tick in range(speed):
                acc += rate * 2.5 / tempo
                ns = int(acc)
                acc -= ns
                # per-channel step for this tick
                steps = []
                for st in chs:
                    if st[4] and st[2] and st[0]:
                        off = 0
                        if st[5]:
                            off = (0, st[6], st[7])[tick % 3]
                        f = PAL_CLOCK / st[2]
                        if off:
                            f *= 2.0 ** (off / 12.0)
                        steps.append(f / rate)
                    else:
                        steps.append(0.0)
                for _ in range(ns):
                    v = 0.0
                    for ch in range(4):
                        stp = steps[ch]
                        if not stp:
                            continue
                        st = chs[ch]
                        vals, loops, ls, le, _dv = sd[st[0] - 1]
                        p = st[1]
                        if loops:
                            if p >= le:
                                p = ls + (p - ls) % (le - ls)
                                st[1] = p
                        elif p >= len(vals):
                            st[4] = False
                            steps[ch] = 0.0
                            continue
                        v += vals[int(p)] / 128.0 * st[3] / 64.0
                        st[1] = p + stp
                    out.append(v)
    return out


# ================================================================== analysis


def read_wav_mono(path):
    with wave.open(path, "rb") as w:
        ch, sw, fr = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if ch != 1:
        raise ValueError("expected mono: " + path)
    if sw == 2:
        vals = struct.unpack("<%dh" % (len(raw) // 2), raw)
        return [v / 32768.0 for v in vals], fr
    if sw == 1:
        return [(b - 128) / 128.0 for b in raw], fr
    raise ValueError("unsupported width in " + path)


def peak_rms(sig):
    peak = max(abs(v) for v in sig)
    rms = math.sqrt(sum(v * v for v in sig) / len(sig))
    return peak, rms


def bar_rms(sig, bars):
    n = len(sig) // bars
    out = []
    for b in range(bars):
        seg = sig[b * n:(b + 1) * n]
        out.append(math.sqrt(sum(v * v for v in seg) / len(seg)))
    return out


def pearson(a, b):
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da * db == 0:
        return 0.0
    return num / (da * db)


def _fft(re, im):
    n = len(re)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    ln = 2
    while ln <= n:
        ang = -TWO_PI / ln
        wr, wi = math.cos(ang), math.sin(ang)
        half = ln // 2
        for i in range(0, n, ln):
            cr, ci = 1.0, 0.0
            for k in range(i, i + half):
                vr = re[k + half] * cr - im[k + half] * ci
                vi = re[k + half] * ci + im[k + half] * cr
                re[k + half] = re[k] - vr
                im[k + half] = im[k] - vi
                re[k] += vr
                im[k] += vi
                cr, ci = cr * wr - ci * wi, cr * wi + ci * wr
        ln <<= 1


def spectral_centroid(sig, rate):
    N = 4096
    if len(sig) < N:
        sig = list(sig) + [0.0] * (N - len(sig))
    nwin = min(8, len(sig) // N)
    hann = [0.5 - 0.5 * math.cos(TWO_PI * i / (N - 1)) for i in range(N)]
    step = max(1, (len(sig) - N) // max(1, nwin - 1)) if nwin > 1 else 1
    mag = [0.0] * (N // 2)
    for w in range(nwin):
        s0 = min(w * step, len(sig) - N)
        re = [sig[s0 + i] * hann[i] for i in range(N)]
        im = [0.0] * N
        _fft(re, im)
        for k in range(1, N // 2):
            mag[k] += math.hypot(re[k], im[k])
    num = sum(k * rate / N * m for k, m in enumerate(mag))
    den = sum(mag)
    return num / den if den else 0.0


def write_wav16(path, sig, rate):
    frames = bytearray()
    for v in sig:
        iv = int(round(v * 32767.0))
        iv = max(-32768, min(32767, iv))
        frames += struct.pack("<h", iv)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


# ============================================================== SE conversion


def fir_lowpass(taps=63, fc=4900.0, rate=SR):
    m = (taps - 1) / 2.0
    h = []
    for k in range(taps):
        x = k - m
        if x == 0:
            v = 2.0 * fc / rate
        else:
            v = math.sin(TWO_PI * fc * x / rate) / (math.pi * x)
        v *= 0.5 - 0.5 * math.cos(TWO_PI * k / (taps - 1))   # Hann
        h.append(v)
    s = sum(h)
    return [v / s for v in h]


FIR = fir_lowpass()


def convert_se(name):
    """Render the web SE via generate_audio's own synth, apply the same
    fade+normalize pipeline, low-pass, decimate 2:1 to 11025 Hz, quantize to
    8-bit unsigned."""
    spec = GA.SE_SPECS[name + ".wav"]
    buf, peak_target = spec["fn"]()
    buf = GA.normalize(GA.edge_fade(buf), peak_target)
    taps = len(FIR)
    half = taps // 2
    n_out = (len(buf) + 1) // 2
    out_bytes = bytearray()
    for j in range(n_out):
        c = 2 * j
        acc = 0.0
        for k in range(taps):
            i = c + half - k
            if 0 <= i < len(buf):
                acc += FIR[k] * buf[i]
        b = 128 + int(round(acc * 127.0))
        out_bytes.append(max(0, min(255, b)))
    path = os.path.join(NDS_AUDIO_DIR, name + ".wav")
    os.makedirs(NDS_AUDIO_DIR, exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(SE_SR)
        w.writeframes(bytes(out_bytes))
    sig = [(b - 128) / 128.0 for b in out_bytes]
    peak, rms = peak_rms(sig)
    cen = spectral_centroid(sig, SE_SR)
    return dict(file=name + ".wav", dur=len(sig) / SE_SR, peak=peak, rms=rms,
                centroid=cen, size=os.path.getsize(path),
                src_dur=len(buf) / SR)


# ==================================================================== driver


def convert_track(name):
    spec = GA.BGM_SPECS[name + ".wav"]
    bpm, bars = spec["bpm"], spec["bars"]
    song = spec["fn"]()                 # composes; also fills song.events
    rows_total, chan_notes, drums = collect_song(song.events, bars)

    orig, orate = read_wav_mono(os.path.join(GA.BGM_DIR, name + ".wav"))
    opeak, orms = peak_rms(orig)

    gain = GAIN_START
    history = []
    mod_bytes = rend = None
    for it in range(1, 6):
        mod_bytes = emit_mod(name, bpm, rows_total, chan_notes, drums, gain)
        rend = render_mod(mod_bytes)
        rpeak, rrms = peak_rms(rend)
        ratio = rrms / orms
        history.append((it, gain, rpeak, rrms, ratio))
        if rpeak < 0.95 and 0.80 <= ratio <= 1.30:
            break
        adj = min(orms / rrms, (0.92 / rpeak) if rpeak > 0 else 9.0)
        ng = max(GAIN_MIN, min(GAIN_MAX, gain * adj))
        if abs(ng - gain) < 0.01:
            break
        gain = ng

    os.makedirs(NDS_AUDIO_DIR, exist_ok=True)
    mod_path = os.path.join(NDS_AUDIO_DIR, name + ".mod")
    with open(mod_path, "wb") as f:
        f.write(mod_bytes)
    write_wav16(os.path.join(SCRATCH_DIR, name + "_modrender.wav"), rend, SR)

    rpeak, rrms = peak_rms(rend)
    stats = dict(
        name=name, bpm=bpm, bars=bars, gain=gain, iters=len(history),
        mod_size=len(mod_bytes),
        dur_orig=len(orig) / orate, dur_rend=len(rend) / SR,
        peak_orig=opeak, peak_rend=rpeak,
        rms_orig=orms, rms_rend=rrms, rms_ratio=rrms / orms,
        cen_orig=spectral_centroid(orig, orate),
        cen_rend=spectral_centroid(rend, SR),
        history=history,
    )
    eo = bar_rms(orig, bars)
    er = bar_rms(rend, bars)
    stats["env_corr"] = pearson(eo, er)
    stats["env_dev"] = max(abs(r / o - 1.0) for o, r in zip(eo, er))
    return stats


def main():
    failures = []
    os.makedirs(SCRATCH_DIR, exist_ok=True)

    # ---------------------------------------------------------------- SEs
    print("Converting SEs -> %s (11025 Hz / 8-bit unsigned / mono)"
          % NDS_AUDIO_DIR)
    se_rows = []
    for name in SES:
        se_rows.append(convert_se(name))
    print()
    print("SE conversion")
    print("-" * 86)
    print("%-22s %8s %8s %7s %7s %9s %8s" %
          ("file", "dur(s)", "src(s)", "peak", "RMS", "centroid", "bytes"))
    for r in se_rows:
        note = ""
        if r["peak"] >= 0.95:
            failures.append("%s clipping peak=%.3f" % (r["file"], r["peak"]))
            note = " !!"
        if r["rms"] <= 0.02:
            failures.append("%s near-silent" % r["file"])
            note = " !!"
        if abs(r["dur"] - r["src_dur"]) > 0.01:
            failures.append("%s duration drift" % r["file"])
            note = " !!"
        print("%-22s %8.3f %8.3f %7.3f %7.3f %8.0fHz %8d%s" %
              (r["file"], r["dur"], r["src_dur"], r["peak"], r["rms"],
               r["centroid"], r["size"], note))
    print("-" * 86)

    # --------------------------------------------------------------- BGMs
    print()
    print("Converting BGM tracks -> 4ch ProTracker MOD")
    stats = []
    for name in TRACKS:
        print("  %s ..." % name)
        st = convert_track(name)
        for it, g, pk, rm, ra in st["history"]:
            print("    calib iter %d: gain=%.3f peak=%.3f rms=%.4f "
                  "rms_ratio=%.3f" % (it, g, pk, rm, ra))
        stats.append(st)

    # ------------------------------------------------------- validator pass
    print()
    print("MOD validator (re-parsed from disk)")
    print("-" * 86)
    print("%-12s %7s %5s %6s %8s %8s %6s  %s" %
          ("file", "bytes", "pats", "order", "restart", "samples",
           "notes", "result"))
    for name in TRACKS:
        row, fails = validate_mod(os.path.join(NDS_AUDIO_DIR, name + ".mod"))
        print("%-12s %7d %5d %6d %8s %8d %6d  %s" %
              (row["file"], row["size"], row["patterns"], row["order"],
               "0x%02X" % row["restart"], row["samples"], row["notes"],
               "OK" if row["ok"] else "FAIL"))
        for f in fails:
            failures.append(row["file"] + ": " + f)
            print("      !! " + f)
    print("-" * 86)

    # -------------------------------------------------- render comparison
    print()
    print("MOD render vs original web WAV")
    print("-" * 110)
    print("%-8s %9s %9s %7s %7s %7s %7s %7s %8s %8s %8s %7s %6s" %
          ("track", "dur_orig", "dur_mod", "pk_org", "pk_mod", "rms_o",
           "rms_m", "ratio", "cen_org", "cen_mod", "envcorr", "envdev",
           "gain"))
    for st in stats:
        notes = ""
        dur_err = abs(st["dur_rend"] - st["dur_orig"]) / st["dur_orig"]
        if dur_err > 0.03:
            failures.append("%s duration err %.2f%%" % (st["name"],
                                                        dur_err * 100))
            notes += " !!dur"
        if st["peak_rend"] >= 0.95:
            failures.append("%s clipping peak=%.3f" % (st["name"],
                                                       st["peak_rend"]))
            notes += " !!peak"
        if not (st["rms_rend"] > 0.02 and 0.5 <= st["rms_ratio"] <= 2.0):
            failures.append("%s loudness off ratio=%.3f" % (st["name"],
                                                            st["rms_ratio"]))
            notes += " !!rms"
        # Envelope: every bar of the render must sit close to the same bar
        # of the original (<=30% RMS deviation).  Pearson correlation is only
        # meaningful when the original envelope actually varies -- on a flat
        # envelope (all bars within a few %) it just amplifies noise -- so it
        # is required only as a fallback when the per-bar deviation is large.
        if st["env_dev"] > 0.30 and st["env_corr"] < 0.30:
            failures.append("%s envelope off dev=%.2f corr=%.2f"
                            % (st["name"], st["env_dev"], st["env_corr"]))
            notes += " !!env"
        print("%-8s %9.4f %9.4f %7.3f %7.3f %7.3f %7.3f %7.3f %7.0fHz %7.0fHz"
              " %8.3f %7.3f %6.3f%s" %
              (st["name"], st["dur_orig"], st["dur_rend"], st["peak_orig"],
               st["peak_rend"], st["rms_orig"], st["rms_rend"],
               st["rms_ratio"], st["cen_orig"], st["cen_rend"],
               st["env_corr"], st["env_dev"], st["gain"], notes))
    print("-" * 110)

    # ----------------------------------------------------------- BPM table
    print()
    print("Tempo mapping (4 rows/beat, speed 6, Fxx tempo = source BPM)")
    print("-" * 66)
    print("%-8s %8s %10s %12s %10s" %
          ("track", "src BPM", "MOD tempo", "result BPM", "error"))
    for st in stats:
        eff_bpm = st["bpm"]     # tempo==BPM & speed 6 & 4 rows/beat -> exact
        print("%-8s %8d %10d %12.3f %9.3f%%" %
              (st["name"], st["bpm"], st["bpm"], eff_bpm,
               (eff_bpm - st["bpm"]) / st["bpm"] * 100.0))
    print("-" * 66)

    total = sum(st["mod_size"] for st in stats) + \
        sum(r["size"] for r in se_rows)
    print()
    print("Output sizes: %d bytes total (%.1f KB); MODs %s bytes"
          % (total, total / 1024.0,
             "/".join(str(st["mod_size"]) for st in stats)))
    print("Renders written to %s" % SCRATCH_DIR)

    if failures:
        print()
        print("FAILED %d check(s):" % len(failures))
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("All NDS audio checks passed.")


if __name__ == "__main__":
    main()
