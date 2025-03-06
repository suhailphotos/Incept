# src/incept/utils.py

import os
import re
import shutil
import json
import jinja2
from pathlib import Path
from platformdirs import user_documents_dir


def detect_numeric_prefix(placeholder: str) -> bool:
    """
    Return True if placeholder starts with '{##'.
    """
    return placeholder.startswith("{##")

def get_next_numeric_prefix(base_dir: Path) -> str:
    """
    Scans base_dir for subfolders whose names start with a two-digit prefix followed by an underscore.
    Returns the next available two-digit number as a string (e.g. "10").
    """
    import re
    existing_numbers = []
    if base_dir.exists():
        for d in base_dir.iterdir():
            if d.is_dir():
                m = re.match(r'^(\d{2})_', d.name)
                if m:
                    existing_numbers.append(int(m.group(1)))
    next_num = (max(existing_numbers) + 1) if existing_numbers else 1
    return f"{next_num:02d}"

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

def create_folder_structure(
    entity_data: dict, 
    template_type: str,
    template_variant: str = "default",
    templates_dir: Path = None
) -> dict:
    """
    Create a folder structure on disk from Jinja2 templates.
    
    Parameters:
      - entity_data (dict): A dictionary of variables to render in the Jinja2 template.
                            e.g. {"chapter_prefix": "01", "chapter_name": "sample_chapter_a", "lessons": [ ... ]}.
      - template_type (str): "course", "chapter", or "lesson".
      - template_variant (str): e.g. "default", "python", "blender", etc.
      - templates_dir (Path): Path to the directory containing user’s .j2 files and templates.json.
                             e.g. Path("~/.incept/templates"). If None, read from environment.

    Returns:
      A dictionary with 
       - "full_path": the final path of the top-level folder or file,
       - "structure": the final JSON structure (dict) that was used to create the folders/files,
         including any modifications (e.g. numeric prefixes).
    """
    # 1) Determine where the templates are stored.
    if templates_dir is None:
        templates_dir = Path(os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))).expanduser()

    # 2) Load the 'templates.json' file to see which .j2 file to use.
    lookup_file = templates_dir / "templates.json"
    if not lookup_file.exists():
        raise FileNotFoundError(f"Missing templates.json at {lookup_file}")

    with lookup_file.open("r") as f:
        template_map = json.load(f)

    # e.g. template_map["chapter"]["default"] = "default_chapter.j2"
    try:
        j2_filename = template_map[template_type][template_variant]
    except KeyError:
        raise ValueError(f"No template found for type={template_type}, variant={template_variant}")

    # 3) Load the Jinja2 environment and template.
    template_path = templates_dir / j2_filename
    if not template_path.exists():
        raise FileNotFoundError(f"Template file {template_path} not found.")

    j2_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        autoescape=False
    )
    template_obj = j2_env.get_template(j2_filename)

    # 4) Render the template with entity_data to get a JSON structure describing folder/files.
    rendered_json_str = template_obj.render(**entity_data)
    structure = json.loads(rendered_json_str)  # e.g. {"folder": "01_sample_chapter_a", "subfolders": [...], "files": [...]}

    # 5) Recursively create the structure on disk.
    #    The top-level structure might be a "folder" or a "file".
    # full_path = create_structure_recursive(structure, entity_data)

    return {
        #"full_path": str(full_path),
        "structure": structure
    }

def create_structure_recursive(structure: dict, entity_data: dict, base_path: Path = None) -> Path:
    """
    Recursively create folder/file structure described by the template's JSON.
    
    structure might look like:
    {
      "folder": "01_sample_chapter_a",
      "subfolders": [
        { "folder": "assignments" },
        { 
          "folder": "lessons",
          "subfolders": [... more children ...]
        }
      ],
      "files": [
        { "file": "notes.md" },
        ...
      ]
    }

    or for a "lesson":
    {
      "file": "01_sample_lesson_e.py"
    }

    Returns the full path of the top-level entity created.
    """
    if base_path is None:
        # If we have an explicit path in entity_data (like $DATALIB/threeD/courses/...), use that.
        # Or fallback to something like Path(os.environ["COURSE_FOLDER_PATH"]) if not provided.
        # For demo, let's just do a fallback user doc folder.
        base_path = Path(entity_data.get("base_path") or os.environ.get("COURSE_FOLDER_PATH") or
                         str(Path.home() / "Documents"))
        base_path = base_path.expanduser()

    # If this structure has a "folder" key, create that folder in base_path.
    if "folder" in structure:
        folder_name = structure["folder"]
        # Potentially sanitize the name or detect numeric prefix:
        folder_name = sanitize_dir_name(folder_name)
        # e.g. handle detect_numeric_prefix if you have placeholders, etc.

        top_dir = base_path / folder_name
        top_dir.mkdir(parents=True, exist_ok=True)

        # Create any subfolders:
        subfolders = structure.get("subfolders", [])
        for subf in subfolders:
            create_structure_recursive(subf, entity_data, top_dir)

        # Create any files:
        files = structure.get("files", [])
        for file_item in files:
            file_name = file_item.get("file")
            if not file_name:
                continue
            file_name = sanitize_dir_name(file_name)
            (top_dir / file_name).touch()

        return top_dir

    # Otherwise, if "file" is top-level, create that file in base_path:
    elif "file" in structure:
        file_name = structure["file"]
        file_name = sanitize_dir_name(file_name)
        file_path = base_path / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        return file_path

    else:
        # No "folder" or "file"?
        raise ValueError("Invalid structure: must contain 'folder' or 'file' key.")

if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv
    from pathlib import Path
    from incept.utils import create_folder_structure

    # Load environment variables from the .env file located in the same directory.
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)

    # Fully expand the templates directory.
    raw_templates_dir = os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))
    expanded_templates_dir = Path(os.path.expandvars(raw_templates_dir)).expanduser()

    # Define sample entity data for a chapter.
    chapter_data = {
        "chapter_prefix": "01",
        "chapter_name": "sample_chapter_a",
        "lessons": [
            {"lesson_prefix": "01", "lesson_name": "sample_lesson_e", "py": "py"},
            {"lesson_prefix": "02", "lesson_name": "sample_lesson_f", "py": "py"},
            {"lesson_prefix": "03", "lesson_name": "sample_lesson_g", "py": "py"}
        ]
    }

    # Call the create_folder_structure function.
    result = create_folder_structure(
        entity_data=chapter_data,
        template_type="chapter",        # e.g., "course", "chapter", or "lesson"
        template_variant="default",     # e.g., "default", "python", etc.
        templates_dir=expanded_templates_dir
    )

    # Since full_path creation is commented out, print the rendered structure.
    print("Rendered Folder Structure:")
    print(json.dumps(result, indent=2))
