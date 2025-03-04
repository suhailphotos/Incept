# src/incept/cli.py

import os
import json
import click
import shutil
from dotenv import load_dotenv
from pathlib import Path
from incept.courses import getCourses

# Set up user configuration directory
CONFIG_DIR = Path.home() / ".incept"
ENV_FILE = CONFIG_DIR / ".env"

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
    for subdir in ["payload", "templates"]:
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


if __name__ == "__main__":
    main()
