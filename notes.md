# Notes

- Primary use case: split one image into per-icon files.
- Input examples: sticker sheets, sprite sheets, logo variations.
- Desired output: `icon_001.png`, `icon_002.png`, etc.

## Quality goals

- Minimal manual work.
- Accurate crops.
- Stable output ordering (left-to-right, top-to-bottom).
- Clean transparent outputs even from opaque-background source images.
- Sharper exports after resize without white/gray halo edges.

## Potential edge cases

- Icons touching each other (merges into one component).
- Non-uniform backgrounds.
- Anti-aliased edges and shadows.
- Very small artifacts/noise.

## Current prototype strengths

- Handles transparent source images well.
- Can isolate foreground from flat opaque backgrounds into transparent PNGs.
- Quality mode now trims transparent padding, cleans alpha, uses premultiplied upscale, and sharpens RGB only.
- Browser MVP works locally for upload -> preview -> split -> zip download.
