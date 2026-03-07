# Image icon splitter app

## Snapshot
- **Status:** incubating
- **Created:** 2026-03-06
- **Owner:** you

## Problem
I have one image with multiple icons/characters and want an app that can
separate each object into its own file automatically.

## Proposed approach
Build a local CLI-first image splitter:

1. Load an image and detect foreground objects.
2. Find connected components (one per icon/object).
3. Crop each component to a tight bounding box.
4. Save each crop as its own PNG file.
5. Output a manifest file with coordinates and file names.

### MVP assumptions

- Works best when icons are separated by empty background space.
- Prioritize PNG with transparent or uniform backgrounds.
- Keep this tool local and offline.

## Next experiment
Run a prototype on a synthetic image with 2-3 separated shapes and verify:

- Correct number of output files.
- Correct crop bounds.
- Useful file naming and output metadata.

If this works, test on real icon sheets and add optional preprocessing for
noisy backgrounds.
