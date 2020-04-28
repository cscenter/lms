import os

from nbconvert import HTMLExporter

from learning.settings import GradeTypes


def grade_to_mark(grade):
    """
    Converts grade to some score for easier grades comparison.

    Assume unsatisfactory > not_graded.
    """
    if grade == GradeTypes.NOT_GRADED:
        return 0
    elif grade == GradeTypes.UNSATISFACTORY:
        return 1
    elif grade == GradeTypes.CREDIT:
        return 2
    elif grade == GradeTypes.GOOD:
        return 3
    elif grade == GradeTypes.EXCELLENT:
        return 4
    raise ValueError("Unknown grade type")


def is_negative_grade(grade):
    return grade == GradeTypes.UNSATISFACTORY


def split_on_condition(iterable, predicate):
    true_lst, false_lst = [], []
    for x in iterable:
        if predicate(x):
            true_lst.append(x)
        else:
            false_lst.append(x)
    return true_lst, false_lst


def convert_ipynb_to_html(ipynb_src_path, html_dest_path):
    """
    Converts *.ipynb to html and saves the new file in the same directory with
    `html_ext` extension.
    """
    if not os.path.exists(html_dest_path):
        try:
            html_exporter = HTMLExporter()
            nb_node, _ = html_exporter.from_filename(ipynb_src_path)
            with open(html_dest_path, 'w') as f:
                f.write(nb_node)
            return True
        except (FileNotFoundError, AttributeError):
            return False
    return True