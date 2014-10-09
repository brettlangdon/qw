#!/usr/bin/env python

from setuptools import setup, find_packages

from qw import __version__

setup(
    name="qw",
    version=__version__,
    description="Python Distributed Redis Queue Workers",
    author="Brett Langdon",
    author_email="brett@blangdon.com",
    url="https://github.com/brettlangdon/qw",
    packages=find_packages(),
    license="MIT",
    scripts=["bin/qw-manager", "bin/qw-client"],
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
    ]
)
