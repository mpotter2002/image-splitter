#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from PIL import Image, ImageFilter


@dataclass
class Component:
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    pixel_count: int
    mean_rgb: Tuple[float, float, float]

    @property
    def width(self) -> int:
        return self.x_max - self.x_min + 1

    @property
    def height(self) -> int:
        return self.y_max - self.y_min + 1

    def padded(self, width: int, height: int, padding: int) -> "Component":
        return Component(
            x_min=max(0, self.x_min - padding),
            y_min=max(0, self.y_min - padding),
            x_max=min(width - 1, self.x_max + padding),
            y_max=min(height - 1, self.y_max + padding),
            pixel_count=self.pixel_count,
            mean_rgb=self.mean_rgb,
        )


@dataclass
class AnalysisResult:
    width: int
    height: int
    source_has_transparency: bool
    components: List[Component]
    alpha_values: List[int]


@dataclass
class RenderedCrop:
    file_name: str
    image: Image.Image
    component: Component


DEFAULT_SETTINGS: Dict[str, object] = {
    "alpha_threshold": 10,
    "color_tolerance": 12,
    "edge_softness": 18,
    "min_pixels": 25,
    "padding": 2,
    "merge_enclosed": True,
    "enclosed_margin": 2,
    "isolate_foreground": True,
    "quality_mode": False,
    "upscale": 1,
    "resample": "lanczos",
    "trim_transparent": False,
    "alpha_clean_threshold": 0,
    "unsharp": False,
    "unsharp_radius": 1.0,
    "unsharp_percent": 140,
    "unsharp_threshold": 2,
}


RESAMPLE_METHODS = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split disconnected icons/objects from one image into separate files."
    )
    parser.add_argument("input_image", help="Path to source image.")
    parser.add_argument(
        "--output-dir",
        default="output_icons",
        help="Directory where split icon files are saved.",
    )
    parser.add_argument(
        "--alpha-threshold",
        type=int,
        default=int(DEFAULT_SETTINGS["alpha_threshold"]),
        help="Foreground threshold for alpha channel (0-255) when transparency exists.",
    )
    parser.add_argument(
        "--color-tolerance",
        type=int,
        default=int(DEFAULT_SETTINGS["color_tolerance"]),
        help="RGB distance tolerance from top-left background color when alpha is fully opaque.",
    )
    parser.add_argument(
        "--edge-softness",
        type=int,
        default=int(DEFAULT_SETTINGS["edge_softness"]),
        help="Soft transition range used when isolating opaque-image backgrounds.",
    )
    parser.add_argument(
        "--min-pixels",
        type=int,
        default=int(DEFAULT_SETTINGS["min_pixels"]),
        help="Ignore components smaller than this pixel count.",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=int(DEFAULT_SETTINGS["padding"]),
        help="Padding pixels added around each crop.",
    )
    parser.add_argument(
        "--merge-enclosed",
        dest="merge_enclosed",
        action="store_true",
        default=bool(DEFAULT_SETTINGS["merge_enclosed"]),
        help="Merge components whose bounding box is enclosed by another component.",
    )
    parser.add_argument(
        "--no-merge-enclosed",
        dest="merge_enclosed",
        action="store_false",
        help="Disable enclosed component merging.",
    )
    parser.add_argument(
        "--enclosed-margin",
        type=int,
        default=int(DEFAULT_SETTINGS["enclosed_margin"]),
        help="Allowed bbox margin when checking enclosed components.",
    )
    parser.add_argument(
        "--preserve-background",
        dest="isolate_foreground",
        action="store_false",
        default=bool(DEFAULT_SETTINGS["isolate_foreground"]),
        help="Keep the detected background pixels instead of making them transparent.",
    )
    parser.add_argument(
        "--quality-mode",
        action="store_true",
        help="Enable quality preset (alpha cleanup + trim + premultiplied upscale + RGB unsharp).",
    )
    parser.add_argument(
        "--upscale",
        type=int,
        default=int(DEFAULT_SETTINGS["upscale"]),
        help="Output scale multiplier per crop (1 keeps original size).",
    )
    parser.add_argument(
        "--resample",
        choices=sorted(RESAMPLE_METHODS.keys()),
        default=str(DEFAULT_SETTINGS["resample"]),
        help="Resampling method for upscale.",
    )
    parser.add_argument(
        "--trim-transparent",
        action="store_true",
        help="Trim fully/mostly transparent outer pixels around each crop.",
    )
    parser.add_argument(
        "--alpha-clean-threshold",
        type=int,
        default=int(DEFAULT_SETTINGS["alpha_clean_threshold"]),
        help="Set alpha values <= threshold to fully transparent.",
    )
    parser.add_argument(
        "--unsharp",
        action="store_true",
        help="Apply an RGB-only unsharp mask after resize.",
    )
    parser.add_argument(
        "--unsharp-radius",
        type=float,
        default=float(DEFAULT_SETTINGS["unsharp_radius"]),
        help="Unsharp mask radius.",
    )
    parser.add_argument(
        "--unsharp-percent",
        type=int,
        default=int(DEFAULT_SETTINGS["unsharp_percent"]),
        help="Unsharp mask strength percent.",
    )
    parser.add_argument(
        "--unsharp-threshold",
        type=int,
        default=int(DEFAULT_SETTINGS["unsharp_threshold"]),
        help="Unsharp mask threshold.",
    )
    return parser


def settings_from_args(args: argparse.Namespace) -> Dict[str, object]:
    return normalize_settings(
        {
            "alpha_threshold": args.alpha_threshold,
            "color_tolerance": args.color_tolerance,
            "edge_softness": args.edge_softness,
            "min_pixels": args.min_pixels,
            "padding": args.padding,
            "merge_enclosed": args.merge_enclosed,
            "enclosed_margin": args.enclosed_margin,
            "isolate_foreground": args.isolate_foreground,
            "quality_mode": args.quality_mode,
            "upscale": args.upscale,
            "resample": args.resample,
            "trim_transparent": args.trim_transparent,
            "alpha_clean_threshold": args.alpha_clean_threshold,
            "unsharp": args.unsharp,
            "unsharp_radius": args.unsharp_radius,
            "unsharp_percent": args.unsharp_percent,
            "unsharp_threshold": args.unsharp_threshold,
        }
    )


def normalize_settings(overrides: Dict[str, object] | None = None) -> Dict[str, object]:
    settings = dict(DEFAULT_SETTINGS)
    if overrides:
        settings.update({key: value for key, value in overrides.items() if value is not None})

    settings["alpha_threshold"] = max(0, min(255, int(settings["alpha_threshold"])))
    settings["color_tolerance"] = max(0, int(settings["color_tolerance"]))
    settings["edge_softness"] = max(0, int(settings["edge_softness"]))
    settings["min_pixels"] = max(1, int(settings["min_pixels"]))
    settings["padding"] = max(0, int(settings["padding"]))
    settings["merge_enclosed"] = bool(settings["merge_enclosed"])
    settings["enclosed_margin"] = max(0, int(settings["enclosed_margin"]))
    settings["isolate_foreground"] = bool(settings["isolate_foreground"])
    settings["quality_mode"] = bool(settings["quality_mode"])
    settings["upscale"] = max(1, int(settings["upscale"]))
    settings["resample"] = str(settings["resample"])
    settings["trim_transparent"] = bool(settings["trim_transparent"])
    settings["alpha_clean_threshold"] = max(0, min(255, int(settings["alpha_clean_threshold"])))
    settings["unsharp"] = bool(settings["unsharp"])
    settings["unsharp_radius"] = max(0.1, float(settings["unsharp_radius"]))
    settings["unsharp_percent"] = max(0, int(settings["unsharp_percent"]))
    settings["unsharp_threshold"] = max(0, int(settings["unsharp_threshold"]))

    if settings["quality_mode"]:
        settings["upscale"] = max(int(settings["upscale"]), 2)
        settings["trim_transparent"] = True
        settings["alpha_clean_threshold"] = max(int(settings["alpha_clean_threshold"]), 2)
        settings["unsharp"] = True

    return settings


def neighbors_8(x: int, y: int) -> Iterable[Tuple[int, int]]:
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            yield x + dx, y + dy


def color_distance_sq(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def build_alpha_map(
    rgba_pixels: List[Tuple[int, int, int, int]],
    alpha_threshold: int,
    color_tolerance: int,
    edge_softness: int,
) -> Tuple[List[int], bool]:
    if any(px[3] < 255 for px in rgba_pixels):
        return [px[3] for px in rgba_pixels], True

    bg = rgba_pixels[0][:3]
    alpha_values: List[int] = []

    for pixel in rgba_pixels:
        distance = math.sqrt(color_distance_sq(pixel[:3], bg))
        if distance <= color_tolerance:
            alpha_values.append(0)
            continue
        if edge_softness <= 0:
            alpha_values.append(255 if distance > color_tolerance else 0)
            continue
        if distance >= color_tolerance + edge_softness:
            alpha_values.append(255)
            continue
        progress = (distance - color_tolerance) / edge_softness
        alpha_values.append(max(alpha_threshold, min(255, int(round(progress * 255)))))

    return alpha_values, False


def extract_components(
    mask: List[bool],
    rgba_pixels: List[Tuple[int, int, int, int]],
    width: int,
    height: int,
) -> List[Component]:
    seen = [False] * (width * height)
    components: List[Component] = []

    for y in range(height):
        for x in range(width):
            idx = y * width + x
            if not mask[idx] or seen[idx]:
                continue

            queue = deque([(x, y)])
            seen[idx] = True

            x_min = x_max = x
            y_min = y_max = y
            pixel_count = 0
            r_sum = g_sum = b_sum = 0

            while queue:
                cx, cy = queue.popleft()
                pixel_count += 1
                pixel = rgba_pixels[cy * width + cx]
                r_sum += pixel[0]
                g_sum += pixel[1]
                b_sum += pixel[2]
                if cx < x_min:
                    x_min = cx
                if cx > x_max:
                    x_max = cx
                if cy < y_min:
                    y_min = cy
                if cy > y_max:
                    y_max = cy

                for nx, ny in neighbors_8(cx, cy):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    n_idx = ny * width + nx
                    if seen[n_idx] or not mask[n_idx]:
                        continue
                    seen[n_idx] = True
                    queue.append((nx, ny))

            components.append(
                Component(
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                    pixel_count=pixel_count,
                    mean_rgb=(r_sum / pixel_count, g_sum / pixel_count, b_sum / pixel_count),
                )
            )

    return components


def sort_components(components: List[Component]) -> List[Component]:
    if len(components) <= 1:
        return list(components)

    ordered = sorted(components, key=lambda c: (c.y_min, c.x_min))
    average_height = sum(component.height for component in ordered) / len(ordered)
    row_tolerance = max(8, int(round(average_height * 0.35)))

    rows: List[Tuple[int, List[Component]]] = []
    for component in ordered:
        for index, (row_y, row_components) in enumerate(rows):
            if abs(component.y_min - row_y) <= row_tolerance:
                row_components.append(component)
                rows[index] = (min(row_y, component.y_min), row_components)
                break
        else:
            rows.append((component.y_min, [component]))

    sorted_components: List[Component] = []
    for _, row_components in sorted(rows, key=lambda row: row[0]):
        sorted_components.extend(sorted(row_components, key=lambda c: c.x_min))
    return sorted_components


def contains_bbox(outer: Component, inner: Component, margin: int) -> bool:
    return (
        outer.x_min <= inner.x_min + margin
        and outer.y_min <= inner.y_min + margin
        and outer.x_max >= inner.x_max - margin
        and outer.y_max >= inner.y_max - margin
    )


def merge_components(components: List[Component]) -> Component:
    if len(components) == 1:
        return components[0]

    total_pixels = sum(component.pixel_count for component in components)
    mean_r = sum(component.mean_rgb[0] * component.pixel_count for component in components) / total_pixels
    mean_g = sum(component.mean_rgb[1] * component.pixel_count for component in components) / total_pixels
    mean_b = sum(component.mean_rgb[2] * component.pixel_count for component in components) / total_pixels
    return Component(
        x_min=min(component.x_min for component in components),
        y_min=min(component.y_min for component in components),
        x_max=max(component.x_max for component in components),
        y_max=max(component.y_max for component in components),
        pixel_count=total_pixels,
        mean_rgb=(mean_r, mean_g, mean_b),
    )


def merge_enclosed_components(components: List[Component], margin: int) -> List[Component]:
    if not components:
        return []

    parent = list(range(len(components)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for outer_index, outer in enumerate(components):
        for inner_index, inner in enumerate(components):
            if outer_index == inner_index:
                continue
            if contains_bbox(outer, inner, margin):
                union(outer_index, inner_index)

    groups: Dict[int, List[Component]] = {}
    for index, component in enumerate(components):
        groups.setdefault(find(index), []).append(component)

    return sort_components([merge_components(group) for group in groups.values()])


def trim_transparent_edges(image: Image.Image, alpha_threshold: int) -> Image.Image:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > alpha_threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def apply_alpha_cleanup(image: Image.Image, alpha_threshold: int) -> Image.Image:
    if alpha_threshold <= 0:
        return image
    alpha = image.getchannel("A").point(lambda value: 0 if value <= alpha_threshold else value)
    cleaned = image.copy()
    cleaned.putalpha(alpha)
    return cleaned


def rgba_pixels(image: Image.Image) -> List[Tuple[int, int, int, int]]:
    width, height = image.size
    pixels = image.load()
    return [pixels[x, y] for y in range(height) for x in range(width)]


def clear_hidden_rgb(image: Image.Image) -> Image.Image:
    pixels = []
    for red, green, blue, alpha in rgba_pixels(image):
        if alpha == 0:
            pixels.append((0, 0, 0, 0))
        else:
            pixels.append((red, green, blue, alpha))
    cleared = Image.new("RGBA", image.size)
    cleared.putdata(pixels)
    return cleared


def premultiply_rgba(image: Image.Image) -> Image.Image:
    pixels = []
    for red, green, blue, alpha in rgba_pixels(image):
        pixels.append(
            (
                (red * alpha) // 255,
                (green * alpha) // 255,
                (blue * alpha) // 255,
                alpha,
            )
        )
    premultiplied = Image.new("RGBA", image.size)
    premultiplied.putdata(pixels)
    return premultiplied


def unpremultiply_rgba(image: Image.Image) -> Image.Image:
    pixels = []
    for red, green, blue, alpha in rgba_pixels(image):
        if alpha == 0:
            pixels.append((0, 0, 0, 0))
            continue
        pixels.append(
            (
                min(255, int(round(red * 255 / alpha))),
                min(255, int(round(green * 255 / alpha))),
                min(255, int(round(blue * 255 / alpha))),
                alpha,
            )
        )
    restored = Image.new("RGBA", image.size)
    restored.putdata(pixels)
    return restored


def apply_rgb_unsharp(image: Image.Image, radius: float, percent: int, threshold: int) -> Image.Image:
    alpha = image.getchannel("A")
    sharpened = image.convert("RGB").filter(
        ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
    )
    sharpened.putalpha(alpha)
    return sharpened


def quality_enhance_crop(image: Image.Image, settings: Dict[str, object]) -> Image.Image:
    output = apply_alpha_cleanup(image, int(settings["alpha_clean_threshold"]))
    output = clear_hidden_rgb(output)

    if bool(settings["trim_transparent"]):
        output = trim_transparent_edges(output, int(settings["alpha_clean_threshold"]))

    upscale = int(settings["upscale"])
    if upscale > 1:
        output = premultiply_rgba(output)
        output = output.resize(
            (max(1, output.width * upscale), max(1, output.height * upscale)),
            resample=RESAMPLE_METHODS[str(settings["resample"])],
        )
        output = unpremultiply_rgba(output)
        output = clear_hidden_rgb(output)

    if bool(settings["unsharp"]):
        output = apply_rgb_unsharp(
            output,
            radius=float(settings["unsharp_radius"]),
            percent=int(settings["unsharp_percent"]),
            threshold=int(settings["unsharp_threshold"]),
        )

    return clear_hidden_rgb(output)


def alpha_crop_image(
    alpha_values: List[int],
    width: int,
    component: Component,
) -> Image.Image:
    crop_width = component.width
    crop_height = component.height
    values: List[int] = []

    for y in range(component.y_min, component.y_max + 1):
        row_start = y * width + component.x_min
        row_end = row_start + crop_width
        values.extend(alpha_values[row_start:row_end])

    alpha_image = Image.new("L", (crop_width, crop_height))
    alpha_image.putdata(values)
    return alpha_image


def analyze_image(image: Image.Image, settings: Dict[str, object] | None = None) -> AnalysisResult:
    normalized = normalize_settings(settings)
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba_pixels(rgba)

    alpha_values, source_has_transparency = build_alpha_map(
        pixels,
        alpha_threshold=int(normalized["alpha_threshold"]),
        color_tolerance=int(normalized["color_tolerance"]),
        edge_softness=int(normalized["edge_softness"]),
    )
    mask = [alpha >= int(normalized["alpha_threshold"]) for alpha in alpha_values]

    components = extract_components(mask, pixels, width, height)
    components = [component for component in components if component.pixel_count >= int(normalized["min_pixels"])]
    if bool(normalized["merge_enclosed"]):
        components = merge_enclosed_components(components, margin=int(normalized["enclosed_margin"]))
    components = [component.padded(width, height, int(normalized["padding"])) for component in components]
    components = sort_components(components)

    return AnalysisResult(
        width=width,
        height=height,
        source_has_transparency=source_has_transparency,
        components=components,
        alpha_values=alpha_values,
    )


def render_crops(
    image: Image.Image,
    analysis: AnalysisResult,
    settings: Dict[str, object] | None = None,
) -> List[RenderedCrop]:
    normalized = normalize_settings(settings)
    rgba = image.convert("RGBA")
    rendered: List[RenderedCrop] = []
    apply_isolation = bool(normalized["isolate_foreground"]) or analysis.source_has_transparency

    for index, component in enumerate(analysis.components, start=1):
        crop_box = (component.x_min, component.y_min, component.x_max + 1, component.y_max + 1)
        crop = rgba.crop(crop_box)
        if apply_isolation:
            crop.putalpha(alpha_crop_image(analysis.alpha_values, analysis.width, component))
        output_image = quality_enhance_crop(crop, normalized)
        rendered.append(
            RenderedCrop(
                file_name=f"icon_{index:03d}.png",
                image=output_image,
                component=component,
            )
        )

    return rendered


def build_manifest(
    input_name: str,
    output_dir: str,
    analysis: AnalysisResult,
    settings: Dict[str, object],
    rendered_crops: List[RenderedCrop],
) -> dict:
    return {
        "input_image": input_name,
        "output_dir": output_dir,
        "component_count": len(rendered_crops),
        "source_has_transparency": analysis.source_has_transparency,
        "settings": settings,
        "components": [
            {
                "index": index,
                "file": rendered.file_name,
                "bbox": {
                    "x_min": rendered.component.x_min,
                    "y_min": rendered.component.y_min,
                    "x_max": rendered.component.x_max,
                    "y_max": rendered.component.y_max,
                },
                "width": rendered.component.width,
                "height": rendered.component.height,
                "pixel_count": rendered.component.pixel_count,
                "output_width": rendered.image.width,
                "output_height": rendered.image.height,
            }
            for index, rendered in enumerate(rendered_crops, start=1)
        ],
    }


def save_rendered_crops(rendered_crops: List[RenderedCrop], output_dir: Path, manifest: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for rendered in rendered_crops:
        rendered.image.save(output_dir / rendered.file_name)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def split_image(
    image: Image.Image,
    input_name: str,
    output_dir: str,
    settings: Dict[str, object] | None = None,
) -> Tuple[dict, List[RenderedCrop], AnalysisResult]:
    normalized = normalize_settings(settings)
    analysis = analyze_image(image, normalized)
    rendered_crops = render_crops(image, analysis, normalized)
    manifest = build_manifest(input_name, output_dir, analysis, normalized, rendered_crops)
    return manifest, rendered_crops, analysis


def split_image_path(
    input_path: Path,
    output_dir: Path,
    settings: Dict[str, object] | None = None,
) -> dict:
    with Image.open(input_path) as image:
        manifest, rendered_crops, _ = split_image(image, str(input_path), str(output_dir), settings)
    save_rendered_crops(rendered_crops, output_dir, manifest)
    return manifest


def split_image_bytes(
    image_bytes: bytes,
    input_name: str,
    output_dir: str,
    settings: Dict[str, object] | None = None,
) -> Tuple[dict, List[RenderedCrop], AnalysisResult]:
    with Image.open(io.BytesIO(image_bytes)) as image:
        return split_image(image, input_name, output_dir, settings)


def encode_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input_image)
    output_dir = Path(args.output_dir)
    settings = settings_from_args(args)
    manifest = split_image_path(input_path, output_dir, settings)
    print(f"Saved {manifest['component_count']} icon files to {output_dir}")
    print(f"Manifest: {output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
