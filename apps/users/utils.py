from typing import TYPE_CHECKING
from learning.settings import GradeTypes

if TYPE_CHECKING:
    from users.models import StudentProfile


def get_passed_courses_total(profile: "StudentProfile"):
    """
    Returns the total number of passed SHAD and online courses.
    """
    shad = 0
    shad_records = profile.user.shadcourserecord_set.all()
    if shad_records.exists():
        for course in shad_records:
            if course.grade in GradeTypes.satisfactory_grades:
                shad += 1
    
    online = profile.user.onlinecourserecord_set.count()
    
    regular = 0
    if hasattr(profile.user, 'prefetched_enrollments'):
        enrollments = profile.user.prefetched_enrollments
    else:
        enrollments = profile.user.enrollment_set.filter(is_deleted=False)
        
    if enrollments:
        for enrollment in enrollments:
            if enrollment.grade in GradeTypes.satisfactory_grades:
                regular += 1
    
    return shad + online + regular
        
def get_courses_grades(profile: "StudentProfile", meta_courses):
    """
    Returns a dictionary mapping course indexes to grade displays for all courses
    where there is at least one grade.
    """
    result = {}
    
    # Process regular course enrollments
    if hasattr(profile.user, 'prefetched_enrollments'):
        enrollments = profile.user.prefetched_enrollments
    else:
        enrollments = profile.user.enrollment_set.filter(is_deleted=False)
        
    if enrollments:
        for enrollment in enrollments:
            if enrollment.grade in GradeTypes.satisfactory_grades:
                # Try to find the course index by name
                course_name = enrollment.course.meta_course.name if hasattr(enrollment.course, 'meta_course') else enrollment.course.name
                if course_name in meta_courses and meta_courses[course_name]:
                    result[meta_courses[course_name]] = enrollment.grade_display.lower()
                else:
                    result[course_name] = enrollment.grade_display.lower()
    
    # Process SHAD courses
    for course in profile.user.shadcourserecord_set.all():
        if course.grade in GradeTypes.satisfactory_grades:
            # Try to find the course index by name
            if course.name in meta_courses and meta_courses[course.name]:
                result[meta_courses[course.name]] = course.grade_display.lower()
            else:
                result[course.name] = course.grade_display.lower()
    
    return result
