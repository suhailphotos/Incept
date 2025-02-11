"""
Incept: A modular package for managing courses, projects, and directories.
"""

# Public API for users
from .coursemanager import newCourse, newChapter, newLesson
from . import media
from . import notion
from . import template
