

def cmp_interview_average(interview):
    from learning.admission.models import Comment
    if not hasattr(interview, "average"):
        # .average_score can produce a lot of additional queries
        average = interview.average_score()
    else:
        average = interview.average
    if average is not None:
        return average
    else:
        return Comment.UNREACHABLE_COMMENT_SCORE


# TODO: Add tests!
def get_best_interview(applicant):
    """
    Returns interview with best average score.

    Don't forget to calculate `average` score for each interview:
        .annotate(average=Avg('comments__score'))
    Or prefetch comments to avoid a lot of additional queries
        .prefetch_related("comments")
    """
    try:
        best_interview = max(applicant.interviews.all(),
                             key=cmp_interview_average)
    except ValueError:  # no interviews at all
        best_interview = None
    return best_interview
