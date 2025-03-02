import pandas as pd
from notionmanager.notion import NotionManager

# Default icon/cover constants
DEFAULT_ICON_URL = "https://www.notion.so/icons/graduate_lightgray.svg"
DEFAULT_COVER_URL = "https://github.com/suhailphotos/notionUtils/blob/main/assets/media/banner/notion_style_banners_lgt_36.jpg?raw=true"

class NotionDB:
    def __init__(self, api_key, database_id):
        """Wrapper around NotionManager for handling Notion database interactions."""
        self.notion = NotionManager(api_key, database_id)
        self.database_id = database_id

    def get_courses(self, **kwargs):
        """
        Fetch courses (and their chapters/lessons) from Notion as a Pandas DataFrame.

        - If no filter is provided, fetch *all* pages (Courses, Chapters, Lessons).
        - If a filter is provided (e.g., Name="Sample Course"), only fetch
          the matching course(s) and their children recursively.
        """
        filter_payload = None

        if "Name" in kwargs:
            if isinstance(kwargs["Name"], dict):
                # Assume it's already a complete filter payload.
                filter_payload = kwargs["Name"]
            else:
                filter_payload = {
                    "filter": {
                        "property": "Name",
                        "title": {
                            "equals": kwargs["Name"]
                        }
                    }
                }

        if not filter_payload:
            # Scenario 1: No filter => Retrieve ALL pages in one go
            notion_data = self.notion.get_pages(retrieve_all=True)
            if not notion_data:
                return pd.DataFrame()
            return self._convert_to_dataframe(notion_data)
        else:
            # Scenario 2: Filter => Retrieve only the matching course(s), 
            # then recursively fetch children.
            filtered_courses = self.notion.get_pages(**filter_payload)
            if not filtered_courses:
                return pd.DataFrame()

            visited_pages = {}

            def fetch_children(page_id):
                """Recursive DFS to get all sub-items of a given page."""
                if page_id in visited_pages:
                    return
                page = self.notion.get_page(page_id)
                visited_pages[page_id] = page

                # Extract child page_ids from 'Sub-item' property
                sub_item_ids = self._extract_relation(page.get("properties", {}), "Sub-item")
                for child_id in sub_item_ids:
                    fetch_children(child_id)

            for course_page in filtered_courses:
                fetch_children(course_page["id"])

            notion_data = list(visited_pages.values())
            return self._convert_to_dataframe(notion_data)

    def get_course(self, course_id):
        """
        Fetch a single course (by page_id), including its chapters and lessons,
        and return a single-row DataFrame with the same rolled-up format.
        """
        visited_pages = {}

        def fetch_children(page_id):
            if page_id in visited_pages:
                return
            page = self.notion.get_page(page_id)
            visited_pages[page_id] = page

            # Recursively fetch any sub-items
            sub_item_ids = self._extract_relation(page.get("properties", {}), "Sub-item")
            for child_id in sub_item_ids:
                fetch_children(child_id)

        # 1) Recursively fetch the course + all its children
        fetch_children(course_id)
        notion_data = list(visited_pages.values())

        # 2) Convert to dataframe
        df = self._convert_to_dataframe(notion_data)

        # 3) Optionally filter down to just the course row
        #    (In theory, _convert_to_dataframe() only creates one "Course" row
        #     if the passed-in page is indeed a course.)
        if not df.empty:
            # Return the single row matching `course_id`
            return df[df["id"] == course_id].reset_index(drop=True)
        return pd.DataFrame()

    def insert_course(self, **kwargs):
        """
        Insert a new "Course" page into Notion using kwargs.

        - name (str) is required (for Title).
        - Optional fields: description, tags, cover, icon, course_link, path, etc.
        - If 'cover' or 'icon' is missing, we use the default external URL.
        - If 'cover'/'icon' is a string, we treat it as an external URL.
        - If 'cover'/'icon' is a dict, we use it directly as the Notion object.
        - 'Path' property is styled with code=True, color="default".
        """
        name = kwargs.get("name")
        if not name:
            raise ValueError("Missing required field: 'name'")

        # Basic Notion page structure
        notion_payload = {
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": name}}
                    ]
                },
                "Type": {
                    "select": {"name": "Course"}
                }
            }
        }

        # 1) Cover logic
        cover_val = kwargs.get("cover")
        if cover_val is None:
            # Use default external URL
            notion_payload["cover"] = {
                "type": "external",
                "external": {"url": DEFAULT_COVER_URL}
            }
        elif isinstance(cover_val, str):
            # Treat as an external URL
            notion_payload["cover"] = {
                "type": "external",
                "external": {"url": cover_val}
            }
        elif isinstance(cover_val, dict):
            # Assume this is already a valid Notion 'cover' object
            notion_payload["cover"] = cover_val

        # 2) Icon logic
        icon_val = kwargs.get("icon")
        if icon_val is None:
            # Default external icon
            notion_payload["icon"] = {
                "type": "external",
                "external": {"url": DEFAULT_ICON_URL}
            }
        elif isinstance(icon_val, str):
            # String => external URL
            notion_payload["icon"] = {
                "type": "external",
                "external": {"url": icon_val}
            }
        elif isinstance(icon_val, dict):
            # Already a Notion icon object
            notion_payload["icon"] = icon_val

        # 3) Additional properties
        desc = kwargs.get("description")
        if desc:
            notion_payload["properties"]["Course Description"] = {
                "rich_text": [{"text": {"content": desc}}]
            }

        tags = kwargs.get("tags")
        if tags:
            notion_payload["properties"]["Tags"] = {
                "multi_select": [{"name": t} for t in tags]
            }

        link = kwargs.get("course_link")
        if link:
            notion_payload["properties"]["Course Link"] = {"url": link}

        path_val = kwargs.get("path")
        if path_val:
            notion_payload["properties"]["Path"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": path_val},
                        "annotations": {
                            "code": True,
                            "color": "default"
                        }
                    }
                ]
            }

        # Post to Notion
        return self.notion.add_page(notion_payload)

    def update_course(self, course_id, data):
        """
        Placeholder method: Update an existing course.

        Currently no advanced logic, just a direct call to notion.
        """
        return self.notion.update_page(course_id, data)

    def delete_course(self, course_id):
        """
        Placeholder method: Delete (archive) a course.

        Currently just sets 'archived': True.
        """
        return self.notion.update_page(course_id, {"archived": True})

    def insert_chapter(self, course_id, data):
        """
        Placeholder: Insert a new chapter under a course.
        Currently a minimal direct pass to notion.
        """
        data["parent_course"] = course_id
        return self.notion.add_page(data)

    def insert_lesson(self, chapter_id, data):
        """
        Placeholder: Insert a new lesson under a chapter.
        Currently minimal logic.
        """
        data["parent_chapter"] = chapter_id
        return self.notion.add_page(data)

    def update_chapter(self, chapter_id, data):
        """
        Placeholder: Update a chapter.
        Currently a direct call to notion.
        """
        return self.notion.update_page(chapter_id, data)

    def update_lesson(self, lesson_id, data):
        """
        Placeholder: Update a lesson.
        Currently a direct call to notion.
        """
        return self.notion.update_page(lesson_id, data)

    def delete_chapter(self, chapter_id):
        """
        Placeholder: Delete (archive) a chapter.
        """
        return self.notion.update_page(chapter_id, {"archived": True})

    def delete_lesson(self, lesson_id):
        """
        Placeholder: Delete (archive) a lesson.
        """
        return self.notion.update_page(lesson_id, {"archived": True})

    def _convert_to_dataframe(self, notion_data):
        """
        Convert Notion API response into a structured DataFrame,
        with each course's chapters and lessons rolled up in the
        "chapters" column.
        """
        courses = {}
        chapters = {}
        lessons = {}
    
        # 1) Organize all pages by type
        for page in notion_data:
            properties = page.get("properties", {})
            page_id = page.get("id")
            page_type = self._extract_select(properties, "Type")
            parent_ids = self._extract_relation(properties, "Parent item")
            sub_items = self._extract_relation(properties, "Sub-item")
    
            icon_data = page.get("icon", {})
    
            entry = {
                "id": page_id,
                "name": self._extract_title(properties),
                "description": self._extract_rich_text(properties, "Course Description"),
                "tags": self._extract_multi_select(properties, "Tags"),
                "tool": self._extract_relation(properties, "Tool"),
                "course_link": properties.get("Course Link", {}).get("url"),
                "path": self._extract_rich_text(properties, "Path"),
                "url": page.get("url"),
                "cover": page.get("cover", {}),
                "icon": icon_data,
                "sub_items": sub_items,
                "parent_id": parent_ids[0] if parent_ids else None,
            }
    
            if page_type == "Course":
                courses[page_id] = {**entry, "chapters": {}}
            elif page_type == "Chapter":
                chapters[page_id] = {
                    "id": page_id,
                    "name": entry["name"],
                    "description": entry["description"],
                    "parent_id": entry["parent_id"],
                    "lessons": {},
                }
            elif page_type == "Lesson":
                lessons[page_id] = {
                    "id": page_id,
                    "name": entry["name"],
                    "description": entry["description"],
                    "parent_id": entry["parent_id"],
                }
    
        # 2) Attach chapters to courses
        for chapter_id, chapter_data in chapters.items():
            parent_course_id = chapter_data.get("parent_id")
            if parent_course_id in courses:
                courses[parent_course_id]["chapters"][chapter_id] = chapter_data
    
        # 3) Attach lessons to chapters
        for lesson_id, lesson_data in lessons.items():
            parent_chapter_id = lesson_data.get("parent_id")
            # Find which course has that chapter
            for course_data in courses.values():
                if parent_chapter_id in course_data["chapters"]:
                    course_data["chapters"][parent_chapter_id]["lessons"][lesson_id] = lesson_data
    
        # 4) Build the final course list
        course_list = []
        for course in courses.values():
            # Key chapters by their name, but keep all their fields
            renamed_chapters = {}
            for ch_id, ch_obj in course["chapters"].items():
                # Also rename the lessons dict to be keyed by the lesson name
                lessons_by_name = {
                    lesson_data["name"]: lesson_data
                    for lesson_data in ch_obj["lessons"].values()
                }
                ch_obj["lessons"] = lessons_by_name
                renamed_chapters[ch_obj["name"]] = ch_obj
    
            course["chapters"] = renamed_chapters
            course_list.append(course)
    
        df = pd.DataFrame(course_list)
        return df

    @staticmethod
    def _extract_title(properties):
        title_data = properties.get("Name", {}).get("title", [])
        return title_data[0]["plain_text"] if title_data else "Untitled"

    @staticmethod
    def _extract_rich_text(properties, field_name):
        rich_text_data = properties.get(field_name, {}).get("rich_text", [])
        return rich_text_data[0]["plain_text"] if rich_text_data else None

    @staticmethod
    def _extract_select(properties, field_name):
        select_data = properties.get(field_name, {}).get("select", {})
        return select_data.get("name") if select_data else None

    @staticmethod
    def _extract_multi_select(properties, field_name):
        multi_select_data = properties.get(field_name, {}).get("multi_select", [])
        return [item["name"] for item in multi_select_data] if multi_select_data else []

    @staticmethod
    def _extract_relation(properties, field_name):
        relation_data = properties.get(field_name, {}).get("relation", [])
        return [item["id"] for item in relation_data] if relation_data else []


# --- TESTING THE NOTIONDB CLASS ---
if __name__ == "__main__":
    from oauthmanager import OnePasswordAuthManager
    import json

    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    NOTION_API_KEY = notion_creds.get("credential")

    DATABASE_ID = "195a1865-b187-8103-9b6a-cc752ca45874"
    db = NotionDB(NOTION_API_KEY, DATABASE_ID)
    filter_criteria={"Name": "Sample Course A"}
    results = db.get_courses(**filter_criteria)
    print(results)





