# src/incept/templates/manager.py
import os
import re
import shutil
from pathlib import Path
from platformdirs import user_documents_dir
from incept.utils.file_utils import sync_templates

CONFIG_DIR = Path.home() / ".incept"
TEMPLATE_DIR = CONFIG_DIR / "folder_templates"

# For example, define placeholder folder names or a pattern:
PLACEHOLDER_PATTERN = re.compile(r'^\{\#\#_.+\}$')

def get_default_documents_folder() -> Path:
    """
    Returns the cross-platform 'Documents' directory using platformdirs.
    On Windows, this typically points to:  C:\\Users\\<YourName>\\Documents
    On macOS:    /Users/<YourName>/Documents
    On Linux:    /home/<YourName>/Documents (or similar, if configured).
    """
    return Path(user_documents_dir())

def builtin_templates_dir() -> Path:
    """Points to the built-in `.config/folder_templates` in the installed package."""
    return (Path(__file__).parent.parent / ".config" / "folder_templates").resolve()

def ensure_templates_from_package():
    """
    Merges built-in templates (from the installed package) into
    ~/.incept/folder_templates, overwriting only the 'default'
    folders and leaving custom user folders alone.
    """
    # ... same as before ...
    pass  # shortened for brevity

def get_default_documents_folder() -> Path:
    """
    Returns the user's cross-platform 'Documents' directory 
    (Windows: C:\\Users\\<user>\\Documents, macOS/Linux: ~/Documents, etc.)
    """
    from platformdirs import user_documents_dir
    return Path(user_documents_dir())

def create_course_structure(
    course_name: str,
    template: str = "default",
    force_init: bool = True,
    base_path: Path | None = None
) -> Path:
    """
    Copies a template from:
      ~/.incept/folder_templates/courses/<template>/
    into `base_path/<course_name>`, ignoring {##_chapter_name} etc.

    If the template includes a subfolder literally named "{course_name}",
    we copy THAT subfolder's contents into the final course directory to avoid
    double nesting.

    Example Template:
      courses/default/{course_name}/assets/...
    Final:
      <base_path>/My_Course/assets/...

    :param course_name: (Already sanitized) name for local folder.
    :param template: The template directory name (default="default").
    :param force_init: If True, calls ensure_templates_from_package first.
    :param base_path: Destination directory. If None, defaults to Documents/courses.
    :return: The final course path that was created.
    """
    if force_init:
        ensure_templates_from_package()

    # The base path to the entire template, e.g. ~/.incept/folder_templates/courses/default
    template_base = TEMPLATE_DIR / "courses" / template
    if not template_base.exists():
        raise ValueError(f"Template '{template}' not found: {template_base}")

    if base_path is None:
        base_path = get_default_documents_folder() / "courses"

    # Our final local course path
    destination_course_path = base_path / course_name

    if destination_course_path.exists():
        raise FileExistsError(f"Course folder already exists: {destination_course_path}")

    def ignore_placeholder_folders(folder: str, items: list[str]) -> list[str]:
        ignored = []
        for item in items:
            if PLACEHOLDER_PATTERN.match(item):
                ignored.append(item)
        return ignored

    # 1) Does the template contain a subfolder named "{course_name}"?
    #    e.g. ~/.incept/folder_templates/courses/default/{course_name}/(assets, etc.)
    subfolder_course_name = template_base / "{course_name}"
    if subfolder_course_name.is_dir():
        # We want to copy the *contents* of {course_name} -> <destination>
        # This prevents a double-nesting.
        shutil.copytree(
            src=subfolder_course_name,
            dst=destination_course_path,
            dirs_exist_ok=False,
            ignore=ignore_placeholder_folders
        )

    else:
        # If no {course_name} subfolder, copy the entire template_base into <destination>
        shutil.copytree(
            src=template_base,
            dst=destination_course_path,
            dirs_exist_ok=False,
            ignore=ignore_placeholder_folders
        )

    return destination_course_path

def get_available_templates() -> list[str]:
    """Lists subfolders in ~/.incept/folder_templates/courses."""
    courses_dir = TEMPLATE_DIR / "courses"
    if not courses_dir.exists():
        return []
    return [folder.name for folder in courses_dir.iterdir() if folder.is_dir()]
