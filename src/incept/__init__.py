from incept.course import Course
from incept.chapter import Chapter
from incept.lesson import Lesson
from incept.media.icon import Icon
from incept.media.cover import Cover
#from incept.coursemanager import newCourse, newChapter, newLesson
#from incept.notion import insertCourse, insertChapter, insertLesson  # Notion-related functions

# Make them available when using `import incept`
#__all__ = [
#    "Course", "Chapter", "Lesson", "Icon", "Cover",
#    "newCourse", "newChapter", "newLesson",
#    "insertCourse", "insertChapter", "insertLesson"
#]

__all__ = [
    "Course", "Chapter", "Lesson", "Icon", "Cover",
    "newCourse", "newChapter", "newLesson",
    "insertCourse", "insertChapter", "insertLesson"
]
