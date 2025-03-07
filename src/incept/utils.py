# src/incept/utils.py

import os
import re
import shutil
import json
import jinja2
from pathlib import Path
from platformdirs import user_documents_dir
from typing import Optional


def detect_numeric_prefix(placeholder: str) -> bool:
    """
    Return True if placeholder starts with '{##'.
    """
    return placeholder.startswith("{##")



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

def get_child_template_folder_from_parent(template_type: str, variant: str, templates_dir: Path) -> Optional[str]:
    """
    Attempts to extract the child_folder_name value from a parent template using Jinja2's meta API.
    It reads the template file (e.g., the chapter template) and searches for an assignment:
    
         {% set child_folder_name = "lessons" %}
    
    If found and the value is constant, returns that value; otherwise, returns None.
    """
    from jinja2 import Environment, meta, nodes

    lookup_file = templates_dir / "templates.json"
    with lookup_file.open("r") as f:
        template_map = json.load(f)
    try:
        parent_filename = template_map[template_type][variant]
    except KeyError:
        return None
    template_path = templates_dir / parent_filename
    if not template_path.exists():
        return None

    # Read the template source.
    source = template_path.read_text()
    env = Environment()
    parsed_content = env.parse(source)

    # Iterate over all assignment nodes.
    for node in parsed_content.find_all(nodes.Assign):
        # Check if the assignment target is a Name node with the correct name.
        if isinstance(node.target, nodes.Name) and node.target.name == "child_folder_name":
            # If the assigned value is a constant, return its value.
            if isinstance(node.node, nodes.Const):
                return node.node.value
    return None


def render_expression(expr: str, context: dict) -> str:
    """
    If the expression contains Jinja2 markers, render it using the context.
    Otherwise, return it unchanged.
    """
    if "{{" in expr and "}}" in expr:
        template = jinja2.Template(expr)
        return template.render(**context)
    return expr

def create_folder_structure(
    entity_data: dict, 
    template_type: str,
    template_variant: str = "default",
    templates_dir: Path = None,
    parent_path: Path = None
) -> dict:
    """
    Create a folder/file structure on disk from a Jinja2 template.
    """
    if templates_dir is None:
        templates_dir = Path(os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates")))
        templates_dir = Path(os.path.expandvars(str(templates_dir))).expanduser()

    lookup_file = templates_dir / "templates.json"
    if not lookup_file.exists():
        raise FileNotFoundError(f"Missing templates.json at {lookup_file}")

    with lookup_file.open("r") as f:
        template_map = json.load(f)

    try:
        j2_filename = template_map[template_type][template_variant]
    except KeyError:
        raise ValueError(f"No template found for type={template_type}, variant={template_variant}")

    template_path = templates_dir / j2_filename
    if not template_path.exists():
        raise FileNotFoundError(f"Template file {template_path} not found.")

    j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(templates_dir)), autoescape=False)
    template_obj = j2_env.get_template(j2_filename)

    # Determine parent_path if not provided.
    if parent_path is None:
        env_course_folder = os.environ.get("COURSE_FOLDER_PATH")
        if env_course_folder and os.path.isdir(os.path.expandvars(env_course_folder)):
            parent_path = Path(os.path.expandvars(env_course_folder)).expanduser()
        else:
            parent_path = Path.home() / "Documents"
    else:
        parent_path = Path(os.path.expandvars(str(parent_path))).expanduser()

    # Sanitize the entity name used for folder/file naming.
    name_key = f"{template_type}_name"
    entity_data[name_key] = sanitize_dir_name(entity_data["name"])

    # Render the template JSON structure.
    rendered_json_str = template_obj.render(**entity_data)
    structure = json.loads(rendered_json_str)

    full_path = create_structure_recursive(structure, entity_data, parent_path)
    entity_data["final_path"] = str(full_path)

    return {
        "full_path": str(full_path),
        "structure": structure,
    }


def create_structure_recursive(structure: dict, context: dict, base_path: Path) -> Path:
    """
    Recursively create the folder/file structure described by the rendered JSON.
    """
    if not isinstance(base_path, Path):
        base_path = Path(base_path).expanduser()

    if "folder" in structure:
        folder_name_expr = structure["folder"]
        folder_name_rendered = render_expression(folder_name_expr, context)
        folder_name = sanitize_dir_name(folder_name_rendered)

        top_dir = base_path / folder_name
        #top_dir.mkdir(parents=True, exist_ok=True) # <-- uncomment

        for subf in structure.get("subfolders", []):
            create_structure_recursive(subf, context, top_dir)

        for file_item in structure.get("files", []):
            file_name_expr = file_item.get("file")
            if not file_name_expr:
                continue
            file_name_rendered = render_expression(file_name_expr, context)
            # Do not re-sanitize to preserve the extension.
            file_name = file_name_rendered
            #(top_dir / file_name).touch() # <-- Uncomment

        return top_dir

    elif "file" in structure:
        file_name_expr = structure["file"]
        file_name_rendered = render_expression(file_name_expr, context)
        file_name = file_name_rendered

        file_path = base_path / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # file_path.touch() # <-- Uncomment
        return file_path

    else:
        raise ValueError("Invalid structure: must contain 'folder' or 'file' key.")


if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv
    from pathlib import Path

    # Load environment variables from the .env file.
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=env_path)

    raw_templates_dir = os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))
    templates_dir = Path(os.path.expandvars(raw_templates_dir)).expanduser()

    def text_folder_creation():

        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "lessons.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            exit(1)

        with open(payload_file, "r") as f:
            payload_data = json.load(f)

        try:
            course = payload_data["courses"][0]         # a dict representing a course
            chapter = course["chapters"][0]              # a dict representing a chapter
            lessons = chapter.get("lessons")             # a list of lesson dicts (or a single dict)
        except (KeyError, IndexError):
            print("Invalid payload structure.")
            exit(1)

        # --- Determine the chapter base path ---
        chapter_raw_path = chapter.get("path")
        if chapter_raw_path:
            chapter_path = Path(os.path.expandvars(chapter_raw_path)).expanduser()
        else:
            env_course_folder = os.environ.get("COURSE_FOLDER_PATH")
            if env_course_folder and os.path.isdir(os.path.expandvars(env_course_folder)):
                chapter_path = Path(os.path.expandvars(env_course_folder)).expanduser() / sanitize_dir_name(chapter["name"])
            else:
                chapter_path = Path.home() / "Documents" / sanitize_dir_name(chapter["name"])

        # Compute the starting prefix once before the loop.
        lessons_dir = chapter_path
        current_prefix = int(get_next_numeric_prefix(lessons_dir, ".py"))  # Start from next available number

        results = []
        for lesson in lessons if isinstance(lessons, list) else [lessons]:
            lesson["type"] = ["Lesson"]
            lesson_context = lesson.copy()

            # Set prefix and sanitized lesson name before processing.
            lesson_context["lesson_prefix"] = f"{current_prefix:02d}"
            current_prefix += 1
            lesson_context["lesson_name"] = sanitize_dir_name(lesson["name"])
            lesson_context["ext"] = "py"  # File extension

            # Process lesson path override: if a literal "path" is provided, use it.
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
            enable_subfolder = lesson_context.get("enable_subfolder", True)
            if enable_subfolder:
                child_folder = lesson_context.get("child_folder_name")
                if not child_folder:
                    # Assume the lesson uses the same variant as its template.
                    lesson_variant = lesson_context.get("template", "default")
                    # Attempt to load the value from the parent chapter template.
                    child_folder = get_child_template_folder_from_parent("chapter", lesson_variant, templates_dir)
                    if not child_folder:
                        child_folder = "lessons"  # Fallback default.
                lesson_context["parent_path"] = Path(lesson_context["parent_path"]) / child_folder
            else:
                lesson_context["parent_path"] = Path(lesson_context["parent_path"])

            # Create the folder structure using the lesson template.
            lesson_result = create_folder_structure(
                entity_data=lesson_context,
                template_type="lesson",
                template_variant=lesson_context.get("template", "default"),
                templates_dir=templates_dir,
                parent_path=lesson_context["parent_path"]
            )

            lesson["final_path"] = lesson_result["full_path"]
            results.append(lesson_result)

        print("Rendered and Created Lesson Structures:")
        print(json.dumps([{k: str(v) if isinstance(v, Path) else v for k, v in r.items()} for r in results], indent=2))

    def test_get_child_template():
        result = get_child_template_folder_from_parent(template_type='chapter', variant='default', templates_dir=templates_dir)
        print("Extracted child_folder_name:", result)
    
    # Call the test functions:
    # test_get_child_template()
    text_folder_creation()  # Uncomment this if you want to test folder creation as well.


    



