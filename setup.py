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
    name='ifmo_xblock_crosscheck-xblock',
    version='0.1',
    description='ifmo_xblock_crosscheck XBlock',   # TODO: write a better description.
    packages=[
        'ifmo_xblock_crosscheck',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'ifmo_xblock_crosscheck = ifmo_xblock_crosscheck:CrossCheckXBlock',
        ]
    },
    package_data=package_data("ifmo_xblock_crosscheck", ["static", "public"]),
)