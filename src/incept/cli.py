# src/incept/cli.py

import os
import json
import click
import shutil
from dotenv import load_dotenv
from pathlib import Path
from incept.courses import getCourses, addCourses, addChapters, addLessons

# Set up user configuration directory
CONFIG_DIR = Path.home() / ".incept"
ENV_FILE = CONFIG_DIR / ".env"
MAPPINGS_DIR = CONFIG_DIR / "mapping"

@click.group()
def main():
    """
    Incept CLI: A command-line interface for managing courses, templates, etc.
    """
    pass

@main.command("init")
def cli_init():
    """
    Initialize Incept configuration by copying default configuration files,
    templates, and payload samples into the user's configuration directory.
    
    This copies the following from the source .config directory:
      - .env file from env.example
      - payload (sample JSON payloads)
      - templates (Jinja2 templates)
    """
    click.echo("Initializing Incept configuration...")

    # Determine the source configuration directory relative to this file.
    config_source = Path(__file__).parent / ".config"

    # Ensure the user config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Copy .env file from env.example if not present.
    env_source = config_source / "env.example"
    if not ENV_FILE.exists():
        if env_source.exists():
            shutil.copy2(env_source, ENV_FILE)
            click.echo(f"Created .env at {ENV_FILE}")
        else:
            click.echo("No env.example found; skipping .env creation.")
    else:
        click.echo(".env file already exists; not overwriting.")

    # 2) Copy the 'payload' and 'templates' directories from the source.
    for subdir in ["payload", "templates", "mapping"]:
        src_subdir = config_source / subdir
        dst_subdir = CONFIG_DIR / subdir
        if src_subdir.exists():
            if dst_subdir.exists():
                click.echo(f"{subdir} already exists at {dst_subdir}; not overwriting.")
            else:
                shutil.copytree(src_subdir, dst_subdir)
                click.echo(f"Copied {subdir} to {dst_subdir}")
        else:
            click.echo(f"Source subdirectory {src_subdir} not found; skipping {subdir}.")

    click.echo("Initialization complete.")

@main.command("get-courses")
@click.option("--api-key", default=None, help="Notion API Key. If not provided, uses .env or environment variable.")
@click.option("--database-id", default=None, help="Notion Database ID. If not provided, uses .env or environment variable.")
@click.option("--filter", default=None, help="Optional filter: name of course to fetch.")
def cli_get_courses(api_key, database_id, filter):
    """
    Fetch courses from the specified Notion database.
    If --api-key or --database-id are not passed, we try .env or system env vars.
    """
    # 1) Load .env if it exists.
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    # 2) Determine DB type (defaulting to "notion")
    db_type = os.getenv("DATABASE_NAME", "notion")

    # 3) If API key not passed via CLI, try environment variable.
    if not api_key:
        api_key = os.getenv("NOTION_API_KEY")
    # 4) Similarly, get database ID.
    if not database_id:
        database_id = os.getenv("NOTION_DATABASE_ID")
    # 5) If missing credentials, raise an error.
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found. Provide via CLI options or .env file.")

    # 6) Call getCourses to get the nested courses hierarchy.
    courses = getCourses(
        db=db_type,
        api_key=api_key,
        database_id=database_id,
        filter=filter
    )
    if not courses or not courses.get("courses"):
        click.echo("No courses found.")
        return

    # 7) Print the nested courses hierarchy as JSON.
    click.echo("Courses found:")
    click.echo(json.dumps(courses, indent=2))

@main.command("add-course")
@click.option("--api-key", default=None, help="Notion API Key (or from .env).")
@click.option("--database-id", default=None, help="Notion Database ID (or from .env).")
@click.option("--data-file-path", default=None, help="Path to JSON file with course data.")
@click.option("--name", default=None, help="Course name (override JSON).")
@click.option("--description", default=None, help="Course description (override JSON).")
@click.option("--link", default=None, help="Course link/URL (override JSON).")
@click.option("--path", default=None, help="Local path for folder creation (override JSON). e.g., '$DATALIB/threeD/courses'")
@click.option("--folder-template", default=None, help="Template folder name for local structure (override JSON). e.g. 'default'")
def cli_add_course(api_key, database_id, data_file_path, name, description, link, path, folder_template):
    """
    Insert one or more new courses (including chapters/lessons) into Notion.
    Either provide --data-file-path or specify the details manually 
    (in which case exactly one course is inserted).
    
    If both a file and CLI options are provided, CLI options override the JSON for 
    corresponding fields (name, description, link, path, template).
    """
    # 1) Load environment variables (if .env is present).
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    db_type = os.getenv("DATABASE_NAME", "notion")

    # If API key or DB ID not provided, try environment variables
    if not api_key:
        api_key = os.getenv("NOTION_API_KEY")
    if not database_id:
        database_id = os.getenv("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found. Provide via CLI or .env file.")

    # 2) If data_file_path is not provided AND no name is provided, we cannot proceed
    #    because we either need a JSON or at least a course name to create one course.
    if not data_file_path and not name:
        raise click.ClickException("Either --data-file-path or --name must be provided.")

    # We'll build a final payload_data in the standard format: {"courses": [...]}
    payload_data = {"courses": []}

    if data_file_path:
        # If data_file_path is provided, load from JSON
        if not os.path.isfile(data_file_path):
            raise click.ClickException(f"File not found: {data_file_path}")
        with open(data_file_path, "r", encoding="utf-8") as f:
            file_payload = json.load(f)

        # Ensure file_payload has "courses" as a list
        if isinstance(file_payload.get("courses"), dict):
            file_payload["courses"] = [file_payload["courses"]]
        else:
            file_payload.setdefault("courses", [])

        # Start from the file payload
        payload_data = file_payload

    # If the user provided CLI options (name, description, link, path, folder_template),
    # then either we add a single course or we override the first one from the file.
    
    # Check if the user gave manual info (like name).
    if name:
        # We'll assume we want exactly 1 course in the final payload. 
        # So if the file had multiple courses, we only override the first or create a new one.
        if not payload_data["courses"]:
            # We'll create a new single-course payload
            payload_data["courses"] = [{
                "id": None,
                "name": name,
                "description": description or None,
                "link": link or None,
                "path": path or None,
                "template": folder_template or None,
                "chapters": []  # user might not have chapters if specifying via CLI
            }]
        else:
            # We override the first course's fields with CLI-provided values.
            first_course = payload_data["courses"][0]
            first_course["name"] = name
            if description is not None:
                first_course["description"] = description
            if link is not None:
                first_course["link"] = link
            if path is not None:
                first_course["path"] = path
            if folder_template is not None:
                first_course["template"] = folder_template

    # 3) Ensure "courses" is a list. (If the user gave no file, we just built it above.)
    if isinstance(payload_data.get("courses"), dict):
        payload_data["courses"] = [payload_data["courses"]]

    # 4) Call addCourses with the final payload
    inserted_courses = addCourses(
        payload_data=payload_data,
        templates_dir=Path.home() / ".incept" / "templates",
        db=db_type,
        api_key=api_key,
        database_id=database_id
    )

    click.echo("Inserted Courses:")
    click.echo(json.dumps(inserted_courses, indent=2))

#
# NEW COMMAND: add-chapter
#
@main.command("add-chapter")
@click.option("--api-key", default=None, help="Notion API Key (or from .env).")
@click.option("--database-id", default=None, help="Notion Database ID (or from .env).")
@click.option("--data-file-path", default=None, help="Path to JSON file with chapter data.")
@click.option("--course-name", default=None, help="Name of the existing course (only required if no data file is provided).")
@click.option("--chapter-name", default=None, help="Chapter name (override JSON; only required if no data file is provided).")
@click.option("--description", default=None, help="Chapter description (override JSON).")
@click.option("--link", default=None, help="Chapter link/URL (override JSON).")
@click.option("--path", default=None, help="Local path for folder creation (override JSON), e.g., '$DATALIB/threeD/courses'")
@click.option("--folder-template", default=None, help="Template folder name for local structure (override JSON), e.g., 'default'")
def cli_add_chapter(api_key, database_id, data_file_path, course_name, chapter_name, description, link, path, folder_template):
    """
    Insert one or more new chapters (and optionally lessons) into an existing course in Notion.
    Either provide --data-file-path or specify details manually (in which case exactly one chapter is inserted).
    CLI options override corresponding JSON fields.
    """
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    db_type = os.getenv("DATABASE_NAME", "notion")
    if not api_key:
        api_key = os.getenv("NOTION_API_KEY")
    if not database_id:
        database_id = os.getenv("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found.")
    
    # If no data file is provided, require course-name and chapter-name from CLI.
    if not data_file_path and (not course_name or not chapter_name):
        raise click.ClickException("--course-name and --chapter-name are required when no data file is provided.")
    
    payload_data = {"courses": []}
    if data_file_path:
        if not os.path.isfile(data_file_path):
            raise click.ClickException(f"File not found: {data_file_path}")
        with open(data_file_path, "r", encoding="utf-8") as f:
            file_payload = json.load(f)
        if isinstance(file_payload.get("courses"), dict):
            file_payload["courses"] = [file_payload["courses"]]
        else:
            file_payload.setdefault("courses", [])
        payload_data = file_payload

    # When CLI options are provided, override values in the payload.
    if course_name:
        if not payload_data["courses"]:
            payload_data["courses"] = [{
                "id": None,
                "name": course_name,
                "chapters": [{
                    "id": None,
                    "name": chapter_name,
                    "description": description or None,
                    "link": link or None,
                    "path": path or None,
                    "template": folder_template or None,
                    "lessons": []
                }]
            }]
        else:
            first_course = payload_data["courses"][0]
            first_course["name"] = course_name
            if "chapters" not in first_course or not first_course["chapters"]:
                first_course["chapters"] = []
            new_chapter = {
                "id": None,
                "name": chapter_name,
                "description": description or None,
                "link": link or None,
                "path": path or None,
                "template": folder_template or None,
                "lessons": []
            }
            first_course["chapters"].append(new_chapter)
    # Else if no CLI override is provided, payload_data will come solely from the file.

    if isinstance(payload_data.get("courses"), dict):
        payload_data["courses"] = [payload_data["courses"]]

    if not course_name:
        try:
            course_name = payload_data["courses"][0]["name"]
        except (KeyError, IndexError):
            raise click.ClickException("Course name not found in the payload.")

    inserted_chapters = addChapters(
        payload_data=payload_data,
        course_filter=course_name,
        templates_dir=Path.home() / ".incept" / "templates",
        db=db_type,
        api_key=api_key,
        database_id=database_id
    )
    click.echo("Inserted Chapters:")
    click.echo(json.dumps(inserted_chapters, indent=2))

#
# NEW COMMAND: add-lesson
#
@main.command("add-lesson")
@click.option("--api-key", default=None, help="Notion API Key (or from .env).")
@click.option("--database-id", default=None, help="Notion Database ID (or from .env).")
@click.option("--data-file-path", default=None, help="Path to JSON file with lesson data.")
@click.option("--course-name", default=None, help="Name of the existing course (only required if no data file is provided).")
@click.option("--chapter-name", default=None, help="Name of the target chapter (only required if no data file is provided).")
@click.option("--lesson-name", default=None, help="Lesson name (override JSON; only required if no data file is provided).")
@click.option("--description", default=None, help="Lesson description (override JSON).")
@click.option("--link", default=None, help="Lesson link/URL (override JSON).")
@click.option("--path", default=None, help="Local path for folder creation (override JSON), e.g., '$DATALIB/threeD/courses'.")
@click.option("--folder-template", default=None, help="Template folder name for local structure (override JSON), e.g., 'default'.")
def cli_add_lesson(api_key, database_id, data_file_path, course_name, chapter_name, lesson_name, description, link, path, folder_template):
    """
    Insert one or more lessons into an existing chapter of a course in Notion.
    The JSON file (if provided) should follow the standard internal format:
      {
        "courses": [
          {
            "name": "Some Course",
            "chapters": [
              {
                "name": "Some Chapter",
                "lessons": [
                  { "name": "Lesson 1", ... },
                  ...
                ]
              }
            ]
          }
        ]
      }
    If no data file is provided, manual CLI options are used to build a minimal payload.
    --course-name, --chapter-name, and --lesson-name are required when no data file is provided.
    CLI options override corresponding JSON fields.
    """
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    db_type = os.getenv("DATABASE_NAME", "notion")
    if not api_key:
        api_key = os.getenv("NOTION_API_KEY")
    if not database_id:
        database_id = os.getenv("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found.")

    # Only require CLI options if no data file is provided.
    if not data_file_path and (not course_name or not chapter_name or not lesson_name):
        raise click.ClickException("--course-name, --chapter-name, and --lesson-name are required when no data file is provided.")

    payload_data = {"courses": []}
    if data_file_path:
        if not os.path.isfile(data_file_path):
            raise click.ClickException(f"File not found: {data_file_path}")
        with open(data_file_path, "r", encoding="utf-8") as f:
            file_payload = json.load(f)
        if isinstance(file_payload.get("courses"), dict):
            file_payload["courses"] = [file_payload["courses"]]
        else:
            file_payload.setdefault("courses", [])
        payload_data = file_payload

    # When CLI options are provided, override or build payload.
    if course_name:
        if not payload_data["courses"]:
            payload_data["courses"] = [{
                "id": None,
                "name": course_name,
                "chapters": [{
                    "id": None,
                    "name": chapter_name,
                    "lessons": [{
                        "id": None,
                        "name": lesson_name,
                        "description": description or None,
                        "link": link or None,
                        "path": path or None,
                        "template": folder_template or None,
                        # Add chapter_name to the lesson payload.
                        "chapter_name": chapter_name
                    }]
                }]
            }]
        else:
            first_course = payload_data["courses"][0]
            first_course["name"] = course_name
            if "chapters" not in first_course or not first_course["chapters"]:
                first_course["chapters"] = []
            # Find or create the target chapter.
            target_chapter = None
            for ch in first_course["chapters"]:
                if ch.get("name") == chapter_name:
                    target_chapter = ch
                    break
            if not target_chapter:
                target_chapter = {
                    "id": None,
                    "name": chapter_name,
                    "lessons": []
                }
                first_course["chapters"].append(target_chapter)
            # Now add the lesson.
            lessons = target_chapter.get("lessons", [])
            if isinstance(lessons, dict):
                lessons = [lessons]
            new_lesson = {
                "id": None,
                "name": lesson_name,
                "description": description or None,
                "link": link or None,
                "path": path or None,
                "template": folder_template or None,
                # Set the chapter_name from the CLI option.
                "chapter_name": chapter_name
            }
            lessons.append(new_lesson)
            target_chapter["lessons"] = lessons

    if isinstance(payload_data.get("courses"), dict):
        payload_data["courses"] = [payload_data["courses"]]

    # If course_name was not provided via CLI, extract it from the payload.
    if not course_name:
        try:
            course_name = payload_data["courses"][0]["name"]
        except (KeyError, IndexError):
            raise click.ClickException("Course name not found in the payload.")

    # Ensure each lesson in every chapter has a 'chapter_name' field.
    for course in payload_data["courses"]:
        for ch in course.get("chapters", []):
            if "chapter_name" not in ch:
                ch["chapter_name"] = ch.get("name")
            lessons = ch.get("lessons", [])
            if isinstance(lessons, dict):
                lessons = [lessons]
            for lesson in lessons:
                if "chapter_name" not in lesson:
                    lesson["chapter_name"] = ch.get("name")

    # Now call addLessons (which expects a lesson payload) and returns the inserted lesson(s).
    try:
        course = payload_data["courses"][0]
        chapter = course["chapters"][0]
        lessons = chapter.get("lessons", [])
        if isinstance(lessons, dict):
            lessons = [lessons]
    except (KeyError, IndexError):
        raise click.ClickException("Invalid payload structure for lessons.")

    inserted_lessons = []
    for lesson_payload in lessons:
        inserted = addLessons(
            lesson_payload,
            course_filter=course_name,
            templates_dir=Path.home() / ".incept" / "templates",
            db=db_type,
            api_key=api_key,
            database_id=database_id
        )
        inserted_lessons.append(inserted)

    click.echo("Inserted Lessons:")
    click.echo(json.dumps(inserted_lessons, indent=2))

if __name__ == "__main__":
    main()
