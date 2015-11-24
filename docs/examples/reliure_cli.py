#!/usr/bin/env python
import sys

from reliure import Optionable
from reliure.types import Numeric

# definition of your component here
class PowerBy(Optionable):
    def __init__(self):
        super(PowerBy, self).__init__("testOptionableName")
        self.add_option("alpha", Numeric(default=4, min=1, max=20,
                        help='power exponent'))

    @Optionable.check
    def __call__(self, value, alpha=None):
        return value**alpha

# creation of your processing component
mycomp = PowerBy()

def main():
    from argparse import ArgumentParser
    from reliure.utils.cli import arguments_from_optionable, get_config_for

    # build the option parser
    parser = ArgumentParser()
    # Add options form your component
    arguments_from_optionable(parser, mycomp, prefix="power_")

    # Add other options, here the input ;
    parser.add_argument('INPUT', type=int, help='the number to process !')

    # Parse the options and get the config for the component
    args = parser.parse_args()
    config = get_config_for(args, mycomp, prefix="power_")

    result = mycomp(args.INPUT, **config)
    print(result)

    return 0

if __name__ == '__main__':
    sys.exit(main())
