"""Registering every step, once, for every facade in this package.

A step registers when its module is imported, and vekna routes a payload to
whichever step is registered for its class. The package's `__init__` imports
this module, so the whole graph is registered before any facade's body, whichever
facade a project names.

A module of its own rather than imports in `__init__`: `identify` and `labels`
are step modules and facades both, and importing them by name there would
shadow the facades.
"""

from cabinet.gates.ritual.vekna import heal, identify, labels

__all__ = ["heal", "identify", "labels"]
