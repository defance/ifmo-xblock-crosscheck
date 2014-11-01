import hashlib
import datetime
import os
import pytz

from django.core.files.storage import default_storage
from functools import partial
from webob.response import Response


class CrosscheckSettingsSaveException(Exception):
    pass


class ValidationException(Exception):
    pass


def download(path, mimetype, filename):
    block_size = 2**10 * 8  # 8kb
    downloaded_file = default_storage.open(path)
    app_iterator = iter(partial(downloaded_file.read, block_size), '')
    return Response(
        app_iter=app_iterator,
        content_type=mimetype,
        content_disposition="attachment; filename=" + filename
    )


def get_sha1(file_handler):
    BLOCK_SIZE = 2**10 * 8  # 8kb
    sha1 = hashlib.sha1()
    for block in iter(partial(file_handler.read, BLOCK_SIZE), ''):
        sha1.update(block)
    file_handler.seek(0)
    return sha1.hexdigest()


def file_storage_path(url, sha1, filename):
    assert url.startswith("i4x://")
    path = url[6:] + '/' + sha1
    path += os.path.splitext(filename)[1]
    return path


def now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)