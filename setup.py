#!/usr/bin/env python

from setuptools import setup, find_packages

#TODO; better setup
# see https://bitbucket.org/mchaput/whoosh/src/999cd5fb0d110ca955fab8377d358e98ba426527/setup.py?at=default
# for ex

setup(
    name='reliure',
    version='1.0',
    description='Cello',
    author='KodexLab',
    author_email='contact@kodexlab.com',
    url='http://kodexlab.com/reliure/',
    packages=['reliure'] + ['reliure.%s' % submod for submod in find_packages('reliure')],
)
