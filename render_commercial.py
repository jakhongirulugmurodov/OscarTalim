#!/usr/bin/env python3
"""Procedural renderer for the 10s eyewear commercial animatic.

Renders 300 frames (1080x1920 @ 30fps) with PIL + numpy, synthesizes the
soundtrack with numpy, and encodes the final MP4 with ffmpeg.

  Shot 1 (0-3s)  : blurry POV city street, hand lifts glasses
  Shot 2 (3-5s)  : glasses slide on, world snaps into focus + lens flare
  Shot 3 (5-10s) : golden-hour hero walk, dolly-in to face, subtle smile
"""

import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

W, H = 1080, 1920
FPS = 30
DUR = 10.0
N_FRAMES = int(FPS * DUR)
MARGIN = 80  # oversize for handheld sway cropping

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "out"
FRAMES_DIR = os.path.join(OUT_DIR, "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

SNAP_T = 4.2  # seconds — the focus-snap moment


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- city scene
def build_city(w, h):
    """Bright stylized city street, one-point perspective, drawn sharp."""
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img, "RGBA")
    horizon = int(h * 0.51)
    vpx = w // 2

    # sky gradient
    for y in range(horizon):
        t = y / horizon
        d.line([(0, y), (w, y)], fill=(
            int(lerp(120, 225, t)), int(lerp(175, 240, t)), int(lerp(250, 255, t))))
    # sun with glow
    sx, sy = int(w * 0.76), int(h * 0.14)
    for r, a in [(260, 25), (180, 45), (110, 80)]:
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 250, 220, a))
    d.ellipse([sx - 70, sy - 70, sx + 70, sy + 70], fill=(255, 252, 235))

    # road
    d.polygon([(0, h), (w, h), (vpx + 105, horizon), (vpx - 105, horizon)],
              fill=(104, 108, 118))
    # sidewalks
    d.polygon([(0, h), (vpx - 105, horizon), (vpx - 160, horizon), (-350, h)],
              fill=(168, 168, 172))
    d.polygon([(w, h), (vpx + 105, horizon), (vpx + 160, horizon), (w + 350, h)],
              fill=(168, 168, 172))

    pal = [(196, 176, 160), (150, 170, 190), (210, 190, 150),
           (170, 150, 150), (185, 195, 205)]
    # buildings, both sides
    for side in (-1, 1):
        for i in range(5):
            d0, d1 = i / 5.0, (i + 1) / 5.0
            def px(dd):  # x of street edge at depth dd
                return vpx + side * int(lerp(w * 0.62, 160, dd))
            x0, x1 = px(d0), px(d1)
            yb0 = int(lerp(h * 1.05, horizon, d0 ** 0.9))
            yb1 = int(lerp(h * 1.05, horizon, d1 ** 0.9))
            yt0 = int(lerp(h * 0.03, horizon - h * 0.16, d0 ** 1.1))
            yt1 = int(lerp(h * 0.03, horizon - h * 0.16, d1 ** 1.1))
            col = pal[(i + (0 if side < 0 else 2)) % len(pal)]
            d.polygon([(x0, yt0), (x1, yt1), (x1, yb1), (x0, yb0)], fill=col)
            # windows
            dark = tuple(int(c * 0.55) for c in col)
            rows = 9 - i
            for r in range(rows):
                for c in range(3):
                    fx = (c + 0.5) / 3.0
                    fy = (r + 0.5) / rows
                    wx = lerp(x0, x1, fx)
                    wy = lerp(lerp(yt0, yt1, fx), lerp(yb0, yb1, fx), fy * 0.82 + 0.04)
                    ww = lerp(26, 8, (d0 + d1) / 2) * 1.2
                    wh = ww * 1.5
                    d.rectangle([wx - ww, wy - wh, wx + ww, wy + wh], fill=dark)

    # red awning (left, near)
    d.polygon([(w * 0.02, h * 0.60), (w * 0.30, h * 0.575),
               (w * 0.30, h * 0.615), (w * 0.02, h * 0.65)], fill=(205, 60, 55))
    # trees (right)
    for tx, ty, tr in [(w * 0.80, h * 0.545, 60), (w * 0.70, h * 0.53, 44)]:
        d.rectangle([tx - 6, ty, tx + 6, ty + tr * 1.2], fill=(90, 70, 55))
        d.ellipse([tx - tr, ty - tr * 1.4, tx + tr, ty + tr * 0.2],
                  fill=(96, 158, 92))
    # yellow car mid-distance
    cx, cy = vpx - 40, horizon + int(h * 0.045)
    d.rounded_rectangle([cx - 60, cy - 34, cx + 60, cy], 12, fill=(235, 190, 60))
    d.rounded_rectangle([cx - 38, cy - 56, cx + 38, cy - 26], 10, fill=(235, 190, 60))
    # pedestrians near horizon
    for px_, s in [(vpx - 140, 1.0), (vpx + 150, 0.85), (vpx + 60, 0.6)]:
        ph = int(h * 0.035 * s)
        d.ellipse([px_ - ph * 0.16, horizon - ph, px_ + ph * 0.16,
                   horizon - ph * 0.68], fill=(60, 60, 70))
        d.polygon([(px_ - ph * 0.22, horizon - ph * 0.66),
                   (px_ + ph * 0.22, horizon - ph * 0.66),
                   (px_ + ph * 0.12, horizon), (px_ - ph * 0.12, horizon)],
                  fill=(60, 60, 70))
    # lane dashes
    for i in range(8):
        dd = i / 8.0
        y0 = lerp(h * 1.02, horizon + 8, dd)
        y1 = lerp(h * 1.02, horizon + 8, dd + 0.055)
        wdt = lerp(26, 3, dd)
        d.polygon([(vpx - wdt, y0), (vpx + wdt, y0),
                   (vpx + wdt * 0.8, y1), (vpx - wdt * 0.8, y1)],
                  fill=(240, 240, 235))
    # crosswalk
    for i in range(6):
        x0 = w * 0.12 + i * w * 0.14
        d.polygon([(x0, h * 0.93), (x0 + w * 0.075, h * 0.93),
                   (x0 + w * 0.055, h * 0.80), (x0 - w * 0.005, h * 0.80)],
                  fill=(235, 235, 230, 220))
    return img


# ------------------------------------------------------------- glasses / hand
def draw_glasses(d, cx, cy, lw, th, tint=18):
    """Front view black-frame glasses. lw = single lens width."""
    lh = lw * 0.74
    r = lw * 0.26
    gap = lw * 0.16
    for s in (-1, 1):
        x0 = cx + s * (gap / 2 + lw) - (lw if s < 0 else 0)
        x0 = cx + (gap / 2 if s > 0 else -gap / 2 - lw)
        box = [x0, cy - lh / 2, x0 + lw, cy + lh / 2]
        d.rounded_rectangle(box, r, fill=(255, 255, 255, tint))
        d.rounded_rectangle(box, r, outline=(18, 16, 18, 255), width=max(2, int(th)))
    # bridge
    d.rounded_rectangle([cx - gap / 2 - 2, cy - lh * 0.16,
                         cx + gap / 2 + 2, cy - lh * 0.16 + max(3, th * 0.9)],
                        3, fill=(18, 16, 18, 255))
    # temple stubs
    for s in (-1, 1):
        x0 = cx + s * (gap / 2 + lw)
        d.line([(x0, cy - lh * 0.18), (x0 + s * lw * 0.30, cy - lh * 0.10)],
               fill=(18, 16, 18, 255), width=max(2, int(th)))


def draw_hand(d, gx, gy, lw):
    """Simple hand gripping the right temple of the glasses."""
    skin = (226, 172, 138, 255)
    px, py = gx + lw * 1.15, gy + lw * 0.30
    d.ellipse([px - lw * 0.42, py - lw * 0.30, px + lw * 0.55, py + lw * 0.85],
              fill=skin)
    for i in range(4):
        fx = px - lw * 0.30 + i * lw * 0.22
        d.rounded_rectangle([fx, py - lw * 0.62, fx + lw * 0.16, py + lw * 0.05],
                            lw * 0.08, fill=skin)
    d.rounded_rectangle([px - lw * 0.52, py - lw * 0.05,
                         px - lw * 0.05, py + lw * 0.22], lw * 0.1, fill=skin)


# --------------------------------------------------------------- shot 3 scene
def build_golden(w, h):
    rng = random.Random(7)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img, "RGBA")
    horizon = int(h * 0.60)
    for y in range(horizon):
        t = y / horizon
        d.line([(0, y), (w, y)], fill=(
            int(lerp(70, 255, t ** 1.6)), int(lerp(52, 150, t ** 1.5)),
            int(lerp(95, 70, t))))
    for y in range(horizon, h):
        t = (y - horizon) / (h - horizon)
        d.line([(0, y), (w, y)], fill=(
            int(lerp(70, 28, t)), int(lerp(45, 20, t)), int(lerp(45, 24, t))))
    # low sun + glow
    sx, sy = int(w * 0.36), int(horizon - h * 0.035)
    for r, a in [(430, 22), (300, 38), (190, 70)]:
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 190, 110, a))
    d.ellipse([sx - 95, sy - 95, sx + 95, sy + 95], fill=(255, 226, 170))
    # sun reflection strip on ground
    for i in range(24):
        yy = horizon + 14 + i * (h - horizon) / 26
        ww = lerp(70, 340, i / 24) * (0.75 + 0.5 * rng.random())
        a = int(lerp(90, 18, i / 24))
        d.ellipse([sx - ww, yy - 7, sx + ww, yy + 7], fill=(255, 170, 90, a))
    # building silhouettes
    for side in (-1, 1):
        base_x = 0 if side < 0 else w
        for i in range(4):
            bw = rng.randint(120, 260)
            bh = rng.randint(int(h * 0.10), int(h * 0.24))
            x0 = base_x + side * (20 + i * 150)
            d.rectangle([min(x0, x0 - side * bw), horizon - bh,
                         max(x0, x0 - side * bw), horizon + 10],
                        fill=(40, 26, 38))
    img = img.filter(ImageFilter.GaussianBlur(13))

    # bokeh layer
    bok = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bok)
    cols = [(255, 200, 110), (255, 160, 80), (255, 230, 170),
            (150, 190, 210), (255, 120, 90)]
    for _ in range(48):
        bx = rng.uniform(0, w)
        by = rng.uniform(0, h * 0.78)
        br = rng.uniform(16, 78)
        c = rng.choice(cols)
        a = rng.randint(38, 105)
        bd.ellipse([bx - br, by - br, bx + br, by + br], fill=c + (a,))
    bok = bok.filter(ImageFilter.GaussianBlur(7))
    img = img.convert("RGBA")
    img.alpha_composite(bok)
    return img.convert("RGB")


def capsule(d, x0, y0, x1, y1, wdt, fill):
    d.line([(x0, y0), (x1, y1)], fill=fill, width=int(wdt))
    r = wdt / 2
    for (x, y) in ((x0, y0), (x1, y1)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def draw_man(img, t, t_sec):
    """Hero walking toward camera; t in [0,1] across shot 3. Anchored at head."""
    d = ImageDraw.Draw(img, "RGBA")
    Ht = lerp(680, 2900, ease(t) ** 1.25)          # dolly-in
    phase = 2 * math.pi * 0.72 * t_sec              # slow-mo walk cycle
    cx = W / 2 + 14 * math.sin(phase * 0.5)
    yhead = H * 0.30 + 8 * math.sin(2 * phase) * (Ht / 1500)
    rh = Ht * 0.068

    jacket = (36, 33, 40, 255)
    pants = (30, 28, 34, 255)
    rim = (255, 168, 96, 110)
    y_sh = yhead + rh * 1.45
    y_hip = y_sh + Ht * 0.30
    sw = Ht * 0.125  # half shoulder width
    hw = Ht * 0.075  # half hip width

    def body_pass(off, torso_c, limb_c, head_c):
        ox, oy = off
        # legs
        for i, s in enumerate((-1, 1)):
            th_ = 0.30 * math.sin(phase + i * math.pi)
            hx = cx + s * hw * 0.6 + ox
            kx = hx + Ht * 0.24 * math.sin(th_)
            ky = y_hip + Ht * 0.24 * math.cos(th_) + oy
            bend = 0.35 * max(0.0, math.sin(phase + i * math.pi + 1.2))
            fx2 = kx + Ht * 0.24 * math.sin(th_ - bend)
            fy2 = ky + Ht * 0.24 * math.cos(th_ - bend)
            capsule(d, hx, y_hip + oy, kx, ky, Ht * 0.055, limb_c)
            capsule(d, kx, ky, fx2, fy2, Ht * 0.048, limb_c)
        # torso
        d.polygon([(cx - sw + ox, y_sh + oy), (cx + sw + ox, y_sh + oy),
                   (cx + hw + ox, y_hip + oy), (cx - hw + ox, y_hip + oy)],
                  fill=torso_c)
        d.ellipse([cx - sw + ox, y_sh - sw * 0.45 + oy,
                   cx + sw + ox, y_sh + sw * 0.55 + oy], fill=torso_c)
        # arms
        for i, s in enumerate((-1, 1)):
            th_ = 0.42 * math.sin(phase + (1 - i) * math.pi)
            ax0 = cx + s * sw * 0.92 + ox
            ay0 = y_sh + sw * 0.12 + oy
            ex = ax0 + Ht * 0.20 * math.sin(th_) * 0.6 + s * Ht * 0.015
            ey = ay0 + Ht * 0.20 * math.cos(th_)
            hx2 = ex + Ht * 0.18 * math.sin(th_ * 1.6) * 0.6
            hy2 = ey + Ht * 0.18 * math.cos(th_ * 0.5)
            capsule(d, ax0, ay0, ex, ey, Ht * 0.042, limb_c)
            capsule(d, ex, ey, hx2, hy2, Ht * 0.036, limb_c)
        # neck + head
        d.rectangle([cx - rh * 0.34 + ox, yhead + rh * 0.9 + oy,
                     cx + rh * 0.34 + ox, y_sh + oy], fill=head_c)
        d.ellipse([cx - rh + ox, yhead - rh * 1.28 + oy,
                   cx + rh + ox, yhead + rh * 1.12 + oy], fill=head_c)

    # warm rim-light pass (offset toward sun side), then main body
    body_pass((10 * (Ht / 1500) + 4, -3), rim, rim, rim)
    body_pass((0, 0), jacket, pants, (112, 78, 62, 255))

    # face lighting: warm crescent on camera-left (sun side)
    lit = (232, 158, 112, 150)
    d.ellipse([cx - rh, yhead - rh * 1.28, cx + rh, yhead + rh * 1.12], fill=(0, 0, 0, 0))
    d.ellipse([cx - rh, yhead - rh * 1.28, cx + rh, yhead + rh * 1.12],
              fill=(118, 82, 66, 255))
    d.ellipse([cx - rh * 0.62, yhead - rh * 1.24, cx + rh * 1.02, yhead + rh * 1.08],
              fill=lit)
    d.ellipse([cx - rh * 0.98, yhead - rh * 1.30, cx + rh * 0.62, yhead + rh * 1.02],
              fill=(118, 82, 66, 235))
    # hair
    d.chord([cx - rh, yhead - rh * 1.34, cx + rh, yhead + rh * 0.4],
            180, 360, fill=(28, 24, 26, 255))
    # glasses
    glw = rh * 0.78
    draw_glasses(d, cx, yhead + rh * 0.02, glw, max(3, glw * 0.10), tint=26)
    # lens specular
    d.line([(cx - glw * 0.9, yhead - glw * 0.16),
            (cx - glw * 0.35, yhead - glw * 0.30)],
           fill=(255, 240, 220, 170), width=max(2, int(glw * 0.05)))
    # subtle smile, late in the shot
    if t > 0.76:
        a = int(200 * ease((t - 0.76) / 0.2))
        d.arc([cx - rh * 0.34, yhead + rh * 0.30, cx + rh * 0.34, yhead + rh * 0.78],
              25, 155, fill=(245, 196, 160, a), width=max(2, int(rh * 0.07)))


# ------------------------------------------------------------------- overlays
def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W / 2) / (W * 0.72)
    dy = (yy - H / 2) / (H * 0.62)
    m = np.clip(1.0 - 0.42 * (dx * dx + dy * dy) ** 1.2, 0.45, 1.0)
    return m[..., None]


VIGNETTE = make_vignette()
GRAIN_RNG = np.random.default_rng(3)


def finish(img, grain=7.0, warm=None):
    a = np.asarray(img, dtype=np.float32)
    if warm:
        a[..., 0] *= warm[0]
        a[..., 1] *= warm[1]
        a[..., 2] *= warm[2]
    a *= VIGNETTE
    g = GRAIN_RNG.normal(0, grain, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    a += g
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def add_flare(img, strength, cx, cy):
    """Anamorphic-ish streak + glow."""
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fl)
    a = int(150 * strength)
    d.line([(cx - 620, cy + 60), (cx + 620, cy - 60)],
           fill=(255, 245, 225, a), width=8)
    d.line([(cx - 420, cy + 40), (cx + 420, cy - 40)],
           fill=(255, 250, 240, int(a * 0.8)), width=3)
    for r, aa in [(240, int(40 * strength)), (130, int(80 * strength))]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 240, 210, aa))
    for i, gr in enumerate([1.35, 1.9]):  # ghosts
        gx = cx + (W / 2 - cx) * gr + (W / 2 - cx)
        gy = cy + (H / 2 - cy) * gr + (H / 2 - cy)
        rr = 40 - i * 14
        d.ellipse([gx - rr, gy - rr, gx + rr, gy + rr],
                  fill=(255, 200, 150, int(45 * strength)))
    fl = fl.filter(ImageFilter.GaussianBlur(4))
    out = img.convert("RGBA")
    out.alpha_composite(fl)
    return out.convert("RGB")


# ------------------------------------------------------------------ rendering
def render_frames(only=None):
    print("building scenes...")
    city_big = build_city(W + 2 * MARGIN, H + 2 * MARGIN)
    city_big_blur = city_big.filter(ImageFilter.GaussianBlur(17))
    golden = build_golden(W, H)

    print("rendering frames...")
    for f in (only if only is not None else range(N_FRAMES)):
        t_sec = f / FPS
        if t_sec < 3.0:  # ---------------------------------------- shot 1
            t = t_sec / 3.0
            sx = MARGIN + 14 * math.sin(1.3 * t_sec * 2.1)
            sy = MARGIN + 10 * math.sin(1.7 * t_sec * 2.1 + 1.0)
            frame = city_big_blur.crop((int(sx), int(sy), int(sx) + W, int(sy) + H))
            frame = ImageEnhance.Color(frame).enhance(0.72)
            frame = ImageEnhance.Brightness(frame).enhance(1.02)
            # hand + glasses layer (near-field, slightly out of focus)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            tt = ease(t)
            gy = lerp(H * 1.25, H * 0.52, tt)
            gx = lerp(W * 0.62, W * 0.50, tt)
            lw = lerp(210, 300, tt)
            draw_hand(ld, gx, gy, lw)
            draw_glasses(ld, gx, gy, lw, lw * 0.09)
            layer = layer.filter(ImageFilter.GaussianBlur(6))
            frame = frame.convert("RGBA")
            frame.alpha_composite(layer)
            frame = frame.convert("RGB")
            frame = finish(frame, grain=8.0)

        elif t_sec < 5.0:  # -------------------------------------- shot 2
            t = (t_sec - 3.0) / 2.0
            snap = (SNAP_T - 3.0) / 2.0  # snap moment in local t
            base = city_big.crop((MARGIN, MARGIN, MARGIN + W, MARGIN + H))
            if t < snap:
                blur_r = lerp(17, 9, t / snap)
                sat = lerp(0.72, 0.80, t / snap)
            else:
                k = ease((t - snap) / 0.06)
                blur_r = lerp(9, 0, k)
                sat = lerp(0.80, 1.30, ease((t - snap) / 0.18))
            frame = base.filter(ImageFilter.GaussianBlur(blur_r)) if blur_r > 0.3 else base.copy()
            frame = ImageEnhance.Color(frame).enhance(sat)
            frame = ImageEnhance.Brightness(frame).enhance(lerp(1.0, 1.07, ease((t - snap) / 0.25)) if t > snap else 1.0)
            frame = ImageEnhance.Contrast(frame).enhance(lerp(1.0, 1.08, ease((t - snap) / 0.25)) if t > snap else 1.0)
            # glasses frame flying past the camera onto the face
            scale_t = ease(min(t / 0.78, 1.0))
            lw = lerp(300, 1650, scale_t)
            if lw < 1500:
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                gy = lerp(H * 0.52, H * 0.50, scale_t)
                draw_glasses(ld, W * 0.5, gy, lw, lw * 0.085, tint=10)
                layer = layer.filter(ImageFilter.GaussianBlur(lerp(2, 12, scale_t)))
                # fade out as it "reaches the face"
                if scale_t > 0.62:
                    alpha = layer.getchannel("A").point(
                        lambda v: int(v * clamp(1 - (scale_t - 0.62) / 0.34)))
                    layer.putalpha(alpha)
                frame = frame.convert("RGBA")
                frame.alpha_composite(layer)
                frame = frame.convert("RGB")
            # sun flare after the snap
            if t > snap:
                fs = math.sin(min((t - snap) / 0.3, 1.0) * math.pi)
                frame = add_flare(frame, 0.85 * fs + 0.1, W * 0.76, H * 0.145)
            frame = finish(frame, grain=6.0)

        else:  # ---------------------------------------------------- shot 3
            t = (t_sec - 5.0) / 5.0
            zoom = 1.0 + 0.06 * t
            zw, zh = int(W * zoom), int(H * zoom)
            bg = golden.resize((zw, zh), Image.LANCZOS)
            frame = bg.crop(((zw - W) // 2, (zh - H) // 2,
                             (zw - W) // 2 + W, (zh - H) // 2 + H)).convert("RGBA")
            draw_man(frame, t, t_sec)
            frame = frame.convert("RGB")
            if t > 0.55:
                fs = 0.35 * math.sin(min((t - 0.55) / 0.45, 1.0) * math.pi)
                frame = add_flare(frame, fs, W * 0.30, H * 0.52)
            frame = finish(frame, grain=6.5, warm=(1.06, 1.0, 0.92))

        frame.save(os.path.join(FRAMES_DIR, f"{f:04d}.png"))
        if f % 30 == 0:
            print(f"  frame {f}/{N_FRAMES}")
    print("frames done.")


# ---------------------------------------------------------------------- audio
SR = 44100


def fft_lowpass(x, cutoff, roll=1.0):
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    gain = 1.0 / (1.0 + (freqs / cutoff) ** (4 * roll))
    return np.fft.irfft(X * gain, len(x))


def fft_highpass(x, cutoff):
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    gain = 1.0 - 1.0 / (1.0 + (freqs / cutoff) ** 4)
    return np.fft.irfft(X * gain, len(x))


def add_at(buf, i0, sig):
    """Add sig into buf starting at i0, clipping at the buffer end."""
    m = min(len(sig), len(buf) - i0)
    if m > 0:
        buf[i0:i0 + m] += sig[:m]


def synth_audio(path):
    print("synthesizing audio...")
    n = int(SR * DUR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(11)

    # pink-ish city ambience
    white = rng.normal(0, 1, n)
    Xw = np.fft.rfft(white)
    fr = np.fft.rfftfreq(n, 1 / SR)
    pink = np.fft.irfft(Xw / np.sqrt(fr + 1.0), n)
    pink /= np.abs(pink).max()
    # traffic rumble
    rumble = 0.5 * np.sin(2 * np.pi * 62 * t + 3 * np.sin(2 * np.pi * 0.23 * t))
    rumble *= 0.4 + 0.25 * np.sin(2 * np.pi * 0.11 * t + 1.0)
    amb_src = 0.8 * pink + 0.5 * fft_lowpass(rumble, 140)

    muffled = fft_lowpass(amb_src, 550)
    muffled /= max(1e-9, np.abs(muffled).max())
    crisp = fft_lowpass(amb_src, 9500)
    crisp /= max(1e-9, np.abs(crisp).max())

    # crossfade at the snap
    xfade = np.clip((t - SNAP_T) / 0.12, 0, 1)
    amb = muffled * (1 - xfade) * 0.55 + crisp * xfade * 0.38
    # ambience ducks under the music
    duck = 1.0 - 0.55 * np.clip((t - 5.0) / 1.5, 0, 1)
    amb *= duck

    # the click
    click = np.zeros(n)
    ci = int(SNAP_T * SR)
    dur_c = int(0.035 * SR)
    ct = np.arange(dur_c) / SR
    burst = rng.normal(0, 1, dur_c) * np.exp(-ct * 320)
    tone = np.sin(2 * np.pi * 1700 * ct) * np.exp(-ct * 160)
    click[ci:ci + dur_c] += 0.9 * fft_highpass(
        np.pad(0.5 * burst + 0.8 * tone, (0, 0)), 900)[:dur_c]

    # music from 5s — minimal upbeat electronic
    music = np.zeros(n)
    bpm = 112
    beat = 60.0 / bpm
    start = 5.0
    # kick
    b = start
    while b < DUR - 0.05:
        i0 = int(b * SR)
        kd = int(0.16 * SR)
        kt = np.arange(kd) / SR
        f0 = 130 * np.exp(-kt * 26) + 44
        ph = 2 * np.pi * np.cumsum(f0) / SR
        add_at(music, i0, 0.85 * np.sin(ph) * np.exp(-kt * 15))
        b += beat
    # hats on offbeats
    b = start + beat / 2
    while b < DUR - 0.03:
        i0 = int(b * SR)
        hd = int(0.03 * SR)
        ht = np.arange(hd) / SR
        add_at(music, i0, 0.16 * fft_highpass(
            rng.normal(0, 1, hd) * np.exp(-ht * 220), 6000))
        b += beat
    # arp — A minor pentatonic, rising
    notes = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25]
    step = beat / 4
    k = 0
    b = start
    while b < DUR - 0.02:
        i0 = int(b * SR)
        nd = int(step * 0.9 * SR)
        nt = np.arange(nd) / SR
        f = notes[min(k % 8 if k % 8 < len(notes) else 14 - k % 8, len(notes) - 1)]
        saw = sum(np.sin(2 * np.pi * f * h * nt) / h for h in range(1, 5))
        env = np.minimum(nt / 0.01, 1) * np.exp(-nt * 9)
        add_at(music, i0, 0.20 * saw * env)
        k += 1
        b += step
    # warm pad
    pad_env = np.clip((t - 5.0) / 2.5, 0, 1) * 0.14
    music += pad_env * (np.sin(2 * np.pi * 110 * t) + 0.6 * np.sin(2 * np.pi * 164.8 * t))
    music = fft_lowpass(music, 9000)
    music *= np.clip((t - 5.0) / 2.0, 0, 1) * 0.9  # rise

    mix = amb + click + music
    # gentle fades at the very ends
    fade = int(0.15 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.1) * 0.88
    pcm = (mix * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm]).ravel()
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo.tobytes())
    print("audio done.")


# --------------------------------------------------------------------- encode
def encode(mp4_path, wav_path):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y",
           "-framerate", str(FPS), "-i", os.path.join(FRAMES_DIR, "%04d.png"),
           "-i", wav_path,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-shortest", mp4_path]
    print("encoding:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("wrote", mp4_path)


if __name__ == "__main__":
    render_frames()
    wav = os.path.join(OUT_DIR, "soundtrack.wav")
    synth_audio(wav)
    encode(os.path.join(OUT_DIR, "eyewear-commercial.mp4"), wav)
