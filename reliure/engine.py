#-*- coding:utf-8 -*-
""" :mod:`reliure.engine`
========================

see :ref:`reliure-engine` for documentation
"""

import time
import logging
import warnings
import traceback
import itertools
from collections import OrderedDict

from reliure.exceptions import ReliureError
from reliure.pipeline import Pipeline, Optionable, Composable


class BasicPlayMeta(object):
    """ Object to store and manage meta data for one component exec

    Here is a typical usage :

    >>> import time
    >>> comp = Composable(name="TheComp", func=lambda x: x)
    >>> # create the meta result before to use the component
    >>> meta = BasicPlayMeta(comp)
    >>> # imagine some input and options for the component
    >>> args, kwargs = [12], {}
    >>> # store these data:
    >>> meta.run_with(args, kwargs)
    >>> # run the component
    >>> start = time.time()     # starting time
    >>> try:
    ...     output = comp(*args, **kwargs)
    ... except Exception as error:
    ...     # store the exception if any
    ...     meta.add_error(error)
    ...     # one can raise a custom error (or not)
    ...     #raise RuntimeError()
    ... finally:
    ...     # this will always be executed (even if the exception is not catched)
    ...     meta.time = time.time() - start
    ...     # for testing purpose we put a fixed time
    ...     meta.time = 9.2e-5
    >>> # one can get a pre-serialization of the collected meta data
    >>> meta.as_dict()
    {'errors': [], 'name': 'TheComp', 'warnings': [], 'time': 9.2e-05}
    """
    def __init__(self, component):
        self._name = component.name
        self._obj = repr(component)
        self._inputs = None      # correspond to args
        self._options = None     # kwargs
        self._time = 0.
        self._warnings = []
        self._errors = []

    @property
    def name(self):
        """ Name of the component """
        return self._name

    @property
    def time(self):
        """ Execution time (walltime)

        >>> comp = Composable(name="TheComp", func=lambda x: x)
        >>> meta = BasicPlayMeta(comp)
        >>> meta.time = 453.6
        >>> meta.time
        453.6
        """
        return self._time

    @time.setter
    def time(self, time):
        self._time = time

    @property
    def errors(self):
        return self._errors

    @property
    def warnings(self):
        return self._warnings

    def run_with(self, inputs, options):
        """ Store the run parameters (inputs and options)
        """
        self._inputs = inputs
        self._options = options

    def add_error(self, error):
        """ Register an error that occurs during component running

        >>> comp = Composable(name="TheComp", func=lambda x: x)
        >>> meta = BasicPlayMeta(comp)
        >>> try:
        ...     output = 1/0
        ... except Exception as error:
        ...     # store the exception if any
        ...     meta.add_error(error)
        >>> from pprint import pprint
        >>> pprint(meta.as_dict())
        {'errors': ['integer division or modulo by zero'],
         'name': 'TheComp',
         'time': 0.0,
         'warnings': []}
        """
        self._errors.append(error)

    @property
    def has_error(self):
        """ wether any error happened """
        return len(self._errors) > 0

    @property
    def has_warning(self):
        """ wether there where a warning during play """
        return len(self._warnings) > 0

    def as_dict(self):
        """ Pre-serialisation of the meta data """
        drepr = {}
        drepr["name"] = self.name
        drepr["time"] = self.time
        # error pre-serialisation
        drepr["errors"] = [str(err) for err in self.errors]
        # warning  pre-serialisation
        drepr["warnings"] = [str(warn) for warn in self.warnings]
        return drepr


class PlayMeta(BasicPlayMeta):
    """ Object to store and manage meta data for a set of component or block play
    
    >>> gres = PlayMeta("operation")
    >>> res_plus = BasicPlayMeta(Composable(name="plus"))
    >>> res_plus.time = 1.6
    >>> res_moins = BasicPlayMeta(Composable(name="moins"))
    >>> res_moins.time = 5.88
    >>> gres.append(res_plus)
    >>> gres.append(res_moins)
    >>> from pprint import pprint
    >>> pprint(gres.as_dict())
    {'details': [{'errors': [], 'name': 'plus', 'time': 1.6, 'warnings': []},
                 {'errors': [], 'name': 'moins', 'time': 5.88, 'warnings': []}],
     'errors': [],
     'name': 'operation:[plus, moins]',
     'time': 7.48,
     'warnings': []}

    """
    def __init__(self, name):
        self._name = name
        self._metas = []     # list of neested BasicPlayMeta

    @property
    def name(self):
        """ Compute a name according to sub meta results names

        >>> gres = PlayMeta("operation")
        >>> res_plus = BasicPlayMeta(Composable(name="plus"))
        >>> res_moins = BasicPlayMeta(Composable(name="moins"))
        >>> gres.append(res_plus)
        >>> gres.append(res_moins)
        >>> gres.name
        'operation:[plus, moins]'
        """
        return "%s:[%s]" % (self._name, ", ".join(meta.name for meta in self._metas))

    @property
    def time(self):
        """ Compute the total time (walltime)

        >>> gres = PlayMeta("operation")
        >>> res_plus = BasicPlayMeta(Composable(name="plus"))
        >>> res_plus.time = 1.6
        >>> res_moins = BasicPlayMeta(Composable(name="moins"))
        >>> res_moins.time = 5.88
        >>> gres.append(res_plus)
        >>> gres.append(res_moins)
        >>> gres.time
        7.48
        """
        return sum(meta.time for meta in self._metas)

    @property
    def errors(self):
        """ get all the errors

        >>> gres = PlayMeta("operation")
        >>> res_plus = BasicPlayMeta(Composable(name="plus"))
        >>> gres.append(res_plus)
        >>> res_plus.add_error(ValueError("invalid data"))
        >>> res_moins = BasicPlayMeta(Composable(name="moins"))
        >>> gres.append(res_moins)
        >>> res_plus.add_error(RuntimeError("server not anwsering"))
        >>> gres.errors
        [ValueError('invalid data',), RuntimeError('server not anwsering',)]
        """
        errors = []
        for meta in self:
            errors.extend(meta.errors)
        return errors

    @property
    def warnings(self):
        #TODO add test
        warnings = []
        for meta in self:
            warnings.extend(meta.warnings)
        return warnings

    def __iter__(self):
        return iter(self._metas)

    def append(self, meta):
        """ Add a :class:`BasicPlayMeta`
        """
        assert isinstance(meta, BasicPlayMeta)
        self._metas.append(meta)

    def add_error(self, error):
        """ It is not possible to add an error here, you sould add it on a
        :class:`BasicPlayMeta`
        """
        raise NotImplementedError

    def as_dict(self):
        """ Pre-serialisation of the meta data """
        drepr = super(PlayMeta, self).as_dict()
        drepr["details"] = [meta.as_dict() for meta in self._metas]
        return drepr


class Block(object):
    """ A block is a processing step realised by one component.

    A component is a callable object that has a *name* attribute, often it is
    also a :class:`reliure.Optionable` object or a pipeline beeing a
    :class:`reliure.Composable`.

    Block object provides methods to discover and parse components options (if
    any).
    
    .. Warning:: You should not have to use a :class:`.Block` directly but
        always throught a :class:`.Engine`.
    """

    #TODO: ajout validation de type sur input/output
    def __init__(self, name):
        """ Intialise a block. This should be done only from the
        :class:`.Engine`.

        :param name: name of the Block
        :type name: str
        """
        self._logger = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        # declare attributs
        self._name = None 
        self._selected = []
        self._components = None
        # note: the componants options values are stored in the components
        # name
        self.name = name
        # input output
        self.in_name = None         #list of input names (for play)
        self.out_name = self.name   #name of the output
        # ^ note this two information are used by the engine, not directly by Block.play
        #
        # default value for component options
        self.required = True
        self.hidden = False
        self.multiple = False
        self._defaults = []
        #handle results meta
        self.meta = None #note: this argument is (re)setted in play

        self.reset()
        # Attrs used to build a result object
        self.has_run = False

    @property
    def name(self):
        """Name of the optionable component"""
        return self._name

    @name.setter
    def name(self, name):
        if not isinstance(name, basestring):
            raise ValueError("Block name should be a string")
        if ' ' in name:
            raise ValueError("Block name should not contain space")
        self._name = name

    def __len__(self):
        """ returns the count of components of the given name
        """
        return len(self._components)

    def __iter__(self):
        """ iterate over all components
        """
        return self._components.itervalues()

    def __getitem__(self, name):
        """ returns the component of the given name
        """
        return self._components[name]

    def __contains__(self, name):
        """ returns whether a component of the given name exists
        """
        return name in self._components

    def component_names(self):
        """ returns the list of component names.
        
        Component names will have the same order than components
        """
        return self._components.keys()

    @property
    def defaults(self):
        """ component default component

        .. Note:: default components is just an indication for user and the
            views, except if the Block is required. If required then default is
            selected if nothing explisitely selected.
        """
        default = self._defaults
        # if require and no default, the first component as default
        if not len(default) and self.required and len(self._components):
            default = [self._components.itervalues().next().name]
        return default

    @defaults.setter
    def defaults(self, defaults):
        if isinstance(defaults, basestring):
            defaults = [defaults]
        for comp_name in defaults:
            if not comp_name in self._components:
                raise ValueError("Component '%s' doesn't exist it can be set as default." % comp_name)
        self._defaults = defaults

    def selected(self):
        """ returns the list of selected component names.

        if no component selected return the one marked as default.
        If the block is required and no component where indicated as default,
        then the first component is selected.
        """
        selected = self._selected
        if len(self._selected) == 0 and self.required:
            # nothing has been selected yet BUT the component is required
            selected = self.defaults
        return selected

    def as_dict(self):
        """ returns a dictionary representation of the block and of all
        component options
        """
        #TODO/FIXME: add selected information
        if self.hidden:
            rdict = {}
        else:
            def_selected = self.selected()
            comps = [
                {
                    'name': comp.name,
                    'default': comp.name in self.defaults,
                    'options': comp.get_ordered_options() if isinstance(comp, Optionable) else None
                }
                for comp in self
            ]
            rdict = {
                'name': self.name,
                'required': self.required,
                'multiple': self.multiple,
                'args': self.in_name,
                'returns': self.out_name,
                'components': comps
            }
        return rdict

    def reset(self):
        """ Removes all the components of the block
        """
        self._components = OrderedDict()
        self.clear_selections()

    def clear_selections(self):
        """ Reset the current selections and **reset option** values to default
        for all components
        
        .. Warning:: This method also reset the components options values to
            the defaults values.
        """
        self._selected = []
        for component in self._components.itervalues():
            if isinstance(component, Optionable):
                self._logger.info("'%s' clear selection an options for '%s'" % (self.name, component.name))
                component.clear_options_values()

    def setup(self, in_name=None, out_name=None, required=None, hidden=None,
                multiple=None, defaults=None):
        """ Set the options of the block.
        Only the not None given options are set

        .. note:: a block may have multiple inputs but have only one output (for now)

        :param in_name: name(s) of the block input data
        :type in_name: str or list of str
        :param out_name: name of the block output data
        :type out_name: str
        :param required: whether the block will be required or not
        :type required: bool
        :param hidden: whether the block will be hidden to the user or not
        :type hidden: bool
        :param multiple: if True more than one component may be selected/ run) 
        :type multiple: bool
        :param defaults: names of the selected components
        :type defaults: list of str, or str
        """
        if in_name is not None:
            self.in_name = in_name if type(in_name) ==list else [in_name]
        if out_name is not None:
            self.out_name = out_name
        if required is not None:
            self.required = required
        if hidden is not None:
            self.hidden = hidden
        if multiple is not None:
            self.multiple = multiple
        if defaults is not None:
            #if default is just a 'str' it is managed in setter
            self.defaults = defaults

    def set(self, *components):
        """ Set the possible components of the block
        
        :param components: components to append Optionables or Composables
        """
        self._logger.info("'%s' set components: \n\t%s", self.name, "\n\t".join(("'%s':%s" % (e.name, e) for e in components)))
        self.reset()
        if len(components) == 1:
            self.append(components[0])
        else:
            for comp in components:
                self.append(comp)

    def append(self, component, default=False):
        """ Add one component to the block
        
        :param default: if true this component will be use by default
        :type default: bool
        """
        if not isinstance(component, Composable):
            if callable(component):
                component = Composable(component)
            else:
                raise ValueError("component '%s' is not Optionable nor Composable and even not callable" % component)
        if component.name in self._components:
            raise ValueError("We already have a component with the name '%s'" % component.name)
        self._components[component.name] = component
        if default:
            if self.multiple:
                self.defaults = self.defaults + [component.name]
            else:
                self.defaults = component.name

    def select(self, comp_name, options=None):
        """ Select the components that will by played (with given options).

        `options` will be passed to :func:`.Optionable.parse_options` if the
        component is a subclass of :class:`Optionable`.

        .. Warning:: this function also setup the options (if given) of the
            selected component. Use :func:`clear_selections` to restore both
            selection and component's options.

        This method may be call at play 'time', before to call :func:`play` to
        run all selected components.

        :param name: name of the component to select
        :type comp_name: str
        :param options: options to set to the components
        :type options: dict
        """
        self._logger.info("select comp '%s' for block '%s' (options: %s)" % (comp_name, self._name, options))
        if comp_name not in self._components:
            raise ValueError("'%s' has no component '%s' (components are: %s)"\
                  % (self._name, comp_name, ", ".join(self.component_names())))
        if options is None:
            options = {}
        # get the componsent
        component = self._components[comp_name]
        # check options make sens
        if not isinstance(component, Optionable) and len(options):
            raise ValueError("the component %s is not optionable you can't provide options..." % comp_name)
        # add component as selected, aware of multiple
        if comp_name not in self._selected:
            if not self.multiple and len(self._selected):
                assert len(self._selected) == 1
                self._selected[0] = comp_name
            else:
                self._selected.append(comp_name)
        else:
            # TODO the component has already been selected
            pass
        # component might be a function or any callable
        # only Optionable will get options
        if isinstance(component, Optionable):
            component.set_options_values(options, parse=True, strict=True)

    def validate(self):
        """ check that the block can be run
        """
        if self.required and len(self.selected()) == 0:
            raise ReliureError("No component selected for block '%s'" % self.name)

    def play(self, *inputs): #XXX web: (*inputs, **named_inputs) in engine
        """ Run the selected components of the block. The selected components 
        are run with the already setted options.

        .. warning:: Defaut 'multiple' behavior is a **pipeline** !

        :param *inputs: arguments (i.e. inputs) to give to the components
        """
        # TODO: multi mode option(False, pipeline, map)
        self.validate() # TODO what if validate fails ?
        # intialise run meta data
        start = time.time()
        self.meta = PlayMeta(self.name)
        
        _break_on_error = True
        results = None
        # run
        for comp_name in self.selected():
            # get the component
            comp = self._components[comp_name]
            # get the options
            if isinstance(comp, Optionable):
                # note: we force the hidden values only if the call is not
                # decorated by a "check" (that already force the hidden values)
                force_hidden = not (hasattr(comp.__call__, '_checked') and comp.__call__._checked)
                options = comp.get_options_values(hidden=force_hidden)
            else:
                options = {}
            # prepare the Play meta data
            comp_meta_res = BasicPlayMeta(comp)
            # it is register right now to be sur to have the data if there is an exception
            self.meta.append(comp_meta_res)
            comp_meta_res.run_with(inputs, options)

            # some logging
            argstr = [repr(arg)[:100].replace('\n', '') for arg in inputs]
            self._logger.info("""'%s' playing: %s
                component: %s,
                args=%s,
                kwargs=%s""" % (self._name, comp.name, comp, "\n\t\t".join(argstr), options))

            # run the component !
            try:
                # multi = False or pipeline
                # given that the input is also the returning value
                # This behavior allows to modify the data given in input.
                # actually same arg if given several times 
                # but may be transformed during the process
                # then finally returned
                results = comp(*inputs, **options)
                #TODO: add validation on inputs name !

                # TODO implements different mode for multiple 
                # another way would be declaring a list var outside the loop,
                # then append result of each call to the components __call__
                # and finally returns all computed results
                #   map( lambda x : x(*arg), *components )
                # >>> results.append( comp(*args, **options) )
                # >>> return *results

            # TODO catch warnings TODO
            # warning may be raised for many reasons like:
            # * options has been modified
            # * deprecation
            # * pipeline inconsistency 
            # * invalid input (graph with no edge ...)
            except Exception as err:
                # component error handling
                comp_meta_res.add_error(err)
                self._logger.error("error in component '%s': %s\n%s" % (comp.name, err.message, traceback.format_exc()))
                if _break_on_error:
                    raise
            finally:
                # store component walltime
                now = time.time()
                comp_meta_res.time = now - start
                start = now
        #TODO: may return more than one value with multi=map 
        return results


class Engine(object):
    """ The Reliure engine.
    """
    
    DEFAULT_IN_NAME = 'input'   # default input name for first component
    
    def __init__(self, *names):
        """ Create the engine
        
        :param names: names of the engine blocks
        """
        self._logger = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self._blocks = OrderedDict()
        self._logger.info("\n\n\t\t\t ** ============= Init engine ============= ** \n")
        if len(names):
            self.requires(*names)

    def requires(self, *names):
        """ Declare what block will be used in this engine.

        It should be call before adding or setting any component.
        Blocks order will be preserved for runnning task.
        """
        if len(names) == 0:
            raise ValueError("You should give at least one block name")
    
        if self._blocks is not None and len(self._blocks) > 0:
            raise ReliureError("Method 'requires' should be called only once before adding any composant")
        for name in names:
            if name in self._blocks:
                raise ValueError("Duplicate block name %s" % name)
            self._blocks[name] = Block(name)
        self._logger.info(" ** requires ** %s", names)

    def set(self, name, *components, **parameters):
        """ Set available components and the options of one block.
        
        :param name: block name
        :param components: the components (see :meth:`Block.set`)
        :param parameters: block configuration (see :meth:`Block.setup`)
        
        for example :
        
        >>> engine = Engine("op1")
        >>> engine.set("op1", Composable(), required=True, in_name="query", out_name="holygrail")
        """
        self._logger.info(" ** SET ** '%s' "% name)

        if name not in self:
            raise ValueError("'%s' is not a block (%s)" % (name, ",".join(self.names())))
        self[name].set(*components)
        self[name].setup(**parameters)

    @property
    def in_name(self):
        """ Give the input name of the **first** block.
        
        If this first block is not required or if other block need some inputs
        then you beter have to look at :func:`needed_inputs`.
        """
        return iter(self).next().in_name or [Engine.DEFAULT_IN_NAME]

    def __contains__(self, name):
        """ Whether a block of the given name exists
        """
        return name in self._blocks

    def __getitem__(self, name):
        """ Get the block of the given name
        """
        if name not in self._blocks:
            raise ValueError("'%s' is not a block (%s)" % (name, ",".join(self.names())))
        return self._blocks[name]

    def __getattr__(self, name):
        """ Get the block of the given name
        """
        return self[name]

    def __len__(self):
        """ Returns block count
        """
        return len(self._blocks)

    def __iter__(self):
        """ Iterate over all blocks
        """
        return self._blocks.itervalues()

    def names(self):
        """ Returns the list of block names
        """
        return self._blocks.keys()

    def configure(self, config):
        """ Configure all the blocks from an (horible) configuration dictionary
        this data are coming from a json client request and has to be parsed.
        It takes the default value if missing (for component selection and 
        options).

        :param config: dictionary that give the component to use for each step
               and the associated options 
        :type config: dict

        `config` format ::

            {
                block_name: [{
                    'name': name_of_the_comp_to_use,
                    'options': {
                            name: value,
                            name: va...
                        }
                    },
                    {...}
                ]
           }
           
        .. warning:: values of options in this dictionnary are strings

        """
        self._logger.info("\n\n\t\t\t ** ============= configure engine ============= ** \n")
        # normalise input format
        for block_name in config.iterkeys():
            if isinstance(config[block_name], dict):
                config[block_name] = [config[block_name]]
        # check errors
        for block_name, request_comps in config.iteritems():
            if block_name not in self:
                raise ValueError("Block '%s' doesn't exist !" % block_name)
            block = self[block_name]
            if block.hidden and len(request_comps):
                raise ValueError("Component '%s' is hidden you can't change it's configuration from here" % block.name)
            if block.required and len(request_comps) == 0:
                raise ValueError("Component '%s' is required but None given" % block.name)
            # comp is given
            if not block.multiple and isinstance(request_comps, list) and len(request_comps) > 1:
                raise ValueError("Block '%s' allows only one component to be selected" % block.name)
            # check input dict
            for req_comp in request_comps:
                if 'name' not in req_comp:
                    raise ValueError("Config error in '%s' " % block.name)
                if req_comp['name'] not in block:
                    raise ValueError("Invalid component (%s) for block '%s' "
                        % (req_comp['name'], block.name))

        # clear the current selection and option
        for block in self:
            # remove selection and reset to default options
            block.clear_selections()
        # configure the blocks
        for block_name, request_comps in config.iteritems():
            block = self[block_name]
            # select and set options
            for req_comp in request_comps:
                block.select(req_comp['name'], req_comp.get("options", {}))

    def validate(self, inputs=None):
        """ Check that the blocks configuration is ok
        
        :param inputs: the names of the play inputs
        :type inputs: list of str
        """
        # if no blocks...
        if not len(self._blocks):
            #TODO: find better error than ReliureError ?
            raise ReliureError("There is no block in this engine")
        # it block should be ok with it-self
        for block in self:
            block.validate()
        # check the inputs and outputs
        # note: fornow only the first block can have user given input
        available = set()       # set of available data
        maybe_available = set() # data that are produced be not required blocks
        # add the first block input as available data
        if inputs is not None:
            for in_name in inputs:
                available.add(in_name)
        else:
            # no inputs given, then consider that the first block input will be given
            if self.in_name is not None:
                for in_name in self.in_name:
                    available.add(in_name)
            else:
                # default input name if nothing specified
                available.add(Engine.DEFAULT_IN_NAME)
        needed = self.needed_inputs()
        miss = needed.difference(available)
        if len(miss):
            raise ReliureError("The following inputs are needed and not given: %s" % (",".join("'%s'" % in_name for in_name in miss)))
        no_need = available.difference(needed)
        if len(no_need):
            raise ReliureError("The following inputs are given but not needed: %s" % (",".join("'%s'" % in_name for in_name in no_need)))
        return

    def needed_inputs(self):
        """ List all the needed inputs of a configured engine

        >>> engine = Engine("op1", "op2")
        >>> engine.op1.setup(in_name="in", out_name="middle", required=False)
        >>> engine.op2.setup(in_name="middle", out_name="out")
        >>> engine.op1.append(lambda x:x+2)
        >>> engine.op2.append(lambda x:x*2)
        >>> engine.op1.select('<lambda>')
        >>> engine.needed_inputs()
        set(['in'])

        But now if we unactivate the first component:

        >>> engine.op1.clear_selections()
        >>> engine.needed_inputs()
        set(['middle'])

        More complex example:

        >>> engine = Engine("op1", "op2")
        >>> engine.op1.setup(in_name="in", out_name="middle")
        >>> engine.op2.setup(in_name=["middle", "in2"], out_name="out")
        >>> engine.op1.append(lambda x:x+2)
        >>> engine.op2.append(lambda x, y:x*y)
        >>> engine.needed_inputs()
        set(['in2', 'in'])

        Note that by default the needed input is 'input':
        
        >>> engine = Engine("op1", "op2")
        >>> engine.op1.append(lambda x:x+2)
        >>> engine.op2.append(lambda x:x*2)
        >>> engine.needed_inputs()
        set(['input'])
        """
        needed = set()
        available = set()       # set of available data
        for bnum, block in enumerate(self):
            if not block.selected():    # if the block will not be used
                continue
            if block.in_name is not None:
                for in_name in block.in_name:
                    if not in_name in available:
                        needed.add(in_name)
            elif bnum == 0:
                # if the first block
                needed.add(Engine.DEFAULT_IN_NAME)
            # register the output
            available.add(block.out_name)
        return needed

    def play(self, *inputs, **named_inputs):
        """ Run the engine (that should have been configured first)
        
        if the `inputs` are given without name it should be the inputs of the
        first block, ig `named_inputs` are used it may be the inputs of any
        block.
        
        .. note:: Either `inputs` or `named_inputs` should be provided, not both
        
        :param inputs: the data to give as input to the first block
        :param named_inputs: named input data should match with
            :func:`needed_inputs` result.
        """
        self._logger.info("\n\n\t\t\t ** ============= play engine ============= ** \n")
        #
        # create data structure for results and metaresults
        results = OrderedDict()
        self.meta = PlayMeta("engine")
        ### manage inputs
        if len(inputs) and len(named_inputs):
            raise ValueError("Either `inputs` or `named_inputs` should be provided, not both !")
        # default input name (so also the default last_output_name)
        if len(inputs):
            # prepare the input data
            first_in_names = self.in_name or [Engine.DEFAULT_IN_NAME]
            if len(inputs) != len(first_in_names):
                raise ValueError("%d inputs are needed for first block, but %d given" % (len(first_in_names), len(inputs)))
            # inputs are store in results dict (then there is no special run for the first block)
            for input_num, in_name in enumerate(first_in_names):
                results[in_name] = inputs[input_num]
        else:
            results.update(named_inputs)
        #
        ## validate
        self.validate(results.keys())
        #
        ### run the blocks
        last_output_name = Engine.DEFAULT_IN_NAME
        for block in self:
            # continue if block is not selected (note: if require the validate should have faild before)
            if not len(block.selected()):
                continue
            # prepare block ipouts
            in_names = block.in_name or [last_output_name]
            # ^ note: if the block has no named input then the last block output is used
            inputs = [results[name] for name in in_names]
            # run the block
            try:
                results[block.out_name] = block.play(*inputs)
                # ^ note: le validate par rapport au type est fait dans le run du block
            finally:
                # store metadata
                self.meta.append(block.meta)
            last_output_name = block.out_name
        return results

    def as_dict(self):
        """ dict repr of the components """
        drepr = {
            'blocks': [
                block.as_dict() for block in self if block.hidden == False
            ],
            'args': list(self.needed_inputs())
        }
        return drepr

