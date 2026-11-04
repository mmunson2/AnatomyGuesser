"""Build data/bodydata.js from the BodyParts3D 4.0 OBJ release.

    python3 build/build_model.py <bp3d_dir> <hra_dir> data/bodydata.js

<bp3d_dir> holds the DBCLS downloads, unzipped in place:
    isa_element_parts.txt, partof_element_parts.txt,
    isa_BP3D_4.0_obj_99/*.obj, partof_BP3D_4.0_obj_99/*.obj

<hra_dir> holds the HRA female reference organs named in HRA_TARGETS, as
<name>.glb (e.g. uterus-female.glb from
https://cdn.humanatlas.io/digital-objects/ref-organ/uterus-female/latest/).
They're placed with the transforms in hra_transforms.json (see fit_hra.py).
The female skin is read from female_skin.npz (see fit_anny.py).

Needs numpy and fast-simplification (pip install fast-simplification).

Every target in parts_table.py becomes one merged mesh, decimated to its
triangle budget. Parts only one body has carry "sex": "male" or "female";
the viewer shows the shared parts plus the chosen body's. Positions are quantised to uint16 over the body's bounding
box and stored base64 with uint16/uint32 indices, so the page can load the
model from file:// with a plain <script> tag.
"""

import base64
import json
import re
import sys
from pathlib import Path

import fast_simplification
import numpy as np

import glb
from parts_table import BAD_ELEMENTS, CONTEXT, HRA_TARGETS, MALE_ONLY, TARGETS

ATTRIBUTION = ("BodyParts3D, (c) The Database Center for Life Science "
               "licensed under CC Attribution-Share Alike 2.1 Japan; "
               "female pelvis and organs adapted from the HuBMAP Human Reference Atlas "
               "3D Reference Object Library, licensed under CC Attribution 4.0; "
               "female skin from the NAVER LABS Europe Anny body model (CC0 assets)")
TRANSFORMS = Path(__file__).with_name("hra_transforms.json")
FEMALE_SKIN = Path(__file__).with_name("female_skin.npz")
MIN_TRIS = 40  # floor per element so small bones survive decimation


def load_tables(root):
    concepts = {}
    for table in ("isa_element_parts.txt", "partof_element_parts.txt"):
        for line in (root / table).read_text().splitlines()[1:]:
            _, name, fj = line.split("\t")
            concepts.setdefault(name.lower(), set()).add(fj)
    return concepts


def index_elements(root):
    files = {}
    for sub in ("partof_BP3D_4.0_obj_99", "isa_BP3D_4.0_obj_99"):
        for path in sorted((root / sub).glob("*.obj")):
            files[path.stem] = path
    names = {}
    for fj, path in files.items():
        with path.open() as f:
            for line in f:
                if line.startswith("# English name"):
                    names[fj] = line.split(":", 1)[1].strip().lower()
                    break
    return files, names


def resolve(selectors, concepts, names):
    found = set()
    for sel in selectors:
        if sel.startswith("re:"):
            rx = re.compile(sel[3:])
            found |= {fj for fj, n in names.items() if rx.search(n)}
        else:
            found |= concepts.get(sel, set())
    return found


def read_obj(path):
    verts, faces = [], []
    with path.open() as f:
        for line in f:
            if line.startswith("v "):
                verts.append(line.split()[1:4])
            elif line.startswith("f "):
                idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
                faces += [(idx[0], idx[i], idx[i + 1]) for i in range(1, len(idx) - 1)]
    return np.array(verts, dtype=np.float64), np.array(faces, dtype=np.int64)


def to_body_space(v):
    # BodyParts3D: mm, +x = patient's left, -y = anterior, +z = up.
    # Output: metres, y up, +z out of the chest, +x = patient's left
    # (viewer's right when facing the body). Pure rotation, so winding holds.
    return np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1) / 1000.0


def decimate(meshes, budget):
    total = sum(len(f) for _, f in meshes)
    out_v, out_f, base = [], [], 0
    for v, f in meshes:
        keep = max(MIN_TRIS, int(budget * len(f) / total))
        if len(f) > keep:
            v, f = fast_simplification.simplify(v, f, 1 - keep / len(f))
        out_v.append(v)
        out_f.append(f + base)
        base += len(v)
    return np.concatenate(out_v), np.concatenate(out_f)


def build_mesh(elements, files, budget):
    v, f = decimate([read_obj(files[fj]) for fj in sorted(elements)], budget)
    return to_body_space(v), f


def build_hra_mesh(hra_dir, sources, budget, fit):
    """Merge the GLB nodes whose names match, then place them on our body."""
    nodes = [(name, v, f) for file, pattern in sources
             for name, v, f in glb.load(Path(hra_dir) / f"{file}.glb")
             if re.search(pattern, name)]
    v, f = decimate([(v, f) for _, v, f in nodes], budget)
    s, r, t = fit["scale"], np.array(fit["rotation"]), np.array(fit["translation"])
    return s * v @ r.T + t, f, [name for name, _, _ in nodes]


def b64(arr):
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode()


def build_parts(root, hra_dir, female_skin=True):
    """Every part of both bodies, decimated, in body space (before centring):
    a list of (id, system, kind, sex, elements, verts, faces)."""
    root = Path(root)
    concepts = load_tables(root)
    files, names = index_elements(root)

    # A BodyParts3D part the female body replaces, or lacks, is male-only.
    male = MALE_ONLY | {pid for pid, *_ in HRA_TARGETS}
    claimed, built = set(BAD_ELEMENTS), []
    for kind, table in (("target", TARGETS), ("context", CONTEXT)):
        for pid, system, budget, selectors in table:
            elements = (resolve(selectors, concepts, names) & files.keys()) - claimed
            if not elements:
                print(f"WARNING: {pid}: no elements", file=sys.stderr)
                continue
            claimed |= elements
            v, f = build_mesh(elements, files, budget)
            built.append((pid, system, kind, "male" if pid in male else None, elements, v, f))
            print(f"{pid:20s} {len(elements):4d} elements {len(f):6d} tris")

    fits = json.loads(TRANSFORMS.read_text())
    for pid, system, budget, region, sources in HRA_TARGETS:
        v, f, nodes = build_hra_mesh(hra_dir, sources, budget, fits[region])
        built.append((pid, system, "target", "female", nodes, v, f))
        print(f"{pid:20s} {len(nodes):4d} HRA nodes {len(f):5d} tris (female)")

    if female_skin:
        skin = np.load(FEMALE_SKIN)
        budget = next(b for pid, _, b, _ in CONTEXT if pid == "skin")
        v, f = decimate([(skin["vertices"], skin["faces"])], budget)
        built.append(("skin", "integumentary", "context", "female", ["anny"], v, f))
        print(f"{'skin':20s}    Anny       {len(f):5d} tris (female)")
    return built


def main(root, hra_dir, out):
    built = build_parts(root, hra_dir)
    allv = np.concatenate([b[5] for b in built])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    center = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    lo, hi = lo - center, hi - center
    scale = (hi - lo) / 65535.0

    parts = []
    for pid, system, kind, sex, elements, v, f in built:
        q = np.round((v - center - lo) / scale).astype(np.uint16)
        idx = f.astype(np.uint16 if len(v) < 65536 else np.uint32)
        parts.append({
            "id": pid, "system": system, "kind": kind, **({"sex": sex} if sex else {}),
            "elements": sorted(elements),
            "positions": b64(q), "indices": b64(idx), "index32": idx.dtype == np.uint32,
        })

    data = {"attribution": ATTRIBUTION, "min": lo.round(6).tolist(),
            "scale": scale.tolist(), "parts": parts}
    Path(out).write_text("// Generated by build/build_model.py - do not edit by hand.\n"
                         f"window.BODY_DATA = {json.dumps(data, separators=(',', ':'))};\n")
    tris = sum(len(b[6]) for b in built)
    print(f"\n{len(built)} parts, {tris} tris, {Path(out).stat().st_size / 1e6:.1f} MB -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
