#!/usr/bin/env python3
"""Seal pup hugging a plush fish -- 3D PIXAR STYLE (v9).

Entry for make.fun bounty "Make the cutest picture" (cutest-picture-01),
ninth entry (v9). Same subject and pattern as v7/v8: a cream-white BABY
SEAL hugging a TEAL PLUSH FISH toy, peach knitted beanie with pom-pom,
giant glossy blue eyes. The user ordered (10:26 WIB): "V8 seal ubah
menjadi 3d pixar style" -- change the v8 seal into 3D Pixar style.

What the top-1 image taught me (studied closely before building):
* The eyes DOMINATE the face: huge, wet, layered irises (dark rim,
  blue striations, light inner ring), a big black pupil, one large
  catchlight plus small sparkles, a dark upper-lid arc like eyeliner,
  and a bright lower lid rim. The eyes are the whole character.
* The head is OVERSIZED and perfectly round -- Pixar proportions:
  giant head, tiny body, big paws with pink toe beans.
* Fur is dense, soft and volumetric: every form is covered in fine
  directional strokes that follow the curvature, lit on the upper-left,
  warm in shadow -- and the strokes BLEND into each other, so no
  single stroke is visible. The surface reads like rendered fur, not
  like drawn lines.
* Subsurface scattering: light bleeds through the fur at the shadow
  edge as a warm pink glow, and the lit side has a soft warm bloom.
* Forms are spheres with smooth gradients -- no flat fills anywhere,
  no hard outlines. The subject sits on a floor with a soft ground
  shadow; the warm background falls off gently behind it.
* The knitted accessory is soft chunky loops: highlight on top of
  each stitch, shadow underneath.

v9 pushes the toolkit toward all of that, past v8:
* fur_flow_pixar(): SHORTER, FINER, DENSER strokes (more of them,
  lower alpha) plus a fur_soft_veil() pass that blends the strokes
  into a smooth coat -- v8's strokes were still visible as fine
  lines; v9's must melt together.
* sphere_light_pixar(): the spherical light model plus a warm pink
  subsurface glow on the shadow rim and a warm bloom on the lit side.
* Bigger, wetter eyes: larger ellipses, a second catchlight, a soft
  wet reflection arc on the iris, a stronger lid arc, brighter lower
  rim.
* The muzzle is a VOLUME now: shaded cheek puffs, fur over the
  muzzle, a soft shadow under the nose -- v8's middle of the face
  was flat white; v9 gives it shading and fur.
* Bigger head (Pixar proportions), pink toe beans on the hind
  flippers (like the top-1 paws), a warm studio spotlight behind
  the head.

The concept stays different from top-1 (seal + plush fish, not
kitten + chick) -- different subject, different toy, different
accessory.

Pure Python 3.13 standard library: no PIL, no network, no model
calls, no clock, no unseeded randomness. Fur strokes use a
deterministic sin-hash, so two runs write byte-identical output.

Rendering notes: the canvas is three byte planes (R, G, B) at 2x
supersampling (2048x2048). Translucent spans blend with
bytes.translate() and per-colour lookup tables, which runs in C and
keeps the render fast. Soft radial shapes are approximated by
horizontal constant-alpha bands. The 2x canvas is downsampled 2x2 to
1024x1024, then encoded as a PNG with zlib (filter 0 per row) written
by hand with struct + crc32.
"""

import math
import os
import struct
import zlib

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

OUT_NAME = "entry.png"
SIZE = 1024            # final image is SIZE x SIZE
SS = 2                 # supersampling factor
W2 = SIZE * SS         # internal canvas width/height

# --------------------------------------------------------------------------
# Palette -- cream-white baby seal, blue eyes, peach knitted beanie,
# teal plush fish, warm cream studio background with a floor.
# New in v9: subsurface pink (SSS), warm bloom, deeper blush, pink
# toe beans.
# --------------------------------------------------------------------------

BG_TOP = (250, 234, 216)
BG_MID = (253, 230, 208)
BG_BOT = (240, 204, 186)
FLOOR = (234, 198, 180)
GLOW = (255, 246, 230)
GROUND_SHADOW = (146, 102, 82)
GROUND_CORE = (120, 78, 60)

FUR = (255, 251, 244)        # cream-white seal fur
FUR_LIGHT = (255, 255, 255)
FUR_MID = (247, 232, 210)    # mid-tone fur for shaded fur strokes
FUR_SHADE = (234, 209, 183)   # warm shade of the fur
FUR_DEEP = (210, 176, 146)    # deeper shade for contact shadows
FUR_DARK = (188, 150, 120)    # darkest fur shade (deep occlusion)
SSS = (255, 198, 188)         # subsurface pink glow at the shadow rim
BLOOM = (255, 236, 216)       # warm bloom on the lit side
MUZZLE = (255, 242, 228)      # soft muzzle tint
NOSE = (70, 62, 66)
NOSE_DARK = (48, 42, 46)
MOUTH = (150, 92, 74)         # soft brown mouth/whisker colour
BLUSH = (255, 148, 166)
BLUSH_DEEP = (250, 128, 150)
IRIS_RING = (24, 70, 148)
IRIS = (62, 130, 208)
IRIS_DARK = (38, 94, 176)
IRIS_LIGHT = (152, 200, 244)
PUPIL = (16, 16, 28)
WHITE = (255, 255, 255)
# Knitted beanie hat (peach/coral).
HAT = (255, 172, 142)
HAT_LIGHT = (255, 202, 178)
HAT_DARK = (236, 132, 100)
HAT_DEEP = (212, 102, 72)
FISH = (116, 192, 203)        # soft teal plush fish
FISH_LIGHT = (170, 224, 230)
FISH_SHADE = (74, 148, 164)
FISH_DEEP = (52, 118, 134)
FISH_BELLY = (206, 239, 239)
THREAD = (255, 246, 224)      # cream stitching thread
BUTTON = (48, 48, 60)         # plush button eye
TOE = (255, 178, 196)         # pink toe beans
TOE_LIGHT = (255, 205, 218)
VIGNETTE = (228, 190, 170)
HEART = (255, 170, 190)


# --------------------------------------------------------------------------
# Canvas: three byte planes, all coordinates in logical 1024-space
# --------------------------------------------------------------------------

_TABLE_CACHE = {}


def _blend_tables(rgb, alpha):
    """Per-colour translate tables for one (colour, alpha) pair, cached."""
    key = (rgb[0], rgb[1], rgb[2], round(alpha, 2))
    tables = _TABLE_CACHE.get(key)
    if tables is None:
        inv = 1.0 - alpha
        tables = tuple(
            bytes(min(255, int(src * alpha + d * inv + 0.5))
                  for d in range(256))
            for src in rgb)
        _TABLE_CACHE[key] = tables
    return tables


class Canvas:
    def __init__(self, size, ss):
        self.size = size
        self.ss = ss
        self.w = size * ss
        self.h = size * ss
        n = self.w * self.h
        self.planes = [bytearray(n), bytearray(n), bytearray(n)]

    def _sx(self, x):
        return int(round(x * self.ss))

    def span(self, y, x0, x1, rgb):
        """Opaque fill of [x0, x1) on row y (logical coords)."""
        yi = self._sx(y)
        if yi < 0 or yi >= self.h:
            return
        a = max(0, self._sx(x0))
        b = min(self.w, self._sx(x1))
        if b <= a:
            return
        base = yi * self.w
        for ch in range(3):
            self.planes[ch][base + a:base + b] = bytes([rgb[ch]]) * (b - a)

    def blend_span(self, y, x0, x1, rgb, alpha):
        """Translucent fill of [x0, x1) on row y, C-speed via translate."""
        yi = self._sx(y)
        if yi < 0 or yi >= self.h or alpha <= 0.0:
            return
        a = max(0, self._sx(x0))
        b = min(self.w, self._sx(x1))
        if b <= a:
            return
        if alpha >= 1.0:
            self.span(y, x0, x1, rgb)
            return
        base = yi * self.w
        tables = _blend_tables(rgb, alpha)
        for ch in range(3):
            pl = self.planes[ch]
            pl[base + a:base + b] = pl[base + a:base + b].translate(tables[ch])

    def ellipse(self, cx, cy, rx, ry, rgb, alpha=1.0):
        if rx <= 0 or ry <= 0:
            return
        cx2, cy2, rx2, ry2 = cx * self.ss, cy * self.ss, rx * self.ss, ry * self.ss
        y0 = max(0, int(math.floor(cy2 - ry2)))
        y1 = min(self.h - 1, int(math.ceil(cy2 + ry2)))
        for yi in range(y0, y1 + 1):
            dy = (yi + 0.5 - cy2) / ry2
            if abs(dy) >= 1.0:
                continue
            dx = rx2 * math.sqrt(1.0 - dy * dy)
            x0 = (cx2 - dx) / self.ss
            x1 = (cx2 + dx) / self.ss
            if alpha >= 1.0:
                self.span(yi / self.ss, x0, x1, rgb)
            else:
                self.blend_span(yi / self.ss, x0, x1, rgb, alpha)

    def circle(self, cx, cy, r, rgb, alpha=1.0):
        self.ellipse(cx, cy, r, r, rgb, alpha)

    def soft_ellipse(self, cx, cy, rx, ry, rgb, a0, bands=20):
        """Radial-gradient ellipse: alpha falls from a0 at the centre to
        0 at the edge, approximated with horizontal constant-alpha bands."""
        if rx <= 0 or ry <= 0 or a0 <= 0.0:
            return
        cx2, cy2, rx2, ry2 = cx * self.ss, cy * self.ss, rx * self.ss, ry * self.ss
        y0 = max(0, int(math.floor(cy2 - ry2)))
        y1 = min(self.h - 1, int(math.ceil(cy2 + ry2)))
        for yi in range(y0, y1 + 1):
            dy = (yi + 0.5 - cy2) / ry2
            if abs(dy) >= 1.0:
                continue
            dx = rx2 * math.sqrt(1.0 - dy * dy)
            span_w = 2.0 * dx / self.ss
            if span_w <= 0:
                continue
            step = span_w / bands
            for i in range(bands):
                bx0 = (cx2 - dx) / self.ss + i * step
                bx1 = bx0 + step
                mid = (bx0 + bx1) / 2.0
                tx = ((mid - cx) / rx) ** 2 + dy * dy
                a = a0 * max(0.0, 1.0 - tx)
                if a > 0.01:
                    self.blend_span(yi / self.ss, bx0, bx1, rgb, a)

    def polygon(self, pts, rgb, alpha=1.0):
        """Filled polygon via scanline spans."""
        if len(pts) < 3:
            return
        pts2 = [(x * self.ss, y * self.ss) for (x, y) in pts]
        ys = [p[1] for p in pts2]
        y0 = max(0, int(math.floor(min(ys))))
        y1 = min(self.h - 1, int(math.ceil(max(ys))))
        n = len(pts2)
        for yi in range(y0, y1 + 1):
            yc = yi + 0.5
            xs = []
            for i in range(n):
                x1, yy1 = pts2[i]
                x2, yy2 = pts2[(i + 1) % n]
                if yy1 == yy2:
                    continue
                lo, hi = (yy1, yy2) if yy1 < yy2 else (yy2, yy1)
                if lo <= yc < hi:
                    t = (yc - yy1) / (yy2 - yy1)
                    xs.append(x1 + t * (x2 - x1))
            if len(xs) < 2:
                continue
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                x0 = xs[k] / self.ss
                x1 = xs[k + 1] / self.ss
                if alpha >= 1.0:
                    self.span(yi / self.ss, x0, x1, rgb)
                else:
                    self.blend_span(yi / self.ss, x0, x1, rgb, alpha)

    def thick_line(self, x1, y1, x2, y2, r, rgb, alpha=1.0):
        """Thick line as a chain of circles (round caps)."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        steps = max(1, int(dist / max(1.0, r * 0.7)) + 1)
        for i in range(steps + 1):
            t = i / steps
            self.circle(x1 + dx * t, y1 + dy * t, r, rgb, alpha)

    def bezier(self, p0, p1, p2, r, rgb, alpha=1.0, steps=24):
        prev = p0
        for i in range(1, steps + 1):
            t = i / steps
            mt = 1.0 - t
            x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
            y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
            self.thick_line(prev[0], prev[1], x, y, r, rgb, alpha)
            prev = (x, y)

    def vgrad(self, y0, y1, top, mid, bot):
        """Two-segment vertical gradient, opaque, full width."""
        for yi in range(self._sx(y0), self._sx(y1)):
            y = yi / self.ss
            if y <= (y0 + y1) / 2.0:
                t = (y - y0) / max(1.0, (y1 - y0) / 2.0)
                c = tuple(int(top[i] + (mid[i] - top[i]) * t) for i in range(3))
            else:
                t = (y - (y0 + y1) / 2.0) / max(1.0, (y1 - y0) / 2.0)
                c = tuple(int(mid[i] + (bot[i] - mid[i]) * t) for i in range(3))
            self.span(y, 0, self.size, c)


# --------------------------------------------------------------------------
# Downsample (2x2 box average) and PNG encoding
# --------------------------------------------------------------------------

def _avg2(a, b, c, d):
    """Average four bytes of one channel across a 2x2 block."""
    return bytes((x + y + z + w) // 4 for x, y, z, w in zip(a, b, c, d))


def downsample(canvas):
    """Return the final 1024x1024 RGB bytes from the 2x canvas."""
    w2, h2 = canvas.w, canvas.h
    w, h = w2 // SS, h2 // SS
    out = bytearray(w * h * 3)
    for y in range(h):
        r0 = [canvas.planes[ch][(2 * y) * w2:(2 * y + 1) * w2] for ch in range(3)]
        r1 = [canvas.planes[ch][(2 * y + 1) * w2:(2 * y + 2) * w2] for ch in range(3)]
        rows = []
        for ch in range(3):
            a, b = r0[ch][0::2], r0[ch][1::2]
            c, d = r1[ch][0::2], r1[ch][1::2]
            rows.append(_avg2(a, b, c, d))
        row = bytearray(w * 3)
        row[0::3] = rows[0]
        row[1::3] = rows[1]
        row[2::3] = rows[2]
        out[y * w * 3:(y + 1) * w * 3] = row
    return bytes(out)


def write_png(path, w, h, rgb):
    """Write RGB bytes as a whole, valid PNG (filter 0, zlib level 6)."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 6)

    def chunk(tag, payload):
        c = struct.pack(">I", len(payload)) + tag + payload
        return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", data)
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# --------------------------------------------------------------------------
# Deterministic helpers -- Pixar fur and light
# --------------------------------------------------------------------------

def _hash01(n):
    """Deterministic pseudo-random in [0, 1) from an integer (sin hash,
    not a random generator -- two runs are byte-identical)."""
    x = math.sin(n * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def fur_rim(cv, cx, cy, rx, ry, n, rgb, alpha, seed=0, out=12.0):
    """Fluffy silhouette: n short strokes straddling an elliptical rim,
    oriented radially outward. Deterministic via _hash01. The strokes
    break the hard vector edge so fur forms read soft and fluffy."""
    for k in range(n):
        h1 = _hash01(k * 3 + seed)
        h2 = _hash01(k * 7 + seed + 1)
        h3 = _hash01(k * 11 + seed + 2)
        ang = h1 * 2.0 * math.pi
        rr = 0.94 + 0.10 * h2
        x0 = cx + math.cos(ang) * rx * rr
        y0 = cy + math.sin(ang) * ry * rr
        x1 = cx + math.cos(ang) * (rx * rr + out * (0.5 + h3))
        y1 = cy + math.sin(ang) * (ry * rr + out * (0.5 + h3))
        cv.thick_line(x0, y0, x1, y1, 2.0 + 2.5 * h3, rgb,
                      alpha * (0.55 + 0.45 * h2))


def fur_stipple(cv, cx, cy, rx0, ry0, rx1, ry1, n, rgb, alpha, seed=0):
    """Soft fur dots scattered in an elliptical band around (cx, cy)."""
    for k in range(n):
        h1 = _hash01(k * 3 + seed)
        h2 = _hash01(k * 7 + seed + 1)
        h3 = _hash01(k * 11 + seed + 2)
        ang = h1 * 2.0 * math.pi
        rx = rx0 + (rx1 - rx0) * h2
        ry = ry0 + (ry1 - ry0) * h2
        x = cx + math.cos(ang) * rx
        y = cy + math.sin(ang) * ry
        cv.circle(x, y, 2.5 + 3.5 * h3, rgb, alpha)


def fur_flow_pixar(cv, cx, cy, rx, ry, n, seed=0, alpha=0.16,
                   lit_ang=3.93, len_min=6.0, len_max=13.0):
    """Pixar fur: SHORTER, FINER, DENSER strokes than v8. n short
    strokes start inside the form and run radially outward, following
    the form's curvature like combed fur. Strokes pointing toward the
    key light (upper-left, lit_ang) are drawn bright; strokes on the
    shadow side are drawn in mid/shade fur, so the fur itself carries
    the light model. Stroke length grows toward the rim, where the fur
    is longest and densest. Thin strokes at low alpha melt into each
    other instead of reading as separate lines -- the rendered-fur
    look. Deterministic via _hash01."""
    lx, ly = math.cos(lit_ang), math.sin(lit_ang)
    for k in range(n):
        h1 = _hash01(k * 3 + seed)
        h2 = _hash01(k * 7 + seed + 1)
        h3 = _hash01(k * 11 + seed + 2)
        h4 = _hash01(k * 13 + seed + 3)
        ang = h1 * 2.0 * math.pi
        # Radius fraction: biased toward the rim (fur is densest there).
        rr = 0.40 + 0.60 * (h2 ** 0.6)
        dx, dy = math.cos(ang), math.sin(ang)
        x0 = cx + dx * rx * rr
        y0 = cy + dy * ry * rr
        # Stroke length grows with radius and varies per stroke.
        ln = len_min + (len_max - len_min) * (0.35 + 0.65 * h3) * rr
        x1 = x0 + dx * ln
        y1 = y0 + dy * ln
        # Lit side (dot with the light direction) vs shadow side.
        dot = dx * lx + dy * ly
        if dot > 0.15:
            rgb = FUR_LIGHT
            a = alpha * (0.75 + 0.25 * h4)
        elif dot < -0.15:
            rgb = FUR_MID if h4 > 0.35 else FUR_SHADE
            a = alpha * (0.6 + 0.4 * h4)
        else:
            rgb = FUR_LIGHT if h4 > 0.5 else FUR_MID
            a = alpha * 0.8
        cv.thick_line(x0, y0, x1, y1, 1.2 + 1.2 * h3, rgb, a)


def fur_soft_veil(cv, cx, cy, rx, ry, rgb, a0):
    """Blend pass: a soft radial veil of the base fur colour over a
    form, melting the individual fur strokes into one smooth coat.
    This is what turns 'drawn strokes' into 'rendered fur' -- the
    strokes underneath still give texture, but no single stroke
    stands out. Call AFTER fur_flow_pixar()."""
    cv.soft_ellipse(cx, cy, rx * 0.96, ry * 0.96, rgb, a0)
    cv.soft_ellipse(cx - rx * 0.15, cy - ry * 0.18, rx * 0.72, ry * 0.62,
                    FUR_LIGHT, a0 * 0.9)


def sphere_light_pixar(cv, cx, cy, rx, ry, light, shade, deep,
                       la=0.30, sa=0.32, da=0.20):
    """Spherical light model for one form, Pixar edition: a bright key
    light from the upper-left with a warm bloom, a warm shadow crescent
    on the lower-right, a deep occlusion at the base, a rim light along
    the top edge, AND a warm pink subsurface glow where the light
    bleeds through the fur at the shadow rim -- the SSS look that
    makes rendered fur read soft and alive. Call AFTER the form's
    flat fill, BEFORE the fur passes."""
    cv.soft_ellipse(cx - rx * 0.30, cy - ry * 0.36, rx * 0.72, ry * 0.62,
                    light, la)
    cv.soft_ellipse(cx - rx * 0.34, cy - ry * 0.40, rx * 0.55, ry * 0.46,
                    BLOOM, 0.20)
    cv.soft_ellipse(cx + rx * 0.22, cy + ry * 0.44, rx * 0.80, ry * 0.55,
                    shade, sa)
    cv.soft_ellipse(cx + rx * 0.10, cy + ry * 0.78, rx * 0.62, ry * 0.30,
                    deep, da)
    cv.soft_ellipse(cx - rx * 0.10, cy - ry * 0.88, rx * 0.70, ry * 0.22,
                    light, 0.22)
    # Subsurface glow: warm pink along the lower-right rim, where the
    # key light passes through the fur.
    cv.soft_ellipse(cx + rx * 0.62, cy + ry * 0.30, rx * 0.34, ry * 0.52,
                    SSS, 0.20)
    cv.soft_ellipse(cx + rx * 0.30, cy + ry * 0.72, rx * 0.50, ry * 0.26,
                    SSS, 0.16)


def _chevron(cv, x, y, s, rgb, alpha=1.0):
    """One knit V-stitch: two short diagonal strokes meeting at the
    bottom point -- the classic chunky-knit texture."""
    cv.thick_line(x - s, y - s * 0.55, x, y + s * 0.55, 2.6, rgb, alpha)
    cv.thick_line(x, y + s * 0.55, x + s, y - s * 0.55, 2.6, rgb, alpha)


def _knit_stitch(cv, x, y, s):
    """One chunky knit stitch with depth: a dark V underneath, a light
    V offset up-left on top -- each stitch reads as a little 3D loop.
    Slightly softer than v8 (lower contrast) for the Pixar fabric."""
    _chevron(cv, x + 2, y + 2, s, HAT_DEEP, 0.75)
    _chevron(cv, x, y, s, HAT_DARK, 0.85)
    _chevron(cv, x - 2, y - 2, s * 0.82, HAT_LIGHT, 0.70)


def _heart(cv, cx, cy, s, rgb, alpha):
    """A tiny soft heart: two circles on top, a triangle below."""
    cv.circle(cx - s * 0.42, cy - s * 0.18, s * 0.48, rgb, alpha)
    cv.circle(cx + s * 0.42, cy - s * 0.18, s * 0.48, rgb, alpha)
    cv.polygon([(cx - s * 0.85, cy - s * 0.05),
                (cx + s * 0.85, cy - s * 0.05),
                (cx, cy + s * 0.95)], rgb, alpha)


# --------------------------------------------------------------------------
# Scene: a baby seal pup hugging a plush fish -- 3D PIXAR STYLE (v9)
# --------------------------------------------------------------------------
# Same subject and pattern as v7/v8 (baby seal + plush fish toy, peach
# beanie, giant blue eyes), rebuilt so the RENDERING reads as a Pixar
# 3D animated character: bigger head (Pixar proportions), bigger and
# wetter eyes, finer/denser/blended fur with a soft veil, subsurface
# pink glow, a muzzle that is a volume (not flat white), pink toe
# beans on the hind flippers, warm studio spotlight. The flippers
# keep wrapping the fish so the hug reads.
# --------------------------------------------------------------------------

HEAD = (512, 418)      # seal head centre (face-forward portrait)
HEAD_R = 208           # Pixar proportions: oversized round head
BODY = (512, 734)      # body centre
BODY_RX, BODY_RY = 262, 184


def draw_background(cv):
    # Warm cream studio: vertical gradient, a soft floor tone at the
    # bottom, a warm studio spotlight behind the subject, a two-layer
    # ground shadow the body sits on, soft vignette corners, a few
    # sea-theme bubbles and one tiny heart.
    cv.vgrad(0, SIZE, BG_TOP, BG_MID, BG_BOT)
    cv.soft_ellipse(512, 1060, 820, 210, FLOOR, 0.32)
    cv.soft_ellipse(512, 460, 480, 430, GLOW, 0.45)
    cv.soft_ellipse(512, 952, 340, 28, GROUND_SHADOW, 0.30)
    cv.soft_ellipse(512, 950, 230, 16, GROUND_CORE, 0.26)
    for (vx, vy) in ((0, 0), (SIZE, 0), (0, SIZE), (SIZE, SIZE)):
        cv.soft_ellipse(vx, vy, 380, 380, VIGNETTE, 0.14)
    for (bx, by, br, ba) in ((150, 170, 20, 0.30), (205, 110, 12, 0.38),
                             (120, 260, 9, 0.30), (880, 150, 16, 0.32),
                             (930, 230, 10, 0.28), (845, 90, 8, 0.35),
                             (255, 210, 7, 0.28)):
        cv.circle(bx, by, br, WHITE, ba)
        cv.circle(bx - br * 0.3, by - br * 0.35, br * 0.28, WHITE, ba + 0.25)
    _heart(cv, 905, 320, 18, HEART, 0.28)


def draw_body(cv):
    # Plump seated seal body as a VOLUME: shade rim, cream fill, a
    # Pixar spherical light model (key light + warm bloom + subsurface
    # pink glow), a lighter belly patch with its own shading, fine
    # dense fur flowing over the whole form, a soft veil that melts
    # the strokes into a smooth coat, and a dense fluffy rim.
    cx, cy = BODY
    cv.ellipse(cx, cy, BODY_RX + 8, BODY_RY + 8, FUR_SHADE, 0.55)
    cv.ellipse(cx, cy, BODY_RX, BODY_RY, FUR)
    sphere_light_pixar(cv, cx, cy, BODY_RX, BODY_RY, FUR_LIGHT,
                       FUR_SHADE, FUR_DEEP, 0.30, 0.36, 0.22)
    # Belly patch: lighter, with its own soft light and shade so the
    # belly reads as a second rounded volume on the body.
    cv.ellipse(cx, cy + 42, 168, 108, FUR_LIGHT, 0.45)
    cv.soft_ellipse(cx - 40, cy - 10, 120, 55, WHITE, 0.16)
    cv.soft_ellipse(cx + 50, cy + 110, 130, 55, FUR_SHADE, 0.22)
    # Fine dense Pixar fur over the whole body, then the soft veil
    # that blends it, then a dense fluffy rim.
    fur_flow_pixar(cv, cx, cy, BODY_RX, BODY_RY, 600, seed=11,
                   alpha=0.16, len_max=13.0)
    fur_soft_veil(cv, cx, cy, BODY_RX, BODY_RY, FUR, 0.10)
    fur_rim(cv, cx, cy, BODY_RX, BODY_RY, 130, FUR_LIGHT, 0.30, 5, out=8.0)
    fur_rim(cv, cx, cy, BODY_RX + 2, BODY_RY + 2, 80, FUR_SHADE, 0.20, 6,
            out=7.0)
    fur_stipple(cv, cx, cy, 180, 110, 250, 175, 70, FUR_LIGHT, 0.22, 7)


def draw_hind_flippers(cv):
    # Two small hind flippers peeking out below the body, overlapping
    # its bottom edge, with soft shade, rim light, and PINK TOE BEANS
    # like the top-1 paws -- three small toes plus one big pad.
    for (fx, fy, sgn) in ((440, 912, -1), (584, 912, 1)):
        cv.ellipse(fx, fy, 68, 38, FUR_SHADE, 0.5)
        cv.ellipse(fx, fy, 62, 33, FUR)
        cv.soft_ellipse(fx, fy - 10, 46, 15, FUR_LIGHT, 0.30)
        cv.soft_ellipse(fx, fy + 18, 48, 13, FUR_SHADE, 0.16)
        fur_rim(cv, fx, fy, 62, 33, 18, FUR_LIGHT, 0.3, 23, out=5.0)
        # Pink toe beans at the bottom edge of the flipper.
        for dx in (-16, 0, 16):
            cv.ellipse(fx + dx, fy + 12, 6, 8, TOE, 0.95)
            cv.ellipse(fx + dx, fy + 11, 4, 5, TOE_LIGHT, 0.7)
        cv.ellipse(fx, fy + 22, 14, 9, TOE, 0.95)
        cv.ellipse(fx, fy + 21, 9, 6, TOE_LIGHT, 0.7)


def draw_head(cv):
    # Big soft round seal head as a SPHERE -- Pixar proportions: shade
    # rim, cream fill, Pixar spherical light (key light + warm bloom +
    # subsurface pink glow), directional fine fur flowing over the whole
    # face, a soft veil that blends the strokes, a dense fluffy rim
    # like the top-1 kitten's fuzzy outline, and a soft forehead light.
    cx, cy = HEAD
    cv.circle(cx, cy, HEAD_R + 8, FUR_SHADE, 0.5)
    cv.circle(cx, cy, HEAD_R, FUR)
    sphere_light_pixar(cv, cx, cy, HEAD_R, HEAD_R, FUR_LIGHT, FUR_SHADE,
                       FUR_DEEP, 0.32, 0.36, 0.22)
    cv.soft_ellipse(cx - 25, cy - 90, 120, 76, WHITE, 0.16)
    fur_flow_pixar(cv, cx, cy, HEAD_R, HEAD_R, 700, seed=21, alpha=0.16,
                   len_max=13.0)
    fur_soft_veil(cv, cx, cy, HEAD_R, HEAD_R, FUR, 0.10)
    fur_rim(cv, cx, cy, HEAD_R, HEAD_R, 210, FUR_LIGHT, 0.30, 1, out=9.0)
    fur_rim(cv, cx, cy, HEAD_R - 4, HEAD_R - 4, 110, FUR_SHADE, 0.18, 2,
            out=7.0)
    fur_stipple(cv, cx, cy, 130, 130, 182, 182, 90, FUR_LIGHT, 0.24, 3)


def draw_hat(cv):
    # Peach knitted beanie hat with a pom-pom. Dome over the top of
    # the head, a folded brim band with chunky 3D knit V-stitches, a
    # soft contact shadow where the brim meets the forehead, and a
    # fluffy cream pom-pom on top.
    arc = []
    for i in range(25):
        ang = math.pi - math.pi * i / 24.0
        arc.append((512 + 200 * math.cos(ang),
                    326 + 130 * math.sin(ang) * -1.0))
    bot = []
    for i in range(25):
        t = i / 24.0
        x = 312 + (712 - 312) * t
        y = 348 + 6 * math.sin(math.pi * t)
        bot.append((x, y))
    cv.polygon(arc + bot[::-1], HAT_DEEP, 0.55)
    cv.polygon([(x, y + 6) for (x, y) in arc] + bot[::-1], HAT)
    cv.soft_ellipse(440, 246, 110, 60, HAT_LIGHT, 0.35)
    cv.soft_ellipse(600, 296, 90, 50, HAT_DARK, 0.30)
    for (sy, xs) in ((241, range(400, 641, 48)), (286, range(360, 681, 48))):
        for k, x in enumerate(xs):
            _knit_stitch(cv, x, sy + (6 if k % 2 else -6), 9)
    brim_top = bot
    brim_bot = [(x, y + 34) for (x, y) in bot]
    cv.polygon(brim_top + brim_bot[::-1], HAT_LIGHT, 0.95)
    cv.polygon([(x, y + 34) for (x, y) in bot] +
               [(x, y + 44) for (x, y) in bot][::-1], HAT_DARK, 0.25)
    for k, x in enumerate(range(340, 701, 40)):
        _knit_stitch(cv, x, 368 + (5 if k % 2 else -5), 9)
    cv.soft_ellipse(512, 388, 180, 20, HAT_DEEP, 0.26)
    for k in range(14):
        ang = math.radians(k * 360.0 / 14.0)
        cv.circle(512 + math.cos(ang) * 30, 201 + math.sin(ang) * 30,
                  13, FUR)
    cv.circle(512, 201, 36, FUR)
    cv.soft_ellipse(500, 188, 24, 16, WHITE, 0.35)
    fur_stipple(cv, 512, 201, 10, 10, 32, 32, 26, WHITE, 0.4, 41)


def draw_eye(cv, cx, cy):
    # GIANT glossy BLUE eye -- the Pixar look, bigger and wetter than
    # v8: dark-blue outer ring (not black), white, striated blue iris,
    # light inner ring, big black pupil, a soft wet reflection arc on
    # the iris, one large catchlight + two small sparkles, a soft
    # upper-lid shadow with a STRONGER dark lid arc (the Pixar
    # eyeliner look), and a bright lower rim -- the wet glossy eye of
    # a 3D animated character.
    # Soft socket shadow grounds the eye in the fur; the dark ring
    # is kept faint so it reads as a lid shadow, not a hard outline.
    cv.soft_ellipse(cx, cy, 72, 90, FUR_DEEP, 0.12)
    cv.ellipse(cx, cy, 70, 88, IRIS_RING, 0.55)
    cv.ellipse(cx, cy, 66, 84, WHITE)
    cv.circle(cx + 4, cy - 2, 52, IRIS_RING)
    cv.circle(cx + 4, cy - 2, 48, IRIS)
    for k in range(24):
        ang = math.radians(k * 15)
        x0 = cx + 4 + math.cos(ang) * 13
        y0 = cy - 2 + math.sin(ang) * 13
        x1 = cx + 4 + math.cos(ang) * 46
        y1 = cy - 2 + math.sin(ang) * 46
        cv.thick_line(x0, y0, x1, y1, 1.8, IRIS_DARK, 0.45)
    cv.circle(cx + 4, cy - 2, 35, IRIS_LIGHT, 0.55)
    cv.circle(cx + 4, cy - 2, 32, IRIS, 0.35)
    cv.circle(cx + 4, cy - 2, 26, PUPIL)
    # Wet reflection arc across the top of the iris.
    cv.soft_ellipse(cx + 4, cy - 30, 30, 12, WHITE, 0.22)
    # Catchlights: one large upper-left, one medium lower-right, one
    # tiny glint at the bottom.
    cv.circle(cx - 15, cy - 30, 18, WHITE, 0.98)
    cv.circle(cx + 26, cy + 20, 7, WHITE, 0.92)
    cv.circle(cx - 2, cy + 36, 4, WHITE, 0.7)
    # Upper-lid shadow + a stronger dark lid arc above the eye.
    cv.soft_ellipse(cx, cy - 58, 64, 28, FUR_DEEP, 0.20)
    cv.bezier((cx - 56, cy - 62), (cx - 20, cy - 88), (cx + 56, cy - 62),
              3.5, MOUTH, 0.5)
    # Bright lower rim (glossy wet lower lid).
    cv.soft_ellipse(cx + 2, cy + 72, 48, 12, WHITE, 0.35)
    # Three soft lashes at the outer top corner only. The outer side
    # is away from the face centre (HEAD[0]).
    for (dx, dy, ln) in ((-50, -58, 16), (-57, -42, 14), (-59, -26, 12)):
        sgn = -1 if cx < HEAD[0] else 1
        cv.thick_line(cx + dx * sgn, cy + dy, cx + (dx - 8) * sgn,
                      cy + dy - ln, 3, MOUTH, 0.85)


def draw_face(cv):
    # The muzzle is a VOLUME now (v8's flat-white middle is fixed):
    # a soft tinted muzzle area, shaded cheek puffs on both sides,
    # fine fur flowing over the muzzle, then the eyes, nose, mouth,
    # blush and whiskers on top of it.
    cv.soft_ellipse(512, 542, 108, 64, MUZZLE, 0.5)
    cv.soft_ellipse(512, 556, 92, 48, MUZZLE, 0.4)
    for (px, sgn) in ((398, -1), (626, 1)):
        cv.soft_ellipse(px, 540, 58, 42, FUR_LIGHT, 0.30)
        cv.soft_ellipse(px + sgn * 8, 566, 50, 26, FUR_SHADE, 0.18)
    fur_flow_pixar(cv, 512, 542, 108, 62, 130, seed=51, alpha=0.14,
                   len_min=5.0, len_max=10.0)
    fur_soft_veil(cv, 512, 542, 108, 62, FUR, 0.08)
    draw_eye(cv, 420, 448)
    draw_eye(cv, 604, 448)
    # Little dark seal nose (small rounded triangle) with a highlight
    # and two nostril dots, then a soft "w" smile mouth in warm brown.
    nose = [(498, 512), (526, 512), (512, 530)]
    cv.polygon(nose, NOSE_DARK, 0.6)
    cv.polygon([(502, 514), (522, 514), (512, 526)], NOSE)
    cv.circle(506, 518, 3, WHITE, 0.85)
    cv.circle(504, 524, 2.2, NOSE_DARK, 0.8)
    cv.circle(520, 524, 2.2, NOSE_DARK, 0.8)
    cv.soft_ellipse(512, 536, 26, 8, FUR_SHADE, 0.18)
    cv.thick_line(512, 532, 512, 544, 2.6, MOUTH, 0.85)
    cv.bezier((512, 544), (501, 555), (491, 553), 2.6, MOUTH, 0.9)
    cv.bezier((512, 544), (523, 555), (533, 553), 2.6, MOUTH, 0.9)
    # Heavy rosy blush -- two soft layers so it reads even at small size.
    cv.soft_ellipse(356, 550, 46, 27, BLUSH, 0.55)
    cv.soft_ellipse(668, 550, 46, 27, BLUSH, 0.55)
    cv.soft_ellipse(356, 550, 29, 17, BLUSH_DEEP, 0.40)
    cv.soft_ellipse(668, 550, 29, 17, BLUSH_DEEP, 0.40)
    # Whiskers: seals have prominent whiskers -- thin translucent
    # lines fanning from the muzzle, plus tiny whisker dots.
    for (x0, y0, x1, y1) in ((452, 524, 372, 506), (452, 538, 372, 534),
                             (452, 552, 372, 562), (572, 524, 652, 506),
                             (572, 538, 652, 534), (572, 552, 652, 562)):
        cv.thick_line(x0, y0, x1, y1, 1.6, MOUTH, 0.35)
    for (dx, dy) in ((-58, 12), (-66, 26), (58, 12), (66, 26)):
        cv.circle(512 + dx, 536 + dy, 1.8, MOUTH, 0.45)


def draw_chin_shadow(cv):
    # The shadow the chin casts on the chest, just below the head --
    # the depth cue that separates head and body into two forms.
    cv.soft_ellipse(512, 640, 150, 30, FUR_DEEP, 0.20)


def draw_fish(cv):
    # The plush fish TOY, held at the seal's chest: a soft teal plush
    # body built from a parametric outline (blunt head, fat middle,
    # tapered tail), a forked tail fin, a dorsal fin, a lighter belly
    # band, a dashed STITCHED SEAM down the middle, a BUTTON EYE, and
    # fabric stipple -- every cue that says "toy", not "animal".
    # Spine from head (500, 612) to tail base (550, 792); tilt ~15 deg.
    hx, hy = 500.0, 612.0
    tx, ty = 550.0, 792.0
    dx, dy = tx - hx, ty - hy
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = uy, -ux  # normal (points to the fish's left)

    def spine(t):
        return (hx + ux * ln * t, hy + uy * ln * t)

    def width(t):
        # Ellipse-like profile: blunt head, fat at t~0.3, tapered tail.
        return 76.0 * math.sqrt(max(0.0, 1.0 - ((t - 0.30) / 0.72) ** 2))

    left, right = [], []
    for i in range(17):
        t = i / 16.0
        sx, sy = spine(t)
        w = width(t)
        left.append((sx + nx * w, sy + ny * w))
        right.append((sx - nx * w, sy - ny * w))
    # Soft contact shadow where the fish meets the seal's chest.
    cv.soft_ellipse(524, 702, 95, 135, FUR_DEEP, 0.20)
    # Tail fin: two triangles fanning from the tail base.
    bx, by = spine(1.0)
    tip1 = (bx + ux * 58 + nx * 42, by + uy * 58 + ny * 42)
    tip2 = (bx + ux * 58 - nx * 42, by + uy * 58 - ny * 42)
    mid = (bx + ux * 34, by + uy * 34)
    cv.polygon([(bx, by), tip1, mid], FISH_SHADE, 0.7)
    cv.polygon([(bx, by), mid, tip2], FISH_SHADE, 0.7)
    cv.polygon([(bx + ux * 4, by + uy * 4), tip1, mid], FISH, 0.9)
    cv.polygon([(bx + ux * 4, by + uy * 4), mid, tip2], FISH, 0.9)
    # Body fill: shade rim, then the teal plush.
    cv.polygon(left + right[::-1], FISH_SHADE, 0.6)
    inset_l = [(sx + nx * (w - 5), sy + ny * (w - 5))
               for (sx, sy), w in
               [(spine(i / 16.0), width(i / 16.0)) for i in range(17)]]
    inset_r = [(sx - nx * (w - 5), sy - ny * (w - 5))
               for (sx, sy), w in
               [(spine(i / 16.0), width(i / 16.0)) for i in range(17)]]
    cv.polygon(inset_l + inset_r[::-1], FISH)
    # Volumetric light/shade so the plush body reads as a soft volume,
    # plus a warm subsurface-style glow on the lit edge.
    lx, ly = spine(0.30)
    cv.soft_ellipse(lx + nx * 8, ly - 12, 48, 80, FISH_LIGHT, 0.42)
    sx2, sy2 = spine(0.70)
    cv.soft_ellipse(sx2 - nx * 10, sy2 + 10, 42, 68, FISH_SHADE, 0.32)
    # Lighter belly band along the lower side of the body.
    band_l, band_r = [], []
    for i in range(9):
        t = 0.15 + 0.75 * i / 8.0
        sx, sy = spine(t)
        w = width(t)
        band_l.append((sx - nx * w * 0.45, sy - ny * w * 0.45))
        band_r.append((sx - nx * w * 0.95, sy - ny * w * 0.95))
    cv.polygon(band_l + band_r[::-1], FISH_BELLY, 0.5)
    # Dorsal fin on the upper side, placed high (t 0.18-0.32) so its
    # tip pokes out above the right flipper and the fish silhouette
    # reads clearly as a fish, not a sock.
    d0x, d0y = spine(0.18)
    d1x, d1y = spine(0.32)
    cv.polygon([(d0x + nx * width(0.18), d0y + ny * width(0.18)),
                (d1x + nx * width(0.32), d1y + ny * width(0.32)),
                ((d0x + d1x) / 2 + nx * (width(0.25) + 42),
                 (d0y + d1y) / 2 + ny * (width(0.25) + 42) - 8)],
               FISH_SHADE, 0.8)
    # Stitched seam down the middle of the body: dashed cream thread.
    for i in range(10):
        t0 = 0.08 + i * 0.082
        t1 = t0 + 0.045
        x0, y0 = spine(t0)
        x1, y1 = spine(t1)
        cv.thick_line(x0, y0, x1, y1, 2.2, THREAD, 0.85)
    # Button eye on the fish head: dark button, white highlight, and a
    # tiny cream stitch cross at its top edge. Placed high (t=0.10) so
    # it stays clearly visible above the flippers.
    ex, ey = spine(0.10)
    ex, ey = ex + nx * 18, ey + ny * 18
    cv.circle(ex, ey, 14, BUTTON, 0.95)
    cv.circle(ex - 4, ey - 4, 4, WHITE, 0.95)
    cv.thick_line(ex - 6, ey - 15, ex + 6, ey - 8, 1.8, THREAD, 0.9)
    cv.thick_line(ex + 6, ey - 15, ex - 6, ey - 8, 1.8, THREAD, 0.9)
    # Fabric stipple across the body (inside the outline only).
    for k in range(46):
        t = 0.08 + 0.84 * _hash01(k * 3 + 91)
        s = (2.0 * _hash01(k * 7 + 92) - 1.0) * 0.62
        sx, sy = spine(t)
        w = width(t)
        cv.circle(sx + nx * w * s, sy + ny * w * s,
                  2.0 + 2.0 * _hash01(k * 11 + 93), FISH_SHADE, 0.22)


# Flipper polygons: big curved arms that sweep in from the body's
# sides and cross OVER the fish, tips pressing on its belly -- the
# hug. Each tip is rounded with a circle, has three soft toe lines,
# and casts a contact shadow on the fish beneath it.
FLIPPER_L = [(402, 638), (368, 655), (344, 690), (348, 728), (372, 752),
             (420, 754), (448, 746), (462, 724), (452, 696), (430, 666),
             (418, 650)]
FLIPPER_R = [(1024 - x, y) for (x, y) in FLIPPER_L]


def draw_flippers(cv):
    # Contact shadows on the fish where the flipper tips press it --
    # drawn first, so the flippers cover their inner half and only a
    # crescent of shadow shows around each tip.
    cv.soft_ellipse(462, 730, 34, 20, FISH_DEEP, 0.30)
    cv.soft_ellipse(562, 730, 34, 20, FISH_DEEP, 0.30)
    for (pts, tip, sgn) in ((FLIPPER_L, (456, 722), -1),
                            (FLIPPER_R, (568, 722), 1)):
        cv.polygon(pts, FUR_SHADE, 0.5)
        cv.polygon(pts, FUR)
        # Rounded tip.
        cv.circle(tip[0], tip[1], 24, FUR)
        # Volumetric light on top, shade underneath, so the arm reads
        # as a rounded volume, not a flat shape, plus a warm
        # subsurface glow on the tip's shadow edge.
        cv.soft_ellipse(tip[0] - sgn * 30, tip[1] - 18, 55, 20,
                        FUR_LIGHT, 0.28)
        cv.soft_ellipse(tip[0] - sgn * 20, tip[1] + 18, 55, 16,
                        FUR_SHADE, 0.20)
        cv.soft_ellipse(tip[0] + sgn * 14, tip[1] + 8, 26, 18, SSS, 0.16)
        # Directional fur only along the arm's outer edge (fur_flow
        # radiating from the tip would spill white strokes onto the
        # fish and hide the toy -- the rim alone keeps the arm fluffy).
        fur_rim(cv, tip[0] - sgn * 45, tip[1], 62, 34, 28, FUR_LIGHT,
                0.28, 32, out=5.0)
        # Three soft toe lines on the tip, pointing inward onto the fish.
        for dy in (-12, 0, 12):
            cv.thick_line(tip[0] - sgn * 8, tip[1] + dy,
                          tip[0] + sgn * 12, tip[1] + dy, 2.0, MOUTH, 0.45)
        # Thin shade line along the flipper's inner edge -- the crease
        # where the arm presses the fish.
        cv.thick_line(tip[0] - sgn * 26, tip[1] - 14,
                      tip[0] - sgn * 26, tip[1] + 14, 2.5, FUR_SHADE, 0.35)


def draw_scene(cv):
    draw_background(cv)
    draw_body(cv)
    draw_hind_flippers(cv)
    draw_head(cv)
    draw_hat(cv)
    draw_face(cv)
    draw_chin_shadow(cv)
    draw_fish(cv)
    draw_flippers(cv)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def render():
    cv = Canvas(SIZE, SS)
    draw_scene(cv)
    return downsample(cv)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, OUT_NAME)
    rgb = render()
    size = write_png(path, SIZE, SIZE, rgb)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
