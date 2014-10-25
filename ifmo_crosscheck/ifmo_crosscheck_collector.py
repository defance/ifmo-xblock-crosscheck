"""TO-DO: Write a description of what this XBlock is."""

import datetime
import hashlib
import json
import mimetypes
import os
import pkg_resources
import pytz

from django.core.files import File
from django.core.files.storage import default_storage
from django.template import Context, Template
from functools import partial
from webob.response import Response
from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, Float, Boolean, DateTime, Dict
from xblock.fragment import Fragment

from .grade_dict import GradeDict
from .graded_submission import GradedSubmission, GradeInfo


class CrosscheckSettingsSaveException(Exception):
    pass


class ValidationException(Exception):
    pass


class CrossCheckCollectorXBlock(XBlock):

    has_score = True
    icon_class = 'problem'

    display_name = String(
        default='[Crosscheck] Collector',
        help="This name appears in the horizontal navigation at the top of "
             "the page.",
        scope=Scope.settings
    )

    weight = Float(
        display_name="Problem Weight",
        help=("Defines the number of points each problem is worth. "
              "If the value is not set, the problem is worth the sum of the "
              "option point values."),
        values={"min": 0, "step": .1},
        default = 1,
        scope=Scope.settings
    )

    points = Float(
        display_name="Maximum score",
        help="Maximum grade score given to assignment by staff.",
        values={"min": 0, "step": .1},
        default=100,
        scope=Scope.settings
    )

    collection_due = DateTime(
        display_name="Collection due",
        help="When system should stop collect solutions and start offer grading them (UTC+0). Format: Y-m-d H:M:S",
        default=datetime.datetime.utcnow().replace(tzinfo=pytz.utc),
        scope=Scope.settings
    )

    score = Float(
        display_name="Grade score",
        default=None,
        help="Grade score given to assignment by staff.",
        values={"min": 0, "step": .1},
        scope=Scope.user_state
    )

    is_assignment_approved = Boolean(
        display_name="Whether student published his solution to peers.",
        default=False,
        scope=Scope.user_state
    )

    score_published = Boolean(
        display_name="Whether score has been published.",
        help="This is a terrible hack, an implementation detail.",
        default=True,
        scope=Scope.user_state
    )

    comment = String(
        display_name="Instructor comment",
        default='',
        scope=Scope.user_state,
        help="Feedback given to student by instructor."
    )

    is_assignment_uploaded = Boolean(
        display_name="Uploaded",
        scope=Scope.user_state,
        default=False,
        help="Whether user has uploaded file"
    )

    uploaded_sha1 = String(
        display_name="Upload SHA1",
        scope=Scope.user_state,
        default=None,
        help="sha1 of the file uploaded by the student for this assignment."
    )

    uploaded_filename = String(
        display_name="Upload file name",
        scope=Scope.user_state,
        default=None,
        help="The name of the file uploaded for this assignment."
    )

    uploaded_mimetype = String(
        display_name="Mime type of uploaded file",
        scope=Scope.user_state,
        default=None,
        help="The mimetype of the file uploaded for this assignment."
    )

    uploaded_timestamp = DateTime(
        display_name="Timestamp",
        scope=Scope.user_state,
        default=None,
        help="When the file was uploaded"
    )

    collected_submissions = GradeDict(
        scope=Scope.settings,
        default=GradeDict.default(),
        help="Contains all data, collected and graded. As keys is has number of grades, as "
    )

    current_rolled_submission = String(
        display_name="Current submission for grading",
        scope=Scope.user_state,
        default=None,
        help="Link to module"
    )

    is_grading_debug = String(
        display_name="Is grading phase",
        scope=Scope.settings,
        default=None,
        help="Debug value"
    )

    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    validators = {
        'string': lambda _, x: unicode(x),
        'float': lambda _, x: float(x),
        'datetime': lambda i, x: i._validate_collection_due(i._str_to_datetime(x))
    }

    filters = {
        'datetime': lambda i, x: i._datetime_to_str(x)
    }

    editable_fields = (
        ('display_name', 'string'),
        ('weight', 'float'),
        ('points', 'float'),
        ('collection_due', 'datetime'),
        ('is_grading_debug', 'string')
    )

    def max_score(self):
        return self.points

    @XBlock.json_handler
    def save_settings(self, data, suffix=''):
        for (name, field_type) in self.editable_fields:
            # TODO: Validate fields before saving them
            _validator = self.validators.get(field_type, lambda x: x)
            try:
                setattr(self, name, _validator(self, data.get(name, getattr(self, name))))
            except Exception as e:
                raise CrosscheckSettingsSaveException('Error while validating data: %s' % (e.message,))

    def student_view(self, context=None):
        frag = Fragment()
        context = self.get_state()
        context['state'] = json.dumps(context)
        frag.add_content(render_template("static/html/lms.html", context))
        frag.add_css(resource_string("static/css/lms.css"))
        frag.add_javascript(resource_string("static/js/src/lms.js"))
        frag.initialize_js('CrossCheckXBlockShow')
        return frag

    def get_state(self):
        state = {
            'upload_allowed': self._upload_allowed(),
            'is_uploaded': self.is_assignment_uploaded,
            'is_collection_phase': self._is_collection_step(),
            'sent_to_peers': self.is_assignment_approved,
            'is_grading_phase': self._is_grading_step(),
        }
        if self.is_assignment_uploaded:
            state.update({
                'uploaded_filename': self.uploaded_filename,
                'uploaded_timestamp': self._datetime_to_str(self.uploaded_timestamp),
                'uploaded_sha1': self.uploaded_sha1,
            })
        if self.current_rolled_submission:
            state.update({
                'is_selected': True
            })
        return state

    @XBlock.handler
    def upload_assignment(self, request, suffix=''):

        assert self._upload_allowed()

        upload = request.params['assignment']

        # Write down old file path to delete it later
        old_path = _file_storage_path(
            self.location.to_deprecated_string(),
            self.uploaded_sha1,
            self.uploaded_filename
        ) if self.is_assignment_uploaded else None

        self.uploaded_sha1 = _get_sha1(upload.file)
        self.uploaded_filename = upload.file.name
        self.uploaded_mimetype = mimetypes.guess_type(upload.file.name)[0]
        self.uploaded_timestamp = _now()
        path = _file_storage_path(
            self.location.to_deprecated_string(),
            self.uploaded_sha1,
            self.uploaded_filename
        )

        # Cleanup if everything is ok
        if old_path is not None and default_storage.exists(old_path):
            default_storage.delete(old_path)

        if not default_storage.exists(path):
            default_storage.save(path, File(upload.file))

        self.is_assignment_uploaded = True

        state = self.get_state()
        message = {
            "message_text": "You file is uploaded",
            "message_type": "info"
        }
        state.update({"message": message})

        return Response(json_body=state)

    @XBlock.handler
    def approve_assignment(self, request, suffix=''):
        """
        During first phase (collection) user can approve his assignment. It will be then sent to peers to be graded.
        It must be approved to be able graded during second phase (grading). It can be approved only when student
        has an uploaded submission.
        """

        assert self._is_collection_step()
        assert self.is_assignment_uploaded
        assert not self.is_assignment_approved

        submission = GradedSubmission(self.course_id, self.location, self.scope_ids.user_id)
        self.fields['collected_submissions'].add_submission(submission)
        self.is_assignment_approved = True

        return Response(json_body=self.get_state())

    @XBlock.handler
    def roll_submission(self, request, suffix=''):

        assert self._is_grading_step()
        assert self.current_rolled_submission is None

        module = self._roll_submission()
        self.current_rolled_submission = module

        return Response(json_body=self.get_state())

    def _roll_submission(self):

        return self.fields['collected_submissions'].get_random()

    def studio_view(self, context=None):
        cls = type(self)
        fields = []
        for (field, field_type) in self.editable_fields:
            # Some kind of a hack, filter takes 2 args: instance and value, return second arg
            _filter = self.filters.get(field_type, lambda _, x: x)
            fields += [(getattr(cls, field), _filter(self, getattr(self, field)), field_type)]

        context = {
            'fields': fields
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

        # Collection due that took place in past can be moved anywhere in past
        if self.collection_due is not None and self.collection_due < _now():
            return a

        if not a > _now():
            raise ValidationException("Collection due must take place in future")

        # if not a > self.start:
        #    raise ValidationException("Collection due must take place after course start")

        if self.due is not None:
            if not (a < self.due):
                raise ValidationException("Collection due must take place before module due")

        return a

    def _upload_allowed(self):
        return self._is_collection_step()

    def _is_collection_step(self):
        if self.is_grading_debug == 'True':
            return False
        return _now() < self.collection_due if self.collection_due else True

    def _is_grading_step(self):
        if self.is_grading_debug == 'True':
            return True
        _is_step = self.collection_due < _now()
        if self.due is not None:
            _is_step &= _now() < self.due
        return _is_step

    @XBlock.handler
    def download_uploaded(self, request, suffix=''):
        path = _file_storage_path(
            self.location.to_deprecated_string(),
            self.uploaded_sha1,
            self.uploaded_filename
        )
        return self.download(
            path,
            self.uploaded_mimetype,
            self.uploaded_filename
        )

    def download(self, path, mimetype, filename):
        block_size = 2**10 * 8  # 8kb
        downloaded_file = default_storage.open(path)
        app_iter = iter(partial(downloaded_file.read, block_size), '')
        return Response(
            app_iter=app_iter,
            content_type=mimetype,
            content_disposition="attachment; filename=" + filename)


def render_template(template_path, context={}):
    """
    Evaluate a template by resource path, applying the provided context
    """
    template_str = load_resource(template_path)
    template = Template(template_str)
    return template.render(Context(context))


def load_resource(resource_path):
    """
    Gets the content of a resource
    """
    resource_content = pkg_resources.resource_string(__name__, resource_path)
    return unicode(resource_content)


def resource_string(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")


def _now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def _file_storage_path(url, sha1, filename):
    assert url.startswith("i4x://")
    path = url[6:] + '/' + sha1
    path += os.path.splitext(filename)[1]
    return path


def _get_sha1(file):
    BLOCK_SIZE = 2**10 * 8  # 8kb
    sha1 = hashlib.sha1()
    for block in iter(partial(file.read, BLOCK_SIZE), ''):
        sha1.update(block)
    file.seek(0)
    return sha1.hexdigest()