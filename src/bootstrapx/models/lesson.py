from .chapter import Chapter

class Lesson:
    DEFAULT_NAME = "Sample Lesson"
    DEFAULT_CONTENT_TYPE = "Lesson"

    def __init__(self, name=DEFAULT_NAME, content_type=DEFAULT_CONTENT_TYPE, parent_chapter=None):
        """
        Represents a Lesson object.

        Parameters:
        - name (str): Lesson title.
        - content_type (str): Type of entry (default: "Lesson").
        - parent_chapter (Chapter or None): The parent Chapter object.
        """
        self.name = name
        self.content_type = content_type
        self.parent_chapter = parent_chapter  # Reference to parent chapter
