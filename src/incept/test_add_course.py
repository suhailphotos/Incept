# test_add_course.py

import pandas as pd
from oauthmanager import OnePasswordAuthManager
from incept.courses import addCourse

def main():
    # 1) Retrieve Notion API credentials
    auth_manager = OnePasswordAuthManager(vault_name="API Keys")
    notion_creds = auth_manager.get_credentials("Quantum", "credential")
    api_key = notion_creds["credential"]
    database_id = "195a1865-b187-8103-9b6a-cc752ca45874"

    # 2) Prepare the single-row DataFrame
    #    Each column corresponds to fields recognized by addCourse.
    df_single = pd.DataFrame([{
        "name": "Sample Course D",  # required
        "description": "This is sample course. Write description here",
        "tags": ["Python"],
        "cover": "https://github.com/suhailphotos/notionUtils/blob/main/assets/media/banner/notion_style_banners_lgt_36.jpg?raw=true",
        "icon": "https://www.notion.so/icons/graduate_lightgray.svg",
        "course_link": "https://example.com",
        "path": "$DATALIB/threeD/courses",
        # "tool": ["149a1865-b187-80f9-b21f-c9c96430bf62"]  # For future relation example
    }])

    # 3) Call addCourse, specifying "notion" + necessary credentials + the DataFrame
    result = addCourse(
        db="notion",
        template="default",
        api_key=api_key,
        database_id=database_id,
        df=df_single
    )

    # 4) Print the result
    print("addCourse result:", result)

if __name__ == "__main__":
    main()
