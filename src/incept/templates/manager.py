# src/incept/templates/manager.py
import os
import re
import shutil
from pathlib import Path
from incept.utils.file_utils import sync_templates, get_default_documents_folder

CONFIG_DIR = Path.home() / ".incept"
TEMPLATE_DIR = CONFIG_DIR / "folder_templates"

# For example, define placeholder folder names or a pattern:
PLACEHOLDER_PATTERN = re.compile(r'^\{\#\#_.+\}$')

def builtin_templates_dir() -> Path:
    """Points to the built-in `.config/folder_templates` in the installed package."""
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


def create_course_structure(
    course_name: str,
    template: str = "default",
    force_init: bool = True,
    base_path: Path | None = None
) -> Path:
    """
    Copies a template from:
      ~/.incept/folder_templates/courses/<template>/
    into `base_path/`, naming the folder `course_name`.

    If there's a subfolder literally named '{course_name}', copy its contents
    into base_path/course_name to avoid double nesting.

    Example:
      courses/default/{course_name}/assets -> base_path/My_Course/assets
    """
    if force_init:
        ensure_templates_from_package()

    template_base = TEMPLATE_DIR / "courses" / template
    if not template_base.is_dir():
        raise ValueError(f"Template '{template}' not found: {template_base}")

    if base_path is None:
        base_path = get_default_documents_folder() / "courses"

    destination_course_path = base_path  # This is already something like ".../My_Course"
    if destination_course_path.exists():
        raise FileExistsError(f"Course folder already exists: {destination_course_path}")

    def ignore_placeholder_folders(folder: str, items: list[str]) -> list[str]:
        """
        Called by shutil.copytree for each directory.
        Returns a list of item names to ignore e.g. {##_chapter_name}, {##_lesson_name}
        """
        ignored = []
        for item in items:
            if PLACEHOLDER_PATTERN.match(item):
                ignored.append(item)
        return ignored

    # 1) Check for subfolder named "{course_name}"
    subfolder_course_name = template_base / "{course_name}"
    if subfolder_course_name.is_dir():
        # We want to copy the **contents** of that subfolder to <destination_course_path>.
        destination_course_path.mkdir(parents=True, exist_ok=True)
        for item in subfolder_course_name.iterdir():
            src_item = subfolder_course_name / item.name
            dst_item = destination_course_path / item.name
            if src_item.is_dir():
                shutil.copytree(
                    src_item,
                    dst_item,
                    dirs_exist_ok=False,
                    ignore=ignore_placeholder_folders
                )
            else:
                shutil.copy2(src_item, dst_item)

    else:
        # 2) No subfolder {course_name}, so we copy the entire template_base
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
