#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_audio.py -- chiptune BGM + SE generator for the 8-bit vertical shooter.

Standard library only (math, wave, struct, random, os, sys).
Output: WAV, 22050 Hz, 16-bit PCM, mono. Fully deterministic (seeded RNG).

Re-run any time:  python3 tools/generate_audio.py
Writes:
    assets/bgm/{title,stage1,stage2,stage3,boss,ending}.wav   (seamless loops)
    assets/se/{shot,hit,explosion,player_death,powerup,boss_explosion,start,clear}.wav

Ends with a mandatory analysis pass (duration / peak / RMS / loop-click check)
and exits non-zero if any check fails.
"""

import math
import os
import random
import struct
import sys
import wave

SR = 22050
TWO_PI = 2.0 * math.pi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BGM_DIR = os.path.join(ROOT, "assets", "bgm")
SE_DIR = os.path.join(ROOT, "assets", "se")

# ---------------------------------------------------------------- note utils

NOTE_OFF = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def N(name):
    """Note name ('C4', 'F#5', 'Bb3') or midi int -> midi number."""
    if isinstance(name, int):
        return name
    pc = NOTE_OFF[name[0]]
    rest = name[1:]
    if rest[0] == "#":
        pc += 1
        rest = rest[1:]
    elif rest[0] == "b":
        pc -= 1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def FR(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def triad(root_pc, quality):
    """Chord tones (midi) rooted in octave 4."""
    base = 60 + (root_pc % 12)
    ints = (0, 3, 7) if quality == "m" else (0, 4, 7)
    return [base + i for i in ints]


# ---------------------------------------------------------------- synth core


class Song:
    """A mixing buffer with musical-time helpers. 4/4 assumed."""

    def __init__(self, bpm, bars):
        self.bpm = bpm
        self.bars = bars
        self.spb = 60.0 / bpm  # seconds per beat
        self.total = int(round(bars * 4 * self.spb * SR))
        self.buf = [0.0] * self.total
        # Note-event log for external converters (tools/generate_nds_audio.py).
        # Append-only side channel; never read by this script, cannot affect
        # the rendered audio.
        self.events = []

    # ---- pitched voices ----------------------------------------------------
    def tone(self, bar, beat, dur_beats, note, wave_kind="sq",
             vol=0.3, duty=0.5, vib=None, sustain=0.35, decay=2.5):
        """Square/triangle note. vib=None -> auto vibrato on notes > 8th."""
        midi = N(note)
        self.events.append(
            ("tone", bar, beat, dur_beats, midi, wave_kind, vol, duty))
        freq = FR(midi)
        start = (bar * 4 + beat) * self.spb
        dur = dur_beats * self.spb
        if vib is None:
            vib = (wave_kind == "sq") and dur_beats > 0.55
        n0 = int(round(start * SR))
        n1 = min(self.total, n0 + int(dur * SR))
        if n1 <= n0:
            return
        buf = self.buf
        release = 0.015 * SR  # samples
        att = 0.004 * SR
        phase = 0.0
        inv_sr = 1.0 / SR
        span = n1 - n0
        sus = sustain
        cmp_sus = 1.0 - sustain
        for i in range(span):
            t = i * inv_sr
            f = freq
            if vib and t > 0.09:
                f = freq * (1.0 + 0.006 * math.sin(TWO_PI * 5.5 * t))
            phase += f * inv_sr
            p = phase - int(phase)
            if wave_kind == "sq":
                s = 1.0 if p < duty else -1.0
            else:  # triangle
                s = 4.0 * abs(p - 0.5) - 1.0
            env = (sus + cmp_sus * math.exp(-decay * t))
            if i < att:
                env *= i / att
            rem = span - 1 - i
            if rem < release:
                env *= rem / release
            buf[n0 + i] += s * vol * env

    # ---- drums -------------------------------------------------------------
    def kick(self, bar, beat, vol=0.5):
        self.events.append(("kick", bar, beat, vol))
        n0 = int(round((bar * 4 + beat) * self.spb * SR))
        rng = random.Random(1000 + n0)
        dur = int(0.10 * SR)
        buf = self.buf
        phase = 0.0
        for i in range(dur):
            idx = n0 + i
            if idx >= self.total:
                break
            t = i / SR
            f = 150.0 * math.exp(-t * 30.0) + 42.0
            phase += f / SR
            s = math.sin(TWO_PI * phase)
            if t < 0.008:  # attack click
                s += 0.35 * rng.uniform(-1.0, 1.0)
            env = math.exp(-t * 32.0)
            if i < 40:
                env *= i / 40.0
            buf[idx] += s * vol * env

    def snare(self, bar, beat, vol=0.32):
        self.events.append(("snare", bar, beat, vol))
        n0 = int(round((bar * 4 + beat) * self.spb * SR))
        rng = random.Random(2000 + n0)
        dur = int(0.13 * SR)
        buf = self.buf
        prev = 0.0
        for i in range(dur):
            idx = n0 + i
            if idx >= self.total:
                break
            t = i / SR
            x = rng.uniform(-1.0, 1.0)
            hp = x - 0.4 * prev  # mild high-pass
            prev = x
            s = hp * 0.85 + 0.4 * math.sin(TWO_PI * 185.0 * t) * math.exp(-t * 45.0)
            env = math.exp(-t * 28.0)
            if i < 20:
                env *= i / 20.0
            buf[idx] += s * vol * env

    def hat(self, bar, beat, vol=0.10):
        self.events.append(("hat", bar, beat, vol))
        n0 = int(round((bar * 4 + beat) * self.spb * SR))
        rng = random.Random(3000 + n0)
        dur = int(0.035 * SR)
        buf = self.buf
        prev = 0.0
        for i in range(dur):
            idx = n0 + i
            if idx >= self.total:
                break
            t = i / SR
            x = rng.uniform(-1.0, 1.0)
            s = x - prev  # strong high-pass -> metallic
            prev = x
            env = math.exp(-t * 120.0)
            if i < 8:
                env *= i / 8.0
            buf[idx] += s * vol * env


# ------------------------------------------------------------- wav utilities


def normalize(buf, peak_target):
    peak = max(abs(v) for v in buf)
    if peak <= 0.0:
        return buf
    g = peak_target / peak
    return [v * g for v in buf]


def edge_fade(buf, n=64):
    ln = len(buf)
    n = min(n, ln // 2)
    for i in range(n):
        g = i / n
        buf[i] *= g
        buf[ln - 1 - i] *= g
    return buf


def write_wav(path, buf, peak_target):
    # fade FIRST, then normalize: edges end exactly at 0 and the peak target
    # is hit exactly even for SEs whose peak sits in the first milliseconds.
    data = normalize(edge_fade(buf), peak_target)
    frames = bytearray()
    for v in data:
        iv = int(round(v * 32767.0))
        if iv > 32767:
            iv = 32767
        elif iv < -32768:
            iv = -32768
        frames += struct.pack("<h", iv)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print("  wrote %-42s %6.3f s" % (os.path.relpath(path, ROOT), len(data) / SR))


# ------------------------------------------------------------ mix level plan

LEAD = 0.30
ARP = 0.15
BASS = 0.35


# ================================================================ BGM tracks


def compose_title():
    """~8 bars, 120 BPM, C major fanfare. C-G-Am-F x2."""
    s = Song(120, 8)
    prog = [("C", "M"), ("G", "M"), ("A", "m"), ("F", "M")] * 2
    for bar, (rt, q) in enumerate(prog):
        pc = N(rt + "4") % 12
        broot = 36 + pc
        tri = triad(pc, q)
        # triangle bass: root-fifth quarters
        for b, m in enumerate([broot, broot + 7, broot, broot + 7]):
            s.tone(bar, b, 0.95, m, "tri", BASS, sustain=0.55, decay=2.0)
        # harmony arp, thin square
        pat = [tri[0], tri[1], tri[2], tri[1]] * 2
        for k, m in enumerate(pat):
            s.tone(bar, k * 0.5, 0.45, m, "sq", ARP, duty=0.25, vib=False)
        # light drums
        s.kick(bar, 0)
        s.kick(bar, 2)
        s.snare(bar, 1)
        s.snare(bar, 3)
        for k in range(8):
            s.hat(bar, k * 0.5)
    mel = [
        (0, 0, 1, "E5"), (0, 1, 0.5, "G5"), (0, 1.5, 0.5, "E5"), (0, 2, 2, "C5"),
        (1, 0, 1, "D5"), (1, 1, 1, "G5"), (1, 2, 2, "B4"),
        (2, 0, 0.5, "C5"), (2, 0.5, 0.5, "A4"), (2, 1, 1, "C5"), (2, 2, 2, "E5"),
        (3, 0, 1, "F5"), (3, 1, 1, "A5"), (3, 2, 1, "G5"), (3, 3, 1, "F5"),
        (4, 0, 2, "G5"), (4, 2, 1, "E5"), (4, 3, 1, "C5"),
        (5, 0, 1, "D5"), (5, 1, 1, "B4"), (5, 2, 1, "D5"), (5, 3, 1, "G5"),
        (6, 0, 1.5, "A5"), (6, 1.5, 0.5, "E5"), (6, 2, 2, "C5"),
        (7, 0, 0.5, "F5"), (7, 0.5, 0.5, "A5"), (7, 1, 1, "C6"), (7, 2, 2, "G5"),
    ]
    for bar, beat, dur, note in mel:
        s.tone(bar, beat, dur * 0.97, note, "sq", LEAD, duty=0.5)
    return s


STAGE1_A = [
    (0, 0, 0.5, "A4"), (0, 0.5, 0.5, "C5"), (0, 1, 1, "E5"), (0, 2, 1, "A5"),
    (0, 3, 0.5, "G5"), (0, 3.5, 0.5, "E5"),
    (1, 0, 1.5, "F5"), (1, 1.5, 0.5, "C5"), (1, 2, 1, "A4"), (1, 3, 1, "C5"),
    (2, 0, 0.5, "E5"), (2, 0.5, 0.5, "G5"), (2, 1, 1, "C6"), (2, 2, 0.5, "B5"),
    (2, 2.5, 0.5, "G5"), (2, 3, 1, "E5"),
    (3, 0, 1, "D5"), (3, 1, 1, "B4"), (3, 2, 2, "G4"),
]
STAGE1_B = [
    (0, 0, 1, "E5"), (0, 1, 1, "A5"), (0, 2, 1, "C6"), (0, 3, 0.5, "B5"),
    (0, 3.5, 0.5, "A5"),
    (1, 0, 1, "A5"), (1, 1, 1, "F5"), (1, 2, 1, "C5"), (1, 3, 1, "D5"),
    (2, 0, 1.5, "G5"), (2, 1.5, 0.5, "E5"), (2, 2, 1, "C5"), (2, 3, 1, "E5"),
    (3, 0, 0.5, "D5"), (3, 0.5, 0.5, "G5"), (3, 1, 1, "B5"), (3, 2, 0.5, "A5"),
    (3, 2.5, 0.5, "G5"), (3, 3, 1, "D5"),
]


def compose_stage1():
    """16 bars, 150 BPM, A minor heroic. Am-F-C-G, driving 8th bass."""
    s = Song(150, 16)
    prog = [("A", "m"), ("F", "M"), ("C", "M"), ("G", "M")] * 4
    for bar, (rt, q) in enumerate(prog):
        pc = N(rt + "4") % 12
        broot = 36 + pc
        tri = triad(pc, q)
        # driving 8th-note bass with octave pops
        bl = [broot, broot, broot + 12, broot, broot, broot + 12, broot, broot + 7]
        for k, m in enumerate(bl):
            s.tone(bar, k * 0.5, 0.46, m, "tri", BASS, sustain=0.6, decay=3.0)
        # off-beat harmony chops
        for k in (0.5, 1.5, 2.5, 3.5):
            s.tone(bar, k, 0.3, tri[1], "sq", ARP, duty=0.25, vib=False)
            s.tone(bar, k, 0.3, tri[2], "sq", ARP * 0.8, duty=0.25, vib=False)
        s.kick(bar, 0)
        s.kick(bar, 2)
        s.kick(bar, 2.5)
        s.snare(bar, 1)
        s.snare(bar, 3)
        for k in range(8):
            s.hat(bar, k * 0.5)
    # A A B A hook
    for sect, phrase in ((0, STAGE1_A), (4, STAGE1_A), (8, STAGE1_B), (12, STAGE1_A)):
        for bar, beat, dur, note in phrase:
            s.tone(sect + bar, beat, dur * 0.97, note, "sq", LEAD, duty=0.5)
    return s


STAGE2_A = [
    (0, 0, 1, "D5"), (0, 1, 0.5, "F5"), (0, 1.5, 0.5, "E5"), (0, 2, 1, "D5"),
    (0, 3, 1, "A4"),
    (1, 0, 1.5, "Bb4"), (1, 1.5, 0.5, "D5"), (1, 2, 2, "F5"),
    (2, 0, 1, "G4"), (2, 1, 0.5, "Bb4"), (2, 1.5, 0.5, "C5"), (2, 2, 2, "D5"),
    (3, 0, 1, "C#5"), (3, 1, 1, "E5"), (3, 2, 2, "A4"),
]
STAGE2_B = [
    (0, 0, 1, "F5"), (0, 1, 0.5, "A5"), (0, 1.5, 0.5, "G5"), (0, 2, 1, "F5"),
    (0, 3, 1, "D5"),
    (1, 0, 1.5, "D5"), (1, 1.5, 0.5, "F5"), (1, 2, 2, "Bb5"),
    (2, 0, 1, "A5"), (2, 1, 0.5, "G5"), (2, 1.5, 0.5, "F5"), (2, 2, 2, "G5"),
    (3, 0, 1, "E5"), (3, 1, 1, "C#5"), (3, 2, 2, "A4"),
]


def compose_stage2():
    """16 bars, 145 BPM, D minor, darker. Dm-Bb-Gm-A, syncopated 3-3-2 bass."""
    s = Song(145, 16)
    prog = [("D", "m"), ("Bb", "M"), ("G", "m"), ("A", "M")] * 4
    sync = [(0.0, 0.7), (0.75, 0.7), (1.5, 0.45), (2.0, 0.7), (2.75, 0.7), (3.5, 0.45)]
    for bar, (rt, q) in enumerate(prog):
        pc = N(rt + "4") % 12
        broot = 36 + pc
        tri = triad(pc, q)
        notes = [broot, broot, broot + 7, broot, broot, broot + 7]
        for (beat, dur), m in zip(sync, notes):
            s.tone(bar, beat, dur, m, "tri", BASS, sustain=0.55, decay=3.5)
        # dark held chord pad, thin duty
        s.tone(bar, 1.5, 0.4, tri[1], "sq", ARP, duty=0.2, vib=False)
        s.tone(bar, 1.5, 0.4, tri[2], "sq", ARP * 0.8, duty=0.2, vib=False)
        s.tone(bar, 3.5, 0.4, tri[1], "sq", ARP, duty=0.2, vib=False)
        s.tone(bar, 3.5, 0.4, tri[2], "sq", ARP * 0.8, duty=0.2, vib=False)
        s.kick(bar, 0)
        s.kick(bar, 1.5)
        s.kick(bar, 2.75)
        s.snare(bar, 1)
        s.snare(bar, 3)
        for k in range(8):
            s.hat(bar, k * 0.5, vol=0.08)
    for sect, phrase in ((0, STAGE2_A), (4, STAGE2_A), (8, STAGE2_B), (12, STAGE2_A)):
        for bar, beat, dur, note in phrase:
            s.tone(sect + bar, beat, dur * 0.97, note, "sq", LEAD, duty=0.5)
    return s


STAGE3_A = [
    (0, 0, 0.5, "E5"), (0, 0.5, 0.5, "B4"), (0, 1, 0.5, "E5"), (0, 1.5, 0.5, "G5"),
    (0, 2, 0.5, "F#5"), (0, 2.5, 0.5, "E5"), (0, 3, 1, "B5"),
    (1, 0, 1, "C6"), (1, 1, 0.5, "B5"), (1, 1.5, 0.5, "G5"), (1, 2, 0.5, "A5"),
    (1, 2.5, 0.5, "G5"), (1, 3, 1, "E5"),
    (2, 0, 0.5, "D5"), (2, 0.5, 0.5, "F#5"), (2, 1, 1.5, "A5"), (2, 2.5, 0.5, "F#5"),
    (2, 3, 0.5, "D5"), (2, 3.5, 0.5, "F#5"),
    (3, 0, 0.5, "B4"), (3, 0.5, 0.5, "D#5"), (3, 1, 1, "F#5"), (3, 2, 2, "B5"),
]
STAGE3_B = [
    (0, 0, 0.5, "G5"), (0, 0.5, 0.5, "E5"), (0, 1, 1, "B5"), (0, 2, 0.5, "A5"),
    (0, 2.5, 0.5, "G5"), (0, 3, 1, "E5"),
    (1, 0, 0.5, "E5"), (1, 0.5, 0.5, "G5"), (1, 1, 1, "C6"), (1, 2, 1, "B5"),
    (1, 3, 1, "G5"),
    (2, 0, 0.5, "F#5"), (2, 0.5, 0.5, "A5"), (2, 1, 1, "D6"), (2, 2, 1, "A5"),
    (2, 3, 1, "F#5"),
    (3, 0, 1, "D#5"), (3, 1, 1, "F#5"), (3, 2, 1.5, "B5"), (3, 3.5, 0.5, "A5"),
]


def compose_stage3():
    """16 bars, 160 BPM, E minor, aggressive. Em-C-D-B, 16th arpeggios."""
    s = Song(160, 16)
    prog = [("E", "m"), ("C", "M"), ("D", "M"), ("B", "M")] * 4
    for bar, (rt, q) in enumerate(prog):
        pc = N(rt + "4") % 12
        broot = 36 + pc
        tri = triad(pc, q)
        # relentless 8th bass, root/octave
        for k in range(8):
            m = broot if k % 2 == 0 else broot + 12
            s.tone(bar, k * 0.5, 0.46, m, "tri", BASS, sustain=0.6, decay=3.0)
        # fast 16th-note arpeggio channel
        arp = [tri[0], tri[2], tri[0] + 12, tri[2]] * 4
        for k, m in enumerate(arp):
            s.tone(bar, k * 0.25, 0.22, m, "sq", ARP, duty=0.25, vib=False)
        s.kick(bar, 0)
        s.kick(bar, 1.5)
        s.kick(bar, 2)
        s.snare(bar, 1)
        s.snare(bar, 3)
        s.snare(bar, 3.75, vol=0.18)
        for k in range(8):
            s.hat(bar, k * 0.5)
    for sect, phrase in ((0, STAGE3_A), (4, STAGE3_A), (8, STAGE3_B), (12, STAGE3_A)):
        for bar, beat, dur, note in phrase:
            s.tone(sect + bar, beat, dur * 0.97, note, "sq", LEAD, duty=0.5)
    return s


def compose_boss():
    """8 bars, 155 BPM, B minor. Menacing ostinato bass + dissonant stabs."""
    s = Song(155, 8)
    riff = ["B2", "B2", "D3", "B2", "B2", "F3", "E3", "D3"]  # F natural = tritone
    for bar in range(8):
        for k, nm in enumerate(riff):
            s.tone(bar, k * 0.5, 0.46, nm, "tri", BASS + 0.03, sustain=0.6, decay=3.0)
        # dissonant stabs (tritone clusters), thin nasty duty
        stab = ("B4", "F5") if bar < 4 else ("D5", "G#5")
        for beat in (1.5, 3.0):
            for nm in stab:
                s.tone(bar, beat, 0.28, nm, "sq", 0.17, duty=0.125, vib=False)
        s.kick(bar, 0)
        s.kick(bar, 2)
        s.kick(bar, 2.5)
        s.snare(bar, 1)
        s.snare(bar, 3)
        for k in range(8):
            s.hat(bar, k * 0.5)
    mel = [
        (4, 0, 1, "F#5"), (4, 1, 1, "G5"), (4, 2, 2, "F#5"),
        (5, 0, 1, "D5"), (5, 2, 1, "E5"), (5, 3, 1, "F5"),
        (6, 0, 2, "F#5"), (6, 2, 1, "A5"), (6, 3, 1, "G5"),
        (7, 0, 1, "F#5"), (7, 1, 1, "E5"), (7, 2, 2, "C#5"),
    ]
    for bar, beat, dur, note in mel:
        s.tone(bar, beat, dur * 0.97, note, "sq", LEAD * 0.9, duty=0.5)
    return s


def compose_ending():
    """8 bars, 100 BPM, F major. Warm triumphant ballad, gentle arps. Loops."""
    s = Song(100, 8)
    prog = [("F", "M"), ("D", "m"), ("Bb", "M"), ("C", "M")] * 2
    for bar, (rt, q) in enumerate(prog):
        pc = N(rt + "4") % 12
        broot = 36 + pc
        tri = triad(pc, q)
        # soft half-note bass
        s.tone(bar, 0, 1.9, broot, "tri", BASS * 0.85, sustain=0.55, decay=1.4)
        s.tone(bar, 2, 1.9, broot + 7, "tri", BASS * 0.85, sustain=0.55, decay=1.4)
        # gentle triangle arpeggio accompaniment
        pat = [tri[0], tri[1], tri[2], tri[1]] * 2
        for k, m in enumerate(pat):
            s.tone(bar, k * 0.5, 0.48, m + 12, "tri", 0.16, vib=False,
                   sustain=0.4, decay=2.4)
    mel = [
        (0, 0, 1, "A4"), (0, 1, 1, "C5"), (0, 2, 2, "F5"),
        (1, 0, 1.5, "E5"), (1, 1.5, 0.5, "D5"), (1, 2, 2, "A4"),
        (2, 0, 1, "F5"), (2, 1, 1, "D5"), (2, 2, 2, "Bb4"),
        (3, 0, 1, "C5"), (3, 1, 1, "D5"), (3, 2, 1, "E5"), (3, 3, 1, "G5"),
        (4, 0, 2, "A5"), (4, 2, 1, "F5"), (4, 3, 1, "C5"),
        (5, 0, 1.5, "D5"), (5, 1.5, 0.5, "C5"), (5, 2, 2, "A4"),
        (6, 0, 1, "Bb4"), (6, 1, 1, "C5"), (6, 2, 1, "D5"), (6, 3, 1, "F5"),
        (7, 0, 2, "E5"), (7, 2, 2, "G5"),
    ]
    for bar, beat, dur, note in mel:
        s.tone(bar, beat, dur * 0.96, note, "sq", 0.27, duty=0.5)
    return s


# ================================================================= SE synths


def se_shot():
    """~0.08 s tiny square blip, 880->440 Hz drop. Quiet (fires constantly)."""
    dur = 0.08
    n = int(dur * SR)
    buf = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 880.0 * (0.5 ** (t / dur))  # ends at 440
        phase += f / SR
        s = 1.0 if (phase - int(phase)) < 0.5 else -1.0
        env = math.exp(-t * 28.0)
        if i < 20:
            env *= i / 20.0
        buf[i] = s * env
    return buf, 0.35


def se_hit():
    """~0.10 s noise + square click."""
    dur = 0.10
    n = int(dur * SR)
    rng = random.Random(42)
    buf = [0.0] * n
    phase = 0.0
    prev = 0.0
    for i in range(n):
        t = i / SR
        f = 330.0 * (0.33 ** (t / dur))
        phase += f / SR
        sq = 1.0 if (phase - int(phase)) < 0.5 else -1.0
        x = rng.uniform(-1.0, 1.0)
        hp = x - 0.5 * prev
        prev = x
        env = math.exp(-t * 42.0)
        if i < 15:
            env *= i / 15.0
        buf[i] = (0.6 * sq + 0.7 * hp) * env
    return buf, 0.60


def se_explosion():
    """~0.45 s noise burst, falling amplitude, darkening tone (closing LPF)."""
    dur = 0.45
    n = int(dur * SR)
    rng = random.Random(7)
    buf = [0.0] * n
    lp = 0.0
    for i in range(n):
        t = i / SR
        x = rng.uniform(-1.0, 1.0)
        a = 0.65 * (1.0 - t / dur) + 0.04  # LPF closes -> darker over time
        lp += a * (x - lp)
        env = math.exp(-t * 7.5)
        if i < 30:
            env *= i / 30.0
        buf[i] = lp * env
    return buf, 0.85


def se_player_death():
    """~0.8 s dramatic descending square sweep layered with noise."""
    dur = 0.8
    n = int(dur * SR)
    rng = random.Random(13)
    buf = [0.0] * n
    phase = 0.0
    lp = 0.0
    for i in range(n):
        t = i / SR
        f = 660.0 * (0.11 ** (t / dur))  # sweeps down to ~72 Hz
        f *= 1.0 + 0.02 * math.sin(TWO_PI * 9.0 * t)  # wobble = drama
        phase += f / SR
        sq = 1.0 if (phase - int(phase)) < 0.5 else -1.0
        x = rng.uniform(-1.0, 1.0)
        lp += 0.30 * (x - lp)
        env = math.exp(-t * 3.4)
        if i < 30:
            env *= i / 30.0
        buf[i] = (0.7 * sq + 0.55 * lp) * env
    return buf, 0.85


def se_powerup():
    """~0.35 s ascending major arpeggio C5-E5-G5-C6, sparkly (octave doubles)."""
    dur = 0.35
    n = int(dur * SR)
    buf = [0.0] * n
    steps = [("C5", 0.00, 0.09), ("E5", 0.07, 0.09), ("G5", 0.14, 0.09),
             ("C6", 0.21, 0.14)]
    for note, st, d in steps:
        f0 = FR(N(note))
        n0 = int(st * SR)
        n1 = min(n, n0 + int(d * SR))
        ph1 = 0.0
        ph2 = 0.0
        for i in range(n0, n1):
            t = (i - n0) / SR
            ph1 += f0 / SR
            ph2 += (f0 * 2.0) / SR
            s1 = 1.0 if (ph1 - int(ph1)) < 0.5 else -1.0
            s2 = 1.0 if (ph2 - int(ph2)) < 0.25 else -1.0  # thin sparkle layer
            env = math.exp(-t * 12.0)
            if i - n0 < 15:
                env *= (i - n0) / 15.0
            rem = n1 - 1 - i
            if rem < 60:
                env *= rem / 60.0
            buf[i] += (0.8 * s1 + 0.3 * s2) * env
    return buf, 0.70


def se_boss_explosion():
    """~1.3 s huge layered rumble: repeated noise bursts + low descending tone."""
    dur = 1.3
    n = int(dur * SR)
    buf = [0.0] * n
    # repeated darkening noise bursts
    for bi, (st, vol) in enumerate([(0.0, 1.0), (0.22, 0.9), (0.46, 0.75),
                                    (0.72, 0.6), (0.98, 0.45)]):
        rng = random.Random(100 + bi)
        n0 = int(st * SR)
        n1 = min(n, n0 + int(0.5 * SR))
        lp = 0.0
        for i in range(n0, n1):
            t = (i - n0) / SR
            x = rng.uniform(-1.0, 1.0)
            a = 0.5 * (1.0 - bi * 0.15) * (1.0 - t / 0.5) + 0.03
            lp += a * (x - lp)
            env = math.exp(-t * 6.0)
            if i - n0 < 40:
                env *= (i - n0) / 40.0
            buf[i] += lp * env * vol
    # low descending doom tone (triangle)
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 110.0 * (0.25 ** (t / dur))  # down to ~27 Hz
        phase += f / SR
        p = phase - int(phase)
        s = 4.0 * abs(p - 0.5) - 1.0
        env = 0.55 * math.exp(-t * 2.0)
        if i < 60:
            env *= i / 60.0
        rem = n - 1 - i
        if rem < 800:
            env *= rem / 800.0
        buf[i] += s * env
    return buf, 0.90


def se_start():
    """~0.3 s two-note confirm blip (E5 then A5)."""
    dur = 0.3
    n = int(dur * SR)
    buf = [0.0] * n
    for note, st, d in (("E5", 0.0, 0.10), ("A5", 0.10, 0.20)):
        f0 = FR(N(note))
        n0 = int(st * SR)
        n1 = min(n, n0 + int(d * SR))
        ph = 0.0
        for i in range(n0, n1):
            t = (i - n0) / SR
            ph += f0 / SR
            s = 1.0 if (ph - int(ph)) < 0.5 else -1.0
            env = math.exp(-t * 11.0)
            if i - n0 < 15:
                env *= (i - n0) / 15.0
            rem = n1 - 1 - i
            if rem < 80:
                env *= rem / 80.0
            buf[i] += s * env
    return buf, 0.70


def se_clear():
    """~1.4 s victory jingle: rising fanfare arp, held C-major chord. One-shot."""
    dur = 1.4
    n = int(dur * SR)
    buf = [0.0] * n

    def blip(note, st, d, vol=1.0, duty=0.5, decay=6.0):
        f0 = FR(N(note))
        n0 = int(st * SR)
        n1 = min(n, n0 + int(d * SR))
        ph = 0.0
        for i in range(n0, n1):
            t = (i - n0) / SR
            f = f0 * (1.0 + (0.005 * math.sin(TWO_PI * 6.0 * t) if t > 0.1 else 0.0))
            ph += f / SR
            s = 1.0 if (ph - int(ph)) < duty else -1.0
            env = math.exp(-t * decay)
            if i - n0 < 20:
                env *= (i - n0) / 20.0
            rem = n1 - 1 - i
            if rem < 100:
                env *= rem / 100.0
            buf[i] += s * env * vol

    blip("C5", 0.00, 0.13)
    blip("E5", 0.11, 0.13)
    blip("G5", 0.22, 0.13)
    blip("C6", 0.33, 0.24, decay=4.0)
    # held triumphant chord, decays naturally to silence (not loop-sounding)
    for note, vol in (("C5", 0.55), ("E5", 0.5), ("G5", 0.5), ("C6", 0.6)):
        blip(note, 0.55, dur - 0.55, vol=vol, duty=0.35, decay=2.6)
    # triangle bass root under the chord
    ph = 0.0
    fb = FR(N("C3"))
    n0 = int(0.55 * SR)
    for i in range(n0, n):
        t = (i - n0) / SR
        ph += fb / SR
        p = ph - int(ph)
        s = 4.0 * abs(p - 0.5) - 1.0
        env = 0.6 * math.exp(-t * 2.6)
        if i - n0 < 40:
            env *= (i - n0) / 40.0
        rem = n - 1 - i
        if rem < 100:
            env *= rem / 100.0
        buf[i] += s * env
    return buf, 0.80


# ============================================================ build + verify

BGM_SPECS = {
    "title.wav": dict(bpm=120, bars=8, fn=compose_title),
    "stage1.wav": dict(bpm=150, bars=16, fn=compose_stage1),
    "stage2.wav": dict(bpm=145, bars=16, fn=compose_stage2, peak=0.88),
    "stage3.wav": dict(bpm=160, bars=16, fn=compose_stage3),
    "boss.wav": dict(bpm=155, bars=8, fn=compose_boss),
    # ending has a dense sustained texture (high RMS/peak ratio); a lower peak
    # target loudness-matches it to the other tracks. still inside 0.7-0.9.
    "ending.wav": dict(bpm=100, bars=8, fn=compose_ending, peak=0.72),
}

SE_SPECS = {
    "shot.wav": dict(dur=0.08, fn=se_shot),
    "hit.wav": dict(dur=0.10, fn=se_hit),
    "explosion.wav": dict(dur=0.45, fn=se_explosion),
    "player_death.wav": dict(dur=0.80, fn=se_player_death),
    "powerup.wav": dict(dur=0.35, fn=se_powerup),
    "boss_explosion.wav": dict(dur=1.30, fn=se_boss_explosion),
    "start.wav": dict(dur=0.30, fn=se_start),
    "clear.wav": dict(dur=1.40, fn=se_clear),
}

BGM_PEAK_TARGET = 0.85


def generate_all():
    random.seed(20260712)
    print("Generating BGM ...")
    for name, spec in BGM_SPECS.items():
        song = spec["fn"]()
        write_wav(os.path.join(BGM_DIR, name),
                  song.buf, spec.get("peak", BGM_PEAK_TARGET))
    print("Generating SE ...")
    for name, spec in SE_SPECS.items():
        buf, peak = spec["fn"]()
        write_wav(os.path.join(SE_DIR, name), buf, peak)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2 and \
            w.getframerate() == SR, "format mismatch: " + path
        raw = w.readframes(w.getnframes())
    vals = struct.unpack("<%dh" % (len(raw) // 2), raw)
    return [v / 32768.0 for v in vals]


def analyze():
    print()
    print("=" * 98)
    print("%-26s %9s %7s %7s %9s %9s  %s" %
          ("file", "dur(s)", "peak", "RMS", "first", "last", "checks"))
    print("-" * 98)
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        return "" if cond else " !! " + msg

    for name, spec in BGM_SPECS.items():
        path = os.path.join(BGM_DIR, name)
        d = read_wav(path)
        n = len(d)
        durs = n / SR
        peak = max(abs(v) for v in d)
        rms = math.sqrt(sum(v * v for v in d) / n)
        expected = spec["bars"] * 4 * (60.0 / spec["bpm"]) * SR
        notes = ""
        notes += check(abs(n - expected) <= 1.0,
                       "%s length %d != %d bars @ %d BPM (%.1f smp)" %
                       (name, n, spec["bars"], spec["bpm"], expected))
        notes += check(abs(d[0]) < 0.01 and abs(d[-1]) < 0.01,
                       "%s loop-click risk (edges not ~0)" % name)
        notes += check(peak < 0.95, "%s clipping risk peak=%.3f" % (name, peak))
        notes += check(0.70 <= peak <= 0.90, "%s peak outside 0.7-0.9" % name)
        notes += check(rms > 0.02, "%s near-silent rms=%.4f" % (name, rms))
        ok = "bars-exact loop-ok" if notes == "" else notes
        print("bgm/%-22s %9.4f %7.3f %7.3f %+9.5f %+9.5f  %s" %
              (name, durs, peak, rms, d[0], d[-1], ok))

    for name, spec in SE_SPECS.items():
        path = os.path.join(SE_DIR, name)
        d = read_wav(path)
        n = len(d)
        durs = n / SR
        peak = max(abs(v) for v in d)
        rms = math.sqrt(sum(v * v for v in d) / n)
        notes = ""
        notes += check(abs(durs - spec["dur"]) <= spec["dur"] * 0.25 + 0.02,
                       "%s duration %.3f != ~%.2f" % (name, durs, spec["dur"]))
        notes += check(peak < 0.95, "%s clipping risk peak=%.3f" % (name, peak))
        notes += check(rms > 0.02, "%s near-silent rms=%.4f" % (name, rms))
        ok = "ok" if notes == "" else notes
        print("se/%-23s %9.4f %7.3f %7.3f %+9.5f %+9.5f  %s" %
              (name, durs, peak, rms, d[0], d[-1], ok))

    print("=" * 98)
    if failures:
        print("FAILED %d check(s):" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("All checks passed.")
    return 0


def main():
    generate_all()
    rc = analyze()
    sys.exit(rc)


if __name__ == "__main__":
    main()
