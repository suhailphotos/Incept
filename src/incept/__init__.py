# src/incept/__init__.py

from incept.courses import (
    getCourses, addCourse, updateCourse, deleteCourse,
    addChapter, addLesson, updateChapter, updateLesson,
    deleteChapter, deleteLesson
)
from incept.databases.notion import NotionDB
from incept.templates.manager import (
    get_available_templates,
    create_course_structure,
    builtin_templates_dir,
    ensure_templates_from_package
)
from incept.utils.file_utils import sync_templates

__all__ = [
    # Course-related
    "getCourses", "addCourse", "updateCourse", "deleteCourse",
    "addChapter", "addLesson", "updateChapter", "updateLesson",
    "deleteChapter", "deleteLesson",

    # Database
    "NotionDB",

    # Templates
    "get_available_templates", "create_course_structure",
    "builtin_templates_dir", "ensure_templates_from_package",

    # File utilities
    "sync_templates",
]
