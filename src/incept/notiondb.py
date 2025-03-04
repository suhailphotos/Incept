import os
import json
from notionmanager.notion import NotionManager

# Default icon/cover constants
DEFAULT_ICON_URL = "https://www.notion.so/icons/graduate_lightgray.svg"
DEFAULT_COVER_URL = "https://github.com/suhailphotos/notionUtils/blob/main/assets/media/banner/notion_style_banners_lgt_36.jpg?raw=true"

class NotionDB:
    def __init__(self, api_key, database_id):
        """Wrapper around NotionManager for handling Notion database interactions."""
        self.notion = NotionManager(api_key, database_id)
        self.database_id = database_id

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
        # Define the forward transformation mapping.
        properties_mapping = {
            "id": {"target": "id", "return": "str"},
            "icon": {"target": "icon", "return": "object"},
            "cover": {"target": "cover", "return": "object"},
            "Name": {"target": "name", "type": "title", "return": "str"},
            "Tool": {"target": "tool", "type": "relation", "return": "list"},
            "Type": {"target": "type", "type": "select", "return": "list"},
            "Course Description": {"target": "description", "type": "rich_text", "return": "str"},
            "Course Link": {"target": "link", "type": "url", "return": "str"},
            "Path": {"target": "path", "type": "rich_text", "return": "str"},
            "Template": {"target": "template", "type": "rich_text", "return": "str"},
            "Tags": {"target": "tags", "type": "multi_select", "return": "list"}
        }
        hierarchy_config = {
            "root": "courses",       # Top-level key for courses (level 0)
            "level_1": "chapters",     # Children of courses
            "level_2": "lessons"       # Children of chapters
        }

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
            # Scenario 1: No filter → Retrieve ALL pages
            notion_data = self.notion.get_pages(retrieve_all=True)
            if not notion_data:
                return {"courses": []}
            # Build and return the hierarchical structure.
            courses_hierarchy = self.notion.build_hierarchy(notion_data, hierarchy_config, properties_mapping)
            return courses_hierarchy
        else:
            # Scenario 2: Filter provided → Retrieve matching course(s) and recursively fetch children.
            filtered_courses = self.notion.get_pages(**filter_payload)
            if not filtered_courses:
                return {"courses": []}

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
            courses_hierarchy = self.notion.build_hierarchy(notion_data, hierarchy_config, properties_mapping)
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

        properties_mapping = {
            "id": {"target": "id", "return": "str"},
            "icon": {"target": "icon", "return": "object"},
            "cover": {"target": "cover", "return": "object"},
            "Name": {"target": "name", "type": "title", "return": "str"},
            "Tool": {"target": "tool", "type": "relation", "return": "list"},
            "Type": {"target": "type", "type": "select", "return": "list"},
            "Course Description": {"target": "description", "type": "rich_text", "return": "str"},
            "Course Link": {"target": "link", "type": "url", "return": "str"},
            "Path": {"target": "path", "type": "rich_text", "return": "str"},
            "Template": {"target": "template", "type": "rich_text", "return": "str"},
            "Tags": {"target": "tags", "type": "multi_select", "return": "list"}
        }
        hierarchy_config = {
            "root": "courses",
            "level_1": "chapters",
            "level_2": "lessons"
        }
        courses_hierarchy = self.notion.build_hierarchy(notion_data, hierarchy_config, properties_mapping)
        # Optionally filter down to just the course with course_id.
        if courses_hierarchy and "courses" in courses_hierarchy:
            filtered = [course for course in courses_hierarchy["courses"] if course.get("id") == course_id]
            return {"courses": filtered} if filtered else {}
        return courses_hierarchy

if __name__ == "__main__":
    import os
    import json
    from dotenv import load_dotenv

    # Load environment variables from the .env file located in the same directory.
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=env_path)

    # Retrieve credentials from environment variables.
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

    if NOTION_API_KEY and NOTION_DATABASE_ID:
        # Initialize NotionDB.
        notion_db = NotionDB(api_key=NOTION_API_KEY, database_id=NOTION_DATABASE_ID)

        # Fetch courses hierarchy without any filter.
        courses_hierarchy = notion_db.get_courses()

        print("Courses Hierarchy:")
        print(json.dumps(courses_hierarchy, indent=2))
    else:
        print("Missing Notion credentials in the .env file.")
