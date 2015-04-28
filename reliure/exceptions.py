#-*- coding:utf-8 -*-
""" :mod:`reliure.exceptions`
==========================
"""
import six

class ReliureError(Exception):
    """Basic reliure error"""

class ReliureValueError(ReliureError, ValueError):
    """Reliure value error: one value (attribute) was wrong"""


class ReliurePlayError(Exception):
    u"""Error occuring at engine 'play' time
    
    This errors can be show to the user

    >>> error = ReliurePlayError("an error message")
    >>> error.msg
    'an error message'
    """
    #TODO: manage i18n
    def __init__(self, msg):
        """
        :param msg: the message for the user
        """
        if six.PY2 and isinstance(msg, str):
           msg = msg.decode("utf8")
        self.msg = msg

    def __str__(self):
        if six.PY2:
            return self.msg.encode("utf8")
        return self.msg

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, str(self))


class ReliureTypeError(ReliureError):
    """Error in a reliure Type"""
    pass

class ValidationError(ReliureTypeError):
    """An error while validating data of a given type.
    
    It may be either a single validation error or a list of validation error
    
    >>> from reliure.utils.i18n import _
    >>> error = ValidationError(_("a message with a value : %(value)s"), {'value': 42})
    >>> for err in error: print(err)
    a message with a value : 42

    """
    def __init__(self, message, params=None):
        super(ValidationError, self).__init__(message, params)
        #
        if isinstance(message, list):
            self.error_list = []
            for error in message:
                # Normalize plain strings to instances of ValidationError.
                if not isinstance(error, ValidationError):
                    error = ValidationError(error)
                self.error_list.extend(error.error_list)
        else:
            self.message = message
            self.params = params
            self.error_list = [self]

    def __iter__(self):
        for error in self.error_list:
            message = error.message
            if error.params:
                message %= error.params
            yield message

    def __str__(self):
        return repr(list(self))

    def __repr__(self):
        return 'ValidationError(%s)' % self

