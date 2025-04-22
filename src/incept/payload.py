# src/incept/payload.py

import csv
import json
from pathlib import Path
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader
from incept.templates import TemplateManager

# — course‑wide defaults (can be overridden) —
DEFAULT_TOOL                    = "149a1865-b187-80f9-b21f-c9c96430bf62"
DEFAULT_INSTRUCTOR              = ["Nick Chamberlain"]
DEFAULT_INSTITUTE               = ["Rebelway"]
DEFAULT_TAGS                    = ["Python"]
DEFAULT_TEMPLATE                = "default"

DEFAULT_LOGO_PUBLIC_ID          = "icon/rebelway_logo"
DEFAULT_FANART_PUBLIC_ID        = "banner/fanart"
DEFAULT_POSTER_BASE_PUBLIC_ID   = "poster/base_image"
DEFAULT_THUMB_BASE_PUBLIC_ID    = "thumb/base_image"


def load_chapters(
    csv_path: Path,
    name_template: str | None = None
) -> List[Dict]:
    """
    Reads chapters.csv and returns a list of chapter dicts.
    If the CSV row has a 'name' column, use that;
    elif name_template is provided, use name_template.format(i=i);
    else default to 'Chapter {i}'.
    """
    chapters: List[Dict] = []
    with open(csv_path, mode='r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader, start=1):
            if "name" in r and r["name"].strip():
                name = r["name"].strip()
            elif name_template:
                name = name_template.format(i=i)
            else:
                name = f"Chapter {i}"
            chapters.append({
                "index":       i,
                "id":          None,
                "icon":        None,
                "cover":       None,
                "name":        name,
                "tool":        [DEFAULT_TOOL],
                "description": r["description"],
                "link":        r["link"],
                "instructor":  DEFAULT_INSTRUCTOR,
                "institute":   DEFAULT_INSTITUTE,
                "tags":        DEFAULT_TAGS,
                "template":    DEFAULT_TEMPLATE,
                "lessons":     []  # filled in by build_payload
            })
    return chapters


def load_lessons(csv_path: Path) -> Dict[int, List[Dict]]:
    """
    Reads lessons.csv, grouping each row under its chapter_index.
    Returns a dict: { chapter_index: [lesson_dict, ...], ... }
    """
    by_chap: Dict[int, List[Dict]] = {}
    with open(csv_path, mode='r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            ci = int(r["chapter_index"])
            lesson = {
                "id":          None,
                "icon":        None,
                "cover":       None,
                "tool":        [DEFAULT_TOOL],
                "name":        r["name"],
                "description": r["description"],
                "link":        r["link"],
                "instructor":  DEFAULT_INSTRUCTOR,
                "institute":   DEFAULT_INSTITUTE,
                "tags":        DEFAULT_TAGS,
                "template":    DEFAULT_TEMPLATE,
            }
            by_chap.setdefault(ci, []).append(lesson)
    return by_chap


def build_payload(
    *,
    course_name: str,
    course_desc: str,
    intro_link: str,
    chapters_csv: Path,
    lessons_csv: Path,
    templates_dir: Path,

    # ← new override, optional
    chapter_name_template: str | None = None,

    # ← existing overrides, optional
    tool:               List[str] | None = None,
    instructor:         List[str] | None = None,
    institute:          List[str] | None = None,
    tags:               List[str] | None = None,
    template:           str        | None = None,

    logo_public_id:     str        | None = None,
    fanart_public_id:   str        | None = None,
    poster_base_public_id: str     | None = None,
    thumb_base_public_id:  str     | None = None,
) -> dict:
    """
    Build the complete nested payload for one course.
    """
    # pick up defaults vs overrides
    tool_list    = tool       if tool       is not None else [DEFAULT_TOOL]
    instr_list   = instructor if instructor is not None else DEFAULT_INSTRUCTOR
    insti_list   = institute  if institute  is not None else DEFAULT_INSTITUTE
    tags_list    = tags       if tags       is not None else DEFAULT_TAGS
    template_str = template   if template   is not None else DEFAULT_TEMPLATE

    logo_id   = logo_public_id        or DEFAULT_LOGO_PUBLIC_ID
    fanart_id = fanart_public_id      or DEFAULT_FANART_PUBLIC_ID
    poster_id = poster_base_public_id or DEFAULT_POSTER_BASE_PUBLIC_ID
    thumb_id  = thumb_base_public_id  or DEFAULT_THUMB_BASE_PUBLIC_ID

    # load & name chapters + attach lessons
    chap_list = load_chapters(chapters_csv, chapter_name_template)
    les_map   = load_lessons(lessons_csv)
    for chap in chap_list:
        chap["lessons"] = les_map.get(chap["index"], [])

    # assemble course
    course = {
      "id": None, "icon": None, "cover": None,
      "name":           course_name,
      "tool":           tool_list,
      "description":    course_desc,
      "logo_public_id":   logo_id,
      "fanart_public_id": fanart_id,
      "poster_base_id":   poster_id,
      "thumb_base_id":    thumb_id,
      "link":           intro_link,
      "instructor":     instr_list,
      "institute":      insti_list,
      "tags":           tags_list,
      "template":       template_str,
      "chapters":       chap_list
    }

    # render via Jinja
    tm       = TemplateManager(templates_dir)
    tpl_path = tm.get_template_path("rebelway", "default")
    env      = Environment(
      loader=FileSystemLoader(str(templates_dir)),
      trim_blocks=True, lstrip_blocks=True,
    )
    tpl      = env.get_template(tpl_path.name)
    rendered = tpl.render(courses=[course])
    return json.loads(rendered)
