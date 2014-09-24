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
    name='ifmo-crosscheck-xblock',
    version='0.1',
    description='ifmo_xblock_crosscheck XBlock',   # TODO: write a better description.
    packages=[
        'ifmo_crosscheck',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'ifmo_crosscheck_collector = ifmo_crosscheck:CrossCheckCollectorXBlock',
            'ifmo_crosscheck_grader = ifmo_crosscheck:CrossCheckGraderXBlock',
        ]
    },
    package_data=package_data("ifmo_crosscheck", ["static", "public"]),
)