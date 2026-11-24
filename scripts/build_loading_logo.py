#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0
"""Build assets/pic/Stella_logo_loading.svg from the JSON written by export_logo_c4d.py.

    python scripts/build_loading_logo.py <scene.json> [assets/pic/Stella_logo_loading.svg]

Needs numpy and Pillow. Every coordinate in the SVG comes from assets/model/CBHB.c4d:

  1. Project all geometry through the scene camera (pinhole, focal / sensor width).
  2. Rasterize the main star and each small-star frame at 4x, then take the outline by
     casting rays from the star's origin (a four-pointed star is star-shaped from its
     centre, so the outermost hit per ray is the silhouette).
  3. Build a z-buffer of the main star; the small star and orbit are "behind" where they
     overlap it and are farther from the camera.
  4. Emit SMIL: the small star morphs between per-frame outlines (fixed 4 x NARM vertices,
     tip-aligned so the morph is stable), the comet tail is a dash running along the path
     through the small star's per-frame centres, and front/back layering is switched per
     frame. One loop = the C4D frame range.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SUPERSAMPLE = 4
NARM = 12           # outline vertices per small-star arm (tip included)
MORPH_STEP = 2      # sample the small-star outline every N frames
DEFAULT_OUT = "assets/pic/Stella_logo_loading.svg"


def fmt(v: float, nd: int = 1) -> str:
    return (f"{v:.{nd}f}").rstrip("0").rstrip(".") or "0"


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
    big_out = np.vstack([rdp(xy[: half + 1], 0.15)[:-1], rdp(np.vstack([xy[half:], xy[:1]]), 0.15)[:-1]])

    zbuf = sc.zbuffer(big)

    def zat(x, y, rad=0):
        xi, yi = math.floor(x + 0.5), math.floor(y + 0.5)
        if rad:
            return zbuf[max(0, yi - rad) : yi + rad + 1, max(0, xi - rad) : xi + rad + 1].min()
        return zbuf[min(sc.h - 1, max(0, yi)), min(sc.w - 1, max(0, xi))]

    # small star, one tip-aligned outline per frame
    frames, prev_tip = [], None
    for fr in data["small"]:
        m = sc.raster(fr["meshes"])
        c = sc.project([fr["origin"]])[0]
        ang, rad = sc.radial(m, c, 2880)
        tips: list[int] = []
        for i in np.argsort(-rad):
            if all(min(abs(ang[i] - ang[j]), 2 * math.pi - abs(ang[i] - ang[j])) > math.radians(50) for j in tips):
                tips.append(int(i))
            if len(tips) == 4:
                break
        tips.sort()
        if prev_tip is not None:  # keep vertex correspondence continuous between frames
            k = min(range(4), key=lambda k: min(abs(ang[tips[k]] - prev_tip), 2 * math.pi - abs(ang[tips[k]] - prev_tip)))
            tips = tips[k:] + tips[:k]
        prev_tip = ang[tips[0]]
        pts = []
        for k in range(4):
            a0, a1 = ang[tips[k]], ang[tips[(k + 1) % 4]]
            span = (a1 - a0) % (2 * math.pi)
            for j in range(NARM):
                i = math.floor(((a0 + span * j / NARM) % (2 * math.pi)) / (2 * math.pi) * len(ang) + 0.5) % len(ang)
                pts.append((c[0] + rad[i] * math.cos(ang[i]), c[1] + rad[i] * math.sin(ang[i])))
        zb = zat(c[0], c[1], 2)
        frames.append({"pts": pts, "c": c.tolist(), "behind": bool(np.isfinite(zb) and c[2] >= zb)})

    orbit = [(x, y, bool(np.isfinite(zat(x, y)) and z < zat(x, y))) for x, y, z in sc.project(data["orbit"])]
    return {"big": big_out.tolist(), "big_center": cb[:2].tolist(), "small": frames, "orbit": orbit}


def build_svg(g: dict, duration: float) -> str:
    dur = f"{fmt(duration, 3)}s"
    small = g["small"]
    nframes = len(small)
    last = nframes - 1

    def poly_d(pts, close=True):
        return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + (" Z" if close else "")

    def kt(i):
        return fmt(i / last, 4)

    allp = np.array(g["big"] + [p for f in small for p in f["pts"]] + [o[:2] for o in g["orbit"]])
    x0, y0 = allp.min(0) - 40
    x1, y1 = allp.max(0) + 40
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    box = (fmt(cx - side / 2), fmt(cy - side / 2), fmt(side), fmt(side))

    # comet path through the per-frame centres (closed Catmull-Rom); last frame == first frame
    pts = np.array([f["c"][:2] for f in small[:last]])
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
    trail_d = f"M{fmt(pts[0][0])} {fmt(pts[0][1])} " + " ".join(
        f"C{fmt(b[0])} {fmt(b[1])} {fmt(c[0])} {fmt(c[1])} {fmt(d[0])} {fmt(d[1])}" for _, b, c, d in segs) + " Z"
    keytimes = ";".join(kt(i) for i in range(nframes))

    def tail(length, width, color, opacity, extra=""):
        # dasharray "L 1-L" with dashoffset L-s draws the dash on [s-L, s]: it ends at the star.
        offs = ";".join(fmt(length - s, 4) for s in cum)
        return (f'<path d="{trail_d}" pathLength="1" fill="none" stroke="{color}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-dasharray="{length:.3f} {1 - length:.3f}" opacity="{opacity}"{extra}>'
                f'<animate attributeName="stroke-dashoffset" dur="{dur}" repeatCount="indefinite" '
                f'values="{offs}" keyTimes="{keytimes}"/></path>')

    tails = "\n    ".join([tail(0.36, 10, "#f5c76a", 0.4, ' filter="url(#st-blur4)"'),
                           tail(0.22, 3.6, "#ffe3a3", 0.75),
                           tail(0.09, 2.4, "#fffaf0", 1)])

    orbit = g["orbit"]
    front_runs, cur = [], []
    for x, y, front in orbit + orbit[:1]:
        if front:
            cur.append((x, y))
        elif cur:
            front_runs.append(cur)
            cur = []
    if cur:
        front_runs.append(cur)
    front_d = " ".join(poly_d(r, False) for r in front_runs if len(r) > 1)
    orbit_full = poly_d([o[:2] for o in orbit])

    morph_frames = list(range(0, nframes, MORPH_STEP))
    if morph_frames[-1] != last:
        morph_frames.append(last)
    morph_vals = ";".join(poly_d(small[f]["pts"]) for f in morph_frames)
    morph_kt = ";".join(kt(f) for f in morph_frames)

    def visibility(flags):
        vals, kts = [], []
        for i, flag in enumerate(flags):
            v = "visible" if flag else "hidden"
            if not vals or vals[-1] != v:
                vals.append(v)
                kts.append(kt(i))
        return (f'<animate attributeName="visibility" dur="{dur}" repeatCount="indefinite" calcMode="discrete" '
                f'values="{";".join(vals)}" keyTimes="{";".join(kts)}"/>')

    behind = [f["behind"] for f in small]
    bx, by = (fmt(v) for v in g["big_center"])
    first_d = poly_d(small[0]["pts"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(box)}" width="256" height="256" role="img" aria-label="Stella 加载中">
  <title>Stella</title>
  <!--
    Stella 动态 Logo（加载装饰）。几何全部来自 assets/model/CBHB.c4d：
    · 主星：细分后的「主星」网格经「RS相机」投影出的轮廓
    · 小星：「动星」沿「运动路径」(对齐曲线) 运动，每 {MORPH_STEP} 帧取一次投影轮廓做形变，近大远小与翻转都来自原始 3D 运动
    · 遮挡：按 C4D 网格深度 (z-buffer) 判断小星与轨迹何时在主星背后 / 前方
    · 一个循环 = C4D 全部 {nframes} 帧 = {dur}，首尾帧相同可无缝循环；第 0 帧即原 Logo 构图
    · 背景透明；prefers-reduced-motion 时显示第 0 帧静态 Logo
    由 scripts/export_logo_c4d.py → scripts/build_loading_logo.py 生成，勿手改坐标。
  -->
  <defs>
    <radialGradient id="st-body" cx="{bx}" cy="{by}" r="330" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fffdf6"/>
      <stop offset="0.3" stop-color="#fff3d6"/>
      <stop offset="1" stop-color="#f0c97a"/>
    </radialGradient>
    <radialGradient id="st-halo" cx="{bx}" cy="{by}" r="300" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#ffe7ae" stop-opacity="0.5"/>
      <stop offset="0.5" stop-color="#f5c76a" stop-opacity="0.12"/>
      <stop offset="1" stop-color="#f5c76a" stop-opacity="0"/>
    </radialGradient>
    <filter id="st-blur16" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="16"/></filter>
    <filter id="st-blur6" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="6"/></filter>
    <filter id="st-blur4" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="4"/></filter>
    <path id="st-big" d="{poly_d(g["big"])}"/>
    <path id="st-small" d="{first_d}">
      <animate attributeName="d" dur="{dur}" repeatCount="indefinite" values="{morph_vals}" keyTimes="{morph_kt}"/>
    </path>
    <path id="st-small-0" d="{first_d}"/>
    <mask id="st-front" maskUnits="userSpaceOnUse" x="{box[0]}" y="{box[1]}" width="{box[2]}" height="{box[3]}">
      <path d="{front_d}" fill="none" stroke="#fff" stroke-width="40" stroke-linecap="round"/>
    </mask>
  </defs>
  <style>
    .st-pulse {{ animation: st-pulse {dur} ease-in-out infinite; }}
    @keyframes st-pulse {{ 0%,100% {{ opacity: .7; }} 50% {{ opacity: 1; }} }}
    .st-static {{ display: none; }}
    @media (prefers-reduced-motion: reduce) {{
      .st-anim {{ display: none; }}
      .st-static {{ display: inline; }}
      .st-pulse {{ animation: none; }}
    }}
  </style>

  <circle class="st-pulse" cx="{bx}" cy="{by}" r="300" fill="url(#st-halo)"/>

  <!-- 背后层：完整轨道淡线、拖尾、处于主星背后的小星 -->
  <path d="{orbit_full}" fill="none" stroke="#f6d68f" stroke-width="1.4" opacity="0.16"/>
  <g class="st-anim">
    {tails}
    <g visibility="hidden">{visibility(behind)}
      <use href="#st-small" fill="#f5c76a" filter="url(#st-blur6)"/>
      <use href="#st-small" fill="#fffaf0"/>
    </g>
  </g>

  <!-- 主星 -->
  <use class="st-pulse" href="#st-big" fill="#f5c76a" filter="url(#st-blur16)"/>
  <use href="#st-big" fill="url(#st-body)"/>

  <!-- 前方层：在主星前方的那段轨道 / 拖尾，以及不在主星背后的小星 -->
  <path d="{front_d}" fill="none" stroke="#e8bd6a" stroke-width="1.4" opacity="0.35"/>
  <g class="st-anim">
    <g mask="url(#st-front)">
    {tails}
    </g>
    <g>{visibility([not b for b in behind])}
      <use href="#st-small" fill="#f5c76a" filter="url(#st-blur6)"/>
      <use href="#st-small" fill="#f5c76a" filter="url(#st-blur6)" opacity="0.5"/>
      <use href="#st-small" fill="#fffaf0"/>
    </g>
  </g>
  <g class="st-static">
    <use href="#st-small-0" fill="#f5c76a" filter="url(#st-blur6)"/>
    <use href="#st-small-0" fill="#fffaf0"/>
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
    print(f"wrote {args.out}: {len(svg.encode())} bytes, small star behind main star at frames {behind}")


if __name__ == "__main__":
    main()
