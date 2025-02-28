# src/incept/cli.py
import os
import click
import shutil
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from incept.templates.manager import ensure_templates_from_package, TEMPLATE_DIR
from incept.courses import getCourses

CONFIG_DIR = Path.home() / ".incept"
CONFIG_SUBDIR = CONFIG_DIR / "config"
ENV_FILE = CONFIG_DIR / ".env"

def format_course_df(df, max_len=50):
    """
    Return a copy of 'df' where all columns except 'id' and 'name'
    are truncated to 'max_len' characters for readability.
    """
    df2 = df.copy()

    def truncate_cell(value):
        if value is None:
            return ""
        s = str(value)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s

    for col in df2.columns:
        # Show full for 'id' and 'name'
        if col not in ("id", "name"):
            df2[col] = df2[col].apply(truncate_cell)

    return df2

@click.group()
def main():
    """
    Incept CLI: A command-line interface for managing courses, templates, etc.
    """
    pass

@main.command("init-templates")
def cli_init_templates():
    """
    Ensure user-level templates are up to date with the built-in templates.
    Also create a placeholder .env file and config JSON files if not present.
    """
    click.echo("Initializing Incept templates...")
    ensure_templates_from_package()  # existing code for folder_templates
    click.echo(f"Templates ready in: {TEMPLATE_DIR}")

    # 2) Now copy env.example -> ~/.incept/.env if missing
    builtin_config_dir = Path(__file__).parent / ".config" / "config_templates"
    env_example = builtin_config_dir / "env.example"
    if not ENV_FILE.exists():
        if env_example.exists():
            shutil.copy2(env_example, ENV_FILE)
            click.echo(f"Created .env at {ENV_FILE}")
        else:
            click.echo("No env.example found; skipping.")
    else:
        click.echo(".env file already exists; not overwriting.")

    # 3) Copy JSON config files
    CONFIG_SUBDIR.mkdir(parents=True, exist_ok=True)
    for json_file in ["course.json", "chapter.json", "lesson.json", "full_course.json"]:
        src_file = builtin_config_dir / json_file
        dst_file = CONFIG_SUBDIR / json_file
        if not dst_file.exists():
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
                click.echo(f"Created config file: {dst_file}")
            else:
                click.echo(f"Missing {src_file}, skipping.")
        else:
            click.echo(f"{dst_file.name} already exists; not overwriting.")

    click.echo("init-templates complete.")

@main.command("get-courses")
@click.option("--api-key", default=None, help="Notion API Key. If not provided, uses .env or environment variable.")
@click.option("--database-id", default=None, help="Notion Database ID. If not provided, uses .env or environment variable.")
@click.option("--filter", default=None, help="Optional filter: name of course to fetch.")
def cli_get_courses(api_key, database_id, filter):
    """
    Fetch courses from the specified Notion database.
    If --api-key or --database-id are not passed, we try .env or system env vars.
    """
    # 1) Load ~/.incept/.env if it exists
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    # 2) DB type: environment or default to 'notion'
    db_type = os.getenv("DATABASE_NAME", "notion")

    # 3) If user didn't pass --api-key, see if environment has API_KEY
    if not api_key:
        api_key = os.getenv("API_KEY")  # from .env or system
    # 4) If user didn't pass --database-id, see if environment has DATABASE_ID
    if not database_id:
        database_id = os.getenv("DATABASE_ID")

    # 5) If still missing, raise error
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found. Provide via CLI options or .env file.")

    # 6) Call getCourses
    df = getCourses(
        db=db_type,
        api_key=api_key,
        database_id=database_id,
        filter=filter
    )
    if df.empty:
        click.echo("No courses found.")
        return

    # 7) Format/truncate columns except for 'id' and 'name'
    df_formatted = format_course_df(df, max_len=10)

    # 8) Print with lines between columns & row data
    click.echo("Courses found:")

    # Option 1: Use to_markdown with fancy_grid for horizontal rules
    # This requires: `pip install tabulate` or `poetry add tabulate`
    table_str = df_formatted.to_markdown(index=False, tablefmt="fancy_grid")
    click.echo(table_str)

@main.command("add-course")
@click.option("--api-key", default=None, help="Notion API Key (or from .env).")
@click.option("--database-id", default=None, help="Notion Database ID (or from .env).")
@click.option("--data-file-path", default=None, help="Path to JSON file with course data.")
@click.option("--name", default=None, help="Course name (override JSON).")
@click.option("--description", default=None, help="Course description.")
@click.option("--link", default=None, help="Course link/URL.")
@click.option("--path", default=None, help="Custom path for Notion property (e.g. '$DATALIB/threeD/courses').")
@click.option("--folder-template", default=None, help="Template folder name for local structure (e.g. 'default').")
def cli_add_course(api_key, database_id, data_file_path, name, description, link, path, folder_template):
    """
    Add new course(s) to your database, creating local folder(s) as well.
    
    If a JSON file is provided, it should contain either:
      - A single course (under the key "course"), in which case any CLI overrides
        (like --name, --description, etc.) will be merged into that record.
      - Or multiple courses (under the key "courses"). In that case, CLI override options
        are not allowed.
    """
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    db_type = os.getenv("DATABASE_NAME", "notion")
    if not api_key:
        api_key = os.getenv("API_KEY")
    if not database_id:
        database_id = os.getenv("DATABASE_ID")
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found. Provide via CLI or .env file.")

    # Load JSON file if provided.
    df = None
    if data_file_path:
        import json
        file_path = Path(data_file_path)
        if not file_path.exists():
            raise click.ClickException(f"Data file not found: {file_path}")
        with file_path.open("r") as f:
            try:
                file_json = json.load(f)
            except json.JSONDecodeError as e:
                raise click.ClickException(f"Invalid JSON in {file_path}: {e}")
        # If JSON contains multiple courses (key "courses")
        if "courses" in file_json:
            courses_list = file_json["courses"]
            if not isinstance(courses_list, list):
                raise click.ClickException("The 'courses' key must contain a list of course objects.")
            if len(courses_list) > 1 and any([name, description, link, path, folder_template]):
                raise click.ClickException(
                    "Multiple courses detected in JSON; please do not mix CLI override options with multi-course JSON input."
                )
            df = pd.DataFrame(courses_list)
        elif "course" in file_json:
            # Single course provided; merge CLI overrides.
            file_data = file_json["course"]
            if name:
                file_data["name"] = name
            if description:
                file_data["description"] = description
            if link:
                file_data["link"] = link
            if path:
                file_data["path"] = path
            if folder_template:
                file_data["folder_template_name"] = folder_template
            if "name" not in file_data:
                raise click.ClickException("No course name found (use --name or JSON).")
            df = pd.DataFrame([file_data])
        else:
            raise click.ClickException("Invalid JSON file: must contain either 'course' or 'courses' key.")
    else:
        # No JSON file provided; require CLI options.
        if not name:
            raise click.ClickException("No data file provided. Please supply CLI options for a single course.")
        course_dict = {
            "name": name,
            "description": description,
            "link": link,
            "path": path,
            "folder_template_name": folder_template,
        }
        df = pd.DataFrame([course_dict])
    
    from incept.courses import addCourse
    result_df = addCourse(
        db=db_type,
        template=df.iloc[0].get("folder_template_name", "default"),
        df=df,
        api_key=api_key,
        database_id=database_id
    )
    result_df_formated = format_course_df(result_df, max_len=10)
    click.echo("add-course result:")
    click.echo(result_df_formated.to_markdown(index=False, tablefmt="fancy_grid"))


if __name__ == "__main__":
    main()
