from __future__ import annotations  #Enables deferred evaluation of annotations
from incept.media.icon import Icon
from incept.media.cover import Cover

class Course:
    DEFAULT_NAME = "Sample Course"
    DEFAULT_DESCRIPTION = "This is a sample course. Write description here."
    DEFAULT_PATH = "$DATALIB/threeD/courses"
    DEFAULT_COURSE_LINK = "https://example.com"
    DEFAULT_CONTENT_TYPE = "Course"
    DEFAULT_TOOL = "149a1865-b187-80f9-b21f-c9c96430bf62"  # Sample tool ID
    DEFAULT_TAGS = ["Python"]
    DEFAULT_TEMPLATE = "default"

    def __init__(self, name=DEFAULT_NAME, description=DEFAULT_DESCRIPTION, path=DEFAULT_PATH,
                 course_link=DEFAULT_COURSE_LINK, content_type=DEFAULT_CONTENT_TYPE,
                 icon=None, cover=None, tool=DEFAULT_TOOL, tags=None, template=DEFAULT_TEMPLATE):
        """
        Represents a Course object.

        Parameters:
        - name (str): Course title.
        - description (str): Short course description.
        - path (str): File system path where course files are stored.
        - course_link (str): URL to the course webpage.
        - content_type (str): Type of entry (default: "Course").
        - icon (Icon): Course icon.
        - cover (Cover): Course cover image.
        - tool (str): Associated tool ID.
        - tags (list): Tags for classification.
        - template (str): Folder template name.
        """
        self.name = name
        self.description = description
        self.path = path
        self.course_link = course_link
        self.content_type = content_type
        self.icon = icon or Icon()
        self.cover = cover or Cover()
        self.tool = tool
        self.tags = tags or self.DEFAULT_TAGS
        self.template = template
        self.chapters = []

    def add_chapter(self, chapter: "Chapter"):  # Use string-based type hint
        """Adds a Chapter object to the Course."""
        from incept.chapter import Chapter  #Import inside method to avoid circular import
        chapter.parent_course = self
        self.chapters.append(chapter)

if __name__ == "__main__":
    newCourse = Course()
    print(newCourse)
