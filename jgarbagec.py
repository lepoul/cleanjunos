#!/usr/bin/python

"""

A cli tool using junosgc
~~~~~~~~~~~~~~~~~~~~~~~~

Finds garbage configuration on a JunOS device

'garbage' refers to specific configuration items

Defined prefix-lists that are not referenced into
any firewall filter and policy are considered 'garbage'

Defined firewall filters that are not referenced into
any interface configuration are considered 'garbage'


"""

from module_utils.junosgc import *
import argparse
import logging

description = """

jgarbagec is a cli tool to collect given JunOS configuration 'garbages'

"""

epilog = """

EXAMPLE: 

jgarbagec --device='example.com' --garbage='prefix-lists' --verbose=DEBUG
jgarbagec -d 'example.com' -g path/to/my_xpaths.yml -vvvv

"""

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description=description, epilog=epilog)
parser.add_argument('--garbages', '-g', dest='garbages', help='the path to a .yml file with the'
                                                             'XPaths definitions to collect')
parser.add_argument('-d', '--device', dest='dev', help='Hostname/IP of the device to run garbage collection on')
parser.add_argument('--verbose', '-v', help='Verbosity level', action='count')
parser.add_argument('--output', '-o', dest='file', help='Path to store the delete commands created')
parser.add_argument('--extra-file', '-e', dest='extra_file', help='Path to a list of immunes')

_args = parser.parse_args()

logger = logging.getLogger('logger')

if _args.verbose is not None:
    if _args.verbose == 1:
        level = logging.INFO
    elif _args.verbose == 2:
        level = logging.ERROR
    elif _args.verbose >= 3:
        level = logging.DEBUG
    else:
        logging.ERROR('Wrong logging level')
        level = None
    if level is not None:
        logging.basicConfig(level=level)


def junos_cleaner(args):

    col = Collector(host=args.dev, defs=args.garbages, extra_file=args.extra_file)
    cleaner = Cleaner(col, args.file)
    cleaner.create_deletes()


if __name__ == '__main__':
    junos_cleaner(_args)
