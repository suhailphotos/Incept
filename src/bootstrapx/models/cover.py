class Cover:
    DEFAULT_COVER_URL = "https://github.com/suhailphotos/notionUtils/blob/main/assets/media/banner/notion_style_banners_lgt_36.jpg?raw=true"

    def __init__(self, cover_url=DEFAULT_COVER_URL):
        """
        Represents a Cover object.

        Parameters:
        - cover_url (str): URL of the cover image.
        """
        self.cover_url = cover_url

    def to_dict(self):
        """Returns a dictionary representation for Notion."""
        return {"type": "external", "external": {"url": self.cover_url}}
