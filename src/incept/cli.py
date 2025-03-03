# src/incept/cli.py

import os
import click
import shutil
from pathlib import Path

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

if __name__ == "__main__":
    main()
