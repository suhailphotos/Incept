# src/incept/courses.py

import os
import re
from pathlib import Path
from dotenv import load_dotenv
from incept.dbfactory import get_db_client

DEFAULT_DB = "notion"
CONFIG_DIR = Path.home() / ".incept"
ENV_FILE = CONFIG_DIR / ".env"


def getCourses(db=DEFAULT_DB, filter=None, **kwargs):
    """
    Retrieve courses from the specified DB client.
    
    If a filter is provided (e.g., a course name), only matching courses
    and their children are fetched recursively.
    
    Returns:
      dict: A nested dictionary (e.g. {"courses": [...]}) built using NotionDB.
    """
    db_client = get_db_client(db, **kwargs)
    if filter:
        return db_client.get_courses(Name=filter)
    else:
        return db_client.get_courses()
