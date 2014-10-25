import random

from xblock.fields import Dict

from .graded_submission import GradedSubmission


class GradeDict(Dict):

    data = {}

    def add_submission(self, submission):

        assert isinstance(submission, GradedSubmission)

        lst = self.data.get(0, [])
        lst.append(submission)
        self.data[0] = lst

    def get_random(self):
        keys = sorted(self.data.keys())
        if not keys:
            return None
        return random.choice(self.data[keys[0]])

    @classmethod
    def default(cls):
        return {}