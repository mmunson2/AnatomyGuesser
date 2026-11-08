"""Fit the HRA female meshes onto the BodyParts3D body; writes hra_transforms.json.

    python3 build/fit_hra.py <bp3d_dir> <hra_dir>

Needs numpy and scipy. All HRA reference organs share one body frame (metres,
y up, +x = patient's left, +z anterior: the same axes as our body space), but
the Visible Human female is shorter and has a wider pelvis than the
BodyParts3D male, so one transform can't place everything. Each region gets
its own similarity transform (uniform scale, rotation, translation), found by
symmetric ICP on points spread evenly over each surface (mesh vertices are
too unevenly dense to fit to directly):

  pelvis  HRA hip bones + sacrum onto ours. Places the female pelvis and the
          organs inside it.
  thorax  HRA torso skin onto ours, from the waist to below the armpits,
          leaving out skin over the breasts. Places the mammary glands.
          Scale and translation only: a band of torso is close to a
          cylinder, so a free rotation just spins it.

Only rerun this when the source meshes change; build_model.py reads the
saved transforms and doesn't need scipy.
"""

import json
import sys
from functools import cache
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

import glb
from build_model import index_elements, load_tables, read_obj, resolve, to_body_space

OUT = Path(__file__).with_name("hra_transforms.json")
SAMPLES = 20000


def surface_points(meshes, n=SAMPLES):
    """n points spread uniformly by area over a list of (verts, faces)."""
    tris = np.concatenate([v[f] for v, f in meshes])
    area = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    rng = np.random.default_rng(0)
    pick = tris[rng.choice(len(tris), n, p=area / area.sum())]
    a, b = rng.random((2, n, 1))
    flip = a + b > 1
    a, b = np.where(flip, 1 - a, a), np.where(flip, 1 - b, b)
    return pick[:, 0] + a * (pick[:, 1] - pick[:, 0]) + b * (pick[:, 2] - pick[:, 0])


@cache
def source_index(root):
    """(concepts, files, names) for a BodyParts3D directory, read once."""
    return load_tables(root), *index_elements(root)


def ours(root, selectors):
    concepts, files, names = source_index(Path(root))
    elements = resolve(selectors, concepts, names) & files.keys()
    meshes = [read_obj(files[fj]) for fj in sorted(elements)]
    return to_body_space(surface_points(meshes))


def hra(hra_dir, name, keep=lambda node: True):
    return surface_points([(v, f) for node, v, f in glb.load(Path(hra_dir) / f"{name}.glb")
                           if keep(node)])


def umeyama(src, dst, rotate=True):
    """Least-squares similarity transform taking src onto dst."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    a, b = src - mu_s, dst - mu_d
    if not rotate:
        s = (a * b).sum() / (a * a).sum()
        return s, np.eye(3), mu_d - s * mu_s
    u, d, vt = np.linalg.svd(b.T @ a / len(src))
    flip = np.eye(3)
    if np.linalg.det(u @ vt) < 0:
        flip[2, 2] = -1
    r = u @ flip @ vt
    s = np.trace(np.diag(d) @ flip) / a.var(0).sum()
    return s, r, mu_d - s * r @ mu_s


def icp(src, dst, scale, symmetric=True, rotate=True, iters=60):
    """symmetric: src and dst cover the same anatomy, so match both ways.
    Otherwise only src is pulled onto dst, which may cover more."""
    s, r = scale, np.eye(3)
    t = dst.mean(0) - s * src.mean(0)
    to_dst = cKDTree(dst)
    for _ in range(iters):
        cur = s * src @ r.T + t
        _, i1 = to_dst.query(cur)
        a, b = src, dst[i1]
        if symmetric:
            _, i2 = cKDTree(cur).query(dst)
            a, b = np.concatenate([a, src[i2]]), np.concatenate([b, dst])
        s, r, t = umeyama(a, b, rotate)
    cur = s * src @ r.T + t
    err = to_dst.query(cur)[0].mean()
    if symmetric:
        err = (err + cKDTree(cur).query(dst)[0].mean()) / 2
    return s, r, t, err


def report(name, s, r, t, err):
    angle = np.degrees(np.arccos(np.clip((np.trace(r) - 1) / 2, -1, 1)))
    print(f"{name:7s} scale {s:.4f}  rotation {angle:.2f} deg  "
          f"translation {np.round(t, 4).tolist()}  mean gap {err * 1000:.1f} mm")


def main(root, hra_dir):
    root = Path(root)
    height = 1.72 / 1.658  # BodyParts3D / Visible Human female, a starting scale
    fits = {}

    pelvis_nodes = lambda n: "compact" in n or n.endswith("sacrum")
    f_pelvis = hra(hra_dir, "pelvis-female", pelvis_nodes)
    s, r, t, err = icp(f_pelvis, ours(root, ["hip bone", "sacrum"]), height)
    report("pelvis", s, r, t, err)
    fits["pelvis"] = (s, r, t)

    # Femoral heads should sit in the new acetabula: report how far the top
    # of each femur is from the fitted female hip bone, next to ours.
    femur = ours(root, ["femur"])
    heads = femur[femur[:, 1] > femur[:, 1].max() - 0.05]
    heads = heads[np.abs(heads[:, 0]) < np.abs(heads[:, 0]).max() - 0.04]  # medial, not the trochanter
    hips = hra(hra_dir, "pelvis-female", lambda n: "compact" in n)
    for label, bone in (("female", s * hips @ r.T + t), ("male", ours(root, ["hip bone"]))):
        d = cKDTree(bone).query(heads)[0]
        print(f"  femoral heads to {label} hip bone: median {np.median(d) * 1000:.1f} mm, "
              f"90% within {np.percentile(d, 90) * 1000:.1f} mm")

    skin = hra(hra_dir, "skin-female")
    breasts = np.concatenate([hra(hra_dir, f"mammary-gland-female-{side}") for side in ("left", "right")])
    band = skin[(skin[:, 1] > 0.22) & (skin[:, 1] < 0.50) & (np.abs(skin[:, 0]) < 0.16)]
    band = band[cKDTree(breasts).query(band)[0] > 0.04]
    our_skin = ours(root, ["skin"])
    our_band = our_skin[(our_skin[:, 1] > 0.95) & (our_skin[:, 1] < 1.45) & (np.abs(our_skin[:, 0]) < 0.18)]
    s, r, t, err = icp(band, our_band, height, symmetric=False, rotate=False)
    report("thorax", s, r, t, err)
    fits["thorax"] = (s, r, t)

    OUT.write_text(json.dumps({k: {"scale": s, "rotation": np.round(r, 8).tolist(),
                                   "translation": np.round(t, 8).tolist()}
                               for k, (s, r, t) in fits.items()}, indent=2) + "\n")
    print(f"-> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python3 build/fit_hra.py <bp3d_dir> <hra_dir>")
    main(*sys.argv[1:3])
