class Icon:
    DEFAULT_PLATFORM = "Notion"
    DEFAULT_ICON_URL = "https://www.notion.so/icons/graduate_lightgray.svg"
    DEFAULT_ICON_TYPE = "external"

    def __init__(self, platform=DEFAULT_PLATFORM, icon_url=DEFAULT_ICON_URL, icon_type=DEFAULT_ICON_TYPE):
        """
        Represents an Icon object.

        Parameters:
        - platform (str): Platform where the icon is used.
        - icon_url (str): URL of the icon.
        - icon_type (str): Type of icon ("external", "custom_emoji").
        """
        self.platform = platform
        self.icon_url = icon_url
        self.icon_type = icon_type

    def to_dict(self):
        """Returns a dictionary representation for Notion."""
        return {"type": self.icon_type, "external": {"url": self.icon_url}}
