import pandas as pd
import json
pd.set_option("display.max_colwidth", None)  # Ensures full content is displayed
from notionmanager.notion import NotionManager

class NotionDB:
    def __init__(self, api_key, database_id):
        """Wrapper around NotionManager for handling Notion database interactions."""
        self.notion = NotionManager(api_key, database_id)
        self.database_id = database_id

    def get_courses(self, **kwargs):
        """
        Fetch courses from Notion, aggregate chapters and lessons, and return as a Pandas DataFrame.

        - If a filter is applied (e.g., `Name="Sample Course"`), it filters only courses
          but retrieves all related chapters and lessons.
        - Ensures related data such as `chapters` and `lessons` are included.

        Parameters:
        - kwargs: Optional filters for querying Notion (e.g., `Name="Sample Course"`).

        Returns:
        - pd.DataFrame: DataFrame containing course details with rolled-up chapters and lessons.
        """
        filter_payload = None

        # Apply filter only if filtering by course name
        if "Name" in kwargs:
            filter_payload = {
                "filter": {
                    "property": "Name",
                    "title": {
                        "equals": kwargs["Name"]
                    }
                }
            }

        # Step 1: Retrieve filtered courses
        courses_data = self.notion._get_pages(**filter_payload) if filter_payload else self.notion._get_pages()

        if not courses_data:
            return pd.DataFrame()  # Return empty DataFrame if no matching courses

        # Extract course IDs from filtered results
        course_ids = [course["id"] for course in courses_data]

        # Step 2: Retrieve all chapters and lessons
        all_data = self.notion._get_pages(retrieve_all=True)

        # Step 3: Convert the full dataset into a structured DataFrame
        return self._convert_to_dataframe(all_data, course_ids)

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
            course["chapters"] = {
                ch["name"]: ch["lessons"] for ch in course["chapters"].values()
            }
            course_list.append(course)

        df = pd.DataFrame(course_list)

        # Step 4: If filtering by course, retain only the specified courses
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

    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    NOTION_API_KEY = notion_creds.get("credential")

    DATABASE_ID = "195a1865-b187-8103-9b6a-cc752ca45874"

    db = NotionDB(NOTION_API_KEY, DATABASE_ID)

    # Test get_courses() with a filter
    courses_df = db.get_courses(Name="Sample Course B")
    for index, value in courses_df["chapters"].items():
        print(f"Row {index}:")
        print(json.dumps(value, indent=2))  # Pretty-print JSON structure
        print("\n" + "-"*50)  # Separator for readability
