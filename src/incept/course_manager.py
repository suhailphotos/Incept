import os
from .models.course import Course
from .models.chapter import Chapter
from .models.lesson import Lesson
from .models.notion_page import NotionPage
from .template_manager import TemplateManager

class CourseManager:
    def __init__(self, notion_api_key: str, database_id: str):
        """
        Manages course creation, folder setup, and Notion integration.

        Parameters:
        - notion_api_key (str): API Key for Notion.
        - database_id (str): Notion database ID.
        """
        self.notion_api_key = notion_api_key
        self.database_id = database_id

    def create_course(self, course: Course):
        """Creates a new course with folder structure and Notion entry."""
        TemplateManager.create_course_structure(course.name, course.template)
        notion_page = NotionPage(
            self.notion_api_key, self.database_id, course.name, course.content_type, course.template,
            icon=course.icon, cover=course.cover, path=course.path, course_link=course.course_link
        )
        return notion_page.create_page()

    def create_chapter(self, course: Course, chapter_name: str):
        """Creates a new chapter and associates it with a course."""
        chapter = Chapter(name=chapter_name, parent_course=course)
        course.add_chapter(chapter)
        return chapter

    def create_lesson(self, chapter: Chapter, lesson_name: str):
        """Creates a new lesson and associates it with a chapter."""
        lesson = Lesson(name=lesson_name, parent_chapter=chapter)
        chapter.add_lesson(lesson)
        return lesson
