# Image Splitter Test Results

Recorded test evidence for the current prototype state.

## Run date

- 2026-03-06

## Test 1: Two-block split + quality mode comparison

Command log:

- `test_results/quality_mode_compare.log`

Key assertions:

- Base mode returns exactly 2 components.
- Quality mode returns exactly 2 components.
- Quality mode is enabled in manifest settings.
- Quality mode outputs are at least 2x dimensions vs base outputs.

Result: **PASS**

Artifacts:

- Base manifest: `test_results/base_output/manifest.json`
- Quality manifest: `test_results/quality_output/manifest.json`
- Base output images:
  - `test_results/base_output/icon_001.png`
  - `test_results/base_output/icon_002.png`
- Quality output images:
  - `test_results/quality_output/icon_001.png`
  - `test_results/quality_output/icon_002.png`

## Test 2: Three-component baseline split

Command log:

- `test_results/three_component_split.log`

Key assertions:

- Split returns exactly 3 components.
- Output files `icon_001.png`..`icon_003.png` are created.

Result: **PASS**

Artifacts:

- Manifest: `test_results/sample_three_output/manifest.json`
- Output images:
  - `test_results/sample_three_output/icon_001.png`
  - `test_results/sample_three_output/icon_002.png`
  - `test_results/sample_three_output/icon_003.png`

## Test 3: Quality-pipeline smoke run after refactor

Command summary:

- `python3 split_icons.py sample_input.png --output-dir smoke_sample --quality-mode`
- `python3 split_icons.py two_block_code_sample.png --output-dir smoke_blocks --quality-mode`

Key assertions:

- Transparent sample still returns exactly 3 components.
- Opaque two-block sample still returns exactly 2 components.
- Quality manifests include `edge_softness`, `isolate_foreground`, and output dimensions.
- Quality mode outputs are trimmed and upscaled relative to source component bounds.

Result: **PASS**

Artifacts:

- Smoke sample manifest: `prototype/smoke_sample/manifest.json`
- Smoke block manifest: `prototype/smoke_blocks/manifest.json`

## Test 4: Browser MVP endpoint smoke run

Command summary:

- local server started with `python3 web_app.py --host 127.0.0.1 --port 8011`
- `POST /api/preview` on `sample_input.png`
- `POST /api/split` on `two_block_code_sample.png`

Key assertions:

- Preview endpoint returns correct component metadata for uploaded image.
- Split endpoint returns expected preview count and a zip download URL.

Result: **PASS**
