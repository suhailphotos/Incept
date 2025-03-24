import os
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from notionmanager.cloudinary_manager import CloudinaryManager

class Poster:
    # Default public IDs for the base image and logo if not provided
    DEFAULT_BASE_PUBLIC_ID = "poster/base_image.jpg"
    DEFAULT_LOGO_PUBLIC_ID = "icon/rebelway_logo.png"

    def __init__(self,
                 base_public_id: str,
                 logo_public_id: str,
                 instructor_name: str,
                 course_title: str,
                 chapter_title: str,
                 lesson_title: str,
                 link_text: str,
                 bounding_box: tuple = (290, 290),
                 logo_offset: tuple = (55, 70),
                 allow_upscale: bool = False):
        """
        Initializes the Poster object with the necessary poster fields.
        """
        # Uppercase certain fields to match your reference style
        self.base_public_id = base_public_id
        self.logo_public_id = logo_public_id
        self.instructor_name = instructor_name.upper()
        self.course_title = course_title.upper()
        self.chapter_title = chapter_title  # keep normal case if desired
        self.lesson_title = lesson_title.upper()
        self.link_text = link_text

        self.bounding_box = bounding_box
        self.logo_offset = logo_offset
        self.allow_upscale = allow_upscale

        # Initialize CloudinaryManager
        self.manager = CloudinaryManager()

        # Set up fonts (using Core Sans C fonts from your .config/fonts/coresansc folder).
        self.font_dir = Path(__file__).parent / ".config" / "fonts" / "coresansc"
        self.font_instructor = ImageFont.truetype(str(self.font_dir / "coresansc35.otf"), 40)
        self.font_course     = ImageFont.truetype(str(self.font_dir / "coresansc75.otf"), 47)
        self.font_chapter    = ImageFont.truetype(str(self.font_dir / "coresansc45.otf"), 40)
        self.font_lesson     = ImageFont.truetype(str(self.font_dir / "coresansc55.otf"), 47)
        self.font_link       = ImageFont.truetype(str(self.font_dir / "coresansc25.otf"), 25)

    @classmethod
    def from_flat_object(cls, flat_object: dict):
        """
        Instantiate a Poster using a flat_object (from your JSON payload).
        Only relevant fields for the poster are used:
          - instructor (list or string)
          - course_title (or fallback to "name")
          - chapter_title
          - lesson_title (or fallback to "name")
          - link_text
        """
        # Use default public IDs for base image and logo
        base_public_id = cls.DEFAULT_BASE_PUBLIC_ID
        logo_public_id = cls.DEFAULT_LOGO_PUBLIC_ID

        instructor = flat_object.get("instructor")
        if isinstance(instructor, list) and instructor:
            instructor_name = instructor[0]
        else:
            instructor_name = instructor or "Unknown Instructor"

        course_title = flat_object.get("course_title") or flat_object.get("name") or "Course Title"
        chapter_title = flat_object.get("chapter_title") or "Chapter Title"
        lesson_title = flat_object.get("lesson_title") or flat_object.get("name") or "Lesson Title"
        link_text = flat_object.get("link") or "www.example.com"

        return cls(base_public_id, logo_public_id, instructor_name,
                   course_title, chapter_title, lesson_title, link_text)

    def _get_text_size(self, draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont) -> tuple:
        """
        Uses draw.textbbox to calculate the text dimensions.
        """
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return (right - left, bottom - top)

    def generate(self, output_path: str):
        """
        Generates the poster image:
          1. Downloads the base image and logo from Cloudinary.
          2. Resizes the logo to fit within the bounding box while preserving aspect ratio.
          3. Overlays the logo onto the base image.
          4. Draws the text blocks (instructor, course, chapter, lesson, link) with 2 dividing lines.
          5. Saves the final image as JPEG.
        """

        # 1) Download the base and logo images
        base_image_url = self.manager.get_asset_url(self.base_public_id)
        logo_image_url = self.manager.get_asset_url(self.logo_public_id)

        base_response = requests.get(base_image_url)
        base_response.raise_for_status()
        base_img = Image.open(BytesIO(base_response.content)).convert("RGBA")
        base_w, base_h = base_img.size

        logo_response = requests.get(logo_image_url)
        logo_response.raise_for_status()
        logo_img = Image.open(BytesIO(logo_response.content)).convert("RGBA")

        # 2) Resize the logo
        orig_w, orig_h = logo_img.size
        max_w, max_h = self.bounding_box
        scale_factor = min(max_w / orig_w, max_h / orig_h)
        if not self.allow_upscale:
            scale_factor = min(scale_factor, 1.0)
        new_w = int(orig_w * scale_factor)
        new_h = int(orig_h * scale_factor)
        logo_img = logo_img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        # 3) Paste the logo
        base_img.paste(logo_img, self.logo_offset, logo_img)

        # 4) Prepare to draw text
        draw = ImageDraw.Draw(base_img)
        text_color = (150, 150, 150, 255)

        # Measure text widths/heights in advance (so we know how long lines need to be)
        instr_w, instr_h   = self._get_text_size(draw, self.instructor_name, self.font_instructor)
        course_w, course_h = self._get_text_size(draw, self.course_title, self.font_course)
        chap_w, chap_h     = self._get_text_size(draw, self.chapter_title, self.font_chapter)
        lesson_w, lesson_h = self._get_text_size(draw, self.lesson_title, self.font_lesson)

        # Define vertical positions (tweak these to match your desired spacing)
        # Starting point: Instructor near the middle
        instr_y = 750
        gap = 30
        # We'll place a line between the instructor and the course.
        # The line should match the width of the COURSE text below it.
        line_1_y = instr_y + instr_h + gap
        course_y = line_1_y + gap - 20
        # Next is the chapter title
        chap_y = course_y + course_h + 200
        # Then a line between chapter and lesson
        line_2_y = chap_y + chap_h + gap
        lesson_y = line_2_y + gap - 20

        # Centering each text horizontally
        instr_x  = (base_w - instr_w) / 2
        course_x = (base_w - course_w) / 2
        chap_x   = (base_w - chap_w) / 2
        lesson_x = (base_w - lesson_w) / 2

        # Draw instructor
        draw.text((instr_x, instr_y), self.instructor_name, font=self.font_instructor, fill=text_color)

        # Draw line #1 (width of the course title), centered
        line_1_x = (base_w - course_w) / 2
        draw.line((line_1_x, line_1_y, line_1_x + course_w, line_1_y), fill=text_color, width=1)

        # Draw course title
        draw.text((course_x, course_y), self.course_title, font=self.font_course, fill=text_color)

        # Draw chapter
        draw.text((chap_x, chap_y), self.chapter_title, font=self.font_chapter, fill=text_color)

        # Draw line #2 (width of the lesson title), centered
        line_2_x = (base_w - lesson_w) / 2
        draw.line((line_2_x, line_2_y, line_2_x + lesson_w, line_2_y), fill=text_color, width=1)

        # Draw lesson
        draw.text((lesson_x, lesson_y), self.lesson_title, font=self.font_lesson, fill=text_color)

        # 5) Link text at bottom, centered
        link_w, link_h = self._get_text_size(draw, self.link_text, self.font_link)
        link_x = (base_w - link_w) // 2
        link_y = base_h - link_h - 50
        draw.text((link_x, link_y), self.link_text, font=self.font_link, fill=text_color)

        # Convert to RGB and save as JPEG
        final_img = base_img.convert("RGB")
        final_img.save(output_path, "JPEG")
        print(f"Poster saved to {output_path}")


# Example usage with a flat object:
if __name__ == "__main__":
    flat_object = {
        "instructor": ["Nick Chamberlain"],
        "name": "Cinematic Lighting in Houdini",
        "link": "https://rebelway.academy/lessons/introduction-6/",
        "course_title": "Cinematic Lighting in Houdini",
        "chapter_title": "Week 1",
        "lesson_title": "The Benefits of USD"
    }

    poster = Poster.from_flat_object(flat_object)
    output_file = "/Users/suhail/Desktop/poster.jpg"
    poster.generate(output_file)
