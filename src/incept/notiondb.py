# src/incept/notiondb.py

import os
import json
from pathlib import Path
from notionmanager.notion import NotionManager

# Default mapping file location
mapping_file_path = Path.home() / ".incept" / "mapping" / "notion_mapping.json"

if mapping_file_path.exists():
    with open(mapping_file_path, 'r') as f:
        mapping = json.load(f)
    forward_mapping = mapping.get("forward_mapping", {})
    back_mapping = mapping.get("back_mapping", {})
    hierarchy_config = mapping.get("hierarchy_config", {})
    DEFAULT_ICON_URL = mapping.get("default_icon", {}).get("external", {}).get("url",
                          "https://www.notion.so/icons/graduate_lightgray.svg")
    DEFAULT_COVER_URL = mapping.get("default_cover", {}).get("external", {}).get("url",
                          "https://res.cloudinary.com/dicttuyma/image/upload/w_1500,h_600,c_fill,g_auto/v1742094799/banner/notion_21.jpg")
else:
    forward_mapping = {
        "id": {"target": "id", "return": "str"},
        "icon": {"target": "icon", "return": "object"},
        "cover": {"target": "cover", "return": "object"},
        "Name": {"target": "name", "type": "title", "return": "str"},
        "Tool": {"target": "tool", "type": "relation", "return": "list"},
        "Type": {"target": "type", "type": "select", "return": "list"},
        "Course Description": {"target": "description", "type": "rich_text", "return": "str"},
        "Course Link": {"target": "link", "type": "url", "return": "str"},
        "Instructor": {"target": "instructor", "type": "select", "return": "list"},
        "Institute": {"target":"institute", "type":"select", "return":"list"},
        "Path": {"target": "path", "type": "rich_text", "return": "str"},
        "Template": {"target": "template", "type": "rich_text", "return": "str", "default": "default"},
        "Tags": {"target": "tags", "type": "multi_select", "return": "list"},
        "Status": {"target": "status",     "type": "status",    "return": "str"},
        "Video": {"target": "video", "type": "checkbox", "return": "boolean"},
        "Video Path": {"target": "video_path", "type": "rich_text", "return": "str"}
    }
    back_mapping = {
        "icon": {"target": "icon", "return": "object"},
        "cover": {"target": "cover", "return": "object"},
        "name": {"target": "Name", "type": "title", "return": "str"},
        "tool": {"target": "Tool", "type": "relation", "return": "list", "default": ["149a1865-b187-80f9-b21f-c9c96430bf62"]},
        "type": {"target": "Type", "type": "select", "return": "list"},
        "description": {"target": "Course Description", "type": "rich_text", "return": "str"},
        "link": {"target": "Course Link", "type": "url", "return": "str"},
        "instructor": {"target": "Instructor", "type": "select", "return": "list"},
        "institute": {"target":"Institute", "type":"select", "return":"list"},
        "path": {"target": "Path", "type": "rich_text", "return": "str", "code": True},
        "template": {"target": "Template", "type": "rich_text", "return": "str", "code": True},
        "tags": {"target": "Tags", "type": "multi_select", "return": "list", "default": ["Python"]},
        "status": {"target": "Status", "type": "status",    "return": "str", "default": "Not started"},
        "video": {"target": "Video", "type": "checkbox", "return": "boolean"},
        "video_path": {"target": "Video Path", "type": "rich_text", "return": "str", "code": True}
    }
    hierarchy_config = {
        "root": "courses",
        "level_1": "chapters",
        "level_2": "lessons"
    }
    DEFAULT_ICON_URL = "https://www.notion.so/icons/graduate_lightgray.svg"
    DEFAULT_COVER_URL = "https://res.cloudinary.com/dicttuyma/image/upload/w_1500,h_600,c_fill,g_auto/v1742094799/banner/notion_21.jpg"



class NotionDB:

    def __init__(self, api_key, database_id, mapping_config: dict = None):
        """
        Wrapper around NotionManager for handling Notion database interactions.
        Optionally accepts a mapping_config dict. If not provided, the fallback/global
        forward_mapping, back_mapping, and hierarchy_config will be used.
        """
        self.notion = NotionManager(api_key, database_id)
        self.database_id = database_id

        if mapping_config:
            self.forward_mapping = mapping_config.get("forward_mapping", forward_mapping)
            self.back_mapping = mapping_config.get("back_mapping", back_mapping)
            self.hierarchy_config = mapping_config.get("hierarchy_config", hierarchy_config)
        else:
            self.forward_mapping = forward_mapping
            self.back_mapping = back_mapping
            self.hierarchy_config = hierarchy_config

    def _extract_relation(self, properties, relation_property):
        """
        Helper to extract a list of relation IDs from a given Notion property.
        """
        relation = properties.get(relation_property, {})
        if relation and "relation" in relation:
            return [rel.get("id") for rel in relation["relation"]]
        return []

    def get_courses(self, **kwargs):
        """
        Fetch courses (and their chapters/lessons) from Notion and return a hierarchical
        nested object (instead of a DataFrame).

        If no filter is provided, all pages are fetched.
        If a filter is provided (e.g., Name="Sample Course"), only matching courses and
        their children are fetched recursively.

        Returns:
          dict: A dictionary with a key (e.g., "courses") containing a list of course objects,
                each with nested chapters and lessons.
        """
        properties_mapping = self.forward_mapping
        config = self.hierarchy_config

        # Build filter payload if a "Name" filter is provided.
        filter_payload = None
        if "Name" in kwargs:
            if isinstance(kwargs["Name"], dict):
                filter_payload = kwargs["Name"]
            else:
                filter_payload = {
                    "filter": {
                        "property": "Name",
                        "title": {"equals": kwargs["Name"]}
                    }
                }

        if not filter_payload:
            notion_data = self.notion.get_pages(retrieve_all=True)
            if not notion_data:
                return {config.get("root", "courses"): []}
            courses_hierarchy = self.notion.build_hierarchy(notion_data, config, properties_mapping)
            return courses_hierarchy
        else:
            filtered_courses = self.notion.get_pages(**filter_payload)
            if not filtered_courses:
                return {config.get("root", "courses"): []}

            visited_pages = {}

            def fetch_children(page_id):
                if page_id in visited_pages:
                    return
                page = self.notion.get_page(page_id)
                visited_pages[page_id] = page
                sub_item_ids = self._extract_relation(page.get("properties", {}), "Sub-item")
                for child_id in sub_item_ids:
                    fetch_children(child_id)

            for course_page in filtered_courses:
                fetch_children(course_page["id"])

            notion_data = list(visited_pages.values())
            courses_hierarchy = self.notion.build_hierarchy(notion_data, config, properties_mapping)
            return courses_hierarchy


    def get_course(self, course_id):
        """
        Fetch a single course (by page_id), including its chapters and lessons,
        and return the hierarchical structure as a nested dictionary.
        """
        visited_pages = {}

        def fetch_children(page_id):
            if page_id in visited_pages:
                return
            page = self.notion.get_page(page_id)
            visited_pages[page_id] = page
            sub_item_ids = self._extract_relation(page.get("properties", {}), "Sub-item")
            for child_id in sub_item_ids:
                fetch_children(child_id)

        fetch_children(course_id)
        notion_data = list(visited_pages.values())

        properties_mapping = self.forward_mapping
        config = self.hierarchy_config

        courses_hierarchy = self.notion.build_hierarchy(notion_data, config, properties_mapping)
        root_key = config.get("root", "courses")
        if courses_hierarchy and root_key in courses_hierarchy:
            filtered = [course for course in courses_hierarchy[root_key] if course.get("id") == course_id]
            return {root_key: filtered} if filtered else {}
        return courses_hierarchy


    def insert_page(self, flat_object, back_mapping, forward_mapping, parent_item=None, parent_icon=None, parent_cover=None, child_key=None):
        """
        Insert a new page (e.g., a course, chapter, or lesson) into Notion.
        This function is generic and can also insert any nested child items if a child_key is provided.

        Parameters:
          - flat_object (dict or list): The processed internal object(s) to insert.
          - back_mapping (dict): Mapping configuration for converting the flat object to a Notion payload.
          - forward_mapping (dict): Mapping configuration to transform the returned Notion page back to internal format.
          - parent_item (dict, optional): The parent page as a dictionary. If provided, its "id", "icon", and "cover" will be used.
          - parent_icon (optional): Icon URL or object to use if flat_object lacks one.
          - parent_cover (optional): Cover URL or object to use if flat_object lacks one.
          - child_key (str, optional): If provided, the key in flat_object that holds child pages (a dict or list) to insert recursively.

        Workflow:
          1. If flat_object is a list, iterate over its items.
          2. If parent_item is a dict, extract its "id", "icon", and "cover" as defaults.
          3. Ensure "icon" and "cover" are present in flat_object.
          4. Build the payload via NotionManager's build_notion_payload().
          5. If a parent ID is available, append a "Parent item" relation.
          6. Call notion.add_page(payload) and transform the returned page.
          7. If child_key is provided and exists in flat_object, iterate over its items (or a single dict) recursively.
          8. Return the transformed page with nested children.
        """
        # If flat_object is a list, iterate over each item.
        if isinstance(flat_object, list):
            inserted_list = []
            for item in flat_object:
                inserted_item = self.insert_page(item, back_mapping, forward_mapping, parent_item, parent_icon, parent_cover, child_key)
                inserted_list.append(inserted_item)
            return inserted_list

        # flat_object is a dict.
        # If parent_item is provided as a dict, extract its id, icon, and cover.
        parent_item_id = None
        if parent_item and isinstance(parent_item, dict):
            parent_item_id = parent_item.get("id")
            if not parent_icon:
                parent_icon = parent_item.get("icon")
            if not parent_cover:
                parent_cover = parent_item.get("cover")
        elif parent_item:
            # If parent_item is not a dict, assume it's a string (ID).
            parent_item_id = parent_item

        # Ensure icon and cover in flat_object.
        if not flat_object.get("icon"):
            flat_object["icon"] = parent_icon if parent_icon else DEFAULT_ICON_URL
        if not flat_object.get("cover"):
            flat_object["cover"] = parent_cover if parent_cover else DEFAULT_COVER_URL

        # Build payload using NotionManager's build_notion_payload().
        payload = self.notion.build_notion_payload(flat_object, back_mapping)


        # Append "Parent item" relation if a parent_item_id is available.
        if parent_item_id:
            parent_relation = {
                "type": "relation",
                "relation": [{"id": parent_item_id}],
                "has_more": False
            }
            if "properties" not in payload:
                payload["properties"] = {}
            payload["properties"]["Parent item"] = parent_relation


        # Insert the page.
        new_page = self.notion.add_page(payload)
        # Transform the returned page.
        transformed_page = self.notion.transform_page(new_page, forward_mapping)

        # If a child_key is provided and exists in flat_object, recursively insert its children.
        if child_key and flat_object.get(child_key):
            children = flat_object[child_key]
            if isinstance(children, list):
                inserted_children = []
                for child in children:
                    inserted_child = self.insert_page(child, back_mapping, forward_mapping, parent_item=transformed_page)
                    inserted_children.append(inserted_child)
                transformed_page[child_key] = inserted_children
            elif isinstance(children, dict):
                transformed_page[child_key] = self.insert_page(children, back_mapping, forward_mapping, parent_item=transformed_page)
        return transformed_page


if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv

    # Load environment variables from the .env file located in the same directory.
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=env_path)

    # Retrieve credentials from environment variables.
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_COURSE_DATABASE_ID = os.getenv("NOTION_COURSE_DATABASE_ID")

    if NOTION_API_KEY and NOTION_COURSE_DATABASE_ID:
        # Initialize NotionDB.
        notion_db = NotionDB(api_key=NOTION_API_KEY, database_id=NOTION_COURSE_DATABASE_ID)
    else:
        print("Missing Notion credentials in the .env file.")
        exit(1)  # Exit if credentials are missing.

    def test_get_courses():
        # Fetch courses hierarchy without any filter.
        courses_hierarchy = notion_db.get_courses()
        print("Courses Hierarchy:")
        print(json.dumps(courses_hierarchy, indent=2))

    def test_insert_lessons(notion_db):
        # Assume the payload file is at $HOME/.incept/payload/lessons.json
        payload_file = os.path.join(os.path.expanduser("~"), ".incept", "payload", "ml_test_payload.json")
        if not os.path.exists(payload_file):
            print(f"Payload file not found: {payload_file}")
            return

        with open(payload_file, "r") as f:
            payload_data = json.load(f)

        # For testing, assume we want to insert lessons for the first course and first chapter.
        try:
            course = payload_data["courses"][0]         # a dict
            chapter = course["chapters"][0]               # a dict
            lessons = chapter.get("lessons")              # a list (or dict) of lessons
        except (KeyError, IndexError):
            print("Invalid payload structure.")
            return

        # Ensure each lesson has a "type": ["Lesson"] field.
        if isinstance(lessons, list):
            for lesson in lessons:
                lesson["type"] = ["Lesson"]
        elif isinstance(lessons, dict):
            lessons["type"] = ["Lesson"]

        # Use the default back and forward mappings from the NotionDB instance.
        lesson_back_mapping = notion_db.back_mapping
        lesson_forward_mapping = notion_db.forward_mapping

        # Use the parent chapter as a dict so that its id (and optionally icon/cover) are used.
        parent_chapter = chapter
        parent_chapter_id = parent_chapter.get("id")
        if not parent_chapter_id:
            print("Parent chapter ID is missing in payload. Cannot insert lessons.")
            return

        # Insert lessons (flat_object is a list of lessons) and specify child_key="lessons".
        inserted_lessons = notion_db.insert_page(
            flat_object=lessons,
            back_mapping=lesson_back_mapping,
            forward_mapping=lesson_forward_mapping,
            parent_item=parent_chapter,  # Pass the whole dict.
            child_key="lessons"
        )
        print("Inserted Lessons:")
        print(json.dumps(inserted_lessons, indent=2))

    # Uncomment to test courses hierarchy.
    # test_get_courses()
    test_insert_lessons(notion_db)
    
