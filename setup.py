#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

cwd = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(cwd, 'README.md')).read()

setup(
    name='reliure',
    version='0.1.0',
    description="Minimal framework to manage data processing pipelines",
    long_description=readme,
    author='KodexLab',
    author_email='contact@kodexlab.com',
    url='https://github.com/kodexlab/reliure',
    packages=['reliure'] + ['reliure.%s' % submod for submod in find_packages('reliure')],
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    install_requires=['six'],
)

