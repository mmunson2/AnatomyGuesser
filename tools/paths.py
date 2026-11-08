"""Where things are, for the tools. The Makefile has the same layout."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("ANATOMY_DATA", Path.home() / "Projects" / "datasets"))
BP3D = DATA / "bodyparts3d" / "ex"
HRA = DATA / "hra-female"
ZA = DATA / "z-anatomy"
ZA_OBJ = ZA / "obj"
# All Z-Anatomy object names, with type and bounds: made by `tools/sources.py za --refresh`.
ZA_INDEX = ZA / "objects.tsv"
# Source pages fetched by tools/page.py, as text.
PAGES = DATA / "pages"
INDEX_HTML = ROOT / "index.html"
BODYDATA = ROOT / "data" / "bodydata.js"
