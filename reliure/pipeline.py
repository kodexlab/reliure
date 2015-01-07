#-*- coding:utf-8 -*-
""" :mod:`reliure.pipeline`
=========================

inheritance diagrams
--------------------

.. inheritance-diagram:: reliure.pipeline

Class
-----
"""
import logging
from collections import OrderedDict
from functools import wraps, update_wrapper

from reliure.options import ValueOption


class Composable(object):
    """ Basic composable element
    
    Composable is abstract, you need to implemented the :meth:`__call__` method
    
    >>> e1 = Composable(lambda element: element**2, name="e1")
    >>> e2 = Composable(lambda element: element + 10, name="e2")
    
    Then :class:`Composable` can be pipelined this way :

    >>> chain = e1 | e2
    >>> # so yo got:
    >>> chain(2)
    14
    >>> # which is equivalent to :
    >>> e2(e1(2))
    14
    >>> # not that by defaut the pipeline agregate the components name
    >>> chain.name
    'e1|e2'
    >>> # however you can override it
    >>> chain.name = "chain"
    >>> chain.name
    'chain'

    It also possible to 'map' the composables
    >>> cmap = e1 & e2
    >>> # so you got:
    >>> cmap(2)
    [4, 12]

    """

    def __init__(self, func=None, name=None):
        """ You can create a :class:`Composable` from a simple function:
        
        >>> def square(val, pow=2):
        ...     return val ** pow
        >>> cfct = Composable(square)
        >>> cfct.name
        'square'
        >>> cfct(2)
        4
        >>> cfct(3, 3)
        27
        """
        self._name = None
        if func and callable(func):
            self._func = func
            if name is None:
                self.name = func.func_name
            else:
                self.name = name
            update_wrapper(self, func)
        elif name is None:
            self.name = self.__class__.__name__
        else:
            self.name = name
        self._logger = logging.getLogger("reliure.%s" % self.__class__.__name__)

    @property
    def name(self):
        """Name of the optionable component"""
        return self._name

    @name.setter
    def name(self, name):
        if ' ' in name:
            raise ValueError("Component name should not contain space")
        self._name = name

    def __or__(self, other):
        if not callable(other):
            raise ValueError("%r is not composable with %r" % (self, other))
        return Pipeline(self, other)
    
    def __and__(self, other):
        if not callable(other):
            raise ValueError("%r is not composable with %r" % (self, other))
        return MapSeq(self, other)

    def __call__(self, *args, **kwargs):
        if hasattr(self, "_func"):
            return self._func(*args, **kwargs)
        else:
            raise NotImplementedError

    def __str__(self):
        if hasattr(self, '_func'):
            return u"<function %s>" % self.name
        return u"<%s.%s>" % (self.__class__.__module__, self.__class__.__name__)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)


class Optionable(Composable):
    """ Abstract class for an optionable component
    """

    def __init__(self, name=None):
        """ 
        :param name: name of the component
        :type name: str
        """
        super(Optionable, self).__init__(name=name)
        self._options = OrderedDict()

    # Option dict is public but read only (sould pass by _options for write)
    @property
    def options(self):
        return self._options

    def add_option(self, opt_name, otype, hidden=False):
        """ Add an option to the object

        :param opt_name: option name
        :type opt_name: str
        :param otype: option type
        :type otype: subclass of :class:`.GenericType`
        :param hidden: if True the option will be hidden
        :type hidden: bool
        """
        if self.has_option(opt_name):
            raise ValueError("The option is already present !")
        opt = ValueOption.FromType(opt_name, otype)
        opt.hidden = hidden
        self._options[opt_name] = opt

    def has_option(self, opt_name):
        """ Whether the  component have a given option
        """
        return opt_name in self._options

    def print_options(self):
        """ print description of the component options
        """
        summary = []
        for opt_name, opt in self._options.iteritems():
            if opt.hidden:
                continue
            summary.append(opt.summary())
        print("\n".join(summary))

    def option_is_hidden(self, opt_name):
        """ Whether the given option is hidden
        """
        return self._options[opt_name].hidden

    def set_option_value(self, opt_name, value, parse=False):
        """ Set the value of one option.
        
        # TODO/FIXME 
            * add force/hide argument
            * add default argument
            * remove methods force option value
            * remove change_option_default
            
        :param opt_name: option name
        :type opt_name: str
        :param value: the new value
        :param parse: if True the value is converted from string to the correct type
        :type parse: bool
        
        """
        if not self.has_option(opt_name):
            raise ValueError("Unknow option name (%s)" % opt_name)
        self._options[opt_name].set(value, parse=parse)

    def clear_option_value(self, opt_name):
        """ Clear the stored option value (so the default will be used)

        :param opt_name: option name
        :type opt_name: str
        """
        if not self.has_option(opt_name):
            raise ValueError("Unknow option name (%s)" % opt_name)
        self._options[opt_name].clear()

    def get_option_value(self, opt_name):
        """ Return the value of a given option
        
        :param opt_name: option name
        :type opt_name: str
        
        :returns: the value of the option
        """
        if not self.has_option(opt_name):
            raise ValueError("Unknow option name (%s)" % opt_name)
        return self._options[opt_name].value

    def change_option_default(self, opt_name, default_val):
        """ Change the default value of an option
        
        :param opt_name: option name
        :type opt_name: str
        
        :param value: new default option value
        """
        if not self.has_option(opt_name):
            raise ValueError("Unknow option name (%s)" % opt_name)
        self._options[opt_name].default = default_val

    def force_option_value(self, opt_name, value):
        """ force the (default) value of an option.
        The option is then no more listed by :func:`get_options()`.
        
        :param opt_name: option name
        :type opt_name: str
        :param value: option value
        """
        if not self.has_option(opt_name):
            raise ValueError("Unknow option name (%s)" % opt_name)
        self._options[opt_name].default = value # also change the value
        self._options[opt_name].hidden = True

    def get_option_default(self, opt_name):
        """ Return the default value of a given option
        
        :param opt_name: option name
        :type opt_name: str
        
        :returns: the default value of the option
        """
        if not self.has_option(opt_name):
            raise ValueError("Unknow option name (%s)" % opt_name)
        return self._options[opt_name].default

    def clear_options_values(self):
        """ Clear all stored option values (so the defaults will be used)
        """
        for opt_name, opt in self._options.iteritems():
            opt.clear()

    def set_options_values(self, options, parse=False, strict=False):
        """ Set the options from a dict of values (in string).
        
        :param option_values: the values of options (in format `{"opt_name": "new_value"}`)
        :type option_values: dict
        :param parse: whether to parse the given value
        :type parse: bool
        :param strict: if True the given `option_values` dict should only 
         contains existing options (no other key)
        :type strict: bool
        """
        if strict:
            for opt_name in options.iterkeys():
                if not self.has_option(opt_name):
                    raise ValueError("'%s' is not a option of the component" % opt_name)
                elif self.option_is_hidden(opt_name):
                    raise ValueError("'%s' is hidden, you can't set it" % opt_name)
        for opt_name, opt in self._options.iteritems():
            if opt.hidden:
                continue
            if opt_name in options:
                opt.set(options[opt_name], parse=parse)

    def get_options_values(self, hidden=False):
        """ return a dictionary of options values
        
        :param hidden: whether to return hidden options
        :type hidden: bool
        :returns: dictionary of all option values
        :rtype: dict
        """
        values = {}
        for opt_name, opt in self._options.iteritems():
            if hidden or not opt.hidden:
                values[opt_name] = opt.value
        return values

    def parse_options(self, option_values):
        """ Set the options (with parsing) and returns a dict of all options values
        """
        self.set_options_values(option_values, parse=True)
        return self.get_options_values(hidden=False)

    def get_options(self, hidden=False):
        """
        :param hidden: whether to return hidden options
        :type hidden: bool
        :returns: dictionary of all options (with option's information)
        :rtype: dict
        """
        return dict((opt['name'], opt) for opt in self.get_ordered_options(hidden=hidden))

    def get_ordered_options(self, hidden=False):
        """
        :param hidden: whether to return hidden option
        :type hidden: bool
        :returns: **ordered** list of options pre-serialised (as_dict)
        :rtype: list `[opt_dict, ...]`
        """
        return [opt.as_dict() for opt in self._options.itervalues() \
                                            if hidden or (not opt.hidden)]

    @staticmethod
    def check(call_fct):
        """ Decorator for optionable __call__ method
        It check the given option values
        """
        # wrap the method
        @wraps(call_fct)
        def checked_call(self, *args, **kwargs):
            self.set_options_values(kwargs, parse=False, strict=True)
            options_values = self.get_options_values(hidden=True)
            return call_fct(self, *args, **options_values)
        # add a flag on the new method to indicate that it is 'checked'
        checked_call._checked = True
        checked_call._no_check = call_fct
        return checked_call


class OptionableSequence(Optionable):
    """ Abstract class to manage a composant made of a sequence of callable
    (Optionable or not).
    
    This object is an Optionable witch as all the options of it composants
    
    """
    def __init__(self, *composants):
        # Composable init
        super(OptionableSequence, self).__init__()
        self._options = None    # to detect better methods that are not overriden
        self.items = []
        for comp in composants:
            if not isinstance(comp, Composable):
                comp = Composable(comp)
            # merge ONLY if the composant is same class than "self"
            if isinstance(comp, self.__class__):
                self.items.extend(comp.items)
            else:
                self.items.append(comp)
        # Optionable init
        self.opt_items = [item for item in self.items if isinstance(item, Optionable)]
        # Check than a given options is not in two items
        all_opt_names = {}
        for item in self.opt_items:
            opt_names = item.get_options().keys()
            for opt_name in opt_names:
                assert not opt_name in all_opt_names, "Option '%s' present both in %s and in %s" % (opt_name, item, all_opt_names[opt_name])
                all_opt_names[opt_name] = item
        name = "+".join(item.name for item in self.items)
        self.name = name

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    @property
    def options(self):
        _options = OrderedDict()
        for item in self.items:
            if isinstance(item, Optionable):
                _options.update(item._options)
        return _options

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join(repr(item) for item in self.items))

    def __getitem__(self, item):
        return self.items.__getitem__(item)

    def __len__(self):
        return len(self.items)

    def __eq__(self, other):
        return (other
                and self.__class__ is other.__class__
                and self.items == other.items)

    def close(self):
        """ Close all the neested components
        """
        for item in self.items:
            if hasattr(item, "close"):
                item.close()

    def add_option(self, opt_name, otype, hidden=False):
        raise NotImplementedError("You can't add option on a OptionableSequence")

    def has_option(self, opt_name):
        return any(item.has_option(opt_name) for item in self.opt_items)

    def _item_from_option(self, opt_name):
        for item in self.opt_items:
            if item.has_option(opt_name):
                return item
        raise ValueError("'%s' is not an existing option" % opt_name)

    def option_is_hidden(self, opt_name):
        item = self._item_from_option(opt_name)
        return item.option_is_hidden(opt_name)

    def clear_option_value(self, opt_name):
        item = self._item_from_option(opt_name)
        item.clear_option_value(opt_name)

    def set_option_value(self, opt_name, value, parse=False):
        item = self._item_from_option(opt_name)
        item.set_option_value(opt_name, value, parse=parse)

    def get_option_value(self, opt_name):
        item = self._item_from_option(opt_name)
        return item.get_option_value(opt_name)

    def change_option_default(self, opt_name, default_val):
        item = self._item_from_option(opt_name)
        item.change_option_default(opt_name, default_val)

    def force_option_value(self, opt_name, value):
        item = self._item_from_option(opt_name)
        item.force_option_value(opt_name, value)

    def get_option_default(self, opt_name):
        item = self._item_from_option(opt_name)
        return item.get_option_default(opt_name)
    
    def clear_options_values(self):
        for item in self.opt_items:
            item.clear_options_values()

    def set_options_values(self, option_values, parse=True, strict=False):
        if strict:
            for opt_name in option_values.iterkeys():
                if not self.has_option(opt_name):
                    raise ValueError("'%s' is not a option of the component" % opt_name)
                elif self.option_is_hidden(opt_name):
                    raise ValueError("'%s' is hidden, you can't set it" % opt_name)
        for item in self.opt_items:
            # on passe strict a false car le check a deja été fait
            item.set_options_values(option_values, parse=parse, strict=False)

    def get_options_values(self, hidden=False):
        values = {}
        for item in self.opt_items:
            values.update(item.get_options_values(hidden=hidden))
        return values

    def get_ordered_options(self, hidden=False):
        opts = []
        for item in self.opt_items:
            opts += item.get_ordered_options(hidden=hidden)
        return opts

    def call_item(self, item, *args, **kwargs):
        item_kwargs = {}
        # if Optionable, build kargs
        item_name = item.name if hasattr(item, 'name') else ""
        if isinstance(item, Optionable):
            item.set_options_values(kwargs, strict=False, parse=False)
            item_kwargs = item.get_options_values()
        self._logger.debug("calling %s '%s' with %s", item, item_name, item_kwargs)
        return item(*args, **item_kwargs)


class Pipeline(OptionableSequence):
    """ A Pipeline is a sequence of function called sequentially.
    
    It may be created explicitely:
    
    >>> step1 = lambda x: x**2
    >>> step2 = lambda x: x-1
    >>> step3 = lambda x: min(x, 22)
    >>> processing = Pipeline(step1, step2, step3)
    >>> processing(4)
    15
    >>> processing(40)
    22

    Or it can be created implicitely with the pipe operator (__or__) if the
    first function is :class:`Composable`:
    
    >>> step1 = Composable(step1)
    >>> processing = step1 | step2 | step3
    >>> processing(3)
    8
    >>> processing(0)
    -1
    """
    def __init__(self, *composables):
        super(Pipeline, self).__init__(*composables)
        # create the "meta" name of the optionable pipeline, and init optionable
        name = "|".join(item.name for item in self.items)
        self.name = name

    @OptionableSequence.check
    def __call__(self, *args, **kwargs):
        for item in self.items:
            args = [self.call_item(item, *args, **kwargs)]
        return args[0] # expect only one output XXX


class MapSeq(OptionableSequence):
    """ Map implentation for components
    
    >>> mapseq = MapSeq(lambda x: x+1, lambda x: x+2, lambda x: x+3)
    >>> mapseq(10)
    [11, 12, 13]
    >>> sum(mapseq(10))
    36
    """
    @OptionableSequence.check
    def __call__(self, *args, **kwargs):
        return self.map(*args, **kwargs)
    
    def map(self, *args, **kwargs):
        return [self.call_item(item, *args, **kwargs) for item in self.items]


class MapReduce(MapSeq):
    """ MapReduce implentation for components

    One can  pass a simple function:
    
    >>> mapseq = MapReduce(sum, lambda x: x+1, lambda x: x+2, lambda x: x+3)
    >>> mapseq(10)
    36
    
    Or implements sub class of MapReduce:
    
    >>> class MyReduce(MapReduce):
    ...     def __init__(self, *composables):
    ...         super(MyReduce, self).__init__(None, *composables)
    ...     def reduce(self, array, *args, **kwargs):
    ...         return  list(args) + [sum(array)]
    >>> mapreduce = MyReduce(lambda x: x+1, lambda x: x+2, lambda x: x+3)
    >>> mapreduce(10)
    [10, 36]
    """
    def __init__(self, reduce, *composables):
        super(MapReduce, self).__init__(*composables)
        if reduce is not None:
            def wrap(array, *args, **kwargs):
                return reduce(array)
            self.reduce = wrap

    @OptionableSequence.check
    def __call__(self, *args, **kwargs):
        array = self.map(*args, **kwargs)
        return self.reduce( array, *args, **kwargs )

    def reduce(self, array, *args,  **kwargs):
        return NotImplementedError


