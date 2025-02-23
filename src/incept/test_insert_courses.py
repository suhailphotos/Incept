# test_insert_course.py

from incept.databases.notion import NotionDB
from oauthmanager import OnePasswordAuthManager

def main():
    # 1) Retrieve your Notion API key & database ID
    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    api_key = notion_creds["credential"]
    database_id = "195a1865-b187-8103-9b6a-cc752ca45874"  # example

    # 2) Prepare the sample data (kwargs) you want to insert
    #    matching the example you gave:
    course_data = {
        "name": "Sample Course C",  # required
        "description": "This is sample course. Write description here",
        "tags": ["Python"],
        "cover": "https://github.com/suhailphotos/notionUtils/blob/main/assets/media/banner/notion_style_banners_lgt_36.jpg?raw=true",
        "icon": "https://www.notion.so/icons/graduate_lightgray.svg",
        "course_link": "https://example.com",
        "path": "$DATALIB/threeD/courses",
        # If you want to eventually handle "Tool", "Parent item", "Sub-item", etc.,
        # you can add them here. 
        # e.g.: "tool": ["149a1865-b187-80f9-b21f-c9c96430bf62"]
    }

    # 3) Create an instance of NotionDB
    notion_db = NotionDB(api_key, database_id)

    # 4) Call insert_course(**course_data)
    result = notion_db.insert_course(**course_data)

    # 5) Print the response from Notion
    print("Inserted course page:", result)

if __name__ == "__main__":
    main()
