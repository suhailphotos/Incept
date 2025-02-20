import pandas as pd
from notionmanager.notion import NotionManager

class NotionDB:
    def __init__(self, database_id):
        self.database_id = database_id
        self.notion = NotionManager(database_id)

    def get_courses(self, filter=None):
        """Fetch courses from Notion and return as a pandas DataFrame."""
        notion_data = self.notion.get_pages(filter=filter)
        return pd.DataFrame(notion_data)

    def insert_course(self, data):
        """Insert a course into Notion."""
        if self.notion.exists("courses", data["name"]):
            return "Course already in DB"
        return self.notion.add_page("courses", data)

    def update_course(self, course_id, data):
        """Update a course in Notion."""
        return self.notion.update_page(course_id, data)

    def delete_course(self, course_id):
        """Delete a course from Notion."""
        return self.notion.delete_page(course_id)

if __name__== "__main__":
    DATABASE_ID = "16aa1865b187810cbb34e07ffd6b40b8"
    db = NotionDB(DATABASE_ID)
