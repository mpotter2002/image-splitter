# Prototype: Image Icon Splitter

This prototype splits disconnected objects in one image into separate PNG files.
It now supports both a CLI workflow and a small local browser MVP.

## Requirements

- Python 3
- Pillow (`pip install pillow`)

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

## MVP limits

- If two icons touch, they become one component.
- Complex textured backgrounds may require preprocessing.

## Browser MVP

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

## Recorded test evidence

- See `test_results/TEST_RESULTS.md` for committed command logs, manifests, and
  sample output files.
