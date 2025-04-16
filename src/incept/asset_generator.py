from __future__ import annotations

"""
asset_generator.py
===================
High‑level, reusable generators for all Jellyfin course artwork
(background, fan‑art, logo, poster variants, thumbnail).

Usage example
-------------

```python
from poster_generator import (
    BackgroundGenerator,
    FanartGenerator,
    LogoGenerator,
    PosterGenerator,
    ThumbGenerator,
    PosterVariant,
)

common = dict(
    instructor="Nick Chamberlain",
    course_title="Cinematic Lighting in Houdini",
    chapter_title="Week 1",  # optional for PosterVariant.COURSE
    lesson_title="Course Overview",  # only used for thumbnails (if desired)
    logo_public_id="icon/rebelway_logo.png",
)

# 1. background
BackgroundGenerator(**common).generate("background.jpg")

# 2. fan‑art – downloads original asset untouched
FanartGenerator(public_id="banner/fanart").generate("fanart.jpg")

# 3. mono‑tinted logo
LogoGenerator(**common).generate("logo.png")

# 4a. course poster
PosterGenerator(variant=PosterVariant.COURSE, **common).generate("poster.jpg")

# 4b. chapter poster
PosterGenerator(variant=PosterVariant.CHAPTER, **common).generate("season_01/poster.jpg")

# 5. episode thumbnail
ThumbGenerator(**common).generate("thumb.jpg")
```

All generators share a small set of utilities so the API stays
consistent and adding new templates later is trivial.

"""

from enum import Enum, auto
from io import BytesIO
from pathlib import Path
from typing import Tuple

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


# -----------------------------------------------------------------------------
# External dependency – cloudinary Manager.
# -----------------------------------------------------------------------------
from notionmanager.cloudinary_manager import CloudinaryManager


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------

FONT_DIR = Path(__file__).parent / ".config" / "fonts" / "coresansc"
FONT_CACHE = {}

def get_font(name: str, size: int) -> ImageFont.FreeTypeFont:  # pragma: no cover
    """Cache & return Core Sans C font at requested size."""
    key = (name, size)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = ImageFont.truetype(str(FONT_DIR / name), size)
    return FONT_CACHE[key]


def fetch_rgba(public_id: str, manager: CloudinaryManager) -> Image.Image:
    url = manager.get_asset_url(public_id)
    resp = requests.get(url)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGBA")


def resize_keep_ratio(img: Image.Image, max_size: Tuple[int, int], upscale: bool = False) -> Image.Image:
    """Resize *img* so it fits inside *max_size* keeping aspect ratio."""
    orig_w, orig_h = img.size
    max_w, max_h = max_size
    scale = min(max_w / orig_w, max_h / orig_h)
    if not upscale:
        scale = min(scale, 1.0)
    return img.resize((int(orig_w * scale), int(orig_h * scale)), Image.Resampling.LANCZOS)

def tint(img: Image.Image, rgb: Tuple[int, int, int]) -> Image.Image:
    """Return *img* recoloured to *rgb*, preserving its original alpha antialias."""
    # 1. Grab the alpha channel as a mask
    mask = img.getchannel("A")
    # 2. Make a solid image in your tint colour
    solid = Image.new("RGBA", img.size, rgb + (255,))
    # 3. Create an empty transparent canvas
    result = Image.new("RGBA", img.size, (0,0,0,0))
    # 4. Paste the solid through the mask
    result.paste(solid, (0,0), mask)
    return result

def draw_center(draw: ImageDraw.Draw, txt: str, y: int, font: ImageFont.FreeTypeFont, fill):
    w, h = draw.textbbox((0, 0), txt, font=font)[2:4]
    x = (draw.im.size[0] - w) / 2
    draw.text((x, y), txt, font=font, fill=fill)
    return y + h

# -----------------------------------------------------------------------------
# Base generator
# -----------------------------------------------------------------------------

class BaseGenerator:
    manager: CloudinaryManager

    def __init__(self):
        self.manager = CloudinaryManager()

    def generate(self, out_path: str):  # pragma: no cover – implemented by subclasses
        raise NotImplementedError

# -----------------------------------------------------------------------------
# Background (1920×1080) – dark grey + tinted logo
# -----------------------------------------------------------------------------

class BackgroundGenerator(BaseGenerator):
    SIZE      = (1920, 1080)
    BG_COLOUR = (12, 12, 12, 255)
    LOGO_TINT = (35, 35, 35)
    # maximum width, height for the logo:
    LOGO_BOX  = (834, 834)

    def __init__(self, *, logo_public_id: str, **_):
        super().__init__()
        self.logo_public_id = logo_public_id

    def generate(self, out_path: str):
        # 1. create canvas
        canvas = Image.new("RGBA", self.SIZE, self.BG_COLOUR)

        # 2. fetch, resize (max 800×800), tint
        raw_logo = fetch_rgba(self.logo_public_id, self.manager)
        logo     = resize_keep_ratio(raw_logo, self.LOGO_BOX)
        logo     = tint(logo, self.LOGO_TINT)

        # 3. compute center offset
        cw, ch       = self.SIZE
        lw, lh       = logo.size
        offset_x     = (cw - lw) // 2
        offset_y     = (ch - lh) // 2

        # 4. composite and save
        canvas.paste(logo, (offset_x, offset_y), logo)
        canvas.convert("RGB").save(out_path, "JPEG", quality=95)


# -----------------------------------------------------------------------------
# Fan‑art (2160×3840) – untouched download & resize if needed
# -----------------------------------------------------------------------------


class FanartGenerator(BaseGenerator):
    SIZE = (2160, 3840)

    def __init__(self, public_id: str):
        super().__init__()
        self.public_id = public_id

    def generate(self, out_path: str):
        img = fetch_rgba(self.public_id, self.manager)
        img = resize_keep_ratio(img, self.SIZE, upscale=True)
        img.convert("RGB").save(out_path, "JPEG", quality=95)


class LogoGenerator(BaseGenerator):
    TINT     = (129, 129, 129)
    # final output size for logo.png
    CANVAS_SIZE = (800, 310)
    # maximum space for the source logo within that canvas
    LOGO_BOX    = (800, 310)

    def __init__(self, *, logo_public_id: str, **_):
        super().__init__()
        self.logo_public_id = logo_public_id


    def generate(self, out_path: str):
        # fetch, resize & tint
        raw   = fetch_rgba(self.logo_public_id, self.manager)
        small = resize_keep_ratio(raw, self.LOGO_BOX)
        logo  = tint(small, self.TINT)

        # make transparent canvas at recommended size
        canvas = Image.new("RGBA", self.CANVAS_SIZE, (0, 0, 0, 0))

        # center
        cw, ch = self.CANVAS_SIZE
        lw, lh = logo.size
        x = (cw - lw) // 2
        y = (ch - lh) // 2

        canvas.paste(logo, (x, y), logo)
        canvas.save(out_path, "PNG")

class PosterVariant(Enum):
    COURSE  = auto()
    CHAPTER = auto()


class PosterGenerator(BaseGenerator):
    # default base image (with your desired background) 
    DEFAULT_BASE_PUBLIC_ID = "poster/base_image.jpg"
    # logo styling
    LOGO_TINT    = (110, 110, 110)
    LOGO_BOX     = (290, 290)   # max width, height
    LOGO_OFFSET  = (55, 70)
    # text colours
    TEXT_COLOUR       = (65, 65, 65, 255)
    TEXT_COLOUR_BOLD  = (140, 140, 140, 255)

    def __init__(
        self,
        *,
        variant: PosterVariant,
        instructor: str,
        course_title: str,
        chapter_title: str | None = None,
        base_public_id: str = DEFAULT_BASE_PUBLIC_ID,
        logo_public_id: str,
        brightness: float = 1.0,
        **_,
    ):
        super().__init__()
        self.variant        = variant
        self.base_public_id = base_public_id
        self.logo_public_id = logo_public_id
        self.instructor     = instructor.upper()
        self.course_title   = course_title.upper()
        self.chapter_title  = chapter_title.upper() if chapter_title else None
        self.brightness     = brightness

    def generate(self, out_path: str):
        # 1) download base
        base = fetch_rgba(self.base_public_id, self.manager)

        # 2) optional brightness adjust
        if self.brightness != 1.0:
            base = ImageEnhance.Brightness(base).enhance(self.brightness)

        # 3) logo: fetch, fit into box, tint & paste
        raw_logo = fetch_rgba(self.logo_public_id, self.manager)
        logo     = tint(resize_keep_ratio(raw_logo, self.LOGO_BOX), self.LOGO_TINT)
        base.paste(logo, self.LOGO_OFFSET, logo)

        # 4) draw text
        draw = ImageDraw.Draw(base)
        y   = 750
        gap = 40

        # instructor
        y = draw_center(
            draw, self.instructor, y,
            get_font("coresansc35.otf", 40),
            self.TEXT_COLOUR
        )
        y += gap

        # underline beneath course title
        w_course, _ = draw.textbbox(
            (0, 0),
            self.course_title,
            font=get_font("coresansc75.otf", 47)
        )[2:4]
        x0 = (base.width - w_course) / 2
        draw.line((x0, y, x0 + w_course, y),
                  fill=self.TEXT_COLOUR, width=1)
        y += gap - 20

        # course title (bold)
        y = draw_center(
            draw, self.course_title, y,
            get_font("coresansc75.otf", 47),
            self.TEXT_COLOUR_BOLD
        )

        # optional chapter line
        if self.variant is PosterVariant.CHAPTER and self.chapter_title:
            y += 250
            draw_center(
                draw, self.chapter_title, y,
                get_font("coresansc45.otf", 40),
                self.TEXT_COLOUR
            )

        # 5) save out as JPEG
        base.convert("RGB").save(out_path, "JPEG", quality=95)


if __name__ == "__main__":
    import argparse
    from asset_generator import (
        BackgroundGenerator,
        FanartGenerator,
        LogoGenerator,
        PosterGenerator,
        PosterVariant,
    )

    parser = argparse.ArgumentParser(
        description="Generate Jellyfin course artwork"
    )

    # Background
    parser.add_argument(
        "--bg-logo-public-id",
        help="Public ID for logo (to generate a centered background)",
    )
    parser.add_argument(
        "--bg-output",
        default="background.jpg",
        help="Filename for the generated background",
    )

    # Fan‑art
    parser.add_argument(
        "--fanart-public-id",
        help="Public ID for banner/fanart",
    )
    parser.add_argument(
        "--fanart-output",
        default="fanart.jpg",
        help="Filename for the downloaded fan‑art",
    )

    # Mono logo
    parser.add_argument(
        "--logo-public-id",
        help="Public ID for the mono‑colour logo",
    )
    parser.add_argument(
        "--logo-output",
        default="logo.png",
        help="Filename for the tinted PNG logo",
    )

    # Poster
    parser.add_argument(
        "--poster-variant",
        choices=["course", "chapter"],
        help="Generate a poster of this variant",
    )
    parser.add_argument(
        "--poster-logo-public-id",
        help="Public ID for the logo inside the poster",
    )
    parser.add_argument(
        "--instructor",
        help="Instructor name (required for poster)",
    )
    parser.add_argument(
        "--course-title",
        help="Course title (required for poster)",
    )
    parser.add_argument(
        "--chapter-title",
        help="Chapter title (only for chapter‐variant poster)",
    )
    parser.add_argument(
        "--poster-brightness",
        type=float,
        default=1.0,
        help="Brightness factor for poster base image",
    )
    parser.add_argument(
        "--poster-output",
        default="poster.jpg",
        help="Filename for the generated poster JPEG",
    )

    args = parser.parse_args()

    did_something = False

    # 1) Background
    if args.bg_logo_public_id:
        did_something = True
        bg = BackgroundGenerator(logo_public_id=args.bg_logo_public_id)
        bg.generate(args.bg_output)
        print(f"Background → {args.bg_output}")

    # 2) Fan‑art
    if args.fanart_public_id:
        did_something = True
        fa = FanartGenerator(public_id=args.fanart_public_id)
        fa.generate(args.fanart_output)
        print(f"Fan‑art   → {args.fanart_output}")

    # 3) Mono logo
    if args.logo_public_id:
        did_something = True
        lg = LogoGenerator(logo_public_id=args.logo_public_id)
        lg.generate(args.logo_output)
        print(f"Logo      → {args.logo-output} (transparent PNG)")

    # 4) Poster
    if args.poster_variant:
        # validation
        if not args.poster_logo_public_id or not args.instructor or not args.course_title:
            parser.error(
                "--poster-variant requires --poster-logo-public-id, "
                "--instructor and --course-title"
            )
        did_something = True
        variant = (
            PosterVariant.COURSE
            if args.poster_variant == "course"
            else PosterVariant.CHAPTER
        )
        pg = PosterGenerator(
            variant        = variant,
            instructor     = args.instructor,
            course_title   = args.course_title,
            chapter_title  = args.chapter_title,
            logo_public_id = args.poster_logo_public_id,
            brightness     = args.poster_brightness,
        )
        pg.generate(args.poster_output)
        print(f"Poster ({args.poster_variant}) → {args.poster_output}")

    if not did_something:
        parser.print_help()
