import pandas as pd
from incept.databases.notion import NotionDB
from incept.templates.manager import create_course_structure

# Default database system (can be extended later)
DEFAULT_DB = "notion"

def getCourses(db=DEFAULT_DB, **kwargs):
    """Retrieve courses from the database as a pandas DataFrame."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).get_courses(filter=kwargs.get("filter"))
    else:
        raise ValueError(f"Unsupported database: {db}")

def addCourse(db=DEFAULT_DB, template="default", **kwargs):
    """Add a new course, ensuring it doesn’t already exist."""
    if db == "notion":
        notion_db = NotionDB(kwargs["api_key"], kwargs["database_id"])
        existing_courses = notion_db.get_courses()
        if kwargs["name"] in existing_courses["name"].values:
            return "Course already exists."
        
        # Create folder structure for the course
        create_course_structure(kwargs["name"], template)

        return notion_db.insert_course(kwargs)
    else:
        raise ValueError(f"Unsupported database: {db}")

def updateCourse(db=DEFAULT_DB, course_id=None, **kwargs):
    """Update a course."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).update_course(course_id, kwargs)
    else:
        raise ValueError(f"Unsupported database: {db}")

def deleteCourse(db=DEFAULT_DB, course_id=None, **kwargs):
    """Delete a course (soft delete by archiving)."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).delete_course(course_id)
    else:
        raise ValueError(f"Unsupported database: {db}")

def addChapter(db=DEFAULT_DB, course_id=None, template="default", **kwargs):
    """Add a chapter under a course."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).insert_chapter(course_id, kwargs)
    else:
        raise ValueError(f"Unsupported database: {db}")

def addLesson(db=DEFAULT_DB, chapter_id=None, template="default", **kwargs):
    """Add a lesson under a chapter."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).insert_lesson(chapter_id, kwargs)
    else:
        raise ValueError(f"Unsupported database: {db}")

def updateChapter(db=DEFAULT_DB, chapter_id=None, **kwargs):
    """Update a chapter."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).update_chapter(chapter_id, kwargs)
    else:
        raise ValueError(f"Unsupported database: {db}")

def updateLesson(db=DEFAULT_DB, lesson_id=None, **kwargs):
    """Update a lesson."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).update_lesson(lesson_id, kwargs)
    else:
        raise ValueError(f"Unsupported database: {db}")

def deleteChapter(db=DEFAULT_DB, chapter_id=None, **kwargs):
    """Delete a chapter."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).delete_chapter(chapter_id)
    else:
        raise ValueError(f"Unsupported database: {db}")

def deleteLesson(db=DEFAULT_DB, lesson_id=None, **kwargs):
    """Delete a lesson."""
    if db == "notion":
        return NotionDB(kwargs["api_key"], kwargs["database_id"]).delete_lesson(lesson_id)
    else:
        raise ValueError(f"Unsupported database: {db}")
