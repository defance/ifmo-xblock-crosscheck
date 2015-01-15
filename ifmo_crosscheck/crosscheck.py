"""TO-DO: Write a description of what this XBlock is."""

import datetime
import json
import mimetypes
import pkg_resources
import pytz

from courseware.models import StudentModule
from django.contrib.auth.models import User
from django.core.files import File
from django.core.files.storage import default_storage
from django.db.models import Q
from aggregate_if import Avg, Count
from django.template import Context, Template
from webob.exc import HTTPNotFound
from webob.response import Response
from xblock.core import XBlock
from xblock.fragment import Fragment
from xmodule.util.duedate import get_extended_due_date

from .models import Score, Submission
from .crosscheck_fields import CrosscheckXBlockFields
from .utils import CrosscheckSettingsSaveException, ValidationException, download, get_sha1, file_storage_path, now, \
    human_size


class CrossCheckXBlock(CrosscheckXBlockFields, XBlock):

    has_score = True
    always_recalculate_grades = True
    icon_class = 'problem'

    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    validators = {
        'string': lambda _, x: unicode(x),
        'float': lambda _, x: float(x),
        'datetime': lambda i, x: i._validate_collection_due(i._str_to_datetime(x)),
        'int': lambda _, x: int(x),
    }

    filters = {
        'datetime': lambda i, x: i._datetime_to_str(x)
    }

    editable_fields = (
        ('display_name', 'string'),
        ('weight', 'float'),
        ('points', 'float'),
        ('grades_required', 'int'),
        ('collection_due', 'datetime'),
        ('allowed_extensions', 'string'),
        ('allowed_file_size', 'int'),
    )

    def max_score(self):
        return self.points

    def get_score(self):

        # We need to make two aggregate-select to calculate score. Need to find out how to cache it.
        default_score = {
            'score': 0,
            'total': self.weight,
            'grades': 0,
            'own_grades': 0,
            'need_grades': self.grades_required,
            'passed': False
        }

        if self.submission is None:
            return default_score

        own_submission = self._get_submission()

        # Score over user's submission
        aggregated_score = Score.objects.filter(submission=own_submission) \
            .aggregate(avg=Avg('score'), count=Count('submission'))

        # Check whether user has graded several submissions himself to get his score
        aggregated_score_own = Score.objects.filter(
            user_id=self.scope_ids.user_id,
            submission__module=own_submission.module,
            submission__course=own_submission.course
        ).aggregate(count=Count('submission'))

        # Update data
        default_score['grades'] = aggregated_score['count']
        default_score['own_grades'] = aggregated_score_own['count']

        # Submission must be graded several times before score can be published
        if aggregated_score['count'] < self.grades_required:
            return default_score

        # User need to grade at least several others' submission before score is published
        if aggregated_score_own['count'] < self.grades_required:
            return default_score

        default_score['score'] = (aggregated_score['avg'] / self.points) * self.weight
        default_score['passed'] = True

        return default_score

    @XBlock.json_handler
    def save_settings(self, data, suffix=''):
        for (name, field_type) in self.editable_fields:
            # TODO: Validate fields before saving them
            _validator = self.validators.get(field_type, lambda x: x)
            try:
                setattr(self, name, _validator(self, data.get(name, getattr(self, name))))
            except Exception as e:
                raise CrosscheckSettingsSaveException('Error while validating data: %s' % (e.message,))

        self.task_text = data.get('task_text', '')
        self.task_criteria = data.get('task_criteria', '')

    def student_view(self, context=None):
        frag = Fragment()
        context = self.get_state()
        context['state'] = json.dumps(context)

        context.update({
            'display_name': self.display_name,
            'task': {
                'text': self.task_text,
                'criteria': self.task_criteria
            },
            'max_score': self.max_score()
        })

        # Get reviews
        if context['score']['passed']:
            context.update({'reviews': self.get_reviews()})

        frag.add_content(render_template("static/html/lms.html", context))
        frag.add_css(resource_string("static/css/lms.css"))
        frag.add_javascript(resource_string("static/js/src/lms.js"))
        frag.initialize_js('CrossCheckXBlockShow')
        return frag

    def get_state(self):

        submission = self._get_submission()

        state = {
            'id': self.location.name.replace('.', '_'),
            'location': unicode(self.location),
            'is_upload_allowed': self._upload_allowed(),
            'is_grading_allowed': self._grading_allowed(),
        }

        if self.is_course_staff():
            state['is_staff'] = self.is_course_staff()

        if submission is not None:
            state.update({'uploaded': {
                'filename': submission.filename,
                'timestamp': self._datetime_to_str(submission.modified),
                'sha1': submission.sha_1,
                'size': submission.size,
                'approved': submission.approved
            }})

        submission_rolled = self._get_submission(self.submission_rolled)
        if submission_rolled is not None:
            state.update({
                'rolled': {
                    'filename': submission_rolled.filename,
                }
            })

        score = self.get_score()
        state.update({'score': score})

        return state

    def get_reviews(self):
        all_reviews = Score.objects.values('score', 'comment').filter(submission=self._get_submission())
        return [
            {
                'peer_name': u'Peer %s' % index,
                # Keep score anonymous
                # 'score': review['score'],
                'comment': review['comment']
            } for index, review in enumerate(all_reviews, start=1) if review['comment']
        ]

    @XBlock.handler
    def staff_info(self, request, suffix=''):

        assert self.is_course_staff()

        submissions_all = Submission.objects.filter(module=self.location)

        # We need 2 separated annotations due to bug
        # https://code.djangoproject.com/ticket/10060

        # Number of scores received by this submission
        submissions_num_scores = submissions_all.annotate(
            num_scores=Count('score')
        ).values(
            'id', 'user__username', 'user__id', 'num_scores', 'approved'
        )

        # Number of scores done by this submission author
        submissions_num_scores_by_user = submissions_all.annotate(
            num_scores_by_user=Count('user__score', only=Q(user__score__submission__module=self.location))
        ).values()

        # Create map of submissions from all submissions: id => row
        submission_map = dict()
        for submission in submissions_num_scores:
            submission_map[submission['id']] = submission

        # Update map with num_scores_by_user (second annotate)
        for submission in submissions_num_scores_by_user:
            submission_map[submission['id']]['num_scores_by_user'] = submission['num_scores_by_user']

        response = {
            'location': unicode(self.location),
            'summary': {
                'total': submissions_all.count(),
                'approved': submissions_all.filter(approved=True).count()
            },
            'submissions': submission_map.values(),
            'score': {
                'need_grades': self.grades_required
            }
        }

        return Response(json_body=response)

    @XBlock.handler
    def upload_assignment(self, request, suffix=''):

        def get_response(msg=None):
            msg = {} if msg is None else msg
            return_state = self.get_state()
            if msg:
                return_state.update({'message': msg})
            return Response(json_body=return_state)

        assert self._upload_allowed()

        upload = request.params['assignment']
        uploaded_file = File(upload.file)

        if self.allowed_extensions:
            if not any([upload.file.name.endswith(i) for i in self.allowed_extensions.split(',')]):
                return get_response({
                    "message_text": "File extension is not allowed. Allowed extension: %s." %
                                    ', '.join(self.allowed_extensions.split(',')),
                    "message_type": "error"
                })

        if self.allowed_file_size:
            if upload.file.size > self.allowed_file_size:
                return get_response({
                    "message_text": "You file is too big. Allowed file size is %s." %
                                    human_size(self.allowed_file_size),
                    "message_type": "error"
                })

        # Do cleanup first
        old_submission = self._get_submission()
        if old_submission is not None:
            old_path = file_storage_path(
                self.location.to_deprecated_string(),
                old_submission.sha_1,
                old_submission.filename
            )
            if default_storage.exists(old_path):
                default_storage.delete(old_path)

        submission = Submission.objects.create(
            user=User.objects.get(id=self.scope_ids.user_id),
            filename=upload.file.name,
            mimetype=mimetypes.guess_type(upload.file.name)[0],
            sha_1=get_sha1(upload.file),
            course=unicode(self.course_id),
            module=unicode(self.location),
            size=uploaded_file.size
        )

        self.submission = submission.id

        path = file_storage_path(
            self.location.to_deprecated_string(),
            submission.sha_1,
            submission.filename
        )

        if not default_storage.exists(path):
            default_storage.save(path, uploaded_file)

        return get_response({
            "message_text": "You submission is successfully uploaded.",
            "message_type": "info"
        })

    @XBlock.handler
    def approve_assignment(self, request, suffix=''):
        """
        During first phase (collection) user can approve his assignment. It will be then sent to peers to be graded.
        It must be approved to be able graded during second phase (grading). It can be approved only when student
        has an uploaded submission.
        """

        assert self._is_collection_step()

        submission = self._get_submission()

        assert submission is not None
        assert not submission.approved

        submission.approved = True
        submission.save()

        return Response(json_body=self.get_state())

    @XBlock.handler
    def roll_submission(self, request, suffix=''):

        assert self._is_grading_step()
        # assert self.current_rolled_submission is None

        rolled_submission = self.submission_rolled

        if not rolled_submission:
            rolled_submission = self._roll_submission()
            if rolled_submission is not None:
                self.submission_rolled = rolled_submission.id

        state = self.get_state()
        if rolled_submission is None:
            message = {
                "message_text": "No submission for grading is available. Please try again later.",
                "message_type": "error"
            }
            state.update({"message": message})

        return Response(json_body=state)

    def _roll_submission(self):

        user = User.objects.get(id=self.scope_ids.user_id)

        submissions = Submission.objects.filter(
            ~Q(user=user),
            module=unicode(self.location),
            course=unicode(self.course_id),
            approved=True,
        ).annotate(num_scores=Count('score')).order_by('num_scores')

        if not submissions.exists():
            return None

        for i in submissions:

            # Make in random?
            rolled_submission = i

            # We are okay only with submission that is not scored with current user.
            # Probably this can be optimized.
            if not Score.objects.filter(user=user, submission=rolled_submission).exists():
                return rolled_submission

        return None

    def studio_view(self, context=None):
        cls = type(self)
        fields = []
        for (field, field_type) in self.editable_fields:
            # Some kind of a hack, filter takes 2 args: instance and value, return second arg
            _filter = self.filters.get(field_type, lambda _, x: x)
            fields += [(getattr(cls, field), _filter(self, getattr(self, field)), field_type)]

        context = {
            'fields': fields,
            'extra_fields': {
                'task_text': self.task_text,
                'task_criteria': self.task_criteria
            }
        }
        frag = Fragment()
        frag.add_content(render_template("static/html/studio.html", context))
        frag.add_css(resource_string("static/css/studio.css"))
        frag.add_javascript(resource_string("static/js/src/studio.js"))
        frag.initialize_js('CrossCheckXBlockEdit')
        return frag

    def _str_to_datetime(self, a):
        return datetime.datetime.strptime(a, self.DATETIME_FORMAT).replace(tzinfo=pytz.utc)

    def _datetime_to_str(self, a):
        return a.strftime(self.DATETIME_FORMAT)

    def _validate_collection_due(self, a):
        """If collection due is ok, return it otherwise throw exception."""

        return a

        # If date has not changed -- skip any check
        if self.collection_due == a:
            return a

        # Collection due that took place in past can be moved anywhere in past
        if self.collection_due is not None and self.collection_due < now() and a < now():
            return a

        # No need to validate if both dues were in past
        if self.collection_due < now() and a < now():
            return a

        if not a > now():
            raise ValidationException("Collection due must take place in future (now=%s)" % now())

        # if not a > self.start:
        #    raise ValidationException("Collection due must take place after course start")

        if self.due is not None:
            if not (a < self.due):
                raise ValidationException("Collection due must take place before module due")

        return a

    def _upload_allowed(self):
        return self._is_collection_step()

    def _grading_allowed(self):
        return self._is_grading_step()

    def _is_collection_step(self):
        return now() < self.collection_due if self.collection_due else True

    def _is_grading_step(self):
        return not self.past_due() and now() > self.collection_due

    def is_course_staff(self):
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def past_due(self):
        due = get_extended_due_date(self)
        if due is not None:
            return now() > due
        return False


    @XBlock.handler
    def download_uploaded(self, request, suffix=''):

        submission = self._get_submission()

        if submission is None:
            return HTTPNotFound()

        path = file_storage_path(
            unicode(self.location),
            submission.sha_1,
            submission.filename
        )
        return download(
            path,
            submission.mimetype,
            submission.filename
        )

    @XBlock.handler
    def download_rolled(self, request, suffix=''):

        submission = self._get_submission(self.submission_rolled)

        if submission is None:
            return HTTPNotFound()

        path = file_storage_path(
            unicode(self.location),
            submission.sha_1,
            submission.filename
        )
        return download(
            path,
            submission.mimetype,
            submission.filename
        )

    @XBlock.handler
    def grade(self, request, suffix=''):

        assert self._is_grading_step()
        assert self.submission_rolled is not None

        submission = self._get_submission(self.submission_rolled)

        assert submission is not None

        user = User.objects.get(id=self.scope_ids.user_id)

        try:
            score = Score.objects.get(user=user, submission=submission)
        except Score.DoesNotExist:
            score = None

        # TODO: Protect passed params
        if score is None:
            score = Score.objects.create(
                user=user,
                comment=request.params.get('comment', ''),
                score=request.params.get('grade', 0),
                submission=submission
            )
        else:
            score.comment = request.params.get('comment', '')
            score.score = request.params.get('score', 0)
            score.save()

        self.submission_rolled = None

        state = self.get_state()
        state.update({
            'message': {
                'message_text': 'Successfully graded user submission.',
                'message_type': 'info'
            }
        })

        return Response(json_body=state)

    # Make it lazy getter and split to rolled_submission
    def _get_submission(self, submission_id=0):

        if submission_id is 0:
            submission_id = self.submission

        if submission_id in [None, 0]:
            return None

        try:
            return Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return None


def render_template(template_path, context=None):
    """
    Evaluate a template by resource path, applying the provided context
    """
    if context is None:
        context = {}
    template_str = load_resource(template_path)
    template = Template(template_str)
    return template.render(Context(context))


def load_resource(resource_path):
    """
    Gets the content of a resource
    """
    resource_content = pkg_resources.resource_string(__name__, resource_path)
    return resource_content
    # return unicode(resource_content)


def resource_string(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data
    # return data.decode("utf8")
