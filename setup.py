"""Setup for ifmo_xblock_crosscheck XBlock."""

import os
from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='ifmo-xblock-crosscheck',
    version='0.2',
    description='ifmo_xblock_crosscheck XBlock',   # TODO: write a better description.
    packages=[
        'ifmo_crosscheck',
    ],
    install_requires=[
        'XBlock',
        'django',
        'django-aggregate-if'
    ],
    entry_points={
        'xblock.v1': [
            'ifmo_crosscheck_xblock = ifmo_crosscheck:CrossCheckXBlock', # absolete
            'ifmo_xblock_crosscheck = ifmo_crosscheck:CrossCheckXBlock',
        ]
    },
    package_data=package_data("ifmo_crosscheck", ["static", "public"]),
)