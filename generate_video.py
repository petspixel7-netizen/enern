"""
Hotel Riviera - High Quality Video Ad Generator
Uses: MoviePy 2.x + FFmpeg (100% free)
Features: Ken Burns zoom, crossfade transitions, animated RGBA text overlays
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn, FadeIn, FadeOut

OUTPUT_DIR = "/home/user/enern"
IMG_DIR    = "/home/user/enern/img"
OUTPUT     = os.path.join(OUTPUT_DIR, "hotel-riviera-ad.mp4")

W, H = 1920, 1080
FPS  = 30
FONT_BOLD  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_LIGHT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
GOLD  = (212, 175, 55)
WHITE = (255, 255, 255)

SCENES = [
    ("exterior.jpg",    5.5, "HOTEL RIVIERA",        "Opplev luksus ved havet",            "center"),
    ("ocean-view.jpg",  5.0, "UTSIKT MOT HAVET",     "Vakker panoramautsikt fra hvert rom", "bottom"),
    ("room-a.jpg",      5.0, "EKSKLUSIVE SUITER",     "Eleganse og komfort i verdensklasse", "bottom"),
    ("pool2.jpg",       5.0, "INFINITY POOL",         "Avslapping på høyeste nivå",          "bottom"),
    ("dining.jpg",      5.0, "GOURMET RESTAURANT",    "Kulinariske opplevelser",             "bottom"),
    ("spa.png",         5.0, "SPA & WELLNESS",        "Totalavslapping for kropp og sjel",   "bottom"),
    ("terrasse.jpg",    5.0, "TERRASSE MED UTSIKT",   "Magiske kvelder ved solnedgang",      "bottom"),
    ("exterior2.jpg",   6.0, "BOOK NÅ",               "rivierahotel.no  ·  +47 55 123 456",  "center"),
]


def load_fill(path: str) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    r = max(W / img.width, H / img.height)
    nw, nh = int(img.width * r), int(img.height * r)
    img = img.resize((nw, nh), Image.LANCZOS)
    ox, oy = (nw - W) // 2, (nh - H) // 2
    return np.array(img.crop((ox, oy, ox + W, oy + H)))


def get_zoomed(base: np.ndarray, t: float, duration: float, zoom_in: bool) -> Image.Image:
    z0, z1 = (1.0, 1.12) if zoom_in else (1.12, 1.0)
    zoom = z0 + (z1 - z0) * (t / duration)
    zw, zh = int(W * zoom), int(H * zoom)
    img = Image.fromarray(base).resize((zw, zh), Image.LANCZOS)
    ox, oy = (zw - W) // 2, (zh - H) // 2
    return img.crop((ox, oy, ox + W, oy + H))


def blend_overlay(bg: Image.Image, t: float, headline: str, subtext: str, position: str) -> np.ndarray:
    """Composite RGBA text/gradient overlay onto the background image."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_h = 240 if position == "bottom" else 300
    bar_y = H - bar_h if position == "bottom" else (H - bar_h) // 2

    # Gradient bar
    bar_fade = min(t / 0.4, 1.0)
    for i in range(bar_h):
        if position == "bottom":
            alpha = int(210 * (i / bar_h) * bar_fade)
        else:
            center_dist = abs(i - bar_h // 2) / (bar_h // 2)
            alpha = int(170 * (1 - center_dist) * bar_fade)
        draw.line([(0, bar_y + i), (W, bar_y + i)], fill=(0, 0, 0, alpha))

    # Gold accent line sweeping in
    line_progress = min(t / 0.8, 1.0)
    line_y = bar_y + (20 if position == "bottom" else bar_h // 2 - 68)
    line_x = int(W * line_progress)
    if line_x > 0:
        draw.rectangle([(0, line_y), (line_x, line_y + 4)], fill=GOLD + (240,))

    try:
        font_big = ImageFont.truetype(FONT_BOLD, 90)
        font_sm  = ImageFont.truetype(FONT_LIGHT, 44)
    except Exception:
        font_big = font_sm = ImageFont.load_default()

    if position == "bottom":
        h_y = bar_y + 38
        s_y = bar_y + 148
    else:
        h_y = bar_y + 54
        s_y = bar_y + 164

    def draw_text(text, font, color, y, delay, slide_px=28):
        progress = max(0.0, min((t - delay) / 0.55, 1.0))
        if progress <= 0:
            return
        alpha = int(255 * progress)
        slide = int(slide_px * (1 - progress))
        bb = draw.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        tx = (W - tw) // 2
        # Shadow
        draw.text((tx + 3, y + slide + 3), text, font=font, fill=(0, 0, 0, int(alpha * 0.65)))
        draw.text((tx, y + slide), text, font=font, fill=color + (alpha,))

    draw_text(headline, font_big, GOLD,  h_y, delay=0.30)
    draw_text(subtext,  font_sm,  WHITE, s_y, delay=0.70)

    # Composite: paste overlay (RGBA) onto RGB background
    result = bg.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return np.array(result.convert("RGB"))


def make_scene(img_path: str, duration: float, headline: str, subtext: str, position: str, zoom_in: bool) -> VideoClip:
    base = load_fill(img_path)

    def frame_func(t):
        bg = get_zoomed(base, t, duration, zoom_in)
        return blend_overlay(bg, t, headline, subtext, position)

    clip = VideoClip(frame_function=frame_func, duration=duration)
    clip.fps = FPS
    return clip


def main():
    print(f"Hotel Riviera Video [{W}x{H} @ {FPS}fps]")
    scenes = []
    for i, (img_file, dur, headline, subtext, pos) in enumerate(SCENES):
        path = os.path.join(IMG_DIR, img_file)
        if not os.path.exists(path):
            print(f"  [skip] {img_file}")
            continue
        print(f"  Scene {i+1}/{len(SCENES)}: {headline}")
        clip = make_scene(path, dur, headline, subtext, pos, zoom_in=(i % 2 == 0))
        if scenes:
            clip = clip.with_effects([CrossFadeIn(0.8)])
        scenes.append(clip)

    if not scenes:
        print("No scenes found!")
        return

    final = concatenate_videoclips(scenes, method="compose", padding=-0.8)
    final = final.with_effects([FadeIn(0.5), FadeOut(1.0)])

    print(f"\nRendering -> {OUTPUT}")
    final.write_videofile(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="slow",
        ffmpeg_params=["-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger="bar",
    )
    mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"\nFerdig! {OUTPUT}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
