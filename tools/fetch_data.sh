#!/usr/bin/env bash
# Download the model's source data into <data_dir> (default
# ~/Projects/datasets), skipping anything already there:
#
#   bodyparts3d/ex/   BodyParts3D 4.0 element tables + both OBJ sets (~870 MB)
#   hra-female/       HRA Visible Human female GLBs named in HRA_TARGETS, plus
#                     skin-female (used by fit_hra.py)
#   z-anatomy/        Z-Anatomy.zip and its Startup.blend (~430 MB)
#
# Then `make export-zanatomy` (Blender) makes z-anatomy/obj/. HRA files come
# from each organ's `latest` version: if a download replaces a file the fits
# were made with, rerun `make fit-hra` and `make fit-anny`.
set -euo pipefail
DATA="${1:-$HOME/Projects/datasets}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

get() {  # url dest
  [ -s "$2" ] && return
  echo "  $2"
  mkdir -p "$(dirname "$2")"
  curl -fsSL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"
}

echo "BodyParts3D -> $DATA/bodyparts3d"
BP=https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST
for f in isa_element_parts.txt partof_element_parts.txt; do
  get "$BP/$f" "$DATA/bodyparts3d/$f"
  mkdir -p "$DATA/bodyparts3d/ex"
  [ -s "$DATA/bodyparts3d/ex/$f" ] || cp "$DATA/bodyparts3d/$f" "$DATA/bodyparts3d/ex/$f"
done
for set in isa partof; do
  zip="$DATA/bodyparts3d/${set}_BP3D_4.0_obj_99.zip"
  get "$BP/${set}_BP3D_4.0_obj_99.zip" "$zip"
  [ -d "$DATA/bodyparts3d/ex/${set}_BP3D_4.0_obj_99" ] || unzip -q "$zip" -d "$DATA/bodyparts3d/ex"
done

echo "HRA female -> $DATA/hra-female"
names=$(cd "$HERE/build" && python3 -c '
from parts_table import HRA_TARGETS
print("\n".join(sorted({f for *_, src in HRA_TARGETS for f, _ in src} | {"skin-female"})))')
for name in $names; do
  dest="$DATA/hra-female/$name.glb"
  [ -s "$dest" ] && continue
  base="https://cdn.humanatlas.io/digital-objects/ref-organ/$name/latest"
  get "$base/graph.json" "$DATA/hra-female/$name.graph.json"
  url=$(grep -o '"https://[^"]*\.glb"' "$DATA/hra-female/$name.graph.json" | head -1 | tr -d '"')
  get "$url" "$dest"
done

echo "Z-Anatomy -> $DATA/z-anatomy"
get https://raw.githubusercontent.com/Z-Anatomy/Models-of-human-anatomy/master/Z-Anatomy.zip \
  "$DATA/z-anatomy/Z-Anatomy.zip"
[ -s "$DATA/z-anatomy/Z-Anatomy/Startup.blend" ] ||
  unzip -q "$DATA/z-anatomy/Z-Anatomy.zip" Z-Anatomy/Startup.blend -d "$DATA/z-anatomy"
[ -d "$DATA/z-anatomy/obj" ] || echo "  no z-anatomy/obj yet: run make export-zanatomy"
echo done
