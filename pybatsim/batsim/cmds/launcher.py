'''
Run PyBatsim Schedulers.

Usage:
    pybatsim <scheduler> [-o <options_string>] [options]

Options:
    --version                               Print the version of pybatsim and exit
    -h --help                               Show this help message and exit.
    -v --verbosity=<verbosity-level>        Sets the verbosity level. Available
                                            values are {debug, info, warning, error, critical}
                                            Default: info
    -s --socket-endpoint=<endpoint>         Batsim socket endpoint to use [default: tcp://*:28000]
    -e --event-socket-endpoint=<endpoint>   Socket endpoint to use to publish scheduler events
    -o --options=<options_string>           A Json string to pass to the scheduler [default: {}]
    -O --options-file=<options_file>        A file containing the json options
    -t --timeout=<timeout>                  How long to wait for responses from Batsim [default: 2000]
'''

import sys
import json
import logging

from docopt import docopt

from pybatsim.batsim.tools.launcher import launch_scheduler, instanciate_scheduler
from pybatsim import __version__

def main():
    arguments = docopt(__doc__, version=__version__)

    loglevel = logging.WARNING
    if not arguments['--verbosity']:
        loglevel = logging.INFO
    else:
        loglevel = logging.getLevelName(arguments['--verbosity'].upper())

    FORMAT = '[pybatsim - %(asctime)s - %(name)s - %(levelname)s] %(message)s'
    logging.basicConfig(format=FORMAT, level=loglevel)

    timeout = int(arguments['--timeout'] or float("inf"))

    if arguments["--options-file"]:
        with open(arguments["--options-file"]) as options_file:
            options = json.load(options_file)
    elif arguments["--options"]:
        options = json.loads(arguments['--options'])
    else:
        options = {}

    scheduler_filename = arguments['<scheduler>']
    socket_endpoint = arguments['--socket-endpoint']
    event_socket_endpoint = arguments['--event-socket-endpoint']

    scheduler = instanciate_scheduler(scheduler_filename, options=options)

    return launch_scheduler(scheduler,
                            socket_endpoint,
                            event_socket_endpoint,
                            options,
                            timeout)