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

    # 2) If user didn't pass --api-key, see if environment has API_KEY
    if not api_key:
        api_key = os.getenv("API_KEY")  # from .env or system
    # 3) If user didn't pass --database-id, see if environment has DATABASE_ID
    if not database_id:
        database_id = os.getenv("DATABASE_ID")

    # 4) If still missing, raise error
    if not api_key or not database_id:
        raise click.ClickException("API_KEY or DATABASE_ID not found. Provide via CLI options or .env file.")

    # 5) Call getCourses
    df = getCourses(
        db="notion",
        api_key=api_key,
        database_id=database_id,
        filter=filter
    )
    if df.empty:
        click.echo("No courses found.")
        return

    # 6) Format/truncate columns except for 'id' and 'name'
    df_formatted = format_course_df(df, max_len=20)

    # 7) Print with lines between columns & row data
    click.echo("Courses found:")

    # Option 1: Use to_markdown with fancy_grid for horizontal rules
    # This requires: `pip install tabulate` or `poetry add tabulate`
    table_str = df_formatted.to_markdown(index=False, tablefmt="fancy_grid")
    click.echo(table_str)

if __name__ == "__main__":
    main()
