import pandas as pd
from incept.databases.factory import get_db_client
from incept.templates.manager import create_course_structure

DEFAULT_DB = "notion"

def getCourses(db=DEFAULT_DB, filter=None, **kwargs):
    """
    Retrieve courses from whichever DB is specified.
      - If `filter` is provided, it might filter by course name.
    :return: A pandas DataFrame.
    """
    db_client = get_db_client(db, **kwargs)

    # If your DB client expects the filter as "Name=...", do so:
    if filter:
        return db_client.get_courses(Name=filter)
    else:
        return db_client.get_courses()

def addCourse(db=DEFAULT_DB, template="default", df=None, **kwargs):
    """
    Add a SINGLE course from a pandas DataFrame (if db=Notion, do Notion logic;
    if db=Postgres, do Postgres, etc.).

    Steps:
     1. If `df` has multiple rows, use the first row only.
     2. Check if it exists (by name).
     3. If not, create local folder structure + insert into DB.
    """
    db_client = get_db_client(db, **kwargs)

    if df is None or df.empty:
        return "DataFrame is empty. No course to add."

    row = df.iloc[0].to_dict()
    if "name" not in row:
        raise ValueError("Missing 'name' column in the first row.")

    course_name = row["name"]

    # Check if course name exists
    existing_df = db_client.get_courses()
    if not existing_df.empty and course_name in set(existing_df["name"].values):
        return f"Course '{course_name}' already exists."

    # create local folder
    create_course_structure(course_name, template)

    # Insert into DB
    return db_client.insert_course(**row)

def addCourses(db=DEFAULT_DB, template="default", df=None, **kwargs):
    """
    Add multiple courses from a DataFrame.
    Each row is a separate course. Skips existing ones.
    """
    db_client = get_db_client(db, **kwargs)

    if df is None or df.empty:
        return "DataFrame is empty. No courses to add."

    if "name" not in df.columns:
        raise ValueError("Missing 'name' column in df.")

    existing_df = db_client.get_courses()
    existing_names = set(existing_df["name"].values) if not existing_df.empty else set()

    results = []
    for idx, row_data in df.iterrows():
        course_data = row_data.to_dict()
        course_name = course_data["name"]

        if course_name in existing_names:
            results.append((course_name, f"Already exists. Skipped."))
            continue

        create_course_structure(course_name, template)
        res = db_client.insert_course(**course_data)
        existing_names.add(course_name)
        results.append((course_name, res))

    return results

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
