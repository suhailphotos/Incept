import os
import re
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from incept.utils.file_utils import sanitize_dir_name, get_default_documents_folder
from incept.databases.factory import get_db_client
from incept.templates.manager import create_course_structure

DEFAULT_DB = "notion"
CONFIG_DIR = Path.home() / ".incept"
CONFIG_SUBDIR = CONFIG_DIR / "config"
ENV_FILE = CONFIG_DIR / ".env"

def getCourses(db=DEFAULT_DB, filter=None, **kwargs):
    """
    Retrieve courses from whichever DB is specified.
      - If `filter` is provided, it might filter by course name.
    :return: A pandas DataFrame.
    """
    db_client = get_db_client(db, **kwargs)
    if filter:
        return db_client.get_courses(Name=filter)
    else:
        return db_client.get_courses()


def addCourse(db=DEFAULT_DB, template="default", df=None, **kwargs):
    """
    Add course(s) from a Pandas DataFrame.
    - If exactly 1 row, returns single insert result or skip message.
    - If multiple rows, returns list of (course_name, status).
    - If empty, returns a simple message.
    """
    db_client = get_db_client(db, **kwargs)

    if df is None or df.empty:
        return "DataFrame is empty. No course(s) to add."
    if "name" not in df.columns:
        raise ValueError("DataFrame must contain 'name' column.")

    # (Optional) load .env here if you want .env to be loaded for each row
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    existing_df = db_client.get_courses()
    existing_names = set(existing_df["name"].values) if not existing_df.empty else set()

    results = []
    for _, row_data in df.iterrows():
        course_data = row_data.to_dict()
        raw_course_name = course_data["name"]
        sanitized_dir_name = sanitize_dir_name(raw_course_name)

        if raw_course_name in existing_names:
            results.append((raw_course_name, f"Course '{raw_course_name}' already exists. Skipped."))
            continue

        # 1) Notion path
        base_notion_path = course_data.get("path") or os.getenv("COURSE_FOLDER_PATH")
        if not base_notion_path:
            # fallback symbolic path
            base_notion_path = str(get_default_documents_folder() / "courses")

        notion_path_str = f"{base_notion_path}/{sanitized_dir_name}"  # e.g. "$DATALIB/threeD/courses/My_Course"
        course_data["path"] = notion_path_str  # store symbolic path in Notion

        # 2) Local folder path
        expanded_base_path = os.path.expandvars(os.getenv("COURSE_FOLDER_PATH", ""))
        if not expanded_base_path:
            expanded_base_path = str(get_default_documents_folder() / "courses")

        local_course_path = Path(expanded_base_path) / sanitized_dir_name

        # 3) Create local folder from template
        create_course_structure(
            course_name=sanitized_dir_name,  # pass sanitized to manager
            template=template,
            base_path=local_course_path
        )

        # 4) Insert into DB
        res = db_client.insert_course(**course_data)
        existing_names.add(raw_course_name)
        results.append((raw_course_name, res))

    return results if len(results) > 1 else results[0][1]

def updateCourse(db=DEFAULT_DB, **kwargs):
    """
    Placeholder for future update logic.
    """
    return "updateCourse not yet implemented."


def deleteCourse(db=DEFAULT_DB, course_id=None, **kwargs):
    """
    Placeholder for future delete logic.
    """
    return "deleteCourse not yet implemented."


def addChapter(db=DEFAULT_DB, course_id=None, template="default", **kwargs):
    """
    Placeholder for future addChapter logic.
    """
    return "addChapter not yet implemented."


def addLesson(db=DEFAULT_DB, chapter_id=None, template="default", **kwargs):
    """
    Placeholder for future addLesson logic.
    """
    return "addLesson not yet implemented."


def updateChapter(db=DEFAULT_DB, chapter_id=None, **kwargs):
    """
    Placeholder for future updateChapter logic.
    """
    return "updateChapter not yet implemented."


def updateLesson(db=DEFAULT_DB, lesson_id=None, **kwargs):
    """
    Placeholder for future updateLesson logic.
    """
    return "updateLesson not yet implemented."


def deleteChapter(db=DEFAULT_DB, chapter_id=None, **kwargs):
    """
    Placeholder for future deleteChapter logic.
    """
    return "deleteChapter not yet implemented."


def deleteLesson(db=DEFAULT_DB, lesson_id=None, **kwargs):
    """
    Placeholder for future deleteLesson logic.
    """
    return "deleteLesson not yet implemented."


# -- EXAMPLE USAGE / TESTING --
if __name__ == "__main__":
    from oauthmanager import OnePasswordAuthManager
    import json

    # Example: show how to retrieve courses
    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    NOTION_API_KEY = notion_creds.get("credential")
    DATABASE_ID = "195a1865-b187-8103-9b6a-cc752ca45874"

    print("=== Fetching ALL courses ===")
    all_courses_df = getCourses(
        db="notion",
        api_key=NOTION_API_KEY,
        database_id=DATABASE_ID
    )
    print(all_courses_df, "\n")

    # 1) Single row insert
    import pandas as pd

    df_single = pd.DataFrame([{
        "name": "Sample Course X",
        "description": "Description for X",
        "tags": ["Python", "Test"],
    }])
    single_result = addCourse(
        db="notion",
        template="default",
        df=df_single,
        api_key=NOTION_API_KEY,
        database_id=DATABASE_ID
    )
    print("Single addCourse result:", single_result)

    # 2) Multi-row insert
    df_multi = pd.DataFrame([
        {"name": "Course Y", "description": "Multi-test Y", "tags": ["Multi"]},
        {"name": "Course Z", "description": "Multi-test Z", "tags": ["Multi"]},
    ])
    multi_result = addCourse(
        db="notion",
        template="default",
        df=df_multi,
        api_key=NOTION_API_KEY,
        database_id=DATABASE_ID
    )
    print("Multi addCourse results:", multi_result)
