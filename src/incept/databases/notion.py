import pandas as pd
from notionmanager.notion import NotionManager

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

        # Only apply a filter if "Name" is in kwargs
        if "Name" in kwargs:
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
                    return  # Avoid duplicate calls or infinite loops
                page = self.notion.get_page(page_id)
                visited_pages[page_id] = page
                # Extract child page_ids from 'Sub-item' property
                sub_item_ids = self._extract_relation(page.get("properties", {}), "Sub-item")
                for child_id in sub_item_ids:
                    fetch_children(child_id)

            # 1) Fetch the filtered course pages
            for course_page in filtered_courses:
                fetch_children(course_page["id"])

            # 2) Convert the visited pages into a DataFrame
            notion_data = list(visited_pages.values())
            return self._convert_to_dataframe(notion_data)

    def insert_course(self, data):
        """Insert a new course into Notion."""
        return self.notion.add_page(data)

    def update_course(self, course_id, data):
        """Update an existing course."""
        return self.notion.update_page(course_id, data)

    def delete_course(self, course_id):
        """Delete (archive) a course."""
        return self.notion.update_page(course_id, {"archived": True})

    def insert_chapter(self, course_id, data):
        """Insert a new chapter under a course."""
        data["parent_course"] = course_id
        return self.notion.add_page(data)

    def insert_lesson(self, chapter_id, data):
        """Insert a lesson under a chapter."""
        data["parent_chapter"] = chapter_id
        return self.notion.add_page(data)

    def update_chapter(self, chapter_id, data):
        """Update a chapter."""
        return self.notion.update_page(chapter_id, data)

    def update_lesson(self, lesson_id, data):
        """Update a lesson."""
        return self.notion.update_page(lesson_id, data)

    def delete_chapter(self, chapter_id):
        """Delete (archive) a chapter."""
        return self.notion.update_page(chapter_id, {"archived": True})

    def delete_lesson(self, lesson_id):
        """Delete (archive) a lesson."""
        return self.notion.update_page(lesson_id, {"archived": True})

    def _convert_to_dataframe(self, notion_data, filter_course_ids=None):
        """
        Convert Notion API response into a structured Pandas DataFrame.
        Rolls up courses with their respective chapters and lessons.

        - Stores `icon` as a dictionary for easy retrieval.
        - Keeps `cover` information for inheritance when adding new chapters and lessons.

        Returns:
        - pd.DataFrame: Cleaned and structured data.
        """
        courses = {}
        chapters = {}
        lessons = {}

        # Pass 1: Organize all entries by type
        for page in notion_data:
            properties = page.get("properties", {})
            page_id = page.get("id")
            page_type = self._extract_select(properties, "Type")
            parent_ids = self._extract_relation(properties, "Parent item")
            sub_items = self._extract_relation(properties, "Sub-item")

            # Store the entire icon object (can be external or custom emoji)
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
                "icon": icon_data,  # Store the full icon object
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

        # Pass 2: Attach chapters to courses
        for chapter_id, chapter_data in chapters.items():
            parent_course_id = chapter_data.get("parent_id")
            if parent_course_id in courses:
                courses[parent_course_id]["chapters"][chapter_id] = chapter_data

        # Pass 3: Attach lessons to chapters
        for lesson_id, lesson_data in lessons.items():
            parent_chapter_id = lesson_data.get("parent_id")
            for course in courses.values():
                if parent_chapter_id in course["chapters"]:
                    course["chapters"][parent_chapter_id]["lessons"][lesson_id] = lesson_data

        # Convert to DataFrame
        course_list = []
        for course in courses.values():
            # This is just an example of how you might "roll up" chapters 
            # and lessons into a single column. You can adjust as needed.
            course["chapters"] = {
                ch["name"]: ch["lessons"] for ch in course["chapters"].values()
            }
            course_list.append(course)

        df = pd.DataFrame(course_list)

        # Optional: If you still want to filter in the DataFrame layer
        if filter_course_ids:
            df = df[df["id"].isin(filter_course_ids)]

        return df

    @staticmethod
    def _extract_title(properties):
        """Extracts the title from Notion properties."""
        title_data = properties.get("Name", {}).get("title", [])
        return title_data[0]["plain_text"] if title_data else "Untitled"

    @staticmethod
    def _extract_rich_text(properties, field_name):
        """Extracts rich text fields (e.g., course description, path)."""
        rich_text_data = properties.get(field_name, {}).get("rich_text", [])
        return rich_text_data[0]["plain_text"] if rich_text_data else None

    @staticmethod
    def _extract_select(properties, field_name):
        """Extracts select values (e.g., 'Type' field)."""
        select_data = properties.get(field_name, {}).get("select", {})
        return select_data.get("name") if select_data else None

    @staticmethod
    def _extract_multi_select(properties, field_name):
        """Extracts multi-select values as a list (e.g., tags)."""
        multi_select_data = properties.get(field_name, {}).get("multi_select", [])
        return [item["name"] for item in multi_select_data] if multi_select_data else []

    @staticmethod
    def _extract_relation(properties, field_name):
        """Extracts relation values as a list of IDs (e.g., parent course, sub-items)."""
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

    # Test get_courses() without filter (retrieves all)
    all_df = db.get_courses()
    print("=== ALL Courses ===")
    print(all_df)

    # Test get_courses() with a filter
    courses_df = db.get_courses(Name="Sample Course B")
    print("=== Filtered Courses ===")
    print(courses_df)
