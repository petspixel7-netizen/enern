"""
Hotel Riviera - Premium Video Ad Generator
Uses: MoviePy 2.x + FFmpeg + PIL (100% free)

Effects:
  - Ken Burns zoom per scene
  - Crossfade transitions
  - Animated text: slide-in per line, staggered delays
  - Glow effect on all text (multi-pass Gaussian blur)
  - Gold sweep line animation
  - Vignette overlay
  - Fade in / fade out
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import VideoClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn, FadeIn, FadeOut

OUTPUT_DIR = "/home/user/enern"
IMG_DIR    = "/home/user/enern/img"
OUTPUT     = os.path.join(OUTPUT_DIR, "hotel-riviera-ad.mp4")

W, H = 1920, 1080
FPS  = 30

FONT_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_LIGHT  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"

GOLD      = (212, 175, 55)
GOLD_PALE = (240, 210, 120)
WHITE     = (255, 255, 255)
SILVER    = (200, 200, 210)

# Each scene:
# (image, duration, tag_text, headline, subline, detail_text, text_position)
# tag_text   = small gold UPPERCASE label (e.g. "THE ROOMS") slides in first
# headline   = large bold white text
# subline    = medium italic gold text
# detail_text= small silver description text
# position   = "bottom" | "center"
SCENES = [
    (
        "banner.jpg", 6.0,
        "VELKOMMEN TIL",
        "HOTEL RIVIERA",
        "Luksus ved havet",
        "Et sted der eleganse møter natur",
        "center",
    ),
    (
        "capri.jpg", 5.5,
        "OPPLEV HAVET",
        "STRANDLIV & SOL",
        "Uendelig frihet ved blått vann",
        "Private strandområder · Livredder · Sjøsport",
        "bottom",
    ),
    (
        "hotel-view.jpg", 5.5,
        "GOURMET",
        "FINE DINING",
        "Kulinariske opplevelser med havutsikt",
        "Michelin-inspirerte retter · Norsk råvarekvalitet",
        "bottom",
    ),
    (
        "room-a.jpg", 5.5,
        "DE BESTE SUITER",
        "LUKSUS & RO",
        "Håndplukket design og eksklusiv komfort",
        "32 suiter · King-size · Privat balkong · Badstue",
        "bottom",
    ),
    (
        "room-c.jpg", 5.0,
        "ELEGANTE ROM",
        "DITT HJEM BORTE",
        "Scandinavisk design møter internasjonal luksus",
        "Smart-TV · Nespresso · Premium sengetøy",
        "bottom",
    ),
    (
        "offer.jpg", 5.5,
        "POOL & AKTIVITETER",
        "LIV VED POOLEN",
        "Refreshing cocktails og uendelig avslapning",
        "Infinity pool · Poolbar · Loungeområde",
        "bottom",
    ),
    (
        "spa.png", 5.5,
        "HELSE & SKJØNNHET",
        "SPA & WELLNESS",
        "Totalavslapping for kropp og sjel",
        "Massasje · Dampbad · Kaldtvannskar · Yoga",
        "bottom",
    ),
    (
        "wellness.jpg", 5.0,
        "PANORAMAUTSIKT",
        "NATUR & STILLHET",
        "Magiske omgivelser rundt hvert hjørne",
        "Fjord · Skog · Fjell — Alt på ett sted",
        "bottom",
    ),
    (
        "outro.jpg", 6.5,
        "RESERVER I DAG",
        "BOOK NÅ",
        "Begrenset tilgjengelighet i høysesongen",
        "rivierahotel.no   ·   +47 55 123 456   ·   post@rivierahotel.no",
        "center",
    ),
]


# ── Image utilities ──────────────────────────────────────────────────────────

def load_fill(path: str) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    r = max(W / img.width, H / img.height)
    nw, nh = int(img.width * r), int(img.height * r)
    img = img.resize((nw, nh), Image.LANCZOS)
    ox, oy = (nw - W) // 2, (nh - H) // 2
    return np.array(img.crop((ox, oy, ox + W, oy + H)))


def get_zoomed(base: np.ndarray, t: float, duration: float, zoom_in: bool) -> Image.Image:
    z0, z1 = (1.0, 1.10) if zoom_in else (1.10, 1.0)
    zoom = z0 + (z1 - z0) * (t / duration)
    zw, zh = int(W * zoom), int(H * zoom)
    img = Image.fromarray(base).resize((zw, zh), Image.LANCZOS)
    ox, oy = (zw - W) // 2, (zh - H) // 2
    return img.crop((ox, oy, ox + W, oy + H))


# ── Vignette (pre-built) ─────────────────────────────────────────────────────

def build_vignette() -> np.ndarray:
    """RGBA vignette mask: dark edges, transparent center."""
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vig)
    cx, cy = W // 2, H // 2
    max_r = (cx**2 + cy**2) ** 0.5
    steps = 80
    for i in range(steps, 0, -1):
        ratio = i / steps
        alpha = int(160 * (ratio ** 1.8))
        rx = int(cx * ratio)
        ry = int(cy * ratio)
        draw.ellipse(
            [(cx - rx, cy - ry), (cx + rx, cy + ry)],
            outline=(0, 0, 0, alpha),
            width=max(1, int(max_r / steps * 3)),
        )
    return np.array(vig)


VIGNETTE = build_vignette()


# ── Glow text utility ────────────────────────────────────────────────────────

def draw_glowing_text(
    canvas: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    color: tuple,
    glow_color: tuple,
    alpha: float = 1.0,
    glow_radius: int = 18,
    glow_passes: int = 3,
):
    """Draw text with multi-pass glow onto canvas (RGBA)."""
    a = int(255 * alpha)
    if a <= 0:
        return

    # Build glow layer
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gd.text((x, y), text, font=font, fill=glow_color + (int(a * 0.85),))
    for r in range(glow_passes, 0, -1):
        blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius * r))
        canvas.paste(blurred, mask=blurred.split()[3])

    # Shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((x + 3, y + 4), text, font=font, fill=(0, 0, 0, int(a * 0.6)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
    canvas.paste(shadow, mask=shadow.split()[3])

    # Main text
    txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_layer)
    td.text((x, y), text, font=font, fill=color + (a,))
    canvas.paste(txt_layer, mask=txt_layer.split()[3])


def centered_x(text: str, font) -> int:
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)
    bb = d.textbbox((0, 0), text, font=font)
    return (W - (bb[2] - bb[0])) // 2


# ── Slide-in animation helper ────────────────────────────────────────────────

def slide_alpha(t: float, delay: float, dur: float = 0.55) -> tuple[float, int]:
    """Returns (alpha 0-1, slide_offset_px)."""
    progress = max(0.0, min((t - delay) / dur, 1.0))
    # Ease-out cubic
    eased = 1 - (1 - progress) ** 3
    alpha = eased
    slide = int(35 * (1 - eased))
    return alpha, slide


# ── Main overlay renderer ────────────────────────────────────────────────────

def build_overlay(
    t: float,
    tag_text: str,
    headline: str,
    subline: str,
    detail_text: str,
    position: str,
) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Fonts
    try:
        font_tag      = ImageFont.truetype(FONT_BOLD,   34)
        font_headline = ImageFont.truetype(FONT_BOLD,   100)
        font_subline  = ImageFont.truetype(FONT_ITALIC, 52)
        font_detail   = ImageFont.truetype(FONT_LIGHT,  36)
    except Exception:
        font_tag = font_headline = font_subline = font_detail = ImageFont.load_default()

    # Layout zones
    if position == "bottom":
        zone_top = H - 370
        tag_y      = zone_top + 20
        line1_y    = zone_top + 65
        line2_y    = zone_top + 185
        line3_y    = zone_top + 258
        detail_y   = zone_top + 315
        bar_h      = 370
        bar_y      = zone_top
        gold_line_y = zone_top + 15
    else:  # center
        zone_top = (H - 420) // 2
        tag_y      = zone_top
        line1_y    = zone_top + 50
        line2_y    = zone_top + 172
        line3_y    = zone_top + 248
        detail_y   = zone_top + 312
        bar_h      = 440
        bar_y      = zone_top - 20
        gold_line_y = zone_top - 10

    # Gradient bar
    bar_fade = min(t / 0.35, 1.0)
    for i in range(bar_h):
        if position == "bottom":
            alpha = int(225 * (i / bar_h) * bar_fade)
        else:
            center_dist = abs(i - bar_h / 2) / (bar_h / 2)
            alpha = int(195 * (1 - center_dist ** 1.4) * bar_fade)
        draw.line([(0, bar_y + i), (W, bar_y + i)], fill=(0, 0, 0, alpha))

    # Gold sweep line (top of overlay)
    sweep = min(t / 0.7, 1.0)
    sx = int(W * sweep)
    if sx > 0:
        for thick in range(4, 0, -1):
            glow_alpha = int(180 / thick)
            draw.rectangle(
                [(0, gold_line_y - thick), (sx, gold_line_y + 3 + thick)],
                fill=GOLD + (glow_alpha,),
            )
        draw.rectangle([(0, gold_line_y), (sx, gold_line_y + 3)], fill=GOLD + (255,))

    # ── TAG line (small gold label) ──
    alpha_tag, slide_tag = slide_alpha(t, delay=0.15, dur=0.45)
    if alpha_tag > 0:
        tx = centered_x(tag_text, font_tag)
        draw_glowing_text(
            canvas, tag_text, font_tag,
            tx, tag_y + slide_tag,
            GOLD, GOLD_PALE,
            alpha=alpha_tag, glow_radius=12, glow_passes=2,
        )
        # Letter-spacing decoration lines beside tag
        bb = ImageDraw.Draw(Image.new("RGBA",(1,1))).textbbox((0,0), tag_text, font=font_tag)
        tw = bb[2] - bb[0]
        pad = 24
        lx1 = (W - tw) // 2 - pad - 120
        lx2 = (W + tw) // 2 + pad
        cy_tag = tag_y + slide_tag + 18
        line_alpha = int(200 * alpha_tag)
        draw.rectangle([(lx1, cy_tag), (lx1 + 110, cy_tag + 2)], fill=GOLD + (line_alpha,))
        draw.rectangle([(lx2, cy_tag), (lx2 + 110, cy_tag + 2)], fill=GOLD + (line_alpha,))

    # ── HEADLINE (large) ──
    alpha_h, slide_h = slide_alpha(t, delay=0.35, dur=0.6)
    if alpha_h > 0:
        tx = centered_x(headline, font_headline)
        draw_glowing_text(
            canvas, headline, font_headline,
            tx, line1_y + slide_h,
            WHITE, (180, 180, 255),
            alpha=alpha_h, glow_radius=22, glow_passes=3,
        )

    # ── SUBLINE (italic gold) ──
    alpha_s, slide_s = slide_alpha(t, delay=0.65, dur=0.55)
    if alpha_s > 0:
        tx = centered_x(subline, font_subline)
        draw_glowing_text(
            canvas, subline, font_subline,
            tx, line2_y + slide_s,
            GOLD, GOLD_PALE,
            alpha=alpha_s, glow_radius=14, glow_passes=2,
        )

    # Thin separator line
    alpha_sep = max(0.0, min((t - 0.9) / 0.4, 1.0))
    if alpha_sep > 0:
        sep_w = int(300 * alpha_sep)
        sep_x = (W - sep_w) // 2
        sep_y = line3_y - 8
        draw.rectangle([(sep_x, sep_y), (sep_x + sep_w, sep_y + 1)], fill=GOLD + (int(180 * alpha_sep),))

    # ── DETAIL LINE (small silver) ──
    alpha_d, slide_d = slide_alpha(t, delay=1.0, dur=0.55)
    if alpha_d > 0:
        tx = centered_x(detail_text, font_detail)
        draw_glowing_text(
            canvas, detail_text, font_detail,
            tx, detail_y + slide_d,
            SILVER, (160, 160, 200),
            alpha=alpha_d, glow_radius=8, glow_passes=1,
        )

    return canvas


# ── Vignette apply ────────────────────────────────────────────────────────────

def apply_vignette(img: Image.Image) -> Image.Image:
    vig = Image.fromarray(VIGNETTE, "RGBA")
    result = img.convert("RGBA")
    result.paste(vig, mask=vig.split()[3])
    return result.convert("RGB")


# ── Scene builder ─────────────────────────────────────────────────────────────

def make_scene(
    img_path: str,
    duration: float,
    tag_text: str,
    headline: str,
    subline: str,
    detail_text: str,
    position: str,
    zoom_in: bool,
) -> VideoClip:
    base = load_fill(img_path)

    def frame_func(t):
        bg = get_zoomed(base, t, duration, zoom_in)
        bg = apply_vignette(bg)
        overlay = build_overlay(t, tag_text, headline, subline, detail_text, position)
        result = bg.convert("RGBA")
        result = Image.alpha_composite(result, overlay)
        return np.array(result.convert("RGB"))

    clip = VideoClip(frame_function=frame_func, duration=duration)
    clip.fps = FPS
    return clip


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"Hotel Riviera Premium Video [{W}x{H} @ {FPS}fps]")
    print(f"Scenes: {len(SCENES)}")

    scenes = []
    for i, (img_file, dur, tag, headline, sub, detail, pos) in enumerate(SCENES):
        path = os.path.join(IMG_DIR, img_file)
        if not os.path.exists(path):
            print(f"  [SKIP] {img_file} — not found")
            continue
        print(f"  [{i+1}/{len(SCENES)}] {img_file:25s} → {headline}")
        clip = make_scene(path, dur, tag, headline, sub, detail, pos, zoom_in=(i % 2 == 0))
        if scenes:
            clip = clip.with_effects([CrossFadeIn(0.9)])
        scenes.append(clip)

    if not scenes:
        print("No scenes! Check IMG_DIR.")
        return

    final = concatenate_videoclips(scenes, method="compose", padding=-0.9)
    final = final.with_effects([FadeIn(0.6), FadeOut(1.2)])

    print(f"\nRendering → {OUTPUT}")
    final.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        ffmpeg_params=["-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger="bar",
    )
    mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"\nFerdig! {OUTPUT}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
