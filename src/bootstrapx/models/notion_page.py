from notionmanager.notion.manager import NotionManager
from bootstrapx.models.icon import Icon
from bootstrapx.models.cover import Cover

class NotionPage:
    def __init__(
        self,
        notion_api_key: str,
        database_id: str,
        name: str,
        content_type: str,
        template_name: str,
        icon: Icon = None,
        cover: Cover = None,
        **kwargs
    ):
        """
        Generic Notion Page class for courses, chapters, and lessons.

        Parameters:
        - notion_api_key (str): API Key for Notion.
        - database_id (str): Notion database ID.
        - name (str): Page title.
        - content_type (str): 'Course', 'Chapter', or 'Lesson'.
        - template_name (str): Name of the folder template used.
        - icon (Icon): Icon object (default: Notion default).
        - cover (Cover): Cover object (default: Notion default).
        - kwargs: Additional metadata properties.
        """
        self.notion = NotionManager(notion_api_key, database_id)
        self.name = name
        self.content_type = content_type
        self.template_name = template_name
        self.icon = icon or Icon()  # Uses default values from the class
        self.cover = cover or Cover()  # Uses default values from the class

        self.properties = {
            "Name": {"title": [{"text": {"content": self.name}}]},
            "Type": {"select": {"name": self.content_type}},
            "Template Name": {"rich_text": [{"text": {"content": self.template_name}}]},
        }
        self.properties.update(kwargs)

    def create_page(self) -> str:
        """Creates a Notion page and returns the page ID."""
         payload = {
            "parent": {"database_id": self.database_id},
            "properties": self.properties,
            "icon": self.icon.to_dict(),  # Kept outside "properties"
            "cover": self.cover.to_dict()  # Kept outside "properties"
        }
        response = self.notion.add_page(payload)
        return response.get("id")
