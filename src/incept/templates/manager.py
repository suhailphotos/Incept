# src/incept/templates/manager.py

import shutil
from pathlib import Path
from incept.utils.file_utils import sync_templates

# Constants for where user-level templates should be stored
CONFIG_DIR = Path.home() / ".incept"
TEMPLATE_DIR = CONFIG_DIR / "folder_templates"

def builtin_templates_dir() -> Path:
    """
    Returns the path to the built-in `.config/folder_templates`
    directory that ships with this package.
    """
    # Example structure: <...>/incept/.config/folder_templates
    return (Path(__file__).parent.parent / ".config" / "folder_templates").resolve()


def ensure_templates_from_package():
    """
    Merge built-in templates (from the installed package) into
    ~/.incept/folder_templates, overwriting only the 'default'
    folders and leaving custom user folders alone.
    """
    src_dir = builtin_templates_dir()
    if not src_dir.exists():
        raise FileNotFoundError(f"Built-in template directory not found: {src_dir}")

    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    # Copy each subfolder in the built-in templates into ~/.incept/folder_templates
    for subfolder in src_dir.iterdir():
        if subfolder.is_dir():
            user_subdir = TEMPLATE_DIR / subfolder.name
            sync_templates(subfolder, user_subdir)
        else:
            # If there's a file in the root of .config/folder_templates,
            # copy it over if it doesn't already exist
            user_file = TEMPLATE_DIR / subfolder.name
            if not user_file.exists():
                shutil.copy2(subfolder, user_file)


def create_course_structure(course_name: str, template: str = "default", force_init: bool = True) -> Path:
    """
    Create a local course folder using the specified template from ~/.incept/folder_templates/courses.
    
    :param course_name: The name of the new course (also the folder name).
    :param template: The template folder to copy from (default is "default").
    :param force_init: If True, automatically updates the user's template folder first
                       by calling `ensure_templates_from_package()`.
    :return: The path to the newly created course folder (e.g. ~/Documents/courses/<course_name>).
    """
    if force_init:
        ensure_templates_from_package()

    # e.g.: ~/.incept/folder_templates/courses/default/{course_name}
    template_path = TEMPLATE_DIR / "courses" / template / "{course_name}"
    if not template_path.exists():
        raise ValueError(f"Template '{template}' not found at: {template_path}")

    course_path = Path.home() / "Documents" / "courses" / course_name
    if course_path.exists():
        raise FileExistsError(f"Course folder already exists: {course_path}")

    # Use a direct copytree (or copy_template, if you prefer) for the final structure
    shutil.copytree(template_path, course_path)
    return course_path


def get_available_templates() -> list:
    """
    Returns a list of available course templates found under
    ~/.incept/folder_templates/courses.
    """
    courses_dir = TEMPLATE_DIR / "courses"
    if not courses_dir.exists():
        return []

    return [
        folder.name
        for folder in courses_dir.iterdir()
        if folder.is_dir()
    ]



