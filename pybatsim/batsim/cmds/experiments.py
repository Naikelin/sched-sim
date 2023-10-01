'''
Run PyBatsim Experiments.

Usage:
    pybatsim-experiment <experiment> [options]

Options:
    --version                               Print the version of pybatsim and exit
    -h --help                               Show this help message and exit.
    -q --quiet                              Silent experiment output.
    -d --debug                              Print additional debug messages.
'''

import sys
import json

from docopt import docopt

from pybatsim.batsim.tools.experiments import launch_experiment
from pybatsim import __version__


def main():
    arguments = docopt(__doc__, version=__version__)

    verbose = not bool(arguments["--quiet"])
    debug = bool(arguments["--debug"])
    options_file = arguments["<experiment>"]

    try:
        with open(options_file) as f:
            options = json.loads(f.read())
    except FileNotFoundError:
        if debug:
            raise
        print("Experiment file does not exist: {}".format(
            options_file), file=sys.stderr)
        sys.exit(1)

    except Exception:
        if debug:
            raise
        print("Error in json file: {}".format(options_file), file=sys.stderr)
        sys.exit(1)

    options["options-file"] = options_file

    if verbose:
        print("Running experiment: {}".format(options_file))

    return launch_experiment(options, verbose=verbose)


if __name__ == "__main__":
    sys.exit(main())
