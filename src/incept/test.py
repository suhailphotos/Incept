from incept.templates.manager import create_course_structure
from pathlib import Path

custom_path = Path("/Users/suhail/Library/CloudStorage/SynologyDrive-dataLib/threeD/courses")
course_path = create_course_structure("CourseABC", base_path=custom_path)
print("Created course at:", course_path)
