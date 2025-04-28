# src/incept/utils.py

import os
import re
import json
import shutil
import jinja2
import datetime
import copy
from pathlib import Path
from platformdirs import user_documents_dir
from typing import Optional, Any, Dict, List, Tuple


# Import TemplateManager
from incept.templates import TemplateManager

# Import asset_generator
from incept.asset_generator import (
    BackgroundGenerator,
    FanartGenerator,
    LogoGenerator,
    PosterGenerator,
    PosterVariant,
    ThumbGenerator,
)

# Default asset IDs for video‑mode generation
DEFAULT_LOGO_PUBLIC_ID   = "icon/rebelway_logo.png"
DEFAULT_FANART_PUBLIC_ID = "banner/fanart"
DEFAULT_POSTER_BASE_ID   = PosterGenerator.DEFAULT_BASE_PUBLIC_ID
DEFAULT_THUMB_BASE_ID    = ThumbGenerator.DEFAULT_BASE_PUBLIC_ID
DEFAULT_VIDEO_EXT = os.environ.get("VIDEO_EXTENSION", "mp4")

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
        # collapse runs of “__” but keep a single leading underscore
        base = re.sub(r"_+", "_", base)
        if not base.startswith("_"):          # allow _publish, _render, …
            base = base.strip("_")            # still trim trailing “_”
            # Return the sanitized base with the original extension.
        return f"{base}.{ext}"
    else:
        # Otherwise, sanitize normally.
        name = re.sub(r"[^\w\s-]", "", name)
        name = name.replace("-", "_")
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"_+", "_", name)
        # keep a single leading underscore if present
        if name.startswith("_"):
            name = name.rstrip("_")      # only trim trailing underscores
        else:
            name = name.strip("_")       # trim both ends
        return name
# ---------------------------------------------------------------------------
#  Video‑specific helpers
# ---------------------------------------------------------------------------

def get_video_root_path(course_path: Path) -> Path:
    """Return the root path where the video hierarchy should be created.

    Logic:
      * If $VIDEO_IN_COURSE_FOLDER == "1" → place video files inside the text‑course
        directory (i.e. alongside README / lesson .md files).
      * Else fall back to $VIDEO_COURSE_FOLDER_PATH if it exists.
      * If that is missing, use ~/Videos/courses as a safe default.
    """
    in_course = os.environ.get("VIDEO_IN_COURSE_FOLDER", "0") == "1"
    if in_course:
        return course_path

    if raw and os.path.isdir(os.path.expandvars(raw)):
        return Path(os.path.expandvars(raw)).expanduser()

    return Path.home() / "Videos" / "courses"


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


def get_next_numeric_prefix(base_dir: Path,
                            file_extension: Optional[str] = None) -> str:
    """
    Return the next free two-digit index found either in *files*
    (filtered by ``file_extension`` when given) **or** in *sub-dirs*.

    Works for:
        01_Intro.md  → 01
        WK03         → 03
        season_07    → 07
        010          → 01
    """
    rx = re.compile(r'(\d{2})')          # ← one-liner change
    existing: list[int] = []

    if not base_dir.exists():
        return "01"

    for entry in base_dir.iterdir():
        # ignore files with the wrong extension
        if entry.is_file() and file_extension and entry.suffix != file_extension:
            continue

        candidate = entry.stem if entry.is_file() else entry.name
        m = rx.search(candidate)
        if m:
            existing.append(int(m.group(1)))

    next_num = (max(existing) + 1) if existing else 1
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
    # If the structure is empty or not a dict, simply return the base_path.
    if not structure or not isinstance(structure, dict):
        return base_path

    if "folder" in structure:
        folder_name_expr = structure["folder"]
        folder_name_rendered = render_expression(folder_name_expr, context)
        folder_name = sanitize_dir_name(folder_name_rendered)

        top_dir = base_path / folder_name
        top_dir.mkdir(parents=True, exist_ok=True)
        # Recurse into subfolders. Skip any empty dictionaries or those without 'folder' or 'file' keys.
        for subf in structure.get("subfolders", []):
            if not subf or not ("folder" in subf or "file" in subf):
                continue
            create_structure_recursive(subf, context, top_dir)

        # Handle files inside this folder.
        for file_item in structure.get("files", []):
            fn_expr = file_item.get("file")
            if not fn_expr:
                continue
            fn = sanitize_dir_name(render_expression(fn_expr, context))
            dst = top_dir / fn
            # if there's template_content, write it; otherwise just touch()
            content = file_item.get("template_content")
            if content is not None:
                dst.parent.mkdir(parents=True, exist_ok=True)
                # content is already unescaped (Jinja did tojson→string→parsed by json.loads)
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                lower = dst.name.lower()
                if lower.endswith("background.jpg") and context.get("logo_public_id"):
                    BackgroundGenerator(**context).generate(str(dst))
                elif lower.endswith("fanart.jpg") and context.get("fanart_public_id"):
                    FanartGenerator(public_id=context["fanart_public_id"]).generate(str(dst))
                elif lower.endswith("logo.png") and context.get("logo_public_id"):
                    LogoGenerator(**context).generate(str(dst))
                elif lower.endswith("poster.jpg"):
                    # pick CHAPTER vs COURSE based on presence of chapter_title
                    variant = PosterVariant.CHAPTER if context.get("chapter_title") else PosterVariant.COURSE
                    PosterGenerator(variant=variant, **context).generate(str(dst))
                elif lower.endswith("thumb.jpg") and context.get("course_title"):
                    ThumbGenerator(
                        instructor=context["instructor"],
                        course_title=context["course_title"],
                        base_public_id=context.get("thumb_base_id"),
                    ).generate(str(dst))
                else:
                    dst.touch()

        return top_dir

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
    # so create_structure_recursive knows which generator to pick:
    entity_data["template_type"] = template_type

    # 3. Render the JSON structure from the template
    rendered_json_str = template_obj.render(**entity_data)
    try:
        structure = json.loads(rendered_json_str)
    except json.JSONDecodeError as e:
        print("JSON error in template:",
              f"type={template_type}, variant={template_variant}")
        print("── rendered snippet ──")
        print(rendered_json_str[:300])  # show first 300 chars
        raise
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
    1) If 'raw_path' is provided, we fully expand it using os.path.expandvars for disk usage.
    2) Meanwhile, final_path_str retains the original (with $VAR) if keep_env_in_path is True.
    3) If raw_path is None, we fallback to parent_path (processed similarly) or to ~/Documents.
    Returns (expanded_path, final_path_str).
    """
    if raw_path:
        final_path_str = raw_path if keep_env_in_path else os.path.expandvars(raw_path)
        # Fully expand raw_path using os.path.expandvars
        expanded = os.path.expandvars(raw_path)
        expanded_path = Path(expanded).expanduser()
        return expanded_path, final_path_str
    else:
        if parent_path is not None:
            if isinstance(parent_path, str):
                final_path_str = parent_path if keep_env_in_path else os.path.expandvars(parent_path)
                expanded = os.path.expandvars(parent_path)
                expanded_path = Path(expanded).expanduser()
                return expanded_path, final_path_str
            else:
                return parent_path, str(parent_path)
        default_fallback = Path.home() / "Documents"
        return default_fallback, str(default_fallback)


##########################################
# Hierarchy creation for courses/chapters/lessons
##########################################

def create_courses(
    courses: List[Dict[str, Any]],
    templates_dir: Path,
    create_folders: bool = True,
    keep_env_in_path: bool = True,
    parent_path: Optional[Path] = None,
    include_video: bool = False,
):
    """
    Create folder structure for a list of courses.
    Injects 'path' back into each course dict.
    Then calls create_chapters for any sub-chapters present.
    """
    template_manager = TemplateManager(templates_dir=templates_dir)
    expanded_parent, raw_parent = expand_or_preserve_env_vars(raw_path=None, parent_path=parent_path, keep_env_in_path=keep_env_in_path)

    for course_dict in courses:
        raw_course_path = course_dict.get("path")
        expanded_course_path, final_course_str = expand_or_preserve_env_vars(raw_course_path, raw_parent, keep_env_in_path)

        # ────────────────────────────────────────────────────────────────
        # Discover the chapter “bucket” (child_folder_name) declared in
        # the *course* template we’re about to use – so that ad-hoc
        # chapter creation later on will automatically land in the right
        # place (e.g. "chapters", "course_materials", "usd/shots", …).
        # ────────────────────────────────────────────────────────────────
        course_variant      = course_dict.get("template", "default")
        course_child_folder = template_manager.get_child_template_folder_from_parent(
            "course",
            course_variant,
        )

        if create_folders:
            base_prefix = int(get_next_numeric_prefix(expanded_course_path))
            prefix = f"{base_prefix:02d}"
            context = {
                "numeric_prefix": prefix,
                "course_name": course_dict["name"],
                "name": course_dict["name"],
                "chapters": course_dict.get("chapters", [])
            }
            result = create_folder_structure(
                entity_data=context,
                template_type="course",
                template_variant=course_dict.get("template", "default"),
                templates_dir=templates_dir,
                parent_path=expanded_course_path
            )
            final_disk_path = Path(result["full_path"])
            course_dict["path"] = str(Path(final_course_str) / final_disk_path.name)
            # Make the discovered child-folder metadata available to
            # downstream chapter creation calls.
            course_dict.setdefault("child_folder_name", course_child_folder)
            course_dict.setdefault("template_variant",  course_variant)
        else:
            course_dict["path"] = final_course_str
            # when video is disabled, still record the field for Notion
            course_dict["video_path"] = "NA"

        # ---------------------------------------------------------------
        #  Optional: generate Jellyfin-compatible *video* hierarchy
        # ---------------------------------------------------------------
        if include_video:
            # 1) pick up the raw env-var path ($VIDEO_COURSE_FOLDER_PATH) or fallback
            raw_video_root = os.environ.get("VIDEO_COURSE_FOLDER_PATH")
            if not raw_video_root or not os.path.isdir(os.path.expandvars(raw_video_root)):
                # fallback to ~/Videos/courses
                raw_video_root = str(Path.home() / "Videos" / "courses")

            # 2) expand it for actual file-system use
            expanded_video_root = Path(os.path.expandvars(raw_video_root)).expanduser()

            # 3) if you explicitly want inline (VIDEO_IN_COURSE_FOLDER=1), override
            if os.environ.get("VIDEO_IN_COURSE_FOLDER") == "1":
                raw_video_root = course_dict["path"]
                expanded_video_root = Path(os.path.expandvars(raw_video_root)).expanduser()

            # that’s your season root
            video_parent_path = expanded_video_root
            # instructors can be a list; generators expect a single string
            raw_instr = course_dict.get("instructor", [])
            instr_str = ", ".join(raw_instr) if isinstance(raw_instr, (list, tuple)) else str(raw_instr or "")

            video_ctx = {
                "numeric_prefix": prefix,
                "course_slug": sanitize_dir_name(course_dict["name"]),
                "course_title": course_dict["name"],
                "description": course_dict.get("description", ""),
                "institute": course_dict.get("institute", []),
                "logo_public_id": course_dict.get("logo_public_id")    or DEFAULT_LOGO_PUBLIC_ID,
                "fanart_public_id": course_dict.get("fanart_public_id") or DEFAULT_FANART_PUBLIC_ID,
                "base_public_id": course_dict.get("poster_base_id")     or DEFAULT_POSTER_BASE_ID,
                "thumb_base_id": course_dict.get("thumb_base_id")       or DEFAULT_THUMB_BASE_ID,
                # now a single string, not a list
                "instructor": instr_str,
                "chapters": course_dict.get("chapters", []),
                "name": course_dict["name"],
                "year": course_dict.get("year", datetime.datetime.now().year),
            }
            video_result = create_folder_structure(
                entity_data=video_ctx,
                template_type="course",
                template_variant=course_dict.get("video_template", "video"),
                templates_dir=templates_dir,
                parent_path=video_parent_path,
            )

            # record the **un-expanded** “$DATALIB/…” style path
            video_folder_name = Path(video_result["full_path"]).name
            course_dict["video_path"] = f"{raw_video_root}/{video_folder_name}"

        # ------------------------------------------------------------------
        #  Process sub‑chapters
        #  1) Always create the standard text hierarchy (back‑compat).
        #  2) If include_video=True, also mirror those chapters as seasons
        #     inside the video hierarchy.
        # ------------------------------------------------------------------
        if "chapters" in course_dict and isinstance(course_dict["chapters"], list):
            # 1) Text/markdown hierarchy (existing behaviour)
            create_chapters(
                course_dict["chapters"],
                templates_dir=templates_dir,
                create_folders=create_folders,
                keep_env_in_path=keep_env_in_path,
                parent_path=course_dict["path"],
                include_video=False,
                parent_course_template_variant=course_variant,
                parent_child_folder_name=course_child_folder,
            )

            # 2) Optional video hierarchy (seasons/episodes)
            if include_video:
                # Deep‑copy so that video‑specific keys don't pollute text entries
                # → also inject course‑level asset IDs & titles into each chapter_dict
                video_chapters = copy.deepcopy(course_dict["chapters"])
                for chap in video_chapters:
                    chap["logo_public_id"]   = video_ctx["logo_public_id"]
                    chap["fanart_public_id"] = video_ctx["fanart_public_id"]
                    chap["poster_base_id"]   = video_ctx["base_public_id"]
                    chap["course_title"]     = video_ctx["course_title"]
                    chap["instructor"]       = video_ctx["instructor"]
                create_chapters(
                    video_chapters,
                    templates_dir=templates_dir,
                    create_folders=create_folders,
                    keep_env_in_path=keep_env_in_path,
                    parent_path=course_dict["video_path"],
                    include_video=True,
                )
                # ───────────────────────────────────────────────────────────────
                # propagate video_path back onto the original chapters & lessons
                for orig_chap, vid_chap in zip(course_dict["chapters"], video_chapters):
                    # copy season (chapter) path
                    orig_chap["video_path"] = vid_chap.get("video_path")
                    # copy each episode (lesson) path
                    for orig_lesson, vid_lesson in zip(
                        orig_chap.get("lessons", []),
                        vid_chap.get("lessons", [])
                    ):
                        orig_lesson["video_path"] = vid_lesson.get("video_path")
                # ───────────────────────────────────────────────────────────────


def create_chapters(
    chapters: List[Dict[str, Any]],
    templates_dir: Path,
    create_folders: bool = True,
    keep_env_in_path: bool = True,
    parent_path: Optional[Path] = None,
    include_video: bool = False,
    parent_course_template_variant: str = "default",
    parent_child_folder_name: Optional[str] = None,
):
    """
    Create folder structure for a list of chapters.
    Then calls create_lessons for any sub-lessons present.
    """
    template_manager = TemplateManager(templates_dir=templates_dir)
    path_key = "video_path" if include_video else "path"
    # Process parent_path as raw string.
    expanded_parent, raw_parent = expand_or_preserve_env_vars(raw_path=None, parent_path=parent_path, keep_env_in_path=keep_env_in_path)

    for i, chapter_dict in enumerate(chapters, start=1):
        raw_chapter_path = chapter_dict.get(path_key)
        expanded_chapter_path, final_chapter_str = expand_or_preserve_env_vars(raw_chapter_path, raw_parent, keep_env_in_path)
        
        # ────────────────────────────────────────────────────────────────
        # Decide (template-driven) where the chapter folder belongs.
        # Priority:
        #   1) explicit chapter_dict["child_folder_name"]
        #   2) parent_child_folder_name passed from create_courses
        #   3) lookup “child_folder_name” in the *course* template
        # If the final value is an empty string  →  no extra nesting.
        # ------------------------------------------------------------------
        # In VIDEO mode we never want an extra “chapters” folder (seasons
        # already live inside season_NN).  Force empty unless the user
        # overrides explicitly.
        # ------------------------------------------------------------------
        if include_video:
            child_folder_name = chapter_dict.get("child_folder_name", "")
        else:
            child_folder_name = chapter_dict.get("child_folder_name")
        if child_folder_name is None:
            child_folder_name = parent_child_folder_name
        if child_folder_name is None:
            child_folder_name = template_manager.get_child_template_folder_from_parent(
                "course",
                parent_course_template_variant,
            )

        # Persist metadata for the benefit of create_lessons():
        chapter_dict.setdefault("parent_child_folder_name", child_folder_name)
        chapter_dict.setdefault("parent_course_template_variant", parent_course_template_variant)

        if child_folder_name:          # skip when "", None, or False
            expanded_chapter_path = expanded_chapter_path / child_folder_name
            final_chapter_str     = str(Path(final_chapter_str) / child_folder_name)

        if create_folders:
            # One generic algorithm that works for *all* templates:
            base_prefix = int(get_next_numeric_prefix(expanded_chapter_path))
            # If nothing matched (==1) *and* we’re iterating, fall back to loop index.
            if base_prefix == 1 and any(Path(expanded_chapter_path).iterdir()):
                base_prefix = i
            prefix = f"{base_prefix:02d}"
            context = {
                "numeric_prefix": prefix,
                "chapter_name": chapter_dict["name"],
                "lessons":      chapter_dict.get("lessons", []),
                "name":         chapter_dict["name"],
            }

            # in video mode, carry along the course assets & titles so
            # our image‐dispatch will fire inside this season folder
            if include_video:
                context.update({
                    "logo_public_id":   chapter_dict.get("logo_public_id")   or DEFAULT_LOGO_PUBLIC_ID,
                    "fanart_public_id": chapter_dict.get("fanart_public_id") or DEFAULT_FANART_PUBLIC_ID,
                    "base_public_id":   chapter_dict.get("poster_base_id")   or DEFAULT_POSTER_BASE_ID,
                    "thumb_base_id":    chapter_dict.get("thumb_base_id")    or DEFAULT_THUMB_BASE_ID,
                    "course_title":     chapter_dict.get("course_title"),
                    "instructor":       chapter_dict.get("instructor"),
                    "chapter_title":    chapter_dict["name"],
                })

            template_used = "chapter"
            variant_used  = "video" if include_video else chapter_dict.get("template", "default")
            result = create_folder_structure(
                entity_data=context,
                template_type=template_used,
                template_variant=variant_used,
                templates_dir=templates_dir,
                parent_path=expanded_chapter_path,
            )
            final_disk_path = Path(result["full_path"])
            # final_chapter_str already preserved raw env-var for parent
            this_raw = str(Path(final_chapter_str) / final_disk_path.name)
            chapter_dict[path_key] = this_raw
            if include_video:
                # point the `video_path` at the season folder
                chapter_dict["video_path"] = this_raw
        else:
            chapter_dict[path_key] = final_chapter_str
            # ensure chapter.video_path even if not creating video
            chapter_dict["video_path"] = "NA"

        # Process lessons if present.
        if "lessons" in chapter_dict:
            lessons = chapter_dict["lessons"]
            if not isinstance(lessons, list):
                lessons = [lessons]
            create_lessons(
                lessons,
                templates_dir=templates_dir,
                create_folders=create_folders,
                keep_env_in_path=keep_env_in_path,
                parent_path=chapter_dict[path_key],
                include_video=include_video,
                parent_chapter_template_variant=variant_used,
            )
            chapter_dict["lessons"] = lessons

def create_lessons(
     lessons: List[Dict[str, Any]],
     templates_dir: Path,
     create_folders: bool = True,
     keep_env_in_path: bool = True,
     parent_path: Optional[Path] = None,
     include_video: bool = False,
     parent_chapter_template_variant: str = "default",
     parent_child_folder_name: Optional[str] = None,     # NEW
):
    """
    Create folder/file structure for a list of lessons.
    """
    template_manager = TemplateManager(templates_dir=templates_dir)
    path_key = "video_path" if include_video else "path"
    expanded_parent, raw_parent = expand_or_preserve_env_vars(raw_path=None, parent_path=parent_path, keep_env_in_path=keep_env_in_path)

    for idx, lesson_dict in enumerate(lessons):
        raw_lesson_path = lesson_dict.get(path_key)
        expanded_lesson_path, final_lesson_str = expand_or_preserve_env_vars(raw_lesson_path, raw_parent, keep_env_in_path)

        if create_folders:
            # ────────────────────────────────────────────────────────────
            # Where does the lesson live? Let the *chapter* template tell
            # us – unless the payload specified something explicit.
            # ────────────────────────────────────────────────────────────
            # ── child-folder resolution (same priority order as create_chapters) ──
            if include_video:
                child_folder_name = lesson_dict.get("child_folder_name", "")
            else:
                child_folder_name = lesson_dict.get("child_folder_name")

            if child_folder_name is None:
                child_folder_name = parent_child_folder_name          # ← NEW step

            if child_folder_name is None:
                child_folder_name = template_manager.get_child_template_folder_from_parent(
                    "chapter",
                    parent_chapter_template_variant,
                )

            if child_folder_name:      # empty string  →  no nesting
                expanded_lesson_path = expanded_lesson_path / child_folder_name
                final_lesson_str     = str(Path(final_lesson_str) / child_folder_name)
            # ---------- text-mode helpers ---------------------------------
            # Needed later for both prefix detection *and* template context.
            ext = f".{lesson_dict.get('ext', 'md')}"


            if include_video:
                video_ext = lesson_dict.get("video_ext", DEFAULT_VIDEO_EXT)
            
                season_folder = Path(parent_path).name
                season_match  = re.search(r'(\d{2})$', season_folder)
                if not season_match:                      # graceful failure if folder renamed
                    raise ValueError(
                        f"Unable to extract 2-digit season prefix from '{season_folder}'. "
                        "Expected something like 'WK08', 'season_08', etc."
                    )
                season_prefix = season_match.group(1)     # “08”
            
                # scan only *.mp4 (or whatever) and extract eNN
                existing = []
                for f in expanded_lesson_path.glob(f"*.{video_ext}"):
                    m = re.search(r"e(\d{2})", f.stem, flags=re.I)
                    if m:
                        existing.append(int(m.group(1)))
                episode_number = f"{(max(existing)+1) if existing else 1:02d}"
            
            
                lesson_context = {
                    "name":           lesson_dict["name"],
                    "numeric_prefix": season_prefix,           # s**04**e02
                    "episode_number": episode_number,          # e**02**
                    "lesson_slug":    sanitize_dir_name(lesson_dict["name"]).lower(),
                    "lesson_title":   lesson_dict["name"],
                    "video_ext":      video_ext,
                    "description":    lesson_dict.get("description", ""),
                    "aired":          lesson_dict.get("aired", None),
                }
            else:
                # text mode: just enumerate by existing files
                base_prefix = int(
                    get_next_numeric_prefix(
                        expanded_lesson_path,
                        file_extension=ext,
                    )
                )
                lesson_context = {
                    "name":           lesson_dict["name"],                        # avoid KeyError
                    "numeric_prefix": f"{base_prefix:02d}",
                    "lesson_name":    lesson_dict["name"],
                    "ext":            lesson_dict.get("ext", "md"),
                }

            template_used  = "lesson"
            variant_used   = "video" if include_video else lesson_dict.get("template", "default")
            result = create_folder_structure(
                entity_data=lesson_context,
                template_type=template_used,
                template_variant=variant_used,
                templates_dir=templates_dir,
                parent_path=expanded_lesson_path,
            )
            final_disk_path = Path(result["full_path"])
            # final_lesson_str preserves the raw parent env-var path
            # ── text vs. video ──────────────────────────────────────────────
            if include_video:
                # The rendered JSON → {"folder":".","files":[{"file": "...mp4"}, …]}
                first_file = sanitize_dir_name(result["structure"]["files"][0]["file"])
                this_raw   = str(Path(final_lesson_str) / first_file)   # full video file
            else:
                this_raw   = str(Path(final_lesson_str) / final_disk_path.name)
            lesson_dict[path_key] = this_raw
            if include_video:
                # point video_path at the actual episode file
                lesson_dict["video_path"] = this_raw
        else:
            lesson_dict[path_key] = final_lesson_str
            # ensure lesson.video_path even if not creating video
            lesson_dict["video_path"] = "NA"


if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv
    from pathlib import Path

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

    def test_create_courses():
        import os, json
        from pathlib import Path
    
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "full_courses.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return
    
        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)
    
        try:
            courses = payload_data["courses"]
        except (KeyError, IndexError) as e:
            print("Invalid payload structure:", e)
            return
    
        # Ensure each course has a 'path'. If not, assign a default.
        for course in courses:
            if "path" not in course or not course["path"]:
                env_course_folder = os.environ.get("COURSE_FOLDER_PATH")
                if env_course_folder and os.path.isdir(os.path.expandvars(env_course_folder)):
                    course["path"] = env_course_folder
                else:
                    course["path"] = str(Path.home() / "Documents")
    
        # Call create_courses with create_folders=True.
        # The parent_path here is left as None so that create_courses uses its internal fallback.
        create_courses(
            courses,
            templates_dir=templates_dir,  # assumes templates_dir is defined globally (as in your main block)
            create_folders=True,
            keep_env_in_path=True,
            parent_path=None
        )
    
        # Print the modified courses with updated "path" fields.
        print("Courses after processing:")
        print(json.dumps(courses, indent=2))

    def test_create_courses_with_video():
        """Create BOTH text and video hierarchies for all courses in full_courses.json."""
        payload_file = os.path.join(
            os.path.expanduser("~"),
            ".incept",
            "payload",
            "cine_light.json",
        )
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)

        try:
            courses = payload_data["courses"]
        except (KeyError, IndexError) as e:
            print("Invalid payload structure:", e)
            return

        # Ensure a text‑course base path; leave video root to helper logic.
        for course in courses:
            if not course.get("path"):
                course["path"] = os.environ.get(
                    "COURSE_FOLDER_PATH",
                    str(Path.home() / "Documents"),
                )

        create_courses(
            courses,
            templates_dir=templates_dir,
            create_folders=True,
            keep_env_in_path=True,
            parent_path=None,
            include_video=True,          # ← key difference
        )

        print("Courses after processing (text + video):")
        print(json.dumps(courses, indent=2))



    # Uncomment the next line to test environment variable substitution.
    # test_substitute_env_vars()

    # Run the test for creating lessons.
    # test_create_lessons()

    # Run the test for creating chapters.
    # test_create_chapters()

    # Run the test for creating courses.
    # test_create_courses()

    # run a quick dual‑tree test
    test_create_courses_with_video()
