import os
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from notionmanager.cloudinary_manager import CloudinaryManager

def create_poster(
    base_public_id: str,
    logo_public_id: str,
    output_path: str,
    instructor_name: str = "Nick Chamberlain",
    course_title: str = "Cinematic Lighting in Houdini",
    chapter_title: str = "Week 1",
    lesson_title: str = "The Benefits of USD",
    link_text: str = "www.rebelway.net",
    bounding_box: tuple = (300, 300),  # max (width, height) for logo
    logo_offset: tuple = (70, 70),
    allow_upscale: bool = False
):
    """
    Creates a poster by:
      1) Downloading a base image from Cloudinary via public_id.
      2) Downloading a logo from Cloudinary and resizing it to fit bounding_box.
      3) Pasting the logo at logo_offset.
      4) Drawing text (instructor, course, chapter, lesson, link) using Core Sans C fonts.
      5) Saving the composite as a JPEG.
    """

    manager = CloudinaryManager()
    base_image_url = manager.get_asset_url(base_public_id)
    logo_image_url = manager.get_asset_url(logo_public_id)

    # 1) Download the base image
    base_response = requests.get(base_image_url)
    base_response.raise_for_status()
    base_img = Image.open(BytesIO(base_response.content)).convert("RGBA")
    base_w, base_h = base_img.size

    # 2) Download and resize the logo
    logo_response = requests.get(logo_image_url)
    logo_response.raise_for_status()
    logo_img = Image.open(BytesIO(logo_response.content)).convert("RGBA")

    orig_w, orig_h = logo_img.size
    max_w, max_h = bounding_box
    scale_factor = min(max_w / orig_w, max_h / orig_h)
    if not allow_upscale:
        scale_factor = min(scale_factor, 1.0)

    new_w = int(orig_w * scale_factor)
    new_h = int(orig_h * scale_factor)
    logo_img = logo_img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

    # 3) Paste the logo
    base_img.paste(logo_img, logo_offset, logo_img)

    # 4) Prepare fonts (adjust paths to your actual location)
    font_dir = Path(__file__).parent / ".config" / "fonts" / "coresansc"
    font_instructor = ImageFont.truetype(str(font_dir / "coresansc35.otf"), 40)
    font_course     = ImageFont.truetype(str(font_dir / "coresansc75.otf"), 47)
    font_chapter    = ImageFont.truetype(str(font_dir / "coresansc45.otf"), 40)
    font_lesson     = ImageFont.truetype(str(font_dir / "coresansc55.otf"), 47)
    font_link       = ImageFont.truetype(str(font_dir / "coresansc25.otf"), 25)

    draw = ImageDraw.Draw(base_img)
    text_color = (255, 255, 255, 255)

    # Helper function to get text width & height using textbbox
    def get_text_size(text, font_obj):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font_obj)
        return (right - left, bottom - top)

    # 5) Place text

    # Instructor name
    instr_x, instr_y = 70, 300
    draw.text((instr_x, instr_y), instructor_name, font=font_instructor, fill=text_color)
    instr_w, instr_h = get_text_size(instructor_name, font_instructor)

    # Optional line under instructor
    line_y = instr_y + instr_h + 10
    draw.line((instr_x, line_y, instr_x + instr_w, line_y), fill=text_color, width=1)

    # Course title
    course_x, course_y = instr_x, line_y + 40
    draw.text((course_x, course_y), course_title, font=font_course, fill=text_color)
    course_w, course_h = get_text_size(course_title, font_course)
    course_line_y = course_y + course_h + 10
    draw.line((course_x, course_line_y, course_x + course_w, course_line_y), fill=text_color, width=1)

    # Chapter title
    chap_x, chap_y = instr_x, course_line_y + 80
    draw.text((chap_x, chap_y), chapter_title, font=font_chapter, fill=text_color)
    chap_w, chap_h = get_text_size(chapter_title, font_chapter)
    chap_line_y = chap_y + chap_h + 10
    draw.line((chap_x, chap_line_y, chap_x + chap_w, chap_line_y), fill=text_color, width=1)

    # Lesson title
    lesson_x, lesson_y = instr_x, chap_line_y + 30
    draw.text((lesson_x, lesson_y), lesson_title, font=font_lesson, fill=text_color)

    # Link (centered at bottom)
    link_w, link_h = get_text_size(link_text, font_link)
    link_x = (base_w - link_w) // 2
    link_y = base_h - link_h - 50
    draw.text((link_x, link_y), link_text, font=font_link, fill=text_color)

    # 6) Convert to RGB and save as JPEG
    final_img = base_img.convert("RGB")
    final_img.save(output_path, "JPEG")
    print(f"Poster saved to {output_path}")


if __name__ == "__main__":
    create_poster(
        base_public_id="poster/base_image.jpg",
        logo_public_id="icon/rebelway_logo.png",
        output_path="/Users/suhail/Desktop/poster.jpg",
        instructor_name="Nick Chamberlain",
        course_title="Cinematic Lighting in Houdini",
        chapter_title="Week 1",
        lesson_title="The Benefits of USD",
        link_text="www.rebelway.net",
        bounding_box=(300, 300),
        logo_offset=(70, 70),
        allow_upscale=False
    )
