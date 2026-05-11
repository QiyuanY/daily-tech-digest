#!/usr/bin/env python3
"""Generate social media cards from batch config. Works in Linux CI (GitHub Actions)."""

import json
import argparse
import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Font paths — supports both macOS (local) and Linux (CI with fonts-dejavu/noto)
FONT_PATHS = {
    "title": [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ],
    "body": [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ],
    "mono": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ],
}


def get_font(size, category="body"):
    for path in FONT_PATHS.get(category, FONT_PATHS["body"]):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def smart_wrap(text, font, max_width, draw):
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        current_line = ''
        for char in paragraph:
            test_line = current_line + char
            if draw.textlength(test_line, font=font) > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
    return lines


def create_card(title, body="", caption="", output="card.png",
                width=1080, height=1080, title_size=44, body_size=28,
                accent_color=(99, 102, 241)):

    # Gradient background
    bg = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(bg)

    # Dark gradient
    for y in range(height):
        r = int(20 + 15 * math.sin(y / height * math.pi))
        g = int(20 + 10 * math.sin(y / height * math.pi))
        b = int(40 + 25 * math.sin(y / height * math.pi))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Subtle radial highlight
    highlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlight)
    cx, cy = width // 2, height // 3
    for r in range(300, 0, -3):
        alpha = int(25 * (1 - r / 300))
        h_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(accent_color[0], accent_color[1], accent_color[2], alpha))
    bg = Image.alpha_composite(bg, highlight)
    draw = ImageDraw.Draw(bg)

    padding = 60
    content_x = padding
    content_y = padding + 20
    content_w = width - padding * 2

    # Card backdrop
    card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_layer)
    c_draw.rounded_rectangle(
        [content_x - 20, content_y - 20, width - content_x + 20, height - content_y + 20],
        radius=20, fill=(0, 0, 0, 150))
    bg = Image.alpha_composite(bg, card_layer)
    draw = ImageDraw.Draw(bg)

    # Accent line
    draw.rounded_rectangle([content_x, content_y, content_x + 60, content_y + 6], radius=3, fill=accent_color)

    # Title
    y = content_y + 30
    title_font = get_font(title_size, "title")
    for line in smart_wrap(title, title_font, content_w, draw):
        draw.text((content_x, y), line, font=title_font, fill=(255, 255, 255))
        y += title_size + 18

    # Body
    if body:
        y += 16
        draw.rounded_rectangle([content_x, y, content_x + content_w, y + 1], fill=(255, 255, 255, 60))
        y += 18
        body_font = get_font(body_size, "body")
        for line in smart_wrap(body, body_font, content_w, draw):
            if y + body_size > height - padding - 40:
                break
            draw.text((content_x, y), line, font=body_font, fill=(220, 220, 220, 240))
            y += body_size + 12

    # Caption at bottom
    if caption:
        cap_font = get_font(20, "mono")
        cap_lines = smart_wrap(caption, cap_font, content_w, draw)
        cap_y = height - padding - len(cap_lines) * 26 - 10
        for line in cap_lines:
            draw.text((content_x, cap_y), line, font=cap_font, fill=(180, 180, 180, 180))
            cap_y += 26

    # Watermark
    wm_font = get_font(18, "mono")
    draw.text((width - padding - 120, height - padding + 8), "Daily Tech Digest", font=wm_font, fill=(255, 255, 255, 80))

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    bg.convert("RGB").save(output, quality=95)
    print(f"  → {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Batch config JSON")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    defaults = config.get("defaults", {})
    cards = config.get("cards", [])
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Generating {len(cards)} cards...")
    for i, card in enumerate(cards):
        accent_str = card.get("accent", defaults.get("accent", "6366F1"))
        accent = tuple(int(accent_str[j:j+2], 16) for j in (0, 2, 4))
        output_name = card.get("output", f"card_{i+1:02d}.png")
        output_path = os.path.join(args.output_dir, output_name)

        print(f"[{i+1}/{len(cards)}] {card['title'][:60]}")
        create_card(
            title=card["title"],
            body=card.get("body", ""),
            caption=card.get("caption", ""),
            output=output_path,
            width=card.get("width", defaults.get("width", 1080)),
            height=card.get("height", defaults.get("height", 1080)),
            title_size=card.get("title_size", defaults.get("title_size", 44)),
            body_size=card.get("body_size", defaults.get("body_size", 28)),
            accent_color=accent,
        )

    print(f"\nDone: {len(cards)} cards in {args.output_dir}/")


if __name__ == "__main__":
    main()
