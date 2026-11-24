#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0
"""Build assets/pic/Stella_logo_loading.svg from the JSON written by export_logo_c4d.py.

    python scripts/build_loading_logo.py <scene.json> [assets/pic/Stella_logo_loading.svg]

Needs numpy and Pillow. Every coordinate in the SVG comes from assets/model/CBHB.c4d:

  1. Project all geometry through the scene camera (pinhole, focal / sensor width).
  2. Rasterize the main star and the frame-0 companion at 4x, then take the outline by
     casting rays from the star's origin (a four-pointed star is star-shaped from its
     centre, so the outermost hit per ray is the silhouette).
  3. Build a z-buffer of the main star; the companion and orbit are "behind" where they
     overlap it and are farther from the camera.
  4. Emit SMIL. The companion keeps the white model's look (its frame-0 silhouette, i.e.
     the logo pose) but faces the camera instead of tumbling with the mesh; it is moved
     along the projected path and scaled by perspective depth only. A camera-style
     starburst sits on top: tapered diffraction spikes along the model's rays,
     fainter secondary spikes, and a slight twinkle. The comet tail is a ribbon traced by
     the companion itself: each point sits where the companion was a moment earlier and is
     as wide as the companion was then (perspective included), tapering to nothing at the
     end. It covers a fixed time window, so it stretches when the companion is fast and
     shrinks when it is slow. Front/back layering is switched per frame. One loop = the
     C4D frame range.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SUPERSAMPLE = 4
# companion starburst (lengths relative to the model's longest ray): diffraction spikes run
# along the four rays of the model, with fainter, shorter secondary spikes between them
SPIKE_LEN, SPIKE_WIDTH = 2.1, 0.06
SECONDARY_LEN, SECONDARY_WIDTH = 1.15, 0.04
TWINKLE_KEYS = 12   # twinkle flicker keyframes per loop (deterministic, seamless)
# comet tail ribbons: (id, time window in frames, head width / companion ray length, taper exponent)
TAIL_RIBBONS = (("st-trail-glow", 8, 0.75, 1.0), ("st-trail-core", 4.5, 0.3, 1.4))
TAIL_SAMPLES = 12   # points along each side of a ribbon
# main star breathing: each point extends / retracts by a fraction of its own length once per
# loop; the long pair (left, bottom) and the short pair (right, top) have separate amplitudes and
# run in opposite phase. The weight (r / tip)^exp keeps the centre still.
BREATH_LONG, BREATH_SHORT, BREATH_EXP = 0.10, 0.06, 2.0
# tones matched to assets/pic/Stella_logo_origin.jpg: pale warm-cream bodies, warm amber accents.
# No glow / halo around the stars: this is a loading decoration drawn over arbitrary page
# backgrounds, so nothing may tint the area around the shapes.
# Two palettes, switched in CSS (see THEME_CSS): "dark" is matched to the original logo; "light"
# deepens the same warm hue so the stars stay visible on light page backgrounds (#F5F7FA).
PALETTES = {
    "dark": {"body-inner": "#faf4d9", "body-mid": "#f9efcd", "body-tip": "#f3dea8",
             "accent": "#f0d8a2", "accent-deep": "#d6b47a", "white": "#fdf9e6"},
    "light": {"body-inner": "#e4b45c", "body-mid": "#d8a248", "body-tip": "#c4862c",
              "accent": "#dcae5c", "accent-deep": "#c18a35", "white": "#d49b3e"},
}


def fill(key: str) -> str:
    """Fill attribute (dark fallback, used if CSS is unavailable) plus the theme-switched class."""
    return f'fill="{PALETTES["dark"][key]}" class="st-f-{key}"'


def stop(key: str) -> str:
    return f'stop-color="{PALETTES["dark"][key]}" class="st-s-{key}"'


def theme_css() -> str:
    """Palette as CSS variables on the logo root. Order of precedence: data-theme attribute on the
    <svg> (set by an app with its own theme switch; needs the SVG inlined), then the system
    preference (also works when the file is loaded through <img>), then dark."""
    def vars_(name):
        return " ".join(f"--st-{k}: {v};" for k, v in PALETTES[name].items())
    keys = PALETTES["dark"]
    rules = [f".stella-loader {{ {vars_('dark')} }}",
             f"@media (prefers-color-scheme: light) {{ .stella-loader:not([data-theme=\"dark\"]) {{ {vars_('light')} }} }}",
             f".stella-loader[data-theme=\"light\"] {{ {vars_('light')} }}"]
    rules += [f".st-f-{k} {{ fill: var(--st-{k}); }}" for k in keys]
    rules += [f".st-s-{k} {{ stop-color: var(--st-{k}); }}" for k in keys]
    return "\n    ".join(rules)
DEFAULT_OUT = "assets/pic/Stella_logo_loading.svg"


def fmt(v: float, nd: int = 1) -> str:
    return (f"{v:.{nd}f}").rstrip("0").rstrip(".") or "0"


def ray_tips(rel: np.ndarray) -> list[tuple[float, float]]:
    """(angle, length) of the four ray tips of a star outline given relative to its centre."""
    r = np.hypot(rel[:, 0], rel[:, 1])
    theta = np.arctan2(rel[:, 1], rel[:, 0])
    tips: list[tuple[float, float]] = []
    for i in np.argsort(-r):
        if all(abs((theta[i] - t + math.pi) % (2 * math.pi) - math.pi) > math.radians(50) for t, _ in tips):
            tips.append((float(theta[i]), float(r[i])))
        if len(tips) == 4:
            break
    return sorted(tips)


def rdp(pts: np.ndarray, eps: float) -> np.ndarray:
    """Ramer-Douglas-Peucker on an open polyline (first and last points must differ)."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    length = float(np.hypot(*ab)) or 1e-9
    dist = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / length
    i = int(np.argmax(dist))
    if dist[i] > eps:
        return np.vstack([rdp(pts[: i + 1], eps)[:-1], rdp(pts[i:], eps)])
    return np.vstack([a, b])


def poly_area(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


class Scene:
    def __init__(self, data: dict):
        cam = data["camera"]
        self.cam = np.array(cam["matrix"])
        self.w, self.h = (int(v) for v in cam["resolution"])
        self.k = cam["focal"] / cam["sensor"] * self.w

    def project(self, pts) -> np.ndarray:
        """World -> screen (x right, y down) plus camera-space depth."""
        rel = np.asarray(pts, dtype=float) - self.cam[0]
        local = rel @ self.cam[1:].T  # rows of the matrix are the camera axes
        x, y, z = local[:, 0], local[:, 1], local[:, 2]
        return np.stack([self.w / 2 + self.k * x / z, self.h / 2 - self.k * y / z, z], 1)

    def raster(self, meshes) -> np.ndarray:
        s = SUPERSAMPLE
        im = Image.new("1", (self.w * s, self.h * s), 0)
        dr = ImageDraw.Draw(im)
        for mesh in meshes:
            p = self.project(mesh["pts"])[:, :2] * s
            for q in mesh["polys"]:
                dr.polygon([tuple(p[i]) for i in dict.fromkeys(q)], fill=1)
        return np.array(im)

    def radial(self, mask: np.ndarray, c, n: int):
        s = SUPERSAMPLE
        ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
        r = np.arange(0, max(self.w, self.h) * s * 0.75, 0.5)
        xs = c[0] * s + np.outer(np.cos(ang), r)
        ys = c[1] * s + np.outer(np.sin(ang), r)
        ok = (xs >= 0) & (ys >= 0) & (xs < self.w * s) & (ys < self.h * s)
        hit = np.zeros_like(ok)
        hit[ok] = mask[ys[ok].astype(int), xs[ok].astype(int)]
        last = np.where(hit.any(1), hit.shape[1] - 1 - np.argmax(hit[:, ::-1], 1), 0)
        return ang, r[last] / s

    def zbuffer(self, meshes) -> np.ndarray:
        zbuf = np.full((self.h, self.w), np.inf)
        for mesh in meshes:
            p = self.project(mesh["pts"])
            for q in mesh["polys"]:
                for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                    if tri[1] == tri[2]:
                        continue
                    _fill_triangle(zbuf, p[list(tri)])
        return zbuf


def _fill_triangle(zbuf: np.ndarray, t: np.ndarray) -> None:
    h, w = zbuf.shape
    x0, x1 = int(max(0, t[:, 0].min())), int(min(w - 1, t[:, 0].max() + 1))
    y0, y1 = int(max(0, t[:, 1].min())), int(min(h - 1, t[:, 1].max() + 1))
    if x1 < x0 or y1 < y0:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-9:
        return
    w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
    w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
    w2 = 1 - w0 - w1
    inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    sub = zbuf[y0 : y1 + 1, x0 : x1 + 1]
    np.minimum(sub, np.where(inside, w0 * az + w1 * bz + w2 * cz, np.inf), out=sub)


def compute_geometry(data: dict) -> dict:
    sc = Scene(data)

    # main star outline
    big = data["big"]["meshes"]
    mask = sc.raster(big)
    cb = sc.project([data["big"]["origin"]])[0]
    ang, rad = sc.radial(mask, cb, 4096)
    xy = np.stack([cb[0] + rad * np.cos(ang), cb[1] + rad * np.sin(ang)], 1)
    ratio = poly_area(xy) / (mask.sum() / SUPERSAMPLE**2)
    if not 0.97 < ratio < 1.03:
        raise SystemExit(f"main star is not star-shaped from its origin (area ratio {ratio:.3f})")
    xy = np.roll(xy, -int(np.argmax(rad)), 0)
    half = len(xy) // 2
    big_out = np.vstack([rdp(xy[: half + 1], 0.3)[:-1], rdp(np.vstack([xy[half:], xy[:1]]), 0.3)[:-1]])

    zbuf = sc.zbuffer(big)

    def zat(x, y, rad=0):
        xi, yi = math.floor(x + 0.5), math.floor(y + 0.5)
        if rad:
            return zbuf[max(0, yi - rad) : yi + rad + 1, max(0, xi - rad) : xi + rad + 1].min()
        return zbuf[min(sc.h - 1, max(0, yi)), min(sc.w - 1, max(0, xi))]

    centres = sc.project([fr["origin"] for fr in data["small"]])

    # companion shape: frame-0 silhouette (the logo pose), relative to its centre
    c0 = centres[0]
    m = sc.raster(data["small"][0]["meshes"])
    ang, rad = sc.radial(m, c0, 2880)
    rel = np.stack([rad * np.cos(ang), rad * np.sin(ang)], 1)
    ratio = poly_area(rel) / (m.sum() / SUPERSAMPLE**2)
    if not 0.95 < ratio < 1.05:
        raise SystemExit(f"companion is not star-shaped from its origin (area ratio {ratio:.3f})")
    rel = np.roll(rel, -int(np.argmax(rad)), 0)
    half = len(rel) // 2
    shape = np.vstack([rdp(rel[: half + 1], 0.1)[:-1], rdp(np.vstack([rel[half:], rel[:1]]), 0.1)[:-1]])

    # occlusion per frame, tested over the companion's whole body (not just its centre):
    # "overlap" = the body covers part of the main star, "behind" = it is farther away there
    body = float(rad.max()) * 0.8
    yy, xx = np.mgrid[0 : sc.h, 0 : sc.w]
    frames = []
    for c in centres:
        rr = body * c0[2] / c[2]
        zb = zbuf[(xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= rr * rr]
        zb = zb[np.isfinite(zb)]
        overlap = zb.size > 0
        frames.append({"c": c.tolist(), "overlap": overlap,
                       "behind": bool(overlap and c[2] >= np.median(zb))})

    orbit =[(x, y, bool(np.isfinite(zat(x, y)) and z < zat(x, y))) for x, y, z in sc.project(data["orbit"])]
    return {"big": big_out.tolist(), "big_center": cb[:2].tolist(), "small": frames,
            "companion": shape.tolist(), "orbit": orbit}


def build_svg(g: dict, duration: float) -> str:
    dur = f"{fmt(duration, 3)}s"
    small = g["small"]
    nframes = len(small)
    last = nframes - 1
    anim = f'dur="{dur}" repeatCount="indefinite"'

    def poly_d(pts, close=True):
        return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if close else "")

    def kt(i):
        return fmt(i / last, 4)

    keytimes = ";".join(kt(i) for i in range(nframes))
    centres = np.array([f["c"] for f in small])

    # companion: the model's frame-0 silhouette, camera-facing, scaled by depth only
    shape = np.array(g["companion"])
    ray_len = float(np.hypot(shape[:, 0], shape[:, 1]).max())
    tips = [a for a, _ in ray_tips(shape)]  # directions of the four ray tips
    between = [a + ((b - a) % (2 * math.pi)) / 2 for a, b in zip(tips, tips[1:] + tips[:1], strict=True)]

    # main star breathing: radial stretch weighted by how far out along its own arm a point is
    bc = np.array(g["big_center"])
    big_rel = np.array(g["big"]) - bc
    big_r = np.hypot(big_rel[:, 0], big_rel[:, 1])
    big_theta = np.arctan2(big_rel[:, 1], big_rel[:, 0])
    big_tips = ray_tips(big_rel)
    nearest = np.array([min(range(4), key=lambda k, a=a: abs((a - big_tips[k][0] + math.pi) % (2 * math.pi) - math.pi))
                        for a in big_theta])
    tip_len = np.array([big_tips[k][1] for k in nearest])
    weight = np.clip(big_r / tip_len, 0, 1) ** BREATH_EXP
    # the star is asymmetric: the two longest points (left, bottom) form one group, the two
    # shorter ones (right, top) the other; each group has its own amplitude and they run in
    # opposite phase, so points move together within a group but not across groups
    long_pair = set(sorted(range(4), key=lambda k: -big_tips[k][1])[:2])
    is_long = np.array([k in long_pair for k in nearest])
    amp = np.where(is_long, BREATH_LONG, BREATH_SHORT) * weight
    phase = np.where(is_long, 1.0, -1.0)

    def breathe(k):  # k = -1: long pair retracted / short pair extended; k = +1: the reverse
        return poly_d(bc + big_rel * (1 + k * phase * amp)[:, None])

    big_breath = ";".join(breathe(k) for k in (-1, 1, -1))
    scale = centres[0, 2] / centres[:, 2]  # perspective: nearer = larger
    move_vals = ";".join(f"{fmt(x)} {fmt(y)}" for x, y in centres[:, :2])
    scale_vals = ";".join(fmt(s, 3) for s in scale)
    near = (scale - scale.min()) / np.ptp(scale)
    spike_vals = ";".join(fmt(float(v), 2) for v in 0.55 + 0.3 * near)

    def spike(angle, length, width, extra=""):
        return (f'<path d="M0 {fmt(-width, 2)} L{fmt(length)} 0 L0 {fmt(width, 2)} Z" fill="url(#st-spike)" '
                f'transform="rotate({fmt(math.degrees(angle), 2)})"{extra}/>')

    sep = "\n          "
    primary = sep.join(
        spike(a, ray_len * SPIKE_LEN, ray_len * SPIKE_WIDTH * 3, ' filter="url(#st-blur2)" opacity="0.6"')
        + spike(a, ray_len * SPIKE_LEN, ray_len * SPIKE_WIDTH) for a in tips)
    secondary = sep.join(spike(a, ray_len * SECONDARY_LEN, ray_len * SECONDARY_WIDTH) for a in between)
    # twinkle: deterministic flicker of spike length/brightness, first key == last key
    flick = np.random.default_rng(7).uniform(0, 1, TWINKLE_KEYS)
    flick = np.append(flick, flick[0])
    twinkle_css = " ".join(
        f"{fmt(100 * i / TWINKLE_KEYS, 2)}% {{ transform: scale({fmt(0.88 + 0.24 * f, 3)}); opacity: {fmt(0.75 + 0.25 * f, 2)}; }}"
        for i, f in enumerate(flick))

    reach = ray_len * 1.3  # frame the body; spikes fade out before the edge
    ext = [list(c[:2] + np.array(d) * reach * s) for c, s in zip(centres, scale, strict=True) for d in ((-1, -1), (1, 1))]
    big_max = bc + big_rel * (1 + amp)[:, None]
    allp = np.array(big_max.tolist() + [o[:2] for o in g["orbit"]] + ext)
    x0, y0 = allp.min(0) - 40
    x1, y1 = allp.max(0) + 40
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    box = (fmt(cx - side / 2), fmt(cy - side / 2), fmt(side), fmt(side))

    # comet path through the per-frame centres (closed Catmull-Rom); last frame == first frame
    pts = centres[:last, :2]
    n = len(pts)
    segs = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        segs.append((p1, p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6, p2))

    def bez(s, t):
        a, b, c, d = s
        u = 1 - t
        return u**3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t**3 * d

    seglen = [sum(np.hypot(*(bez(s, (k + 1) / 24) - bez(s, k / 24))) for k in range(24)) for s in segs]
    cum = np.concatenate([[0], np.cumsum(seglen)])
    cum /= cum[-1]  # arc fraction reached at each frame
    # dense polyline of the path, parameterised by arc fraction, for positions and tangents
    sub = 24
    dense = np.array([bez(sg, k / sub) for sg in segs for k in range(sub)] + [segs[0][0]])
    dlen = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(dense, axis=0).T))])
    dlen /= dlen[-1]

    def wrap(frame):
        return frame - math.floor(frame / last) * last

    def arc_at(frame):  # arc fraction at a (possibly fractional or negative) frame
        return float(np.interp(wrap(frame), np.arange(nframes), cum))

    def scale_at(frame):
        return float(np.interp(wrap(frame), np.arange(nframes), scale))

    def ribbon(frame, window, head, taper):
        """Outline of the tail at `frame`: where the companion was over the last `window` frames."""
        u = np.linspace(0, 1, TAIL_SAMPLES)  # 0 = oldest (tail end), 1 = now (head)
        side_l, side_r = [], []
        for uj in u:
            t = frame - window * (1 - uj)
            a = arc_at(t)
            x, y = np.interp(a, dlen, dense[:, 0]), np.interp(a, dlen, dense[:, 1])
            ia = min(int(np.searchsorted(dlen, a)), len(dense) - 1)
            tx, ty = dense[ia] - dense[ia - 1]
            nrm = math.hypot(tx, ty) or 1.0
            half = 0.5 * head * ray_len * scale_at(t) * uj**taper
            side_l.append((x - ty / nrm * half, y + tx / nrm * half))
            side_r.append((x + ty / nrm * half, y - tx / nrm * half))
        return poly_d(side_l + side_r[::-1])

    ribbons = "\n    ".join(
        f'<path id="{rid}" d="{ribbon(0, w, h, tp)}">'
        f'<animate attributeName="d" {anim} values="{";".join(ribbon(f, w, h, tp) for f in range(nframes))}" '
        f'keyTimes="{keytimes}"/></path>'
        for rid, w, h, tp in TAIL_RIBBONS)
    # crisp edges like the star bodies: the ribbons' own taper gives the fade, no blur
    tails = (f'<use href="#st-trail-glow" {fill("accent-deep")} opacity="0.5"/>\n'
             f'    <use href="#st-trail-glow" {fill("accent")} opacity="0.4"/>\n'
             f'    <use href="#st-trail-core" {fill("white")}/>')

    def visibility(flags):
        vals, kts = [], []
        for i, flag in enumerate(flags):
            v = "visible" if flag else "hidden"
            if not vals or vals[-1] != v:
                vals.append(v)
                kts.append(kt(i))
        return (f'<animate attributeName="visibility" {anim} calcMode="discrete" '
                f'values="{";".join(vals)}" keyTimes="{";".join(kts)}"/>')

    def companion(flags):
        start = "visible" if flags[0] else "hidden"
        return (f'<g visibility="{start}">{visibility(flags)}\n'
                f'      <g><animateTransform attributeName="transform" type="translate" {anim} '
                f'values="{move_vals}" keyTimes="{keytimes}"/>\n'
                f'        <g><animateTransform attributeName="transform" type="scale" {anim} '
                f'values="{scale_vals}" keyTimes="{keytimes}"/>\n'
                f'          <use href="#st-companion"/>\n'
                f'        </g>\n      </g>\n    </g>')

    behind = [f["behind"] for f in small]
    # The trail switches layer as a whole: it goes behind the main star if any moment it covers
    # was behind, in front if it only crossed the star in front. (A fixed spatial mask cannot
    # work here: the orbit crosses itself right at the main star's centre, once behind and once
    # in front, and the two crossings are far apart in time but not in space.)
    window = max(r[1] for r in TAIL_RIBBONS)

    def covered(f):
        return [small[(f - k) % last] for k in range(math.ceil(window) + 1)]

    trail_behind = [any(x["behind"] for x in covered(f)) or not any(x["overlap"] for x in covered(f))
                    for f in range(nframes)]

    def layered(flags, body):
        start = "visible" if flags[0] else "hidden"
        return f'<g visibility="{start}">{visibility(flags)}\n    {body}\n    </g>'

    def companion_def(cid, animated):
        def fade(values):
            first = values.split(";", 1)[0]
            if not animated:
                return f'opacity="{first}">'
            return f'opacity="{first}"><animate attributeName="opacity" {anim} values="{values}" keyTimes="{keytimes}"/>'

        return (f'<g id="{cid}">\n'
                f'      <use href="#st-model" {fill("white")}/>\n'
                f'      <g {fade(spike_vals)}<use href="#st-spikes"/></g>\n'
                f'      <circle r="{fmt(ray_len * 0.18)}" {fill("white")} opacity="0.7" filter="url(#st-blur2)"/>\n'
                f'    </g>')

    bx, by = (fmt(v) for v in g["big_center"])
    c0x, c0y = (fmt(v) for v in centres[0, :2])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" class="stella-loader" viewBox="{" ".join(box)}" width="256" height="256" role="img" aria-label="Stella 加载中">
  <title>Stella</title>
  <!--
    Stella 动态 Logo（加载装饰）：双星。几何全部来自 assets/model/CBHB.c4d：
    · 主星：细分后的「主星」网格经「RS相机」投影出的轮廓；星芒分两组伸缩（中心不动）：
      较长的左、下星芒一组、幅度较大，较短的右、上星芒一组，组内同步、两组反相
    · 伴星：位置与远近取「动星」沿「运动路径」的真实 3D 运动；本体保持白模第 0 帧（原 Logo）造型，
      始终朝向镜头，只随远近缩放，不随网格翻滚；外加相机式星芒：沿四条星芒方向的衍射芒、次级芒与轻微闪烁
    · 拖尾：覆盖伴星最近一段固定时长走过的路径，速度快则长、慢则短
    · 遮挡：按 C4D 网格深度 (z-buffer) 判断伴星与轨迹何时在主星背后 / 前方
    · 一个循环 = C4D 全部 {nframes} 帧 = {dur}，首尾帧相同可无缝循环；第 0 帧即原 Logo 构图
    · 背景透明，星体外不加光晕 / 阴影，避免干扰页面背景；prefers-reduced-motion 时显示第 0 帧静态 Logo
    由 scripts/export_logo_c4d.py → scripts/build_loading_logo.py 生成，勿手改坐标。
  -->
  <defs>
    <radialGradient id="st-body" cx="{bx}" cy="{by}" r="380" gradientUnits="userSpaceOnUse">
      <stop offset="0" {stop("body-inner")}/>
      <stop offset="0.55" {stop("body-mid")}/>
      <stop offset="1" {stop("body-tip")}/>
    </radialGradient>
    <linearGradient id="st-spike">
      <stop offset="0" {stop("white")}/>
      <stop offset="0.25" {stop("body-inner")} stop-opacity="0.7"/>
      <stop offset="0.6" {stop("accent")} stop-opacity="0.25"/>
      <stop offset="1" {stop("accent-deep")} stop-opacity="0"/>
    </linearGradient>
    <filter id="st-blur2" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="2"/></filter>
    <path id="st-big" d="{poly_d(g["big"])}"/>
    <path id="st-big-breath" d="{breathe(-1)}">
      <animate attributeName="d" {anim} values="{big_breath}" keyTimes="0;0.5;1" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>
    </path>
    <path id="st-model" d="{poly_d(shape)}"/>
    <!-- 拖尾带：伴星最近一段时间走过的位置，宽度随当时远近变化，向尾部收窄 -->
    {ribbons}
    <!-- 伴星星芒：衍射芒 + 次级芒，轻微闪烁（CSS，减少动态时停止） -->
    <g id="st-spikes" class="st-twinkle">
      {primary}
      {secondary}
    </g>
    <!-- 伴星（以自身中心为原点）：白模本体 + 星芒；星芒亮度随远近变化 -->
    {companion_def("st-companion", True)}
    <!-- 减少动态时使用的静态伴星（不含 SMIL 动画，CSS 无法暂停 SMIL） -->
    {companion_def("st-companion-still", False)}
  </defs>
  <style>
    {theme_css()}
    .st-twinkle {{ transform-origin: 0 0; animation: st-twinkle {dur} linear infinite; }}
    @keyframes st-twinkle {{ {twinkle_css} }}
    .st-static {{ display: none; }}
    @media (prefers-reduced-motion: reduce) {{
      .st-anim {{ display: none; }}
      .st-static {{ display: inline; }}
      .st-twinkle {{ animation: none; }}
    }}
  </style>

  <!-- 背后层：拖尾、处于主星背后的伴星 -->
  <g class="st-anim">
    {layered(trail_behind, tails)}
    {companion(behind)}
  </g>

  <!-- 主星：星芒分两组伸缩；减少动态时用静态轮廓 -->
  <g class="st-anim">
    <use href="#st-big-breath" fill="url(#st-body)"/>
  </g>
  <g class="st-static">
    <use href="#st-big" fill="url(#st-body)"/>
  </g>

  <!-- 前方层：在主星前方的拖尾，以及不在主星背后的伴星 -->
  <g class="st-anim">
    {layered([not b for b in trail_behind], tails)}
    {companion([not b for b in behind])}
  </g>
  <g class="st-static" transform="translate({c0x} {c0y})">
    <use href="#st-companion-still"/>
  </g>
</svg>
'''


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", help="JSON written by export_logo_c4d.py")
    ap.add_argument("out", nargs="?", default=DEFAULT_OUT)
    args = ap.parse_args()
    with Path(args.scene).open(encoding="utf-8") as fh:
        data = json.load(fh)
    first, last = data["frames"]
    if last <= first or len(data["small"]) != last - first + 1:
        raise SystemExit("scene JSON has no animation frames")
    geom = compute_geometry(data)
    svg = build_svg(geom, (last - first) / data["fps"])
    with Path(args.out).open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    behind = [i for i, f in enumerate(geom["small"]) if f["behind"]]
    print(f"wrote {args.out}: {len(svg.encode())} bytes, companion behind main star at frames {behind}")


if __name__ == "__main__":
    main()
