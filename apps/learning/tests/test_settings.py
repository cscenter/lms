from learning.settings import GradeTypes, GradingSystems


def test_get_choices_for_grading_system():
    grades = dict(GradeTypes.get_choices_for_grading_system(GradingSystems.BASE))
    assert GradeTypes.NOT_GRADED in grades
    assert GradeTypes.EXCELLENT in grades
    assert GradeTypes.TEN not in grades
    grades = dict(GradeTypes.get_choices_for_grading_system(GradingSystems.BINARY))
    assert GradeTypes.NOT_GRADED in grades
    assert GradeTypes.EXCELLENT not in grades
    assert GradeTypes.CREDIT in grades
    grades = dict(GradeTypes.get_choices_for_grading_system(GradingSystems.TEN_POINT))
    assert GradeTypes.NOT_GRADED in grades
    assert GradeTypes.EXCELLENT not in grades
    assert GradeTypes.TEN in grades


def test_get_grades_for_grading_system():
    grades = GradeTypes.get_grades_for_grading_system(GradingSystems.BASE)
    assert GradeTypes.NOT_GRADED in grades
    assert GradeTypes.EXCELLENT in grades
    assert GradeTypes.TEN not in grades
    grades = GradeTypes.get_grades_for_grading_system(GradingSystems.BINARY)
    assert GradeTypes.NOT_GRADED in grades
    assert GradeTypes.EXCELLENT not in grades
    assert GradeTypes.CREDIT in grades
    grades = GradeTypes.get_grades_for_grading_system(GradingSystems.TEN_POINT)
    assert GradeTypes.NOT_GRADED in grades
    assert GradeTypes.EXCELLENT not in grades
    assert GradeTypes.TEN in grades