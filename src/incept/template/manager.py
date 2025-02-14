import os
import shutil
from pathlib import Path

DEFAULT_TEMPLATE_NAME = "default"
PACKAGE_TEMPLATE_DIR = Path(__file__).parent / ".config/folder_templates"
USER_TEMPLATE_DIR = Path.home() / ".incpet/folder_templates"
DEFAULT_COURSE_PATH = Path.home() / "Library/CloudStorage/SynologyDrive-dataLib/threeD/courses"

def ensure_templates_exist():
    """Ensures user template directory exists and copies default templates if missing."""
    USER_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    for template in PACKAGE_TEMPLATE_DIR.iterdir():
        user_template_path = USER_TEMPLATE_DIR / template.name
        if not user_template_path.exists():
            shutil.copytree(template, user_template_path)

def get_available_templates():
    """Lists available templates (both user-defined and built-in)."""
    ensure_templates_exist()
    user_templates = {d.name for d in USER_TEMPLATE_DIR.iterdir() if d.is_dir()}
    package_templates = {d.name for d in PACKAGE_TEMPLATE_DIR.iterdir() if d.is_dir()}
    return sorted(user_templates | package_templates)  # Return unique templates

def get_template_path(template_name):
    """
    Returns the path of the specified template, preferring user-defined ones.
    If the template doesn't exist in the user's folder, fallback to the package's default.
    """
    ensure_templates_exist()
    user_template_path = USER_TEMPLATE_DIR / template_name
    package_template_path = PACKAGE_TEMPLATE_DIR / template_name

    if user_template_path.exists():
        return user_template_path
    elif package_template_path.exists():
        return package_template_path
    else:
        return None  # No matching template found

def create_course_structure(course_name, template_name=None):
    """Creates a course directory structure based on the selected template."""
    template_name = template_name or DEFAULT_TEMPLATE_NAME
    template_path = get_template_path(template_name)

    if not template_path:
        raise ValueError(f"Template '{template_name}' not found.")

    course_path = DEFAULT_COURSE_PATH / course_name  # Uses module-level variable
    shutil.copytree(template_path, course_path)
    print(f"Course '{course_name}' created using template '{template_name}' at {course_path}")
