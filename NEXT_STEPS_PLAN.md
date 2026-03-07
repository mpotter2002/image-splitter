# Next Steps Plan

## 1) Real-world validation (highest priority)

- Test on 10 real images with varied backgrounds and icon styles.
- Measure:
  - correct split count
  - crop tightness
  - visual quality (edge clarity)
- Record per-image command settings that worked best.

Success target: at least 8/10 images need no manual correction.

## 2) Smarter background handling

- Add optional preprocessing:
  - grayscale threshold mode
  - blur + threshold mode
  - auto foreground estimation mode

Success target: difficult backgrounds produce clean masks without manual editing.

## 3) Touching-icon separation

- Add optional watershed/distance transform split when components touch.
- Keep it opt-in via flag for safety.

Success target: touching icons can be separated on known test samples.

## 4) UX improvements

- Add a single-command batch mode for directories.
- Add output naming templates (`{base}_{index}`).
- Add dry-run mode that only writes manifest + preview boxes.

Success target: process a folder with one command and predictable names.

## 5) Productization checkpoint

- Package as:
  - CLI tool first
  - browser UI flow second (drag-and-drop)
- Decide whether to graduate idea to standalone repo.

Success target: clear go/no-go decision with sample outputs and user feedback.

## 6) Browser MVP follow-up

- Current status:
  - local upload UI exists
  - detection preview exists
  - split output preview exists
  - zip download exists
  - settings persist in local storage
- Next browser improvements:
  - drag-and-drop upload
  - side-by-side original vs selected crop inspection
  - per-run manifest viewer
  - optional before/after background isolation toggle

Tech direction:

- Frontend: React + simple upload/preview UI.
- Backend: lightweight Python API wrapper around current splitter.
- Packaging: run local first, then optional hosted version later.

Success target: end-to-end browser flow completes in under 20 seconds for a
typical icon sheet and produces the same split quality as CLI mode.
