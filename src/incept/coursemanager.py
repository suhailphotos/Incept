from incept.course import Course
from incept.chapter import Chapter
from incept.lesson import Lesson
from incept.template.manager import create_course_structure 

def newCourse(name, description=None, path=None, template="default"):
    """
    Creates a new Course object and sets up folder structure.
    """
    course = Course(name, description, path, template=template)
    create_course_structure(course.name, template)
    return course

def newChapter(course, name, materials_path=None, assignments_path=None):
    """
    Creates a new Chapter object and associates it with a Course.
    """
    chapter = Chapter(name, materials_path=materials_path, assignments_path=assignments_path, parent_course=course)
    course.add_chapter(chapter)
    return chapter

def newLesson(chapter, name):
    """
    Creates a new Lesson object and associates it with a Chapter.
    """
    lesson = Lesson(name, parent_chapter=chapter)
    chapter.add_lesson(lesson)
    return lesson
