"""Search the source data, to find what to put in build/parts_table.py.

    tools/sources.py bp3d REGEX       BodyParts3D elements whose English name
                                      matches, and the part that claims each
    tools/sources.py concept REGEX    BodyParts3D IS-A / PART-OF concepts
                                      (usable as plain selectors), with sizes
    tools/sources.py hra FILE [REGEX] nodes of an HRA GLB (FILE: name without
                                      .glb, e.g. pelvis-female); no FILE: list them
    tools/sources.py za REGEX         Z-Anatomy objects (name, type, size, bounds)
    tools/sources.py za --refresh     rebuild the Z-Anatomy index (needs Blender, ~1 min)
    tools/sources.py part ID          what a built part in data/bodydata.js is made of

Regexes are case-insensitive. Run with .venv/bin/python (make setup).
Body-space bounds are metres, y up, +x = patient's left, +z anterior.
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import glb  # noqa: E402
from build_model import claim_elements, read_obj, to_body_space  # noqa: E402
from fit_hra import source_index  # noqa: E402
from paths import BODYDATA, BP3D, HRA, ROOT, ZA, ZA_INDEX  # noqa: E402


def bounds(v):
    return f"{np.round(v.min(0), 3).tolist()} .. {np.round(v.max(0), 3).tolist()}"


def bp3d(pattern, with_bounds=True):
    concepts, files, names = source_index(BP3D)
    owner = {fj: pid for pid, (*_, els) in claim_elements(concepts, files, names).items() for fj in els}
    rx = re.compile(pattern, re.I)
    hits = sorted((n, fj) for fj, n in names.items() if rx.search(n))
    for name, fj in hits:
        where = bounds(to_body_space(read_obj(files[fj])[0])) if with_bounds and len(hits) <= 60 else ""
        print(f"{fj:8s} {name:55s} {owner.get(fj, '-'):22s} {where}")
    print(f"{len(hits)} elements" + ("" if len(hits) <= 60 else " (bounds shown for 60 or fewer)"))


def concept(pattern):
    concepts, files, _ = source_index(BP3D)
    rx = re.compile(pattern, re.I)
    for name in sorted(n for n in concepts if rx.search(n)):
        print(f"{len(concepts[name] & files.keys()):5d}  {name}")


def hra(name=None, pattern=""):
    if not name:
        for path in sorted(HRA.glob("*.glb")):
            print(path.stem)
        return
    rx = re.compile(pattern, re.I)
    for node, v, f in glb.load(HRA / f"{name}.glb"):
        if rx.search(node):
            print(f"{node:60s} {len(f):7d} tris  {bounds(v)}")


def za(pattern):
    if pattern == "--refresh":
        subprocess.run(["blender", "-b", "--factory-startup", "--disable-autoexec",
                        str(ZA / "Z-Anatomy" / "Startup.blend"),
                        "--python", str(ROOT / "tools" / "za_index.py"), "--", str(ZA_INDEX)],
                       check=True, stdout=subprocess.DEVNULL)
        print(f"-> {ZA_INDEX}")
        return
    if not ZA_INDEX.exists():
        sys.exit("no Z-Anatomy index yet: run tools/sources.py za --refresh")
    rx = re.compile(pattern, re.I)
    with ZA_INDEX.open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if rx.search(row["name"]):
                lo = [row[k] for k in ("min_x", "min_y", "min_z")]
                hi = [row[k] for k in ("max_x", "max_y", "max_z")]
                print(f"{row['name']:55s} {row['type']:6s} {row['verts']:>6s}  "
                      f"[{', '.join(lo)}] .. [{', '.join(hi)}]  {row['collections']}")


def part(pid):
    text = BODYDATA.read_text()
    data = json.loads(text[text.index("{"):text.rindex("}") + 1])
    for p in (p for p in data["parts"] if p["id"] == pid):
        tris = len(np.frombuffer(__import__("base64").b64decode(p["indices"]),
                                 np.uint32 if p["index32"] else np.uint16)) // 3
        print(f"{p['id']} ({p['system']}, {p['kind']}, {p.get('sex', 'both bodies')}): "
              f"{tris} tris, {len(p['elements'])} elements")
        _, _, names = source_index(BP3D)
        for el in p["elements"]:
            print(f"  {el:12s} {names.get(el, '')}")


def main(args):
    commands = {"bp3d": bp3d, "concept": concept, "hra": hra, "za": za, "part": part}
    if not args or args[0] not in commands:
        sys.exit(__doc__)
    commands[args[0]](*args[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
