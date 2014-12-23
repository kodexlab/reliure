#-*- coding:utf-8 -*-
""" :mod:`reliure.exceptions`
==========================
"""

class ReliureError(Exception):
    """Basic reliure error"""

class ReliureValueError(ReliureError, ValueError):
    """Reliure value error: one value (attribute) was wrong"""


class ReliurePlayError(Exception):
    u"""Error occuring at engine 'play' time
    
    This errors can be show to the user
    
    The message could be given as a str (not unicode), it will be decode as utf8 :
    
    >>> error = ReliurePlayError("un méssage en str")
    >>> error.msg
    u'un m\\xe9ssage en str'

    Note that `str()` will return an utf8 string:
    >>> type(str(error))
    <type 'str'>
    >>> str(error)
    'un m\\xc3\\xa9ssage en str'
    >>> error = ReliurePlayError(u"un méssage en str")
    >>> error.msg
    u'un m\\xe9ssage en str'
    >>> type(str(error))
    <type 'str'>
    >>> str(error)
    'un m\\xc3\\xa9ssage en str'

    """
    #TODO: manage i18n
    def __init__(self, msg):
        """
        :param msg: the message for the user
        """
        if isinstance(msg, str):
           msg = msg.decode("utf8")
        assert isinstance(msg, unicode)
        self.msg = msg

    def __str__(self):
        return self.msg.encode("utf8")

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, str(self))


class SchemaError(Exception):
    """ Error
    
    #TODO: précissé le docstr, c'est quoi quand on a cette erreur exactement ?
    """
    pass


class FieldValidationError(Exception):
    """ Error in a field validation """
    def __init__(self, field, value, errors):
        super(FieldValidationError, self).__init__(field)
        self.field = field
        self.value = value
        self.errors = errors

    def __repr__(self):
        return "<FieldValidationError '%s', '%s'>" % (self.field, self.value)
        
    def __str__(self):
        return "FieldValidationError '%s' : %s \n  %s " % (self.field, self.value, 
                            "\n".join([ "\t*%s" % err for err in self.errors]))
    
class ValidationError(Exception):
    """An error while validating data of a given type.
    
    It may be either a single validation error or a list of validation error
    
    >>> from cello.utils.i18n import _
    >>> error = ValidationError(_("a message with a value : %(value)s"), {'value': 42})
    >>> for err in error: print err
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
