# src/incept/__init__.py

from incept.courses import (
    getCourses, addCourse, updateCourse, deleteCourse,
    addChapter, addLesson, updateChapter, updateLesson,
    deleteChapter, deleteLesson
)
from incept.databases.notion import NotionDB
from incept.templates.manager import (
    get_available_templates,
    create_folder_structure,
    builtin_templates_dir,
    ensure_templates_from_package,
    find_placeholder_folder
)
from incept.utils.file_utils import sync_templates, sanitize_dir_name, get_default_documents_folder

__all__ = [
    # Course-related
    "getCourses", "addCourse", "updateCourse", "deleteCourse",
    "addChapter", "addLesson", "updateChapter", "updateLesson",
    "deleteChapter", "deleteLesson",

    # Database
    "NotionDB",

    # Templates
    "get_available_templates", "create_folder_structure",
    "builtin_templates_dir", "ensure_templates_from_package", "find_placeholder_folder",

    # File utilities
    "sync_templates", "get_default_documents_folder", "sanitize_dir_name",
]
