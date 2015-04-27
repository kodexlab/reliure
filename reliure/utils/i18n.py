#-*- coding:utf-8 -*-
""" :mod:`reliure.utils.i18n`
===========================

helpers for internationalisation
"""
import gettext

trans = gettext.translation('reliure', fallback=True)
_ = trans.gettext

