"""
    pybatsim.plugin
    ~~~~~~~~~~~~~~~

    PyBatsim plugin interface.

    Register user-defined scheduler via the entry point mechanism.

    The following snippet shows how to register under the name
    ``yourschedulername`` the user-defined scheduler :py:class:`YourScheduler`
    defined in the module :py:mod:`yourscheduler`.

    .. code-block:: cfg

       [pybatsim.schedulers]
       yourschedulername = yourscheduler:YourScheduler


    Refer to the documentation of entry points of your packaging tool to
    register a scheduler.
"""

import collections
import sys

# selectable entry points were introduced in Python 3.10
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


SCHEDULER_ENTRY_POINT = 'pybatsim.schedulers'


def find_plugin_schedulers():
    """Yield the tuples (name, class) of registered schedulers."""
    for scheduler in entry_points(group=SCHEDULER_ENTRY_POINT):
        yield scheduler.name, scheduler.load()


def find_ambiguous_scheduler_names():
    """
    Return the dict of names bound to multiple schedulers.

    For each ambiguous name, the dict maps the name to the set of entry points
    values.
    """
    known_scheduler_names = collections.defaultdict(set)
    for scheduler in entry_points(group=SCHEDULER_ENTRY_POINT):
        known_scheduler_names[scheduler.name].add(scheduler.value)
    ambiguous_scheduler_names = {
        name: values
        for (name, values) in known_scheduler_names.items()
        if len(values) > 1
    }
    return ambiguous_scheduler_names
