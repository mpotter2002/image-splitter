#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw


def draw_code_symbol(draw: ImageDraw.ImageDraw, box, color, width: int = 10) -> None:
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0

    left = [
        (x0 + int(0.35 * w), y0 + int(0.35 * h)),
        (x0 + int(0.22 * w), y0 + int(0.50 * h)),
        (x0 + int(0.35 * w), y0 + int(0.65 * h)),
    ]
    slash = [
        (x0 + int(0.47 * w), y0 + int(0.72 * h)),
        (x0 + int(0.57 * w), y0 + int(0.28 * h)),
    ]
    right = [
        (x0 + int(0.67 * w), y0 + int(0.35 * h)),
        (x0 + int(0.80 * w), y0 + int(0.50 * h)),
        (x0 + int(0.67 * w), y0 + int(0.65 * h)),
    ]

    draw.line(left, fill=color, width=width, joint="curve")
    draw.line(slash, fill=color, width=width, joint="curve")
    draw.line(right, fill=color, width=width, joint="curve")


def main() -> None:
    out_path = Path("two_block_code_sample.png")
    image = Image.new("RGBA", (1024, 683), (235, 235, 235, 255))
    draw = ImageDraw.Draw(image)

    blue = (19, 167, 219, 255)
    white = (255, 255, 255, 255)

    left_box = (115, 178, 440, 503)
    right_box = (580, 178, 915, 503)

    draw.rounded_rectangle(left_box, radius=28, fill=blue)
    draw.rectangle(right_box, outline=blue, width=8)

    draw_code_symbol(draw, left_box, white, width=11)
    draw_code_symbol(draw, right_box, blue, width=10)

    image.save(out_path)
    print(f"Wrote sample image: {out_path}")


if __name__ == "__main__":
    main()
