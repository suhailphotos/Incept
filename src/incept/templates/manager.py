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

def find_placeholder_folder(base: Path, placeholder: str) -> Path | None:
    """
    Recursively searches for a subfolder in 'base' whose name equals 'placeholder'.
    Returns the first match found or None.
    """
    for root, dirs, _ in os.walk(base):
        for d in dirs:
            if d == placeholder:
                return Path(root) / d
    return None


def create_folder_structure(
    folder_name: str,
    search_folder_name: str = "{course_name}",
    template: str = "default",
    force_init: bool = True,
    base_path: Path | None = None
) -> Path:
    """
    Copies a template from:
      TEMPLATE_DIR/courses/<template>/
    into 'base_path', naming the final folder as 'folder_name'.
    
    The function recursively searches for a subfolder named exactly
    'search_folder_name' (e.g. "{course_name}") within the template.
    If found, it copies its contents into the destination folder, so that the
    final folder is not nested within an extra folder.
    
    Example Template:
      courses/default/{course_name}/assets/...
    Final destination:
      <base_path>/My_new_fun_course/assets/...
    
    :param folder_name: The sanitized folder name for the course.
    :param search_folder_name: The placeholder folder name to search for (default "{course_name}").
    :param template: The template folder name (e.g. "default" or "usd").
    :param force_init: If True, ensures templates are synced.
    :param base_path: The destination directory for the course (should already include the final folder name).
    :return: The destination course folder path.
    """
    if force_init:
        ensure_templates_from_package()

    # Template base folder e.g. ~/.incept/folder_templates/courses/default
    template_base = TEMPLATE_DIR / "courses" / template
    if not template_base.is_dir():
        raise ValueError(f"Template '{template}' not found: {template_base}")

    if base_path is None:
        base_path = get_default_documents_folder() / "courses"

    # destination_course_path is provided by the caller (already includes the sanitized folder name)
    destination_course_path = base_path  
    if destination_course_path.exists():
        raise FileExistsError(f"Folder already exists: {destination_course_path}")

    def ignore_placeholder_folders(folder: str, items: list[str]) -> list[str]:
        ignored = []
        for item in items:
            if PLACEHOLDER_PATTERN.match(item):
                ignored.append(item)
        return ignored

    # Recursively search for a folder named exactly "search_folder_name" in template_base.
    placeholder_folder = find_placeholder_folder(template_base, search_folder_name)
    if placeholder_folder is not None:
        # Copy the contents of the placeholder folder (instead of the folder itself)
        destination_course_path.mkdir(parents=True, exist_ok=True)
        for item in placeholder_folder.iterdir():
            src_item = placeholder_folder / item.name
            dst_item = destination_course_path / item.name
            if src_item.is_dir():
                shutil.copytree(src_item, dst_item, dirs_exist_ok=False, ignore=ignore_placeholder_folders)
            else:
                shutil.copy2(src_item, dst_item)
    else:
        # If no placeholder folder is found, copy the entire template_base into destination
        shutil.copytree(src=template_base, dst=destination_course_path, dirs_exist_ok=False, ignore=ignore_placeholder_folders)

    return destination_course_path

def get_available_templates() -> list[str]:
    """Lists subfolders in ~/.incept/folder_templates/courses."""
    courses_dir = TEMPLATE_DIR / "courses"
    if not courses_dir.exists():
        return []
    return [folder.name for folder in courses_dir.iterdir() if folder.is_dir()]
