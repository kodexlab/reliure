#-*- coding:utf-8 -*-
""" :mod:`reliure.validators`
===========================

:copyright: (c) 2013 - 2014 by Yannick Chudy, Emmanuel Navarro.
:license: LGPL
"""

from reliure.utils.i18n import _
from reliure.exceptions import ValidationError


class TypeValidator(object):
    """ Validate that a value have a given type
    """
    message = "The value '%(show_value)s' is not of type %(value_type)s"

    def __init__(self, vtype, message=None):
        self.vtype = vtype
        if message:
            self.message = message

    def __call__(self, value):
        if not isinstance(value, self.vtype):
            param = {
                "show_value": value,
                "value_type": self.vtype,
            }
            raise ValidationError(self.message, param)
        return value


class compareValidator(object):
    """ Validate a value by comparing it to a reference value
    """
    # may change the value before to compare it
    preprocess = lambda self, value: value
    # the comparison it self 
    compare = lambda self, value, ref: value is not ref
    message = _("The value '%(show_value)s' is not %(ref_value)s")

    def __init__(self, ref_value):
        self.ref_value = ref_value

    def __call__(self, value):
        pvalue = self.preprocess(value)
        params = {'ref_value': self.ref_value, 'show_value': pvalue}
        if self.compare(pvalue, self.ref_value):
            raise ValidationError(self.message, params=params)
        return value


class ChoiceValidator(compareValidator):
    compare = lambda self, value, ref: value not in ref
    message = _('Ensure this value ("%(show_value)s") is in %(ref_value)s.')


class MaxValueValidator(compareValidator):
    compare = lambda self, value, ref: value > ref
    message = _('Ensure this value ("%(show_value)s") is less than or equal to %(ref_value)s.')


class MinValueValidator(compareValidator):
    compare = lambda self, value, ref: value < ref
    message = _('Ensure this value ("%(show_value)s") is greater than or equal to %(ref_value)s.')



