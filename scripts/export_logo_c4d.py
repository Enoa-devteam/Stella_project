#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0
"""Export the Stella logo scene (assets/model/CBHB.c4d) to JSON for build_loading_logo.py.

Must run under Cinema 4D's c4dpy (tested with Cinema 4D 2024):

    "<C4D>/c4dpy.exe" scripts/export_logo_c4d.py assets/model/CBHB.c4d <out.json>

The first c4dpy run asks for a license method interactively; after that it is remembered.
The output (~45 MB) is an intermediate file; keep it out of the repository.

Exported (world space, C4D units, Y up, camera looks down +Z):
  camera   RS相机 global matrix, focal length (mm), sensor width (mm), render resolution
  orbit    运动路径 spline, 401 evenly spaced samples
  big      主星 subdivision-surface cache at frame 0, plus the object origin
  small    动星 subdivision-surface cache and object origin for every frame
"""
import json
import sys
from pathlib import Path

import c4d

CAMERA, ORBIT = "RS相机", "运动路径"
BIG_SDS, BIG_MESH = "细分曲面.2", "主星"
SMALL_SDS, SMALL_MESH = "细分曲面", "动星"
RS_CAMERA_FOCAL, RS_CAMERA_SENSOR = 500, 1006  # Redshift camera parameter ids


def vec(p):
    return [p.x, p.y, p.z]


def fail(msg):
    print(msg)  # c4dpy swallows the SystemExit message, so print it first
    raise SystemExit(1)


def find(doc, name):
    obj = doc.SearchObject(name)
    if obj is None:
        fail(f"object not found in scene: {name}")
    return obj


def cached_meshes(obj):
    """Flatten the generator/deformer cache of obj into world-space polygon meshes."""
    meshes = []

    def walk(node):
        while node:
            if isinstance(node, c4d.PolygonObject):
                mg = node.GetMg()
                meshes.append({
                    "pts": [vec(mg * p) for p in node.GetAllPoints()],
                    "polys": [[q.a, q.b, q.c, q.d] for q in node.GetAllPolygons()],
                })
            sub = node.GetDeformCache() or node.GetCache()
            if sub:
                walk(sub)
            walk(node.GetDown())
            node = node.GetNext()

    walk(obj.GetCache())
    if not meshes:
        fail(f"empty cache for {obj.GetName()}")
    return meshes


def main(src, dst):
    # LoadDocument fails silently on relative paths under c4dpy
    src, dst = str(Path(src).resolve()), Path(dst).resolve()
    doc = c4d.documents.LoadDocument(src, c4d.SCENEFILTER_OBJECTS)
    if doc is None:
        fail(f"cannot load {src}")
    fps = doc.GetFps()
    first, last = doc.GetMinTime().GetFrame(fps), doc.GetMaxTime().GetFrame(fps)

    def goto(frame):
        doc.SetTime(c4d.BaseTime(frame, fps))
        doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)

    cam = find(doc, CAMERA)
    rd = doc.GetActiveRenderData()
    mg = cam.GetMg()
    out = {
        "fps": fps,
        "frames": [first, last],
        "camera": {
            "matrix": [vec(mg.off), vec(mg.v1), vec(mg.v2), vec(mg.v3)],
            "focal": cam[RS_CAMERA_FOCAL],
            "sensor": cam[RS_CAMERA_SENSOR],
            "resolution": [rd[c4d.RDATA_XRES], rd[c4d.RDATA_YRES]],
        },
    }

    goto(first)
    spline = find(doc, ORBIT)
    real = spline.GetRealSpline() or spline
    out["orbit"] = [vec(spline.GetMg() * real.GetSplinePoint(i / 400.0)) for i in range(401)]
    out["big"] = {"origin": vec(find(doc, BIG_MESH).GetMg().off),
                  "meshes": cached_meshes(find(doc, BIG_SDS))}

    small = []
    for frame in range(first, last + 1):
        goto(frame)
        small.append({"origin": vec(find(doc, SMALL_MESH).GetMg().off),
                      "meshes": cached_meshes(find(doc, SMALL_SDS))})
    out["small"] = small

    with dst.open("w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"OK frames {first}-{last} @ {fps}fps -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        fail(__doc__)
    main(sys.argv[1], sys.argv[2])
