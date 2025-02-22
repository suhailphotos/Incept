import pandas as pd
from incept.databases.notion import NotionDB
from incept.templates.manager import create_course_structure

DEFAULT_DB = "notion"

def getCourses(db=DEFAULT_DB, api_key=None, database_id=None, filter=None):
    """
    Retrieve courses from the specified database (defaults to Notion),
    returning a Pandas DataFrame.

    - If `filter` is provided (e.g., filter="Sample Course"),
      it will only retrieve the matching course(s) + their chapters/lessons.
    - If `filter` is not provided, it retrieves all courses, chapters, and lessons.
    """
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    notion_db = NotionDB(api_key, database_id)

    if filter:
        # Pass the filter along as 'Name' to match the `NotionDB.get_courses()` logic
        return notion_db.get_courses(Name=filter)
    else:
        # Retrieve all courses
        return notion_db.get_courses()

def addCourse(db=DEFAULT_DB, template="default", **kwargs):
    """
    Add a new course, ensuring it doesn’t already exist.

    - Creates a local folder structure for the course (via `create_course_structure`).
    - Inserts a new page in the Notion database.
    """
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    course_name = kwargs["name"]

    notion_db = NotionDB(api_key, database_id)

    # Check if course already exists
    existing_df = notion_db.get_courses()
    if course_name in existing_df["name"].values:
        return f"Course '{course_name}' already exists."

    # Create the local folder structure (notion page + local project alignment)
    create_course_structure(course_name, template)

    # Insert into Notion
    return notion_db.insert_course(kwargs)

def updateCourse(db=DEFAULT_DB, course_id=None, **kwargs):
    """Update a course."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.update_course(course_id, kwargs)

def deleteCourse(db=DEFAULT_DB, course_id=None, **kwargs):
    """Soft-delete (archive) a course."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.delete_course(course_id)

def addChapter(db=DEFAULT_DB, course_id=None, template="default", **kwargs):
    """Add a chapter under a specific course."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.insert_chapter(course_id, kwargs)

def addLesson(db=DEFAULT_DB, chapter_id=None, template="default", **kwargs):
    """Add a lesson under a specific chapter."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.insert_lesson(chapter_id, kwargs)

def updateChapter(db=DEFAULT_DB, chapter_id=None, **kwargs):
    """Update a chapter."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.update_chapter(chapter_id, kwargs)

def updateLesson(db=DEFAULT_DB, lesson_id=None, **kwargs):
    """Update a lesson."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.update_lesson(lesson_id, kwargs)

def deleteChapter(db=DEFAULT_DB, chapter_id=None, **kwargs):
    """Delete (archive) a chapter."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.delete_chapter(chapter_id)

def deleteLesson(db=DEFAULT_DB, lesson_id=None, **kwargs):
    """Delete (archive) a lesson."""
    if db != "notion":
        raise ValueError(f"Unsupported database: {db}")

    api_key = kwargs["api_key"]
    database_id = kwargs["database_id"]
    notion_db = NotionDB(api_key, database_id)

    return notion_db.delete_lesson(lesson_id)


# -- EXAMPLE USAGE / TESTING --
if __name__ == "__main__":
    from oauthmanager import OnePasswordAuthManager
    import json

    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    NOTION_API_KEY = notion_creds.get("credential")
    DATABASE_ID = "195a1865-b187-8103-9b6a-cc752ca45874"

    # 1) Fetch ALL courses:
    print("=== Fetching ALL courses ===")
    all_courses_df = getCourses(
        db="notion",
        api_key=NOTION_API_KEY,
        database_id=DATABASE_ID
    )
    print(all_courses_df, "\n")

    if not all_courses_df.empty:
        # Pretty-print each course's "chapters"
        for i, chapters_dict in enumerate(all_courses_df["chapters"]):
            print(f"Course row {i} chapters:")
            print(json.dumps(chapters_dict, indent=2))
            print("-" * 50)

    # 2) Fetch a specific course by name:
    course_name = "Sample Course A"  # example
    print(f"\n=== Fetching course with name='{course_name}' ===")
    filtered_df = getCourses(
        db="notion",
        api_key=NOTION_API_KEY,
        database_id=DATABASE_ID,
        filter=course_name
    )
    print(filtered_df, "\n")

    if not filtered_df.empty:
        # Print the "chapters" dict for the filtered course
        chapters_dict = filtered_df["chapters"].iloc[0]
        print("Filtered course chapters:")
        print(json.dumps(chapters_dict, indent=2))
