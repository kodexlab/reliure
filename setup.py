#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages
from reliure import __version__

cwd = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(cwd, 'README.md')).read()

setup(
    name='reliure',
    version=__version__,
    description="Minimal framework to manage data processing pipelines",
    long_description=readme,
    author='Emmanuel Navarro, Yannick Chudy',
    author_email='contact@kodexlab.com',
    url='http://kodexlab.com/reliure/',
    packages=['reliure'] + ['reliure.%s' % submod for submod in find_packages('reliure')],
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Natural Language :: French",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
)

