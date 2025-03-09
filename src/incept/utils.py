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
    # If there's a dot, assume it's a file with an extension.
    if '.' in name:
        base, ext = name.rsplit('.', 1)
        # Sanitize the base name.
        base = re.sub(r"[^\w\s-]", "", base)
        base = base.replace("-", "_")
        base = re.sub(r"\s+", "_", base)
        base = re.sub(r"_+", "_", base)
        base = base.strip("_")
        # Return the sanitized base with the original extension.
        return f"{base}.{ext}"
    else:
        # Otherwise, sanitize normally.
        name = re.sub(r"[^\w\s-]", "", name)
        name = name.replace("-", "_")
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"_+", "_", name)
        return name.strip("_")


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
    Recursively create the folder/file structure described by the already-rendered JSON.
    - 'structure' is a dict with either "folder" or "file" plus optional "subfolders" or "files".
    - 'context' is any data you passed to the Jinja template (e.g. numeric_prefix, chapter_name, etc.).
    - 'base_path' is where we create the current folder/file.

    We do not do any automatic prefixing here; we rely on the template to produce the final names.
    """

    # --- Folder creation ---
    if "folder" in structure:
        folder_name_expr = structure["folder"]
        folder_name_rendered = render_expression(folder_name_expr, context)
        folder_name = sanitize_dir_name(folder_name_rendered)

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
            file_name_rendered = sanitize_dir_name(file_name_rendered)
            (top_dir / file_name_rendered).touch()

        return top_dir

    # --- File creation ---
    elif "file" in structure:
        file_name_expr = structure["file"]
        file_name_rendered = render_expression(file_name_expr, context)
        file_name_rendered = sanitize_dir_name(file_name_rendered)
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
    if templates_dir is None:
        raw_dir = os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))
        templates_dir = Path(os.path.expandvars(raw_dir)).expanduser()

    template_manager = TemplateManager(templates_dir=templates_dir)
    template_path = template_manager.get_template_path(template_type, template_variant)

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

    # e.g. "name" → "chapter_name" or "lesson_name"
    name_key = f"{template_type}_name"
    entity_data[name_key] = sanitize_dir_name(entity_data["name"])

    # 3. Render the JSON structure from the template
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
    1) If 'raw_path' is given, we substitute the environment variables (using _substitute_env_vars)
       and then fully expand it (using os.path.expandvars) for actual disk usage.
    2) Meanwhile, the final_path_str we store in JSON keeps '$VAR' if keep_env_in_path is True.
    3) If 'raw_path' is None, fallback to 'parent_path' (processed similarly) or the user's home/Documents.
    Returns (expanded_path, final_path_str).
    """
    if raw_path:
        final_path_str = raw_path if keep_env_in_path else os.path.expandvars(raw_path)
        # Substitute using our helper:
        substituted = _substitute_env_vars(raw_path)
        # Fully expand the substituted string.
        fully_expanded = os.path.expandvars(substituted)
        expanded_path = Path(fully_expanded).expanduser()
        return expanded_path, final_path_str
    else:
        if parent_path is not None:
            if isinstance(parent_path, str):
                final_path_str = parent_path if keep_env_in_path else os.path.expandvars(parent_path)
                substituted = _substitute_env_vars(parent_path)
                fully_expanded = os.path.expandvars(substituted)
                expanded_path = Path(fully_expanded).expanduser()
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
    pattern = re.compile(r'(\$[A-Za-z0-9_]+)')
    def replacer(match):
        var_name = match.group(1)[1:]  # remove the '$'
        # If the variable is not set, you may decide to return an empty string or a default.
        return os.environ.get(var_name, "")
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
    template_manager = TemplateManager(templates_dir=templates_dir)

    for idx, chapter_dict in enumerate(chapters):
        raw_chapter_path = chapter_dict.get("path")
        expanded_chapter_path, final_chapter_str = expand_or_preserve_env_vars(
            raw_chapter_path,
            parent_path,
            keep_env_in_path
        )
    
        if create_folders:
            # Compute the base prefix from the destination folder.
            # For example, if there are 5 chapters already, this returns "06" as an integer value 6.
            base_prefix = int(get_next_numeric_prefix(expanded_chapter_path))
            # Add the current payload index offset.
            prefix = f"{base_prefix + idx:02d}"
            
            context = {
                "numeric_prefix": prefix,      # e.g. "06", "07", ...
                "chapter_name": chapter_dict["name"],
                "lessons": chapter_dict.get("lessons", []),
                "name": chapter_dict["name"]
            }
    
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
    template_manager = TemplateManager(templates_dir=templates_dir)

    if parent_path is None:
        parent_path = Path.home() / "Documents"
    else:
        parent_path = Path(parent_path).expanduser()

    for idx, lesson_dict in enumerate(lessons):
        raw_lesson_path = lesson_dict.get("path")
        expanded_lesson_path, final_lesson_str = expand_or_preserve_env_vars(
            raw_lesson_path,
            parent_path,
            keep_env_in_path
        )
    
        if create_folders:
            # If a subfolder is enabled, add it first.
            enable_subfolder = lesson_dict.get("enable_subfolder", True)
            if enable_subfolder:
                child_folder_name = lesson_dict.get("child_folder_name") or "lessons"
                expanded_lesson_path = expanded_lesson_path / child_folder_name
                final_lesson_str = str(Path(final_lesson_str) / child_folder_name)
    
            # Compute the base prefix from the destination (final) folder.
            base_prefix = int(get_next_numeric_prefix(expanded_lesson_path))
            print(f'Expanded Lesson Path: {expanded_lesson_path}, base prefix: {base_prefix}  final_lesson_string: {final_lesson_str}')
            # Add the index offset for this lesson.
            prefix = f"{base_prefix + idx:02d}"
    
            lesson_context = {
                "numeric_prefix": prefix,
                "lesson_name": lesson_dict["name"],
                "ext": lesson_dict.get("ext", "md"),
                "name": lesson_dict["name"]
            }
    
            result = create_folder_structure(
                entity_data=lesson_context,
                template_type="lesson",
                template_variant=lesson_dict.get("template", "default"),
                templates_dir=templates_dir,
                parent_path=expanded_lesson_path
            )
            final_disk_path = Path(result["full_path"])
            lesson_dict["path"] = str(Path(final_lesson_str) / final_disk_path.name)
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
        parent_path = "$DATALIB/threeD/courses/01_Sample_Course_A/01_Sample_Chapter_A"
        expanded, final_str = expand_or_preserve_env_vars(raw_path=None, parent_path=parent_path)
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

    def test_create_chapters():
        # Locate the payload file for chapters.
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "chapters.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        # Load the JSON payload.
        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)

        # Extract the first course and its chapters.
        try:
            course = payload_data["courses"][0]
            chapters = course.get("chapters", [])
        except (KeyError, IndexError) as e:
            print("Invalid payload structure:", e)
            return

        # Determine the parent path for chapters.
        # IMPORTANT: We pass the raw value so that environment variables (e.g. "$DATALIB")
        # are preserved in the final JSON output.
        if "path" in course:
            parent_path = course["path"]  # Do not expand here!
        else:
            parent_path = str(Path.home() / "Documents")

        # Call create_chapters with create_folders=True so that folders/files are actually created.
        create_chapters(
            chapters,
            templates_dir=templates_dir,
            create_folders=True,     # Change to False if you only want to test JSON modification.
            keep_env_in_path=True,   # Ensures that the final "path" retains the $ variable.
            parent_path=parent_path   # Pass the raw string here.
        )

        # Print the modified chapters (including nested lessons, if any) with updated "path" fields.
        print("Chapters after processing:")
        print(json.dumps(chapters, indent=2))


    # Uncomment the next line to test environment variable substitution.
    test_substitute_env_vars()

    # Run the test for creating lessons.
    # test_create_lessons()

    # Run the test for creating chapters.
    # test_create_chapters()
 

