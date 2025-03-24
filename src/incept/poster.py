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
        self.base_public_id = base_public_id
        self.logo_public_id = logo_public_id
        self.instructor_name = instructor_name.upper()
        self.course_title = course_title.upper()
        self.chapter_title = chapter_title
        self.lesson_title = lesson_title.upper()
        self.link_text = link_text
        self.bounding_box = bounding_box
        self.logo_offset = logo_offset
        self.allow_upscale = allow_upscale

        # Initialize CloudinaryManager.
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
        Relevant fields for the poster are:
          - instructor (either a string or a list; we'll use the first element if a list)
          - course_title (or fallback to "name")
          - chapter_title
          - lesson_title (or fallback to "name")
          - link_text
        The cover and icon Notion fields are ignored for the poster.
        """
        # Use default public IDs for base image and logo.
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
          4. Draws the text blocks (instructor, course, chapter, lesson, link).
          5. Saves the final image as JPEG.
        """
        # Retrieve asset URLs via CloudinaryManager.
        base_image_url = self.manager.get_asset_url(self.base_public_id)
        logo_image_url = self.manager.get_asset_url(self.logo_public_id)

        # Download the base image.
        base_response = requests.get(base_image_url)
        base_response.raise_for_status()
        base_img = Image.open(BytesIO(base_response.content)).convert("RGBA")
        base_w, base_h = base_img.size

        # Download the logo image.
        logo_response = requests.get(logo_image_url)
        logo_response.raise_for_status()
        logo_img = Image.open(BytesIO(logo_response.content)).convert("RGBA")

        # Resize logo to fit within the bounding box.
        orig_w, orig_h = logo_img.size
        max_w, max_h = self.bounding_box
        scale_factor = min(max_w / orig_w, max_h / orig_h)
        if not self.allow_upscale:
            scale_factor = min(scale_factor, 1.0)
        new_w = int(orig_w * scale_factor)
        new_h = int(orig_h * scale_factor)
        logo_img = logo_img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        # Paste the logo onto the base image.
        base_img.paste(logo_img, self.logo_offset, logo_img)

        # Draw text on the image.
        draw = ImageDraw.Draw(base_img)
        text_color = (255, 255, 255, 255)

        # Instructor name.
        instr_w, instr_h = self._get_text_size(draw, self.instructor_name, self.font_instructor)
        instr_x, instr_y = (base_w - instr_w)*0.5, 750
        draw.text((instr_x, instr_y), self.instructor_name, font=self.font_instructor, fill=text_color)
        
        line_y = instr_y + instr_h + 10
        # draw.line((instr_x, line_y, instr_x + instr_w, line_y), fill=text_color, width=1)

        # Course title.
        course_x, course_y = instr_x, line_y + 40
        draw.text((course_x, course_y), self.course_title, font=self.font_course, fill=text_color)
        course_w, course_h = self._get_text_size(draw, self.course_title, self.font_course)
        course_line_y = course_y + course_h - 15
        draw.line((course_x, course_line_y, course_x + course_w, course_line_y), fill=text_color, width=1)

        # Chapter title.
        chap_x, chap_y = instr_x, course_line_y + 80
        draw.text((chap_x, chap_y), self.chapter_title, font=self.font_chapter, fill=text_color)
        chap_w, chap_h = self._get_text_size(draw, self.chapter_title, self.font_chapter)
        chap_line_y = chap_y + chap_h + 10
        draw.line((chap_x, chap_line_y, chap_x + chap_w, chap_line_y), fill=text_color, width=1)

        # Lesson title.
        lesson_x, lesson_y = instr_x, chap_line_y + 30
        draw.text((lesson_x, lesson_y), self.lesson_title, font=self.font_lesson, fill=text_color)

        # Link text centered at the bottom.
        link_w, link_h = self._get_text_size(draw, self.link_text, self.font_link)
        link_x = (base_w - link_w) // 2
        link_y = base_h - link_h - 50
        draw.text((link_x, link_y), self.link_text, font=self.font_link, fill=text_color)

        # Save the final composite as JPEG.
        final_img = base_img.convert("RGB")
        final_img.save(output_path, "JPEG")
        print(f"Poster saved to {output_path}")

# Example usage with a flat object:
if __name__ == "__main__":
    # Simulated flat object derived from addCourses payload.
    flat_object = {
        "instructor": ["Nick Chamberlain"],
        "name": "Cinematic Lighting in Houdini",
        "link": "https://rebelway.academy/lessons/introduction-6/",
        "course_title": "Cinematic Lighting in Houdini",
        "chapter_title": "Week 1",
        "lesson_title": "The Benefits of USD"
    }
    
    # Create a Poster instance from the flat object.
    poster = Poster.from_flat_object(flat_object)
    output_file = "/Users/suhail/Desktop/poster.jpg"
    poster.generate(output_file)
