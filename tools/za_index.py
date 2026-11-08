"""Write every Z-Anatomy object's name, type, size and bounds to a TSV. Runs
inside Blender; `tools/sources.py za --refresh` runs it:

    blender -b --factory-startup --disable-autoexec Startup.blend \
        --python tools/za_index.py -- <out.tsv>

Bounds are Blender world coordinates (metres, z up, +x = patient's left,
+y posterior), from each object's bounding box.
"""

import sys

import bpy
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
with open(out, "w") as f:
    f.write("name\ttype\tverts\tmin_x\tmin_y\tmin_z\tmax_x\tmax_y\tmax_z\tcollections\n")
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = [min(c[i] for c in corners) for i in range(3)]
        hi = [max(c[i] for c in corners) for i in range(3)]
        verts = len(ob.data.vertices) if ob.type == "MESH" else ""
        cols = ",".join(c.name for c in ob.users_collection)
        f.write("\t".join([ob.name, ob.type, str(verts)] + [f"{x:.4f}" for x in lo + hi] + [cols]) + "\n")
print(f"-> {out}")
