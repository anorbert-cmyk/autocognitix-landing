#!/usr/bin/env python3
"""
generate-og-images.py — AutoCognitix

Reproducible generator for Open Graph / Twitter card images, favicon,
apple-touch-icon, and Schema.org logo.

Design spec (see tasks/og-images-spec.md):
  - 1200x630 sRGB JPG cards
  - Brand dark background #12110E with orange accent #D97757
  - Wordmark top-left, title centered-left, subtitle below, bottom accent bar

Dependencies: Pillow (PIL). Zero external design tools required.

Usage:
  python3 scripts/generate-og-images.py                # generate all
  python3 scripts/generate-og-images.py --clean        # wipe images/og/ first
  python3 scripts/generate-og-images.py --only home-hu # regenerate a single slug

Idempotent: re-running overwrites existing files in place.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.stderr.write(
        "ERROR: Pillow is required. Install with: pip3 install Pillow\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
IMG_ROOT = ROOT / "images"
OG_DIR = IMG_ROOT / "og"
OG_BLOG_DIR = OG_DIR / "blog"
OG_TOOLS_DIR = OG_DIR / "tools"  # currently unused; kept for forward-compat
SOURCES_DIR = IMG_ROOT / "sources"

# ---------------------------------------------------------------------------
# Brand tokens (sourced from shared/styles.css — keep in sync)
# ---------------------------------------------------------------------------

COLOR_DARK = (18, 17, 14)          # #12110E
COLOR_ACCENT = (217, 119, 87)      # #D97757
COLOR_ACCENT_DARK = (170, 86, 60)  # hand-tuned darker shade for gradient end
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (204, 204, 204)       # #CCCCCC per spec
COLOR_MUTED = (141, 150, 163)      # #8D96A3

# Canvas
OG_W, OG_H = 1200, 630
SAFE_PAD = 88  # > spec's 80px minimum
JPG_QUALITY = 82  # ~keeps files comfortably under 300KB

# ---------------------------------------------------------------------------
# Font loader — macOS / linux fallbacks, no copyrighted downloads.
# ---------------------------------------------------------------------------

FONT_CANDIDATES_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES_REGULAR = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _pick_font(candidates: Iterable[str], size: int) -> ImageFont.FreeTypeFont:
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except OSError:
                continue
    # last resort: default bitmap
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_gradient_background(img: Image.Image, variant: str) -> None:
    """
    variant = "dark"  -> solid base dark with subtle diagonal orange glow
    variant = "orange" -> full orange diagonal gradient (spec alt)
    """
    draw = ImageDraw.Draw(img)
    if variant == "orange":
        for y in range(OG_H):
            t = y / OG_H
            r = int(COLOR_ACCENT[0] * (1 - t) + COLOR_ACCENT_DARK[0] * t)
            g = int(COLOR_ACCENT[1] * (1 - t) + COLOR_ACCENT_DARK[1] * t)
            b = int(COLOR_ACCENT[2] * (1 - t) + COLOR_ACCENT_DARK[2] * t)
            draw.line([(0, y), (OG_W, y)], fill=(r, g, b))
        return

    # "dark" — fill dark, then paint a soft radial-ish diagonal glow in accent
    draw.rectangle([(0, 0), (OG_W, OG_H)], fill=COLOR_DARK)

    # Diagonal accent glow: offset circle with alpha overlay
    glow = Image.new("RGBA", (OG_W, OG_H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    # Ellipse bottom-right, soft
    gdraw.ellipse(
        [(OG_W - 820, OG_H - 720), (OG_W + 120, OG_H + 120)],
        fill=(COLOR_ACCENT[0], COLOR_ACCENT[1], COLOR_ACCENT[2], 55),
    )
    # Smaller warm highlight top-left
    gdraw.ellipse(
        [(-240, -240), (460, 460)],
        fill=(COLOR_ACCENT[0], COLOR_ACCENT[1], COLOR_ACCENT[2], 28),
    )
    img.alpha_composite(glow) if img.mode == "RGBA" else img.paste(
        Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"), (0, 0)
    )


def _draw_logo_mark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int = 44) -> None:
    """
    Stacked-layers mark (3 chevron/diamond lines) inside a rounded square.
    Matches the inline nav SVG in hu/index.html & en/index.html.
    """
    # Rounded square background
    draw.rounded_rectangle(
        [(x, y), (x + size, y + size)],
        radius=int(size * 0.22),
        fill=COLOR_ACCENT,
    )

    # Three stacked chevrons (simplified layers icon)
    cx = x + size / 2
    # Top diamond
    top_y = y + size * 0.28
    pts_top = [
        (cx, top_y - size * 0.12),
        (cx + size * 0.28, top_y),
        (cx, top_y + size * 0.12),
        (cx - size * 0.28, top_y),
    ]
    draw.polygon(pts_top, outline=COLOR_WHITE, width=max(2, size // 18))

    # Middle chevron
    mid_y = y + size * 0.56
    draw.line(
        [
            (cx - size * 0.28, mid_y - size * 0.05),
            (cx, mid_y + size * 0.07),
            (cx + size * 0.28, mid_y - size * 0.05),
        ],
        fill=COLOR_WHITE,
        width=max(2, size // 18),
        joint="curve",
    )

    # Bottom chevron
    bot_y = y + size * 0.78
    draw.line(
        [
            (cx - size * 0.28, bot_y - size * 0.05),
            (cx, bot_y + size * 0.07),
            (cx + size * 0.28, bot_y - size * 0.05),
        ],
        fill=COLOR_WHITE,
        width=max(2, size // 18),
        joint="curve",
    )


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Greedy word-wrap to fit max_width."""
    words = text.split()
    if not words:
        return [""]
    lines, current = [], words[0]
    for w in words[1:]:
        probe = current + " " + w
        if font.getlength(probe) <= max_width:
            current = probe
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return lines


def _draw_wordmark(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """Render the 'AutoCognitix' wordmark as logo + text, left-aligned at (x,y)."""
    mark_size = 44
    _draw_logo_mark(draw, x, y, size=mark_size)
    font = _pick_font(FONT_CANDIDATES_BOLD, 30)
    draw.text(
        (x + mark_size + 14, y + 5),
        "AutoCognitix",
        fill=COLOR_WHITE,
        font=font,
    )


# ---------------------------------------------------------------------------
# Card renderer
# ---------------------------------------------------------------------------

@dataclass
class Card:
    slug: str            # filename without extension, relative to og/
    title: str
    subtitle: str
    lang: str = "hu"     # for corner badge ("HU" / "EN")
    variant: str = "dark"  # "dark" | "orange"


def _render_card(card: Card) -> Image.Image:
    img = Image.new("RGB", (OG_W, OG_H), COLOR_DARK).convert("RGBA")
    _draw_gradient_background(img, card.variant)
    draw = ImageDraw.Draw(img)

    # --- Wordmark top-left
    _draw_wordmark(draw, SAFE_PAD, SAFE_PAD - 10)

    # --- Language badge top-right
    badge_font = _pick_font(FONT_CANDIDATES_BOLD, 22)
    badge_text = card.lang.upper()
    bw = int(badge_font.getlength(badge_text)) + 28
    bh = 34
    bx = OG_W - SAFE_PAD - bw
    by = SAFE_PAD - 4
    draw.rounded_rectangle(
        [(bx, by), (bx + bw, by + bh)],
        radius=6,
        outline=COLOR_ACCENT,
        width=2,
    )
    draw.text(
        (bx + 14, by + 4),
        badge_text,
        fill=COLOR_ACCENT,
        font=badge_font,
    )

    # --- Title (wrapped to max 2 lines @ 84px, else drop to 72px)
    max_text_w = OG_W - 2 * SAFE_PAD
    for size in (92, 84, 76, 68, 60):
        title_font = _pick_font(FONT_CANDIDATES_BOLD, size)
        lines = _wrap_text(card.title, title_font, max_text_w)
        if len(lines) <= 2 and all(title_font.getlength(l) <= max_text_w for l in lines):
            break
    else:
        title_font = _pick_font(FONT_CANDIDATES_BOLD, 60)
        lines = _wrap_text(card.title, title_font, max_text_w)[:2]

    # Compute block height
    ascent, descent = title_font.getmetrics()
    line_h = ascent + descent + 8
    title_block_h = line_h * len(lines)

    subtitle_font = _pick_font(FONT_CANDIDATES_REGULAR, 30)
    sub_lines = _wrap_text(card.subtitle, subtitle_font, max_text_w)[:2] if card.subtitle else []
    sub_ascent, sub_descent = subtitle_font.getmetrics()
    sub_line_h = sub_ascent + sub_descent + 4
    sub_block_h = sub_line_h * len(sub_lines)

    gap = 24 if sub_lines else 0
    total_block_h = title_block_h + gap + sub_block_h

    # Vertical centering (slightly above geometric center — feels better with
    # the top wordmark)
    start_y = (OG_H - total_block_h) // 2 + 20

    # Draw accent eyebrow above title
    eyebrow_y = start_y - 36
    draw.rectangle(
        [(SAFE_PAD, eyebrow_y), (SAFE_PAD + 72, eyebrow_y + 4)],
        fill=COLOR_ACCENT,
    )

    y = start_y
    for line in lines:
        draw.text((SAFE_PAD, y), line, fill=COLOR_WHITE, font=title_font)
        y += line_h

    if sub_lines:
        y += gap - (line_h - (ascent + descent))  # small adjustment
        for line in sub_lines:
            draw.text((SAFE_PAD, y), line, fill=COLOR_GRAY, font=subtitle_font)
            y += sub_line_h

    # --- Bottom accent bar (spec: 4px full-width orange)
    draw.rectangle(
        [(0, OG_H - 6), (OG_W, OG_H)],
        fill=COLOR_ACCENT,
    )

    # --- Domain stamp bottom-left
    domain_font = _pick_font(FONT_CANDIDATES_REGULAR, 22)
    draw.text(
        (SAFE_PAD, OG_H - SAFE_PAD + 8),
        "autocognitix.hu",
        fill=COLOR_MUTED,
        font=domain_font,
    )

    return img.convert("RGB")


# ---------------------------------------------------------------------------
# Card inventory — must stay in sync with tasks/og-images-spec.md
# ---------------------------------------------------------------------------

CARDS: list[Card] = [
    # Default / fallback
    Card("og-default", "AutoCognitix", "AI autódiagnosztika hibakód-elemzéssel", "HU"),

    # ── Priority 1: homepages + hubs ───────────────────────────────────────
    Card("hu-homepage", "AI Autódiagnosztika", "Hibakód, tünet, javítási költség — magyarul", "HU"),
    Card("en-homepage", "AI Car Diagnostics", "Decode fault codes, estimate repair cost", "EN"),
    Card("hu-tools", "Ingyenes Autós Eszközök", "Szerviz kereső, vizsga prediktor, költségbecslő", "HU"),
    Card("en-tools", "Free Car Diagnostic Tools", "Workshop finder, MOT predictor, repair calculator", "EN"),
    Card("hu-blog", "Autós Blog", "DTC hibakódok, javítási útmutatók, karbantartás", "HU"),
    Card("en-blog", "Car Diagnostics Blog", "DTC codes, repair guides, maintenance tips", "EN"),

    # ── Priority 2: tool pages ─────────────────────────────────────────────
    Card("hu-tool-repair", "Megéri Megjavítani?", "Javítás vs. csere kalkulátor másodpercek alatt", "HU"),
    Card("hu-tool-mot", "Műszaki Vizsga Prediktor", "Mekkora eséllyel megy át az autód?", "HU"),
    Card("hu-tool-workshop", "Szerviz Kereső", "Ellenőrzött szervizek és árak Magyarországon", "HU"),
    Card("en-tool-repair", "Worth Repairing?", "Repair vs. replace calculator in seconds", "EN"),
    Card("en-tool-mot", "MOT Predictor", "Estimate your car's chance of passing MOT", "EN"),
    Card("en-tool-workshop", "Workshop Finder", "Verified garages and pricing across Hungary", "EN"),

    # ── Priority 3: blog articles ──────────────────────────────────────────
    Card("blog/hu-ai-diagnosztika", "AI Autódiagnosztika: Hogyan Működik?", "A gépi tanulás a műhelyben — kezdőknek érthetően", "HU"),
    Card("blog/hu-akkumulator", "5 Figyelmeztető Jel", "Az akkumulátorod hamarosan feladja a szolgálatot", "HU"),
    Card("blog/hu-otthon-diagnosztika", "Autódiagnosztika Otthon", "Kezdők útmutatója OBD2-vel és okostelefonnal", "HU"),
    Card("blog/hu-dtc-utmutato", "DTC Hibakód Kereső", "Teljes útmutató a hibakódok értelmezéséhez", "HU"),
    Card("blog/hu-p0171", "P0171 Hibakód", "Okok, tünetek, javítási költség — 2026-os árak", "HU"),
    Card("blog/hu-p0420", "P0420 Hibakód Útmutató", "Katalizátor hatékonyság — diagnózis és javítás", "HU"),
    Card("blog/en-battery", "5 Signs Your Car Battery Is Dying", "Catch it before you're stranded in the cold", "EN"),
    Card("blog/en-home-diagnostics", "Car Diagnostics At Home", "Beginner's guide with OBD2 and your smartphone", "EN"),
    Card("blog/en-dtc-guide", "DTC Trouble Code Lookup", "Complete guide to reading and fixing fault codes", "EN"),
    Card("blog/en-ai-diagnostics", "How AI Car Diagnostics Works", "Machine learning in the workshop — explained simply", "EN"),
    Card("blog/en-p0171", "P0171 DTC Code", "Causes, symptoms, repair cost — 2026 prices", "EN"),
    Card("blog/en-p0420", "P0420 DTC Code Guide", "Catalyst efficiency — diagnosis and repair", "EN"),

    # ── Priority 4: legal (reused per spec) ────────────────────────────────
    Card("legal-hu", "Jogi Nyilatkozatok", "Adatvédelem, cookie, ÁSZF, AI felelősség", "HU"),
    Card("legal-en", "Legal Notices", "Privacy, cookies, terms of service, AI disclaimer", "EN"),
]


def _ensure_dirs() -> None:
    OG_DIR.mkdir(parents=True, exist_ok=True)
    OG_BLOG_DIR.mkdir(parents=True, exist_ok=True)
    OG_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)


def _out_path(slug: str) -> Path:
    return OG_DIR / f"{slug}.jpg"


def generate_cards(only: str | None = None) -> list[Path]:
    _ensure_dirs()
    produced: list[Path] = []
    for card in CARDS:
        if only and card.slug != only:
            continue
        out = _out_path(card.slug)
        out.parent.mkdir(parents=True, exist_ok=True)
        img = _render_card(card)
        img.save(out, "JPEG", quality=JPG_QUALITY, optimize=True, progressive=True)
        produced.append(out)
    return produced


# ---------------------------------------------------------------------------
# Logo (SVG source + PNG raster)
# ---------------------------------------------------------------------------

LOGO_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120" role="img" aria-label="AutoCognitix">
  <rect x="8" y="30" width="60" height="60" rx="13" fill="#D97757"/>
  <g fill="none" stroke="#FFFFFF" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M38 46 L54 54 L38 62 L22 54 Z"/>
    <path d="M22 64 L38 72 L54 64"/>
    <path d="M22 74 L38 82 L54 74"/>
  </g>
  <text x="90" y="78"
        font-family="'Funnel Sans', -apple-system, 'Helvetica Neue', Arial, sans-serif"
        font-size="52" font-weight="700" fill="#12110E">AutoCognitix</text>
</svg>
"""


def write_logo_svg() -> Path:
    _ensure_dirs()
    path = IMG_ROOT / "logo.svg"
    path.write_text(LOGO_SVG, encoding="utf-8")
    # Also keep a source copy for future editing
    (SOURCES_DIR / "logo.svg").write_text(LOGO_SVG, encoding="utf-8")
    return path


def render_logo_png(dark_on_light: bool = True) -> Path:
    """
    600x60 wordmark PNG — close to Google's Schema.org Organization logo guidance
    (max 600x60 for wordmark-style logos). Raster fallback, transparent PNG.
    """
    W, H = 600, 60
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Mark (left-aligned, square)
    mark_size = 48
    mx, my = 6, (H - mark_size) // 2
    _draw_logo_mark(draw, mx, my, size=mark_size)
    # Wordmark
    text_color = COLOR_DARK if dark_on_light else COLOR_WHITE
    font = _pick_font(FONT_CANDIDATES_BOLD, 34)
    draw.text((mark_size + 18, (H - 40) // 2), "AutoCognitix", fill=text_color, font=font)
    out = IMG_ROOT / "logo.png"
    img.save(out, "PNG", optimize=True)
    return out


# ---------------------------------------------------------------------------
# Favicon + apple-touch-icon
# ---------------------------------------------------------------------------

def _render_square_mark(size: int, rounded: bool = True) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Full-bleed orange rounded square background
    if rounded:
        draw.rounded_rectangle(
            [(0, 0), (size - 1, size - 1)],
            radius=int(size * 0.22),
            fill=COLOR_ACCENT,
        )
    else:
        draw.rectangle([(0, 0), (size - 1, size - 1)], fill=COLOR_ACCENT)

    # Draw stacked layers (scaled)
    stroke_w = max(2, size // 14)
    cx = size / 2
    top_y = size * 0.32
    mid_y = size * 0.56
    bot_y = size * 0.76
    spread = size * 0.26
    lift = size * 0.10

    # Top diamond
    pts_top = [
        (cx, top_y - lift),
        (cx + spread, top_y),
        (cx, top_y + lift),
        (cx - spread, top_y),
    ]
    draw.polygon(pts_top, outline=COLOR_WHITE, width=stroke_w)
    # Middle chevron
    draw.line(
        [(cx - spread, mid_y - size * 0.04), (cx, mid_y + size * 0.06), (cx + spread, mid_y - size * 0.04)],
        fill=COLOR_WHITE,
        width=stroke_w,
        joint="curve",
    )
    # Bottom chevron
    draw.line(
        [(cx - spread, bot_y - size * 0.04), (cx, bot_y + size * 0.06), (cx + spread, bot_y - size * 0.04)],
        fill=COLOR_WHITE,
        width=stroke_w,
        joint="curve",
    )
    return img


def generate_favicon() -> Path:
    _ensure_dirs()
    # Multi-resolution ICO. Pillow accepts a list of (w,h) tuples via `sizes`
    # and also supports embedding multiple images by saving from one base
    # image with the `sizes` parameter.
    base = _render_square_mark(64)
    out = IMG_ROOT / "favicon.ico"
    base.save(
        out,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
    )
    return out


def generate_apple_touch_icon() -> Path:
    _ensure_dirs()
    img = _render_square_mark(180, rounded=False)  # iOS auto-rounds; full bleed fill
    out = IMG_ROOT / "apple-touch-icon.png"
    img.save(out, "PNG", optimize=True)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _humansize(p: Path) -> str:
    n = p.stat().st_size
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate AutoCognitix OG images and icons.")
    ap.add_argument("--clean", action="store_true", help="Delete all images in images/og/ before generating.")
    ap.add_argument("--only", type=str, default=None, help="Regenerate a single card slug (e.g. 'home-hu' or 'blog/hu-p0420').")
    ap.add_argument("--skip-icons", action="store_true", help="Skip favicon/apple-touch-icon/logo generation.")
    args = ap.parse_args()

    if args.clean:
        for p in sorted(OG_DIR.rglob("*.jpg")):
            p.unlink()
        print(f"[clean] removed existing JPGs under {OG_DIR}")

    print(f"[render] generating OG cards into {OG_DIR}")
    produced = generate_cards(only=args.only)

    if not args.skip_icons and not args.only:
        print(f"[render] writing logo.svg + logo.png")
        svg_path = write_logo_svg()
        png_path = render_logo_png()
        ico_path = generate_favicon()
        apple_path = generate_apple_touch_icon()
        extras = [svg_path, png_path, ico_path, apple_path]
    else:
        extras = []

    all_files = produced + extras

    print("\n─── Generated files ─────────────────────────────────")
    for p in all_files:
        rel = p.relative_to(ROOT)
        print(f"  {rel}  ({_humansize(p)})")
    print(f"\nTotal: {len(all_files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
