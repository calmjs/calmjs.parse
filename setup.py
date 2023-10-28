import os
import sys
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from subprocess import call


class BuildHook(build_py):
    """Forcing the optimizer to run before the build step"""
    def __init__(self, *a, **kw):
        # must use clone of this, otherwise Python on Windows gets sad.
        env = os.environ.copy()
        env['PYTHONPATH'] = 'src'
        code = call([
            sys.executable, '-m', 'calmjs.parse.parsers.optimize', '--build'
        ], env=env)
        if code:
            sys.exit(1)
        build_py.__init__(self, *a, **kw)


# Attributes

version = '1.4.0'

classifiers = """
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: JavaScript
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Programming Language :: Python :: 3.12
""".strip().splitlines()

long_description = (
    open('README.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')

setup(
    name='calmjs.parse',
    version=version,
    description="Various parsers for ECMA standards.",
    long_description=long_description,
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=classifiers,
    keywords='',
    author='Tommy Yu',
    author_email='tommy.yu@auckland.ac.nz',
    url='https://github.com/calmjs/calmjs.parse',
    license='mit',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['calmjs'],
    include_package_data=True,
    zip_safe=False,
    cmdclass={
        'build_py': BuildHook,
    },
    install_requires=[
        'setuptools',
        'ply>=3.6',
    ],
    entry_points={
    },
    test_suite="calmjs.parse.tests.make_suite",
)
