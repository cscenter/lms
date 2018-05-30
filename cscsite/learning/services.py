from learning.models import StudyProgram, Semester


def calculate_areas_for_student(student):
    """
    For each area from the student program checks that he accomplished all the
    course requirements.
    Other conditions like `1 research work for graduating from CS`
    are not taken into account.
    """
    programs = (StudyProgram.objects
                .filter(year=student.curriculum_year,
                        city_id=student.city_id)
                .syllabus())
    current_term = Semester.get_current()
    stats = student.stats(current_term=current_term)
    passed_courses = stats["passed"]["center_courses"]
    passed_courses = passed_courses.union(stats["passed"]["club_courses"])
    areas = []
    for program in programs:
        # Student should have at least 1 passed course in each group
        groups_total = len(program.course_groups.all())
        groups_satisfied = 0
        for course_group in program.course_groups.all():
            groups_satisfied += any(c.id in passed_courses for c in
                                    course_group.courses.all())
        if groups_total and groups_satisfied == groups_total:
            areas.append(program.area.code)
    if areas:
        student.areas_of_study.set(areas)
