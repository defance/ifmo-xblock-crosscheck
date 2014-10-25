class GradedSubmission(object):

    def __init__(self, course_id, module_id, user_id):
        self.course_id = course_id
        self.module_id = module_id
        self.user_id = user_id
        self.grades = []

    def add_grade(self, grade):
        assert isinstance(grade, GradeInfo)
        self.grades += [grade]

    @property
    def average(self):
        if len(self.grades):
            return float(reduce(lambda x, y: x.grade + y.grade, self.grades)) / len(self.grades)
        else:
            return 0


class GradeInfo(object):

    def __init__(self, grade=0, message=None):
        self.grade = grade
        self.message = message
