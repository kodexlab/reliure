#-*- coding:utf-8 -*-
""" :mod:`reliure.utils.cli`
==========================

:copyright: (c) 2013 - 2014 by Yannick Chudy, Emmanuel Navarro.
:license: ${LICENSE}

Helper function to setup argparser from reliure components and engines
"""
import sys
import argparse

from reliure.pipeline import Optionable

from reliure.exceptions import ValidationError
from reliure.types import Boolean, Text, Numeric


def argument_from_option(parser, component, opt_name, prefix=""):
    """ Add an argparse argument to a parse from one option of one :class:`Optionable`

    >>> comp = Optionable()
    >>> comp.add_option("num", Numeric(default=1, max=12, help="An exemple of option"))
    >>> parser = argparse.ArgumentParser(prog="PROG")
    >>> argument_from_option(parser, comp, "num")
    >>> parser.print_help()
    usage: PROG [-h] [--num NUM]
    <BLANKLINE>
    optional arguments:
      -h, --help  show this help message and exit
      --num NUM   An exemple of option
    >>> parser.parse_args(["--num", "2"])
    Namespace(num=2)
    >>> parser.parse_args(["--num", "20"])
    Traceback (most recent call last):
    ...
    ValidationError: [u'Ensure this value ("20") is less than or equal to 12.']
    """
    assert component.has_option(opt_name)
    option = component.options[opt_name]
    argument_name = "%s%s" % (prefix, opt_name)
    otype = option.otype
    config = {}
    config["action"] = "store"
    config["dest"] = argument_name
    config["help"] = otype.help
    config["default"] = otype.default
    if otype.choices is not None:
        config["choices"] = otype.choices

    if isinstance(otype, Boolean):
        config["action"] = "store_true"
        if config["default"]:
            config["action"] = "store_false"
            # ADD a "not" in the name
            argument_name = "%snot-%s" % (prefix, opt_name)
    else:
        # Not boolean
        def check_type(value):
            try:
                value = option.parse(value)
                option.validate(value)
            except ValidationError as err_list:
                raise argparse.ArgumentTypeError("\n".join(err for err in err_list))
            return value
        config["type"] = check_type

    parser.add_argument(
        "--%s" % argument_name,
        **config
    )


def arguments_from_optionable(parser, component):
    """ Add argparse arguments from all options of one :class:`Optionable`

    >>> comp = Optionable()
    >>> comp.add_option("num", Numeric(default=1, max=12, help="An exemple of option"))
    >>> comp.add_option("title", Text(help="The title of the title"))
    >>> comp.add_option("ok", Boolean(help="is it ok ?", default=True))
    >>> comp.add_option("cool", Boolean(help="is it cool ?", default=False))
    >>> parser = argparse.ArgumentParser(prog="PROG")
    >>> arguments_from_optionable(parser, comp)
    >>> parser.print_help()
    usage: PROG [-h] [--num NUM] [--title TITLE] [--not-ok] [--cool]
    <BLANKLINE>
    optional arguments:
      -h, --help     show this help message and exit
      --num NUM      An exemple of option
      --title TITLE  The title of the title
      --not-ok       is it ok ?
      --cool         is it cool ?

    """
    for option in component.options:
        argument_from_option(parser, component, option)

