# Image Splitter

Split separate icons, logos, or marks from a single image into individual PNG files.

This repo currently ships:

- a local browser app for previewing bounds and exporting split PNGs
- a CLI for batch-style local runs
- a Python image-processing pipeline built around connected-component detection

## Live app

Production:

`https://skill-deploy-ms3se8xl4f.vercel.app`

## Project layout

- `prototype/` - the current app, deploy config, tests, and image splitting logic
- `prototype/web_app.py` - local Python server
- `prototype/web/index.html` - browser UI
- `prototype/split_icons.py` - detection and crop pipeline

## Quick start

From `prototype/`:

1. `python3 -m pip install -r requirements.txt`
2. `python3 web_app.py --port 8008`
3. Open `http://127.0.0.1:8008`

You can also run the CLI directly:

`python3 split_icons.py /path/to/your/image.png --output-dir out_icons`

## Features

- image upload with browser preview
- detection bounds overlay before export
- isolated PNG export plus manifest zip
- settings for background sensitivity, grouping, and quality
- advanced controls for fine-tuning cleanup and export behavior
- local automated tests for health, happy path, and invalid uploads

## Deploy

The Vercel-linked app lives in `prototype/`.

Preview deploy:

`cd prototype && npx vercel deploy -y`

Production deploy:

`cd prototype && npx vercel deploy --prod -y`

## Tests

From `prototype/`:

`python3 -m unittest test_web_app.py`

## Notes

- works best when objects are visually separated from each other
- touching objects are treated as one component
- textured or noisy backgrounds may still need preprocessing

For implementation details, runtime safeguards, Docker usage, and the full local workflow, see `prototype/README.md`.
