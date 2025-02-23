# src/incept/cli.py
import click
import pandas as pd
from incept.templates.manager import ensure_templates_from_package, TEMPLATE_DIR
from incept.courses import getCourses


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
    """
    click.echo("Initializing Incept templates...")
    ensure_templates_from_package()
    click.echo(f"Templates ready in: {TEMPLATE_DIR}")


@main.command("get-courses")
@click.option("--api-key", required=True, help="Notion API Key.")
@click.option("--database-id", required=True, help="Notion Database ID.")
@click.option("--filter", default=None, help="Optional filter: name of course to fetch.")
def cli_get_courses(api_key, database_id, filter):
    """
    Fetch courses from the specified Notion database.
    If --filter is provided, only retrieve that course (plus its chapters/lessons).
    """
    df = getCourses(
        db="notion",
        api_key=api_key,
        database_id=database_id,
        filter=filter
    )
    if df.empty:
        click.echo("No courses found.")
        return

    # Print a simple summary
    click.echo("Courses found:")
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        click.echo(df)


# Potential future subcommands for add-course, update-course, etc.
# e.g.:
#
# @main.command("add-course")
# @click.option("--api-key", required=True, ...)
# def cli_add_course(api_key, ...):
#     pass


if __name__ == "__main__":
    main()
