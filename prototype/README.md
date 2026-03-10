# Image Icon Splitter

Split disconnected objects in one image into separate PNG files.
The project includes both a CLI workflow and a local browser app.

## Requirements

- Python 3
- Install dependencies with `python3 -m pip install -r requirements.txt`

## Quick run

From this directory:

1. `python3 make_sample_image.py`
2. `python3 split_icons.py sample_input.png --output-dir out_sample`

Expected output:

- `out_sample/icon_001.png`
- `out_sample/icon_002.png`
- `out_sample/icon_003.png`
- `out_sample/manifest.json`

## Code-block style sample (2 outputs)

To match your test style (filled code block + outlined code block):

1. `python3 make_two_block_code_sample.py`
2. `python3 split_icons.py two_block_code_sample.png --output-dir out_two_blocks`

Expected output:

- `out_two_blocks/icon_001.png`
- `out_two_blocks/icon_002.png`

`--merge-enclosed` is enabled by default, so disconnected inner strokes inside
an outlined block are grouped into that block's crop.

## Real image run

`python3 split_icons.py /path/to/your/image.png --output-dir out_icons`

Useful flags:

- `--min-pixels 50` to ignore tiny noise.
- `--padding 4` to include margin around crops.
- `--color-tolerance 20` for non-transparent backgrounds.
- `--edge-softness 24` for smoother alpha falloff on opaque backgrounds.
- `--preserve-background` to keep the original background instead of transparent output.

### Quality mode (recommended)

For crisper exports:

`python3 split_icons.py /path/to/your/image.png --output-dir out_icons --quality-mode`

`--quality-mode` applies:

- foreground isolation for opaque images when possible
- upscale to at least 2x using a premultiplied RGBA resize
- alpha cleanup to remove edge haze
- transparent-edge trim
- RGB-only unsharp pass for clearer strokes without alpha fringe artifacts

Manual quality controls:

- `--upscale 3`
- `--resample bicubic`
- `--trim-transparent`
- `--alpha-clean-threshold 3`
- `--unsharp --unsharp-radius 1.2 --unsharp-percent 160 --unsharp-threshold 2`

## Current limits

- If two icons touch, they become one component.
- Complex textured backgrounds may require preprocessing.

## Browser app

Run the local web app:

`python3 web_app.py --port 8008`

Then open:

`http://127.0.0.1:8008`

Browser flow currently supports:

- upload image
- choose detection and quality settings
- preview detected bounding boxes
- split outputs into isolated PNGs
- preview generated crops
- download a zip containing PNGs + manifest
- persist last-used settings in local storage

### Tests

Run the automated server tests:

`python3 -m unittest test_web_app.py`

### Runtime safeguards

The web app now includes basic public-instance guardrails:

- upload size limit via `IMAGE_SPLITTER_MAX_UPLOAD_BYTES` (default `12 MB`)
- request body limit via `IMAGE_SPLITTER_MAX_REQUEST_BYTES` (default `18 MB`)
- capped temporary download retention via `IMAGE_SPLITTER_MAX_STORED_DOWNLOADS` (default `24`)
- temporary zip downloads stored outside process memory
- user-safe error messages for invalid uploads instead of raw exceptions

Health check:

`GET /healthz`

### Docker deploy

Build:

`docker build -t image-splitter .`

Run:

`docker run --rm -p 8008:8008 image-splitter`

The container starts:

`python web_app.py --host 0.0.0.0 --port 8008`

### Vercel preview deploy

This folder now includes a Vercel Python entrypoint in [api/index.py](/Users/michaelpotter/ClaudeCowork/projects/image-splitter/prototype/api/index.py) and routing in [vercel.json](/Users/michaelpotter/ClaudeCowork/projects/image-splitter/prototype/vercel.json).

From this directory, deploy a preview with:

`vercel deploy . -y`

If the Vercel CLI is unavailable, use the Codex Vercel deploy skill fallback script.

## Recorded test evidence

- See `test_results/TEST_RESULTS.md` for committed command logs, manifests, and
  sample output files.
