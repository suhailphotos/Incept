# src/incept/courses.py

import os
import re
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from incept.databases.factory import get_db_client
from incept.templates.manager import create_folder_structure
from incept.utils import (
    sanitize_dir_name,
    get_default_documents_folder,
    get_next_numeric_prefix,
    normalize_placeholder,
)

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
    
    - If exactly 1 row, returns a DataFrame with one row.
    - If multiple rows, returns a DataFrame with one row per inserted course.
    - If the DataFrame is empty, returns a DataFrame with a message.
    
    This function accumulates the raw page responses returned from each insert,
    and once all courses are inserted, calls _convert_to_dataframe() on the accumulated list.
    This produces a rolled‐up DataFrame (in the same format as get_courses()) without
    having to re‐query all pages from Notion.
    """
    db_client = get_db_client(db, **kwargs)
    if df is None or df.empty:
        return pd.DataFrame([{"course_name": None, "result": "DataFrame is empty. No course(s) to add."}])
    if "name" not in df.columns:
        raise ValueError("DataFrame must contain 'name' column.")

    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    existing_df = db_client.get_courses()
    existing_names = set(existing_df["name"].values) if not existing_df.empty else set()
    env_search_folder_name = os.getenv('COURSE_SEARCH_FOLDER')
    inserted_pages = []  # accumulate raw responses
    results = []         # to record error messages or inserted IDs

    for _, row_data in df.iterrows():
        course_data = row_data.to_dict()
        raw_course_name = course_data["name"]
        sanitized_dir_name = sanitize_dir_name(raw_course_name)

        if raw_course_name in existing_names:
            results.append((raw_course_name, "Course already exists"))
            continue

        # Determine the provided path from JSON or environment.
        provided_path = course_data.get("path") or os.getenv("COURSE_FOLDER_PATH")
        if not provided_path:
            provided_path = str(get_default_documents_folder() / "courses")
        
        # Check if provided_path ends with a placeholder pattern.
        placeholder_match = re.search(r'(\{[^}]+\})\s*$', provided_path)
        if placeholder_match:
            placeholder = placeholder_match.group(1)
            if placeholder.startswith("{##"):
                # Numeric prefix mode triggered from the provided path.
                expanded_base = os.path.expandvars(provided_path)
                base_for_numeric = Path(expanded_base).parent
                numeric_prefix = get_next_numeric_prefix(base_for_numeric)
                new_folder_name = f"{numeric_prefix}_{sanitized_dir_name}"
                notion_path_str = provided_path.replace(placeholder, new_folder_name)
                local_course_path = base_for_numeric / new_folder_name
                search_placeholder = normalize_placeholder(placeholder)
            else:
                notion_path_str = provided_path.replace(placeholder, sanitized_dir_name)
                expanded_base = os.path.expandvars(provided_path)
                local_course_path = Path(expanded_base.replace(placeholder, sanitized_dir_name))
                search_placeholder = normalize_placeholder(placeholder)
        elif env_search_folder_name and env_search_folder_name.startswith("{##"):
            # Fallback: no placeholder in provided_path, but env value triggers numeric prefix.
            expanded_base = os.path.expandvars(provided_path)
            base_for_numeric = Path(expanded_base)
            numeric_prefix = get_next_numeric_prefix(base_for_numeric)
            new_folder_name = f"{numeric_prefix}_{sanitized_dir_name}"
            notion_path_str = f"{provided_path.rstrip('/')}/{new_folder_name}"
            local_course_path = base_for_numeric / new_folder_name
            search_placeholder = normalize_placeholder(env_search_folder_name)
        else:
            notion_path_str = f"{provided_path.rstrip('/')}/{sanitized_dir_name}"
            expanded_base = os.path.expandvars(provided_path)
            local_course_path = Path(expanded_base) / sanitized_dir_name
            search_placeholder = normalize_placeholder(env_search_folder_name) if env_search_folder_name else "{course_name}"

        # Update course_data with the symbolic Notion path.
        course_data["path"] = notion_path_str

        try:
            create_folder_structure(
                folder_name=sanitized_dir_name,
                search_folder_name=search_placeholder,
                template=template,
                base_path=local_course_path
            )
        except Exception as e:
            results.append((raw_course_name, f"Folder exists: {local_course_path}"))
            continue

        # Insert the course; insert_course() returns the raw Notion page object.
        resp = db_client.insert_course(**course_data)
        if resp.get("id"):
            inserted_pages.append(resp)
            existing_names.add(raw_course_name)
            results.append((raw_course_name, resp.get("id")))
        else:
            results.append((raw_course_name, "Insert failed"))

    # Once all insertions are complete, convert the accumulated raw responses to a rolled-up DataFrame.
    if inserted_pages:
        new_courses_df = db_client._convert_to_dataframe(inserted_pages)
    else:
        new_courses_df = pd.DataFrame(results, columns=["course_name", "result"])

    return new_courses_df

def addChapter(
    db=DEFAULT_DB,
    template="default",
    chapter_folder="chapters",
    df=None,
    **kwargs
):
    """
    Add chapter(s) from a Pandas DataFrame to the given course.

    - Either `course_id` or `course_name` must be provided.
    - For Notion, sets the "Parent item" property to the parent course ID.
    - Copies the local chapter folder from the template into <course_folder>/<chapter_folder>/...
    - Returns a rolled‐up DataFrame.
    """
    return {
        "db": db,
        "template": template,
        "chapter_folder": chapter_folder,
        "df": df,
        **kwargs
    }

def addLesson(db=DEFAULT_DB, chapter_id=None, template="default", **kwargs):
    """
    Placeholder for future addLesson logic.
    """
    return "addLesson not yet implemented."

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


if __name__ == "__main__":
    from oauthmanager import OnePasswordAuthManager
    import json
    from notionmanager.notion import NotionManager
    from incept.cli import format_course_df

    # --- Environment setup ---
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    db_type = os.getenv("DATABASE_NAME", "notion")

    # --- Retrieve Notion API credentials ---
    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    api_key = notion_creds.get("credential")
    database_id = "195a1865-b187-8103-9b6a-cc752ca45874"

    # --- Override options (unused because we rely solely on JSON) ---
    name = None
    description = None
    link = None
    path = None
    folder_template = None

    # --- Define chapter folder (for example purposes) ---
    chapter_folder = "chapters"

    # --- Load JSON file ---
    data_file_path = CONFIG_SUBDIR / "full_course.json"
    file_path = data_file_path
    if not file_path.exists():
        raise Exception(f"Data file not found: {file_path}")
    with file_path.open("r") as f:
        try:
            file_json = json.load(f)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in {file_path}: {e}")

    # --- Extract course objects from JSON ---
    courses_list = []
    if "course" in file_json:
        courses_list = [file_json["course"]]
    elif "courses" in file_json:
        courses = file_json["courses"]
        if isinstance(courses, list):
            courses_list = courses
        elif isinstance(courses, dict):
            courses_list = [courses]
        else:
            raise Exception("The 'courses' key must contain a list or a dictionary.")
    else:
        raise Exception("Invalid JSON file: must contain either 'course' or 'courses' key.")

    # --- Build filter criteria based on course names ---
    course_names = []
    for course in courses_list:
        if "name" in course and course["name"]:
            course_names.append(course["name"])
        else:
            raise Exception("Course name not found in one of the courses in JSON.")
    # If only one unique course name is provided, use it directly.
    if len(set(course_names)) == 1:
        filter_criteria = course_names[0]
    else:
        # Build an OR filter JSON payload.
        filter_criteria = {
            "filter": {
                "or": [
                    {
                        "property": "Name",
                        "title": {"equals": cn}
                    } for cn in course_names
                ]
            }
        }

    # --- Query the database for the course(s) ---
    # getCourses returns a DataFrame with each course as a single row (including its children).
    courses_df = getCourses(db=db_type, filter=filter_criteria, api_key=api_key, database_id=database_id)
    if courses_df.empty:
        raise Exception("No course found in the database matching the provided JSON course name(s).")
    # Take only the first row from the result (as a DataFrame).
    course_row_df = courses_df.iloc[[0]]

    # --- Call addChapter using the course information from the database ---
    result_df = addChapter(
        db=db_type,
        template=folder_template if folder_template else "default",
        chapter_folder=chapter_folder,
        df=course_row_df
    )
    print(result_df)

    #result_df_formatted = format_course_df(result_df, max_len=10)
    #print("add-chapter result:")
    #print(result_df_formatted.to_markdown(index=False, tablefmt="fancy_grid"))
