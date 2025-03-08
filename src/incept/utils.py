# src/incept/utils.py

import os
import re
import json
import shutil
import jinja2
from pathlib import Path
from platformdirs import user_documents_dir
from typing import Optional, Any, Dict, List, Tuple


# Import TemplateManager
from incept.templates import TemplateManager


def get_default_documents_folder() -> Path:
    """
    Returns the cross-platform 'Documents' directory using platformdirs.
    On Windows, this typically points to:  C:\\Users\\<YourName>\\Documents
    On macOS:    /Users/<YourName>/Documents
    On Linux:    /home/<YourName>/Documents (or similar, if configured).
    """
    return Path(user_documents_dir())

def sanitize_dir_name(name: str) -> str:
    """
    Converts 'Course Name 123!' → 'Course_Name_123'
    - Spaces & dashes are converted to underscores.
    - Special characters (except `_`) are removed.
    - Ensures only **one** underscore (`_`) between words.
    """
    name = re.sub(r"[^\w\s-]", "", name)  # Remove special characters except space & dash
    name = name.replace("-", "_")         # Convert dashes to underscores
    name = re.sub(r"\s+", "_", name)      # Convert spaces to underscores
    name = re.sub(r"_+", "_", name)       # Remove multiple underscores
    return name.strip("_")  # Remove leading/trailing underscores


def normalize_placeholder(placeholder: str) -> str:
    """
    If a placeholder starts with "{##", remove "##" after '{'.
      e.g. "{##_course_name}" -> "{course_name}"
           "{##_chapter_name}" -> "{chapter_name}"
    """
    # Detect something like "{##_"
    if placeholder.startswith("{##"):
        # e.g. "{##_course_name}" -> "{" + placeholder[3:]
        return "{" + placeholder[4:]
    return placeholder


def get_next_numeric_prefix(base_dir: Path, file_extension: Optional[str] = None) -> str:
    """
    Scans base_dir for subfolders (if file_extension is None) or files with the given file_extension
    whose names start with a two-digit prefix followed by an underscore.
    Returns the next available two-digit number as a string (e.g. "10").

    Parameters:
    - base_dir (Path): The directory to scan.
    - file_extension (Optional[str]): The file extension to filter by (e.g., ".txt"). 
                                      If None, the function will scan directories.
    """
    import re
    existing_numbers = []

    if base_dir.exists():
        for entry in base_dir.iterdir():
            if file_extension:
                # Ensure we only process files and that the file has the specified extension.
                if entry.is_file() and entry.suffix == file_extension:
                    # Use the stem (name without extension) for matching.
                    m = re.match(r'^(\d{2})_', entry.stem)
                    if m:
                        existing_numbers.append(int(m.group(1)))
            else:
                if entry.is_dir():
                    m = re.match(r'^(\d{2})_', entry.name)
                    if m:
                        existing_numbers.append(int(m.group(1)))
    
    next_num = (max(existing_numbers) + 1) if existing_numbers else 1
    return f"{next_num:02d}"


def render_expression(expr: str, context: dict) -> str:
    """
    If the expression contains Jinja2 markers, render it using the context.
    Otherwise, return it unchanged.
    """
    if "{{" in expr and "}}" in expr:
        template = jinja2.Template(expr)
        return template.render(**context)
    return expr

############################################################
# Folder / file structure creation via Jinja2 template JSON
############################################################


def create_structure_recursive(structure: dict, context: dict, base_path: Path) -> Path:
    """
    Recursively create the folder/file structure described by the rendered JSON.
    
    If context["template_uses_prefix"] is True, we assume the template is manually
    handling numeric prefixes. Otherwise, we automatically add them.
    """
    if not isinstance(base_path, Path):
        base_path = Path(base_path).expanduser()

    uses_prefix = context.get("template_uses_prefix", False)

    # Folder creation
    if "folder" in structure:
        folder_name_expr = structure["folder"]
        folder_name_rendered = render_expression(folder_name_expr, context)
        folder_name = sanitize_dir_name(folder_name_rendered)

        if uses_prefix:
            # If template is handling numeric prefix itself, we get the next prefix here:
            prefix = get_next_numeric_prefix(base_path)
            folder_name = f"{prefix}_{folder_name}"

        top_dir = base_path / folder_name
        top_dir.mkdir(parents=True, exist_ok=True)

        # Recurse into subfolders
        for subf in structure.get("subfolders", []):
            create_structure_recursive(subf, context, top_dir)

        # Handle files inside this folder
        for file_item in structure.get("files", []):
            file_name_expr = file_item.get("file")
            if not file_name_expr:
                continue
            file_name_rendered = render_expression(file_name_expr, context)
            if uses_prefix:
                # Example: only prefix certain file types, or all
                prefix = get_next_numeric_prefix(top_dir, file_extension=".py")
                file_name_rendered = f"{prefix}_{file_name_rendered}"
            (top_dir / file_name_rendered).touch()
        return top_dir

    # File creation (if top-level is a single file)
    elif "file" in structure:
        file_name_expr = structure["file"]
        file_name_rendered = render_expression(file_name_expr, context)
        if uses_prefix:
            prefix = get_next_numeric_prefix(base_path, file_extension=".py")
            file_name_rendered = f"{prefix}_{file_name_rendered}"
        file_path = base_path / file_name_rendered
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        return file_path

    else:
        raise ValueError("Invalid structure: must contain 'folder' or 'file' key.")


def create_folder_structure(
    entity_data: dict,
    template_type: str,
    template_variant: str = "default",
    templates_dir: Path = None,
    parent_path: Path = None
) -> dict:
    """
    Create a folder/file structure on disk from a Jinja2-based JSON template.
    
    1. Loads the template from templates.json using TemplateManager.
    2. Detects if 'use_numeric_prefix' is set (True/False).
    3. Renders the JSON structure, then calls create_structure_recursive().
    """
    if templates_dir is None:
        # Default to user home .incept/templates or an ENV override
        raw_dir = os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))
        templates_dir = Path(os.path.expandvars(raw_dir)).expanduser()

    # Instantiate TemplateManager to load and parse templates
    template_manager = TemplateManager(templates_dir=templates_dir)
    
    # 1. Get the path to the desired .j2 template
    template_path = template_manager.get_template_path(template_type, template_variant)
    
    # 2. Detect use_numeric_prefix from the template
    use_numeric_prefix = bool(template_manager.get_variable_value(template_type, template_variant, "use_numeric_prefix"))
    entity_data["template_uses_prefix"] = use_numeric_prefix

    # Set up Jinja environment to actually render the JSON structure
    j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(templates_dir)), autoescape=False)
    template_obj = j2_env.get_template(template_path.name)

    # Decide the output parent path
    if parent_path is None:
        env_course_folder = os.environ.get("COURSE_FOLDER_PATH")
        if env_course_folder and os.path.isdir(os.path.expandvars(env_course_folder)):
            parent_path = Path(os.path.expandvars(env_course_folder)).expanduser()
        else:
            parent_path = Path.home() / "Documents"
    else:
        parent_path = Path(os.path.expandvars(str(parent_path))).expanduser()

    # Sanitize the primary name field: e.g. "course_name" or "chapter_name" or "lesson_name"
    name_key = f"{template_type}_name"
    entity_data[name_key] = sanitize_dir_name(entity_data["name"])

    # 3. Render the JSON structure
    rendered_json_str = template_obj.render(**entity_data)
    structure = json.loads(rendered_json_str)

    # Create the structure recursively on disk
    full_path = create_structure_recursive(structure, entity_data, parent_path)
    entity_data["final_path"] = str(full_path)

    return {
        "full_path": str(full_path),
        "structure": structure,
    }


#################################################
# Generic hierarchy creation / path handling
#################################################

def expand_or_preserve_env_vars(
    raw_path: Optional[str],
    parent_path: Optional[Any],
    keep_env_in_path: bool = True
) -> Tuple[Path, str]:
    """
    Takes a potential 'raw_path' that may contain environment variables like '$ANYVAR/some/dir'.
    1) If 'raw_path' is given, we do a partial expansion for actual disk usage:
       - Find each '$XYZ' pattern, see if there's an os.environ['XYZ'].
       - If so, substitute that in a temporary string for actual creation.
    2) Meanwhile, the final_path_str we store in JSON keeps '$XYZ' if keep_env_in_path=True.
    3) If 'raw_path' is None, fallback to 'parent_path' or the user's home/Documents.
    Returns (expanded_path, final_path_str).
    """

    if raw_path:
        final_path_str = raw_path if keep_env_in_path else os.path.expandvars(raw_path)
        expanded_str = _substitute_env_vars(raw_path)
        expanded_path = Path(os.path.expandvars(expanded_str)).expanduser()
        return expanded_path, final_path_str
    else:
        if parent_path is not None:
            # If parent_path is provided as a raw string, do similar processing.
            if isinstance(parent_path, str):
                final_path_str = parent_path if keep_env_in_path else os.path.expandvars(parent_path)
                expanded_str = _substitute_env_vars(parent_path)
                expanded_path = Path(os.path.expandvars(expanded_str)).expanduser()
                return expanded_path, final_path_str
            else:
                return parent_path, str(parent_path)
        default_fallback = Path.home() / "Documents"
        return default_fallback, str(default_fallback)


def _substitute_env_vars(path_str: str) -> str:
    """
    Internal helper that replaces any '$VAR' with os.environ['VAR'] if it exists,
    else leaves it empty.
    Example: 'some/$DROPBOX/path' -> 'some/<expanded>/path'
    """
    # Regex capturing $SOMETHING with letters, digits, underscore
    pattern = re.compile(r'(\$[A-Za-z0-9_]+)')
    def replacer(match):
        var_name = match.group(1)[1:]  # remove '$'
        return os.environ.get(var_name, "")  # if not found, blank
    return pattern.sub(replacer, path_str)


##########################################
# Hierarchy creation for courses/chapters/lessons
##########################################

def create_courses(
    courses: List[Dict[str, Any]],
    templates_dir: Path,
    create_folders: bool = True,
    keep_env_in_path: bool = True,
    parent_path: Optional[Path] = None
):
    """
    Create folder structure (optionally) for a list of courses.
    Injects 'path' back into each course dict.
    Then calls `create_chapters` for any sub-chapters present.
    """
    template_manager = TemplateManager(templates_dir=templates_dir)

    for course_dict in courses:
        raw_course_path = course_dict.get("path")
        expanded_course_path, final_course_str = expand_or_preserve_env_vars(
            raw_course_path,
            parent_path,
            keep_env_in_path
        )

        if create_folders:
            context = {"type": "course", "name": course_dict["name"]}
            result = create_folder_structure(
                entity_data=context,
                template_type="course",
                template_variant=course_dict.get("template", "default"),
                templates_dir=templates_dir,
                parent_path=expanded_course_path
            )
            final_disk_path = Path(result["full_path"])
            # The actual folder name (may have numeric prefixes):
            final_folder_name = final_disk_path.name
            course_dict["path"] = str(Path(final_course_str) / final_folder_name)
        else:
            course_dict["path"] = final_course_str

        # Now process chapters if present
        if "chapters" in course_dict and isinstance(course_dict["chapters"], list):
            create_chapters(
                course_dict["chapters"],
                templates_dir=templates_dir,
                create_folders=create_folders,
                keep_env_in_path=keep_env_in_path,
                parent_path=Path(course_dict["path"])
            )


def create_chapters(
    chapters: List[Dict[str, Any]],
    templates_dir: Path,
    create_folders: bool = True,
    keep_env_in_path: bool = True,
    parent_path: Optional[Path] = None
):
    """
    Create folder structure for a list of chapters.
    Then calls `create_lessons` for any sub-lessons present.
    """
    template_manager = TemplateManager(templates_dir=templates_dir)

    for chapter_dict in chapters:
        raw_chapter_path = chapter_dict.get("path")
        expanded_chapter_path, final_chapter_str = expand_or_preserve_env_vars(
            raw_chapter_path,
            parent_path,
            keep_env_in_path
        )

        if create_folders:
            context = {"type": "chapter", "name": chapter_dict["name"]}
            result = create_folder_structure(
                entity_data=context,
                template_type="chapter",
                template_variant=chapter_dict.get("template", "default"),
                templates_dir=templates_dir,
                parent_path=expanded_chapter_path
            )
            final_disk_path = Path(result["full_path"])
            final_folder_name = final_disk_path.name
            chapter_dict["path"] = str(Path(final_chapter_str) / final_folder_name)
        else:
            chapter_dict["path"] = final_chapter_str

        # Process lessons if present
        if "lessons" in chapter_dict:
            lessons = chapter_dict["lessons"]
            if not isinstance(lessons, list):
                lessons = [lessons]
            create_lessons(
                lessons,
                templates_dir=templates_dir,
                create_folders=create_folders,
                keep_env_in_path=keep_env_in_path,
                parent_path=Path(chapter_dict["path"])
            )
            chapter_dict["lessons"] = lessons  # In case we reassign.


def create_lessons(
    lessons: List[Dict[str, Any]],
    templates_dir: Path,
    create_folders: bool = True,
    keep_env_in_path: bool = True,
    parent_path: Optional[Path] = None
):
    """
    Create folder structure for a list of lessons.
    """
    template_manager = TemplateManager(templates_dir=templates_dir)

    for lesson_dict in lessons:
        raw_lesson_path = lesson_dict.get("path")
        expanded_lesson_path, final_lesson_str = expand_or_preserve_env_vars(
            raw_lesson_path,
            parent_path,
            keep_env_in_path
        )

        if create_folders:
            # Basic context for the lesson
            lesson_context = {
                "type": "lesson",
                "name": lesson_dict["name"],
                "ext": lesson_dict.get("ext", "py"),
            }

            # Subfolder logic if desired
            enable_subfolder = lesson_dict.get("enable_subfolder", True)
            if enable_subfolder:
                child_folder_name = lesson_dict.get("child_folder_name")
                if not child_folder_name:
                    # Possibly read from the parent template (chapter)
                    variant = lesson_dict.get("template", "default")
                    child_folder_name = template_manager.get_child_template_folder_from_parent("chapter", variant)
                    if not child_folder_name:
                        child_folder_name = "lessons"

                expanded_lesson_path = expanded_lesson_path / child_folder_name
                final_lesson_str = str(Path(final_lesson_str) / child_folder_name)

            result = create_folder_structure(
                entity_data=lesson_context,
                template_type="lesson",
                template_variant=lesson_dict.get("template", "default"),
                templates_dir=templates_dir,
                parent_path=expanded_lesson_path
            )
            final_disk_path = Path(result["full_path"])
            # Could be a folder or a single file
            final_name = final_disk_path.name
            lesson_dict["path"] = str(Path(final_lesson_str) / final_name)
        else:
            lesson_dict["path"] = final_lesson_str


if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv
    from pathlib import Path

    # Load environment variables.
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=env_path)

    raw_templates_dir = os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))
    templates_dir = Path(os.path.expandvars(raw_templates_dir)).expanduser()

    def text_folder_creation():
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "lessons.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)

        try:
            course = payload_data["courses"][0]
            chapter = course["chapters"][0]
            lessons = chapter.get("lessons")
        except (KeyError, IndexError):
            print("Invalid payload structure.")
            return

        # Determine a base path for the chapter
        chapter_raw_path = chapter.get("path")
        if chapter_raw_path:
            chapter_path = Path(os.path.expandvars(chapter_raw_path)).expanduser()
        else:
            env_course_folder = os.environ.get("COURSE_FOLDER_PATH")
            if env_course_folder and os.path.isdir(os.path.expandvars(env_course_folder)):
                chapter_path = Path(os.path.expandvars(env_course_folder)).expanduser() / sanitize_dir_name(chapter["name"])
            else:
                chapter_path = Path.home() / "Documents" / sanitize_dir_name(chapter["name"])

        # Instantiate our TemplateManager once
        from incept.templates import TemplateManager
        template_manager = TemplateManager(templates_dir=templates_dir)

        results = []
        for lesson in lessons if isinstance(lessons, list) else [lessons]:
            lesson["type"] = ["Lesson"]  # or ["Lesson"] if needed
            lesson_context = lesson.copy()
            lesson_context["lesson_name"] = sanitize_dir_name(lesson["name"])
            lesson_context["ext"] = "py"

            # Decide parent path for the lesson
            if lesson.get("path"):
                lesson_context["parent_path"] = Path(os.path.expandvars(lesson["path"])).expanduser()
            else:
                lesson_context["parent_path"] = chapter_path



            # --- Subfolder Logic ---
            # We want to decide whether to place the lesson in a child folder.
            # We use:
            #   - enable_subfolder (boolean flag, default True)
            #   - child_folder_name: if not present in lesson_context,
            #       we try to extract it from the parent (chapter) template of the same variant.
            # If subfolder is enabled, see if we can get child_folder_name from the parent template
            enable_subfolder = lesson_context.get("enable_subfolder", True)
            if enable_subfolder:
                child_folder = lesson_context.get("child_folder_name")
                if not child_folder:
                    lesson_variant = lesson_context.get("template", "default")
                    # Use our template_manager here:
                    child_folder = template_manager.get_child_template_folder_from_parent("chapter", lesson_variant)
                    if not child_folder:
                        child_folder = "lessons"
                lesson_context["parent_path"] = Path(lesson_context["parent_path"]) / child_folder
            else:
                lesson_context["parent_path"] = Path(lesson_context["parent_path"])

            # Create the folder structure using the 'lesson' template
            lesson_result = create_folder_structure(
                entity_data=lesson_context,
                template_type="lesson",
                template_variant=lesson_context.get("template", "default"),
                templates_dir=template_manager.templates_dir,
                parent_path=lesson_context["parent_path"]
            )
            lesson["final_path"] = lesson_result["full_path"]
            results.append(lesson_result)

        print("Rendered and Created Lesson Structures:")
        print(json.dumps([
            {k: str(v) if isinstance(v, Path) else v for k, v in r.items()} 
            for r in results
        ], indent=2))

    # Uncomment to test:
    # text_folder_creation()

    def test_substitute_env_vars():
        raw_path = "$DROPBOX/matrix/packages"
        expanded, final_str = expand_or_preserve_env_vars(raw_path, parent_path=None)
        print("Expanded path:", expanded)
        print("Final path string:", final_str)

    def test_create_lessons():
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "lessons.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)

        # Extract lessons from the payload.
        try:
            course = payload_data["courses"][0]
            chapter = course["chapters"][0]
            lessons = chapter.get("lessons", [])
        except (KeyError, IndexError) as e:
            print("Invalid payload structure:", e)
            return

        # Determine the parent path for lessons.
        # If the chapter already has a 'path', use that; otherwise, fall back to a default.
        if "path" in chapter:
            parent_path = chapter["path"]
        else:
            parent_path = Path.home() / "Documents"

        # Call create_lessons with create_folders=True so that the template is applied.
        # This should result in a file (or folder) created by the lesson template.
        create_lessons(
            lessons,
            templates_dir=templates_dir,
            create_folders=True,  # Set to True to create folders/files on disk.
            keep_env_in_path=True,
            parent_path=parent_path
        )

        # Print the modified lessons with updated "path" fields.
        print("Lessons after processing:")
        print(json.dumps(lessons, indent=2))

    # Uncomment to test environment variable substitution.
    # test_substitute_env_vars()

    # Uncomment the next line to test environment variable substitution.
    # test_substitute_env_vars()

    # Run the test for creating lessons.
    test_create_lessons()
 

