"""Simple configuration used for py.test"""

# Always prefer setuptools over distutils
from setuptools import setup

setup(
    name='cscsite',
    version='1.0.0',
    description='Computer Science Center',
    long_description="No long description provided",
    # The project's main homepage.
    url='https://compscicenter.ru/',
    # Author details
    author='CSC',
    author_email='sergey.zherevchuk@jetbrains.com',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ]
)