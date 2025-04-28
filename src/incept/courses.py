# src/incept/courses.py

import os
import re
import copy
from pathlib import Path
from incept.dbfactory import get_db_client
from incept.utils import create_lessons, create_chapters, create_courses, expand_or_preserve_env_vars

DEFAULT_DB = "notion"
CONFIG_DIR = Path.home() / ".incept"
ENV_FILE = CONFIG_DIR / ".env"


def getCourses(db=DEFAULT_DB, filter=None, **kwargs):
    """
    Retrieve courses from the specified DB client.
    
    If a filter is provided (e.g., a course name), only matching courses
    and their children are fetched recursively.
    
    Returns:
      dict: A nested dictionary (e.g. {"courses": [...]}) built using NotionDB.
    """
    db_client = get_db_client(db, **kwargs)
    if filter:
        return db_client.get_courses(Name=filter)
    else:
        return db_client.get_courses()

def addCourses(payload_data: dict, templates_dir: Path, db=DEFAULT_DB, include_video: bool = False, **kwargs):
    """
    Add one or more courses (including their chapters and lessons) to Notion.
    The payload_data is expected to follow your standard internal format, e.g.:
      {
        "courses": [
          {
            "id": null,
            "name": "Sample Course A",
            "path": "...",  (optional - if missing, we assign one from environment)
            "chapters": [
              {
                "id": null,
                "name": "Chapter X",
                "lessons": [
                  {
                    "id": null,
                    "name": "Lesson 1"
                  },
                  ...
                ]
              },
              ...
            ]
          },
          ...
        ]
      }
    Steps:
      1) Fetch all existing courses from Notion (getCourses with no filter).
      2) For each course in payload_data["courses"]:
         a) Check if that course name already exists in Notion -> skip.
         b) Ensure "path" is defined (fallback to $COURSE_FOLDER_PATH or ~Documents).
         c) Call create_courses([thatCourse]) to build local folder structure (course/chapters/lessons).
         d) Insert the course as a Notion page (no "parent_item" or a known workspace parent if you prefer).
         e) Inline: for each new chapter, insert it as a sub-page; for each lesson in that chapter, insert it as a sub-sub-page.
      3) Return the list of newly inserted courses (with updated 'id', etc.).
    """
    db_client = get_db_client(db, **kwargs)

    # 1) Fetch all existing courses from Notion (with no filter).
    existing_hierarchy = getCourses(db=db, **kwargs)  # no filter => returns all courses
    existing_courses = existing_hierarchy.get("courses", [])
    existing_course_names = {c.get("name") for c in existing_courses if c.get("name")}

    # We'll store newly inserted courses in a list.
    inserted_courses = []

    # Define back/forward mappings for the "course" entity.
    course_back_mapping = db_client.back_mapping
    course_forward_mapping = db_client.forward_mapping

    # Define minimal inline mappings for chapters & lessons.
    chapter_back_mapping = db_client.back_mapping
    chapter_forward_mapping = db_client.forward_mapping
    lesson_back_mapping = db_client.back_mapping
    lesson_forward_mapping = db_client.forward_mapping

    def insert_lesson_inline(lesson_dict: dict, parent_chapter: dict):
        # Carry the video flag into the lesson
        lesson_dict["video"] = include_video
        # Ensure video_path is set or NA
        lesson_dict["video_path"] = lesson_dict.get("video_path") if include_video else "NA"
        # Set lesson type.
        lesson_dict["type"] = ["Lesson"]
        inserted_lesson = db_client.insert_page(
            flat_object=lesson_dict,
            back_mapping=lesson_back_mapping,
            forward_mapping=lesson_forward_mapping,
            parent_item=parent_chapter,
            child_key="lessons"
        )
        lesson_dict["id"] = inserted_lesson.get("id")
        return inserted_lesson

    def insert_chapter_inline(chapter_dict: dict, parent_course: dict):
        # Carry the video flag into the chapter
        chapter_dict["video"] = include_video
        # Ensure video_path is set or NA
        chapter_dict["video_path"] = chapter_dict.get("video_path") if include_video else "NA"
        # Set chapter type.
        chapter_dict["type"] = ["Chapter"]
        inserted_chapter = db_client.insert_page(
            flat_object=chapter_dict,
            back_mapping=chapter_back_mapping,
            forward_mapping=chapter_forward_mapping,
            parent_item=parent_course,
            child_key="chapters"
        )
        chapter_dict["id"] = inserted_chapter.get("id")
        # If the chapter has lessons, insert them inline.
        lessons = chapter_dict.get("lessons", [])
        if isinstance(lessons, dict):
            lessons = [lessons]
        for lesson_dict in lessons:
            insert_lesson_inline(lesson_dict, inserted_chapter)
        return inserted_chapter

    # 2) Loop over courses in payload_data["courses"].
    local_courses = payload_data.get("courses", [])
    if isinstance(local_courses, dict):
        local_courses = [local_courses]

    for local_course in local_courses:
        course_name = local_course.get("name")
        if not course_name:
            print("Skipping a course that has no 'name' field.")
            continue

        # Set course type.
        local_course["type"] = ["Course"]

        # 2a) If course_name is already in existing_course_names, skip.
        if course_name in existing_course_names:
            print(f"Course '{course_name}' already exists; skipping insertion.")
            continue

        # 2b) Ensure "path" is defined (fallback to $COURSE_FOLDER_PATH or ~/Documents).
        if "path" not in local_course or not local_course["path"]:
            env_course_folder = os.environ.get("COURSE_FOLDER_PATH")
            if env_course_folder and os.path.isdir(os.path.expandvars(env_course_folder)):
                local_course["path"] = env_course_folder
            else:
                local_course["path"] = str(Path.home() / "Documents")

        # 2c) Create local folders.
        create_courses(
            courses=[local_course],
            templates_dir=templates_dir,
            create_folders=True,
            keep_env_in_path=True,
            parent_path=None, # let create_courses handle the parent's logic
            include_video=include_video
        )
        # Ensure course-level video_path is set or NA
        if not include_video:
            local_course["video_path"] = "NA"

        # 2d) Make sure the `video` flag is carried into Notion
        local_course["video"] = include_video
        inserted_course = db_client.insert_page(
            flat_object=local_course,
            back_mapping=course_back_mapping,
            forward_mapping=course_forward_mapping,
            parent_item=None,  # or pass a workspace-level parent if your schema requires it
            child_key="courses"
        )
        local_course["id"] = inserted_course.get("id")  # record the new ID
        inserted_courses.append(inserted_course)
        existing_course_names.add(course_name)

        # 2e) Now insert the chapters (and their lessons) inline.
        local_chapters = local_course.get("chapters", [])
        if isinstance(local_chapters, dict):
            local_chapters = [local_chapters]
        for local_chapter in local_chapters:
            insert_chapter_inline(local_chapter, inserted_course)

    return inserted_courses


def addChapters(payload_data: dict,
               course_filter: str,
               templates_dir: Path,
               db=DEFAULT_DB,
               include_video: bool = False,
               **kwargs):
    """
    Add one or more chapters (and optionally lessons) to a single course in Notion.
    The payload_data is expected to follow the standard internal format:
      {
        "courses": [
          {
            "id": ...,
            "name": "Some Course Name",
            "chapters": [
              {
                "id": null,
                "name": "Sample Chapter",
                "lessons": [ ... ],
                ...
              },
              ...
            ]
          }
        ]
      }
    Steps:
      1) Extract the first course from payload_data.
      2) Fetch that course from Notion using getCourses(filter=course_filter).
      3) For each chapter in payload_data's "chapters":
         a) Check if it already exists by name in the Notion-fetched course -> skip if duplicate.
         b) Create local folders (via create_chapters).
         c) Insert the new chapter as a Notion page (parent = the course).
         d) If the chapter has lessons, insert them in-line.
      4) Return the list of newly inserted chapters (with updated 'id', 'path', etc.).
    """
    db_client = get_db_client(db, **kwargs)

    # 1) Extract the first course from payload_data.
    try:
        local_course = payload_data["courses"][0]  # We'll handle the first course only.
    except (KeyError, IndexError):
        raise Exception("Payload must have at least one course in 'courses' list.")

    local_course_name = local_course.get("name")
    if not local_course_name:
        raise Exception("Local course object must have a 'name' field.")

    # 2) Fetch the course from Notion using getCourses (with course_filter).
    #    We assume course_filter matches local_course_name (or something similar).
    courses_hierarchy = getCourses(db=db, filter=course_filter, **kwargs)
    if not courses_hierarchy or "courses" not in courses_hierarchy or not courses_hierarchy["courses"]:
        raise Exception(f"Course not found in Notion using filter='{course_filter}'.")

    notion_course = courses_hierarchy["courses"][0]

    # Check that the Notion course also has a valid path for folder creation.
    notion_course_path = notion_course.get("path")
    if not notion_course_path:
        raise Exception("Target course in Notion does not have a valid 'path' field.")

    # Build a set of existing chapter names to detect duplicates quickly.
    existing_chapter_names = {ch.get("name") for ch in notion_course.get("chapters", []) if ch.get("name")}

    # We store newly inserted chapters for returning later.
    inserted_chapters = []

    # --- We'll define the back/forward mappings for 'chapter' insertion in Notion. ---
    chapter_back_mapping = db_client.back_mapping
    chapter_forward_mapping = db_client.forward_mapping

    # --- We'll define minimal inline mappings for lessons. ---
    lesson_back_mapping = db_client.back_mapping
    lesson_forward_mapping = db_client.forward_mapping

    # Inline helper to insert a lesson under a newly inserted chapter.
    def insert_lesson_inline(lesson_dict: dict, parent_chapter: dict):
        # Carry the video flag into the lesson
        lesson_dict["video"] = include_video
        # Ensure video_path is set or NA
        lesson_dict["video_path"] = lesson_dict.get("video_path") if include_video else "NA"
        # Ensure the lesson payload has the correct type.
        lesson_dict["type"] = ["Lesson"]
        inserted_lesson = db_client.insert_page(
            flat_object=lesson_dict,
            back_mapping=lesson_back_mapping,
            forward_mapping=lesson_forward_mapping,
            parent_item=parent_chapter,  # The newly inserted chapter is the parent.
            child_key="lessons"
        )
        # Update local lesson's 'id'
        lesson_dict["id"] = inserted_lesson.get("id")
        return inserted_lesson

    # 3) Loop over local_course["chapters"] in the payload.
    local_chapters = local_course.get("chapters", [])
    if isinstance(local_chapters, dict):
        local_chapters = [local_chapters]

    for chapter_payload in local_chapters:
        chapter_name = chapter_payload.get("name")
        if not chapter_name:
            print("Skipping a chapter that has no 'name'.")
            continue

        # Set the chapter type to "Chapter"
        chapter_payload["type"] = ["Chapter"]

        # 3a) Check if it already exists.
        if chapter_name in existing_chapter_names:
            print(f"Chapter '{chapter_name}' already exists; skipping insertion.")
            continue

        # 3b) Create local folders (chapter + lessons) by calling create_chapters on a single chapter.
        # ---------- TEXT hierarchy (always) ----------
        create_chapters(
            chapters        = [chapter_payload],
            templates_dir   = templates_dir,
            create_folders  = True,
            keep_env_in_path= True,
            parent_path     = notion_course_path,
            include_video   = False,
            parent_course_template_variant = notion_course.get("template", "default"),
            parent_child_folder_name       = notion_course.get("child_folder_name"),
        )
        
        # ---------- VIDEO hierarchy (optional) ----------
        if include_video:
            video_parent = notion_course.get("video_path")
            if not video_parent:
                raise Exception(
                    "Course was never created with --include-video; no 'video_path' to attach seasons under."
                )
        
            video_chap = copy.deepcopy(chapter_payload)
            # carry course-level artwork & titles so image dispatch works
            video_chap.update({
                "logo_public_id":   notion_course.get("logo_public_id"),
                "fanart_public_id": notion_course.get("fanart_public_id"),
                "poster_base_id":   notion_course.get("poster_base_id"),
                "thumb_base_id":    notion_course.get("thumb_base_id"),
                "course_title":     notion_course.get("name"),
                "instructor":       ", ".join(notion_course.get("instructor", [])),
            })
        
            create_chapters(
                chapters        = [video_chap],
                templates_dir   = templates_dir,
                create_folders  = True,
                keep_env_in_path= True,
                parent_path     = video_parent,      # <-- correct root
                include_video   = True,
            )
        
            # bubble the season path back so Notion gets it
            chapter_payload["video_path"] = video_chap.get("video_path")

            # ─── copy episode paths (works for list *or* single-dict) ──────────
            orig_ls_list = chapter_payload.get("lessons", [])
            if isinstance(orig_ls_list, dict):
                orig_ls_list = [orig_ls_list]
            
            vid_ls_list = video_chap.get("lessons", [])
            if isinstance(vid_ls_list, dict):
                vid_ls_list = [vid_ls_list]
            
            for orig_ls, vid_ls in zip(orig_ls_list, vid_ls_list):
                orig_ls["video_path"] = vid_ls.get("video_path")
            # ───────────────────────────────────────────────────────────────────

        # make sure the column is *always* present
        if "video_path" not in chapter_payload:
            chapter_payload["video_path"] = "NA"

        # 3c) Carry the video flag into chapter (if desired)
        chapter_payload["video"] = include_video

        # 3d) Insert the new chapter as a Notion page.
        inserted_chapter = db_client.insert_page(
            flat_object=chapter_payload,
            back_mapping=chapter_back_mapping,
            forward_mapping=chapter_forward_mapping,
            parent_item=notion_course,  # The Notion-fetched course is the parent.
            child_key="chapters"
        )
        chapter_payload["id"] = inserted_chapter.get("id")  # Record the new ID.
        inserted_chapters.append(inserted_chapter)
        existing_chapter_names.add(chapter_name)

        # 3d) If the chapter has lessons, insert them inline.
        lessons = chapter_payload.get("lessons")
        if lessons:
            if isinstance(lessons, dict):
                lessons = [lessons]
            # before inserting lessons, ensure each one has video_path
            if not include_video:
                for ls in lessons:
                    ls["video_path"] = "NA"

            for lesson_dict in lessons:
                insert_lesson_inline(lesson_dict, inserted_chapter)

    # 4) Return the newly inserted chapters.
    return inserted_chapters


def addLessons(lesson_payload: dict, course_filter: str, templates_dir: Path, db=DEFAULT_DB, include_video: bool = False, **kwargs):
    """
    Add a lesson to a course in Notion.
    
    Steps:
      1. Fetch the course (with its chapters and lessons) using getCourses(filter=course_filter).
      2. Identify the target chapter where the lesson should be added (using lesson_payload["chapter_name"]).
      3. Check if a lesson with the same name already exists; if yes, skip insertion.
      4. Otherwise, call create_lessons to build the folder structure.
      5. Update the lesson payload with the new "path" (and other info as needed).
      6. Insert the lesson as a new page in Notion using the DB client defaults.
      7. Return the inserted lesson object.
    """
    # 1. Get the course from Notion.
    courses_hierarchy = getCourses(db=db, filter=course_filter, **kwargs)
    if not courses_hierarchy or "courses" not in courses_hierarchy or not courses_hierarchy["courses"]:
        raise Exception("Course not found using filter: " + course_filter)
    
    # For simplicity, assume the first course is the target.
    course = courses_hierarchy["courses"][0]
    
    # 2. Identify the target chapter.
    # We expect the lesson_payload to include a "chapter_name" key.
    target_chapter_name = lesson_payload.get("chapter_name")
    if not target_chapter_name:
        raise Exception("Lesson payload must include a 'chapter_name' field.")
    
    target_chapter = None
    for chapter in course.get("chapters", []):
        if chapter.get("name") == target_chapter_name:
            target_chapter = chapter
            break
    if not target_chapter:
        raise Exception(f"Chapter '{target_chapter_name}' not found in course '{course.get('name')}'.")
    
    # 3. Check if a lesson with the same name already exists in the target chapter.
    lesson_name = lesson_payload.get("name")
    for existing in target_chapter.get("lessons", []):
        if existing.get("name") == lesson_name:
            print(f"Lesson '{lesson_name}' already exists; skipping insertion.")
            return existing  # or return a status/message
    
    # ----------------------------------------------------------
    # 4.  Book-keeping fields expected by Notion
    # ----------------------------------------------------------
    lesson_payload["type"]  = ["Lesson"]
    lesson_payload["video"] = include_video

    # -----------------------------------------------------------
    #  Gather chapter-template metadata so the lesson helper
    #  can decide whether to add a sub-folder or not.
    # -----------------------------------------------------------
    chap_variant      = target_chapter.get("template", "default")
    chap_child_folder = target_chapter.get("child_folder_name")

    # --- TEXT hierarchy (always) -------------------------------
    create_lessons(
        lessons=[lesson_payload],
        templates_dir=templates_dir,
        create_folders=True,
        keep_env_in_path=True,
        include_video=False,                      # <- text first
        parent_path=target_chapter["path"],
        parent_chapter_template_variant=chap_variant,
        parent_child_folder_name=chap_child_folder,
    )
    text_path = lesson_payload["path"]           # now guaranteed

    # --- VIDEO hierarchy (optional) ----------------------------
    if include_video:
        video_copy = copy.deepcopy(lesson_payload)
        create_lessons(
            lessons=[video_copy],
            templates_dir=templates_dir,
            create_folders=True,
            keep_env_in_path=True,
            include_video=True,                  # <- build episode
            parent_path=target_chapter["video_path"],
            parent_chapter_template_variant=target_chapter.get("template", "video"),
            parent_child_folder_name="",               # seasons never want an extra bucket
        )
        lesson_payload["video_path"] = video_copy["video_path"]
    else:
        lesson_payload["video_path"] = "NA"
    
    # 6. Insert the lesson into Notion.
    # Get the DB client (assumed to be an instance of NotionDB) with its loaded mappings.
    db_client = get_db_client(db, **kwargs)
    inserted_lesson = db_client.insert_page(
        flat_object=lesson_payload,
        back_mapping=db_client.back_mapping,       # Use default back mapping
        forward_mapping=db_client.forward_mapping,   # Use default forward mapping
        parent_item=target_chapter,                    # Use target chapter as parent
        child_key="lessons"
    )
    
    # 7. Return the inserted lesson.
    return inserted_lesson
    

if __name__ == "__main__":
    import os, json
    from pathlib import Path
    from dotenv import load_dotenv

    raw_templates_dir = os.environ.get("JINJA_TEMPLATES_PATH", str(Path.home() / ".incept" / "templates"))
    templates_dir = Path(os.path.expandvars(raw_templates_dir)).expanduser()

    # Retrieve Notion credentials from environment variables.
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_COURSE_DATABASE_ID = os.getenv("NOTION_COURSE_DATABASE_ID")

    def test_add_lessons():
    
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "lessons.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return
    
        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)
    
        try:
            # Extract the first course and its first chapter.
            course = payload_data["courses"][0]
            chapter = course["chapters"][0]
            lessons = chapter.get("lessons", [])
            # If lessons is a dict, convert it to a list.
            if isinstance(lessons, dict):
                lessons = [lessons]
            # Add the chapter name to each lesson.
            for lesson in lessons:
                lesson["chapter_name"] = chapter["name"]
        except (KeyError, IndexError) as e:
            print("Invalid payload structure:", e)
            return
    
        # Use the course name as a filter.
        course_filter = course.get("name")
    
        # Insert each lesson by calling addLessons.
        inserted_lessons = []
        for lesson_payload in lessons:
            inserted = addLessons(
                lesson_payload,
                course_filter,
                templates_dir=templates_dir,
                api_key=os.getenv("NOTION_API_KEY"),
                database_id=os.getenv("NOTION_COURSE_DATABASE_ID")
            )
            inserted_lessons.append(inserted)
    
        print("Inserted Lessons:")
        print(json.dumps(inserted_lessons, indent=2))

    def test_add_chapters():
       payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "chapters.json")
       if not os.path.exists(payload_file):
           print(f"Payload file not found: {payload_file}")
           return

       with open(payload_file, "r", encoding="utf-8") as f:
           payload_data = json.load(f)

       try:
           # Extract the first course and its chapters.
           course = payload_data["courses"][0]
           chapters = course.get("chapters", [])
           # Standardize chapters to always be a list.
           if isinstance(chapters, dict):
               chapters = [chapters]
       except (KeyError, IndexError) as e:
           print("Invalid payload structure:", e)
           return

       # Use the course name as a filter.
       course_filter = course.get("name")
       if not course_filter:
           print("Course payload must include a 'name' field.")
           return

       # Call addChapters. This function processes the chapters payload, creates local folder structures,
       # inserts new chapters (skipping any duplicates), and if lessons exist within a chapter, inserts those too.
       inserted_chapters = addChapters(
           payload_data=payload_data,
           course_filter=course_filter,
           templates_dir=templates_dir,
           api_key=NOTION_API_KEY,
           database_id=NOTION_COURSE_DATABASE_ID
       )

       print("Inserted Chapters:")
       print(json.dumps(inserted_chapters, indent=2))

    def test_add_courses():
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "full_courses.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)

        # Ensure that "courses" is a list.
        courses = payload_data.get("courses", [])
        if isinstance(courses, dict):
            courses = [courses]
        payload_data["courses"] = courses

        # Call addCourses which will:
        #  1. Check for duplicate courses by name,
        #  2. Ensure each course has a defined "path" (falling back to COURSE_FOLDER_PATH or ~/Documents),
        #  3. Create local folder structure (course/chapters/lessons),
        #  4. Insert the course (and its chapters/lessons) as Notion pages.
        inserted_courses = addCourses(
            payload_data=payload_data,
            templates_dir=templates_dir,
            api_key=NOTION_API_KEY,
            database_id=NOTION_COURSE_DATABASE_ID
        )

        print("Inserted Courses:")
        print(json.dumps(inserted_courses, indent=2))

    def test_add_courses_with_video():
        """Create BOTH text and video hierarchies for all courses in cine_light.json."""
        payload_file = os.path.join(
            os.path.expanduser("~"),
            ".incept",
            "payload",
            "cine_light_subset.json",
        )
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        with open(payload_file, "r", encoding="utf-8") as f:
            payload_data = json.load(f)

        # Ensure that "courses" is a list
        courses = payload_data.get("courses", [])
        if isinstance(courses, dict):
            courses = [courses]
        payload_data["courses"] = courses
    
        # Call addCourses with include_video=True
        inserted_courses = addCourses(
            payload_data=payload_data,
            templates_dir=templates_dir,
            include_video=True,
            api_key=NOTION_API_KEY,
            database_id=NOTION_COURSE_DATABASE_ID
        )

        print("Inserted Courses with Video:")
        print(json.dumps(inserted_courses, indent=2))


    # Uncomment to test addCourses + video:
    test_add_courses_with_video()
  

    # Uncomment to test addLessons.
    # test_add_lessons()

    # Uncomment to test addChapter.
    # test_add_chapters()

    # Uncomment to test addCourses.
    # test_add_courses()
