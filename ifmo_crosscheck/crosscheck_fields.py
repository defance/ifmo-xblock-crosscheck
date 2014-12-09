import datetime
import pytz

from xblock.fields import Scope, Integer, String, Float, Boolean, DateTime


class CrosscheckXBlockFields(object):

    display_name = String(
        default='Crosscheck Assignment',
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
        default=0,
        help="Grade score given to assignment by staff.",
        values={"min": 0, "step": .1},
        scope=Scope.user_state
    )

    score_published = Boolean(
        display_name="Whether score has been published.",
        help="This is a terrible hack, an implementation detail.",
        default=True,
        scope=Scope.user_state
    )

    submission = Integer(
        scope=Scope.user_state,
        default=None,
        help="Submission id"
    )

    submission_rolled = Integer(
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

    grades_required = Integer(
        display_name="Grades required",
        scope=Scope.settings,
        default=3,
        help="Amount of grades required for each submission."
    )

    task_text = String(
        display_name="Task text",
        default='',
        help="Text will be shown to students while this module is open.",
        scope=Scope.settings
    )

    task_criteria = String(
        display_name="Task criteria",
        default='',
        help="These criteria will be shown to peer when grading one's submission.",
        scope=Scope.settings
    )

    allowed_extensions = String(
        display_name="Allowed file extensions",
        default='',
        help="Comma separated allowed extensions. If empty - no file restrictions are used. Example: <em>jpg,png</em>",
        scope=Scope.settings
    )

    allowed_file_size = Integer(
        display_name="Allowed file extensions",
        default=0,
        help="Allowed file size (in bytes). If 0 - no file restrictions are used.",
        scope=Scope.settings
    )