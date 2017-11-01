# installation: pip install dbsnap_verify
from setuptools import (
  setup,
  find_packages,
)

setup( 
    name = 'dbsnap_verify',
    version = '0.0.4',
    description = 'Tool for verifying AWS RDS snapshots.',
    keywords = 'aws rds snapshot tool infrastructure',
    long_description = open('README.rst').read(),

    author = 'Russell Ballestrini',
    author_email = 'russell@remind101.com',
    url = 'https://github.com/remind101/dbsnap-verify',

    license='New BSD license',

    packages = find_packages(),

    install_requires = [
        'boto3',
    ],
    tests_require = [
        'nose',
        'mock',
        'funcsigs',
        'flake8',
    ],
    entry_points = {
      'console_scripts': [
        'dbsnap-verify = dbsnap_verify.__main__:main',
      ],
    },
    classifiers=[
        'Intended Audience :: Developers, Operators, System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)

"""
setup()
  keyword args: http://peak.telecommunity.com/DevCenter/setuptools
configure pypi username and password in ~/.pypirc::
 [pypi]
 username:
 password:
build and upload to pypi with this::
 python setup.py sdist bdist_egg register upload
"""
