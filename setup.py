import atexit
import sys
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from subprocess import call


class DevelopHook(develop):
    """For hooking the optimizer when setup exits"""
    def __init__(self, *a, **kw):
        develop.__init__(self, *a, **kw)
        atexit.register(
            call, [sys.executable, '-m', 'calmjs.parse.parsers.optimize'])


class InstallHook(install):
    """For hooking the optimizer when setup exits"""
    def __init__(self, *a, **kw):
        install.__init__(self, *a, **kw)
        atexit.register(
            call, [sys.executable, '-m', 'calmjs.parse.parsers.optimize'])


version = '0.9.0'

classifiers = """
Development Status :: 4 - Beta
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: JavaScript
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
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
        'develop': DevelopHook,
        'install': InstallHook,
    },
    install_requires=[
        'ply>=3.6',
    ],
    entry_points={
    },
    test_suite="calmjs.parse.tests.make_suite",
)
