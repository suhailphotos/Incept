# src/incept/templates/manager.py
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
    Create a local course folder from ~/.incept/folder_templates/courses/<template>/{course_name},
    ignoring any sub-folders that match placeholder patterns (e.g. {##_chapter_name}, {##_lesson_name}, etc.),
    regardless of how many levels deep they occur.

    :param course_name: Name of the new course folder.
    :param template: Which template to use (default="default").
    :param force_init: If True, ensure templates are synced from package first.
    :param base_path: Where to create the folder. Defaults to (Documents)/courses.
    :return: Path to the newly created course folder.
    """
    if force_init:
        ensure_templates_from_package()

    # Example source folder: ~/.incept/folder_templates/courses/default/{course_name}
    template_path = TEMPLATE_DIR / "courses" / template / "{course_name}"
    if not template_path.exists():
        raise ValueError(f"Template '{template}' not found at: {template_path}")

    if base_path is None:
        base_path = get_default_documents_folder() / "courses"

    course_path = base_path / course_name
    if course_path.exists():
        raise FileExistsError(f"Course folder already exists: {course_path}")

    def ignore_placeholder_folders(folder: str, items: list[str]) -> list[str]:
        """
        Called by shutil.copytree for each directory.
        Return a list of item names to 'ignore' (i.e. skip copying).
        """
        ignored = []
        for item in items:
            # Check if this item is a known placeholder folder.
            # For maximum flexibility, let's do a regex match:
            if PLACEHOLDER_PATTERN.match(item):
                ignored.append(item)
        return ignored

    shutil.copytree(
        src=template_path,
        dst=course_path,
        dirs_exist_ok=False,
        ignore=ignore_placeholder_folders
    )
    return course_path

def get_available_templates() -> list[str]:
    """Lists subfolders in ~/.incept/folder_templates/courses."""
    courses_dir = TEMPLATE_DIR / "courses"
    if not courses_dir.exists():
        return []
    return [folder.name for folder in courses_dir.iterdir() if folder.is_dir()]
