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
    if filter:
        return db_client.get_courses(Name=filter)
    else:
        return db_client.get_courses()


def addCourse(db=DEFAULT_DB, template="default", df=None, **kwargs):
    """
    Add course(s) from a Pandas DataFrame. 
    - If the DataFrame has exactly 1 row, returns a single insert result or a skip message.
    - If multiple rows are present, processes each row in a loop, returns a list of (course_name, status).
    - If the DataFrame is empty, returns a simple message.

    Steps for each row:
      1) Check if 'name' is present.
      2) Check if the name already exists in the DB.
      3) If not, create local folder structure + insert into DB.
      4) Gather results in a list if multi-row, or return single result if one row.
    """
    db_client = get_db_client(db, **kwargs)

    if df is None or df.empty:
        return "DataFrame is empty. No course(s) to add."

    if "name" not in df.columns:
        raise ValueError("DataFrame must contain a 'name' column.")

    # Fetch existing courses once
    existing_df = db_client.get_courses()
    existing_names = set(existing_df["name"].values) if not existing_df.empty else set()

    # If multiple rows, we will store results for each course
    results = []

    for idx, row_data in df.iterrows():
        course_data = row_data.to_dict()
        course_name = course_data["name"]

        if course_name in existing_names:
            # Already exists, skip
            results.append((course_name, f"Course '{course_name}' already exists. Skipped."))
            continue

        # Create local folder structure
        create_course_structure(course_name, template)

        # Insert into DB
        res = db_client.insert_course(**course_data)
        # Mark the name as existing now
        existing_names.add(course_name)

        results.append((course_name, res))

    # If there's exactly 1 row, return the single result directly
    if len(df) == 1:
        return results[0][1]  # i.e. the "status" part

    # Otherwise return the list of tuples
    return results


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
