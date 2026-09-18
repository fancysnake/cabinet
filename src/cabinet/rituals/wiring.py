"""Binding the services, once, for every facade in this package.

The package's `__init__` re-exports this module, and Python imports a package
before any module inside it — so this runs before any facade's body, whichever
facade a project names, and runs exactly once.

Once is the point. Four facades each calling `wire()` bound four fresh
`Services()`, each throwing away the caches of the one before it, and which
binding a step ended up reading was an accident of import order. Nothing broke
only because the services hold nothing that matters yet.

A module of its own rather than two lines in `__init__`, which this project
holds to docstrings and re-exports.
"""

from cabinet.inits.services import wire

wire()
