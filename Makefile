# Every build and dev command, with the source data paths filled in.
# `make help` lists them. Source data lives outside the repo in $(DATA)
# (see tools/fetch_data.sh); override with `make model DATA=/elsewhere`.
# tools/paths.py holds the same layout for the Python tools.

DATA ?= $(HOME)/Projects/datasets
BP3D := $(DATA)/bodyparts3d/ex
HRA := $(DATA)/hra-female
ZA := $(DATA)/z-anatomy
ZA_OBJ := $(ZA)/obj
BLENDER ?= blender
PY := .venv/bin/python
export ANATOMY_DATA := $(DATA)

.PHONY: help setup setup-anny fetch model export-zanatomy fit-hra fit-zanatomy fit-anny \
        check shot clean-venv

help:  ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

setup: .venv/.ok  ## Python venv for the build, fits and tools (no torch)
.venv/.ok: build/requirements.txt
	test -x $(PY) || python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r build/requirements.txt
	touch $@

setup-anny: .venv/.anny  ## Add torch and anny, for fit-anny only (~1 GB)
.venv/.anny: .venv/.ok build/requirements-anny.txt
	$(PY) -m pip install -q -r build/requirements-anny.txt
	touch $@

fetch:  ## Download whatever source data is missing from $(DATA)
	tools/fetch_data.sh "$(DATA)"

model: setup  ## Rebuild data/bodydata.js (after editing build/parts_table.py or build_model.py)
	$(PY) build/build_model.py "$(BP3D)" "$(HRA)" "$(ZA_OBJ)" data/bodydata.js

export-zanatomy:  ## Export the Z-Anatomy objects parts_table.py names to OBJ (needs Blender)
	$(BLENDER) -b --factory-startup --disable-autoexec "$(ZA)/Z-Anatomy/Startup.blend" \
		--python build/export_zanatomy.py -- "$(ZA_OBJ)"

fit-hra: setup  ## Refit the HRA female pelvis and breasts (only if those meshes change)
	$(PY) build/fit_hra.py "$(BP3D)" "$(HRA)"

fit-zanatomy: setup  ## Refit Z-Anatomy onto our body (after export-zanatomy)
	$(PY) build/fit_zanatomy.py "$(BP3D)" "$(ZA_OBJ)"

fit-anny: setup-anny  ## Refit the female skin (when the female anatomy changes; slow)
	$(PY) build/fit_anny.py "$(BP3D)" "$(HRA)"

check: setup  ## Validate questions, names and the model in headless Chrome
	$(PY) tools/check.py $(ARGS)

shot: setup  ## Screenshot the app: make shot ARGS="--body female --solo cardiovascular"
	$(PY) tools/shot.py $(ARGS)

clean-venv:  ## Delete .venv
	rm -rf .venv
