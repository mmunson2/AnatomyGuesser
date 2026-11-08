"""Fit the Z-Anatomy meshes onto the BodyParts3D body; writes zanatomy_transforms.json.

    python3 build/fit_zanatomy.py <bp3d_dir> <za_obj_dir>

<za_obj_dir> is the output of export_zanatomy.py. Needs numpy and scipy.
Z-Anatomy is built on BodyParts3D, but its skeleton has been remeshed and
moved by several centimetres, differently in different places (its legs
are turned ~12 degrees, its head tilted ~6 degrees on its neck), so each
region in ZANATOMY_FIT gets its own similarity transform: symmetric ICP of
the Z-Anatomy bones onto ours (see fit_hra.py). ZANATOMY_BLENDS mix two of
them by height. Afterwards it reports the gaps where the new arteries
should meet each other or ours.

Only rerun this when the source meshes change; build_model.py reads the
saved transforms and doesn't need scipy.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from build_model import placer, read_obj, za_to_body_space
from fit_hra import icp, ours, report, surface_points
from parts_table import ZANATOMY_BLENDS, ZANATOMY_FIT

OUT = Path(__file__).with_name("zanatomy_transforms.json")

# Where vessels should meet: (Z-Anatomy object, region, what it joins), the
# last either a Z-Anatomy (object, region) or BodyParts3D selectors.
JOINS = [
    ("Left common carotid artery", "head_neck", ["re:^left common carotid artery$"]),
    ("Internal carotid artery.l", "head_neck", ["re:^left posterior communicating artery$"]),
    ("External carotid artery.l", "head_neck", ("Left common carotid artery", "head_neck")),
    ("Facial artery.l", "head_neck", ("External carotid artery.l", "head_neck")),
    ("Superficial temporal artery.l", "head_neck", ("External carotid artery.l", "head_neck")),
    ("Transverse facial artery.l", "head_neck", ("Superficial temporal artery.l", "head_neck")),
    ("Maxillary artery.l", "head_neck", ("External carotid artery.l", "head_neck")),
    ("Occipital artery.l", "head_neck", ("External carotid artery.l", "head_neck")),
    ("Fibular artery.l", "leg_left", ["re:^left posterior tibial artery$"]),
    ("Fibular artery.r", "leg_right", ["re:^right posterior tibial artery$"]),
    ("External jugular vein.l", "head_neck", ["re:^left subclavian vein$"]),
    ("External jugular vein.r", "head_neck", ["re:^right subclavian vein$"]),
]


def za(obj_dir, name):
    v, f = read_obj(Path(obj_dir) / f"{name}.obj")
    return za_to_body_space(v), f


def main(root, obj_dir):
    root = Path(root)
    fits = {}
    for region, (bones, selectors) in ZANATOMY_FIT.items():
        src = surface_points([za(obj_dir, name) for name in bones])
        s, r, t, err = icp(src, ours(root, selectors), 1.0)
        report(region, s, r, t, err)
        fits[region] = {"scale": s, "rotation": np.round(r, 8).tolist(),
                        "translation": np.round(t, 8).tolist()}
    for region, (lower, upper, low_obj, high_obj) in ZANATOMY_BLENDS.items():
        fits[region] = {"blend": [lower, upper],
                        "from": round(float(za(obj_dir, low_obj)[0][:, 1].mean()), 5),
                        "to": round(float(za(obj_dir, high_obj)[0][:, 1].mean()), 5)}

    placed = lambda name, region: placer(fits, region)(za(obj_dir, name)[0])
    for name, region, other in JOINS:
        target = placed(*other) if isinstance(other, tuple) else ours(root, other)
        gap = cKDTree(target).query(placed(name, region))[0].min()
        label = other[0] if isinstance(other, tuple) else other[0][4:-1]  # "re:^...$"
        print(f"  {name} to {label}: {gap * 1000:.1f} mm")

    OUT.write_text(json.dumps(fits, indent=2) + "\n")
    print(f"-> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python3 build/fit_zanatomy.py <bp3d_dir> <za_obj_dir>")
    main(*sys.argv[1:3])
