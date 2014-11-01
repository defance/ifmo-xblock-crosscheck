from django.contrib.auth.models import User
from django.db import models


class Submission(models.Model):
    user = models.ForeignKey(User, db_index=True)
    sha_1 = models.CharField(max_length=255, db_index=True)
    filename = models.CharField(max_length=255, db_index=True)
    mimetype = models.CharField(max_length=255, default="")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    approved = models.BooleanField()
    course = models.CharField(max_length=255, db_index=True, default="")
    module = models.CharField(max_length=255, db_index=True, default="")


class Score(models.Model):
    submission = models.ForeignKey(Submission, db_index=True)
    user = models.ForeignKey(User, db_index=True)
    comment = models.TextField()
    score = models.FloatField()