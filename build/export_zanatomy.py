"""Export the Z-Anatomy objects the build needs to OBJ files. Runs inside Blender:

    blender -b --factory-startup --disable-autoexec <za_dir>/Startup.blend \
        --python build/export_zanatomy.py -- <za_dir>/obj

Startup.blend is in Z-Anatomy.zip from
https://github.com/Z-Anatomy/Models-of-human-anatomy (CC BY-SA 4.0). Keep
--disable-autoexec: the file carries its own add-on script, which we don't
need. Writes one <object name>.obj per object named in ZANATOMY_TARGETS,
ZANATOMY_FIT and ZANATOMY_BLENDS, in Blender's world frame (metres, z up,
+x = patient's left, +y posterior). Many Z-Anatomy vessels are bevelled curves; these are written
as the tube mesh Blender evaluates for them.
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from parts_table import ZANATOMY_BLENDS, ZANATOMY_FIT, ZANATOMY_TARGETS  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=True)
wanted = {entry[0] for *_, objects in ZANATOMY_TARGETS for entry in objects}
wanted |= {name for bones, _ in ZANATOMY_FIT.values() for name in bones}
wanted |= {name for *_, a, b in ZANATOMY_BLENDS.values() for name in (a, b)}

depsgraph = bpy.context.evaluated_depsgraph_get()
missing = wanted - set(bpy.data.objects.keys())
if missing:
    sys.exit(f"not in the .blend: {sorted(missing)}")
for name in sorted(wanted):
    ob = bpy.data.objects[name].evaluated_get(depsgraph)
    mesh = ob.to_mesh()
    mesh.calc_loop_triangles()
    world = ob.matrix_world
    with (out / f"{name}.obj").open("w") as f:
        f.write(f"# {name}, Z-Anatomy (CC BY-SA 4.0)\n")
        for v in mesh.vertices:
            x, y, z = world @ v.co
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for tri in mesh.loop_triangles:
            a, b, c = tri.vertices
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")
    print(f"{name:50s} {len(mesh.loop_triangles):6d} tris")
    ob.to_mesh_clear()
