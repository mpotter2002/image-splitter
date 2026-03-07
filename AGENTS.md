# AGENTS.md

## Cursor Cloud specific instructions

This is a single-package Python prototype (Image Icon Splitter) with one external dependency: **Pillow**.

### Services

| Service | How to run | Port |
|---|---|---|
| CLI splitter | `python3 prototype/split_icons.py <image> --output-dir <dir>` | N/A |
| Browser MVP | `python3 prototype/web_app.py --host 0.0.0.0 --port 8008` | 8008 |

### Lint / Test / Build

- **Lint:** `ruff check prototype/` (passes clean).
- **Type check:** `pyright prototype/` — currently has pre-existing type errors (prototype has no type annotations); treat these as known.
- **Automated tests:** No test framework is configured. Validation is done via CLI runs and recorded test evidence in `prototype/test_results/TEST_RESULTS.md`.
- **Generate sample images:** `python3 prototype/make_sample_image.py` and `python3 prototype/make_two_block_code_sample.py` (run from `prototype/` directory).

### Caveats

- The web app API expects JSON bodies with base64-encoded data URLs (`image_data_url` field), not multipart form uploads. See `prototype/web_app.py` `read_json_payload()`.
- Sample images (`sample_input.png`, `two_block_code_sample.png`) are `.gitignore`d and must be regenerated via the `make_*` scripts before running tests.
- All Python scripts must be run from the `prototype/` working directory (they use relative imports/paths).
