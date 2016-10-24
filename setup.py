#!/usr/bin/env python
"""Project setup."""
import os
import re
from setuptools import setup, find_packages

here = os.path.dirname(__file__)
with open(os.path.join(here, 'src', 'bossa_session', '__init__.py')) as v_file:
    package_version = re.compile(
        r'.*__version__ = "(.*?)"', re.S
    ).match(v_file.read()).group(1)

dependency_links = []


def extract_packages(file_name):
    """
    List packages with versions from a requirements file.

    :param str file_name: path to the requirements file
    :rtype: list
    :returns: a list of packages (with versions) specified
    in the requirements file
    """
    packages = []
    with open(file_name) as f:
        for package in f.read().splitlines():
            if package.find('#egg=') != -1:
                dependency_links.append(package)
                # extracting package name and version from link
                # eg. git+ssh://repo.org/foo/bar.git@v1.2.0#egg=bar-1.2.0
                # turns into
                # bar==1.2.0
                packages.append(
                    '=='.join(package.split('#egg=')[1].rsplit('-', 1))
                )
            else:
                packages.append(package)
    return packages

requirements = extract_packages('requirements.txt')
requirements_tests = extract_packages('requirements-tests.txt')

setup(
    name='bossa_session',
    version=package_version,
    include_package_data=True,
    zip_safe=False,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    description="The package with basic operations from bossa using requests.",
    install_requires=requirements,
    test_suite='tests',
    extras_require={
        'tests': requirements_tests
    },
    dependency_links=dependency_links,
)
