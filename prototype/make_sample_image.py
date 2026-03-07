#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    out_path = Path("sample_input.png")
    image = Image.new("RGBA", (420, 180), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((20, 30, 140, 150), radius=22, fill=(220, 0, 0, 255))
    draw.ellipse((160, 25, 280, 145), fill=(0, 100, 230, 255))
    draw.polygon([(320, 30), (390, 90), (340, 150), (285, 80)], fill=(0, 175, 90, 255))

    image.save(out_path)
    print(f"Wrote sample image: {out_path}")


if __name__ == "__main__":
    main()
