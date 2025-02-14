from __future__ import annotations
#from incept.lesson import Lesson  

class Chapter:
    DEFAULT_NAME = "Sample Chapter"
    DEFAULT_CONTENT_TYPE = "Chapter"

    def __init__(self, name=DEFAULT_NAME, content_type=DEFAULT_CONTENT_TYPE,
                 materials_path=None, assignments_path=None, parent_course=None):
        """
        Represents a Chapter object.

        Parameters:
        - name (str): Chapter title.
        - content_type (str): Type of entry (default: "Chapter").
        - materials_path (str or None): Path to chapter materials.
        - assignments_path (str or None): Path to assignments.
        - parent_course (Course or None): The parent Course object.
        """
        self.name = name
        self.content_type = content_type
        self.materials_path = materials_path
        self.assignments_path = assignments_path
        self.parent_course = parent_course  # Store parent reference
        self.lessons = []

    def add_lesson(self, lesson: "Lesson"):
        """Adds a Lesson object to the Chapter."""
        from incept.lesson import Lesson
        lesson.parent_chapter = self  # Assigns parent reference
        self.lessons.append(lesson)
