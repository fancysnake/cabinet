"""The rituals a project casts, one facade per ritual.

Naming any facade in a `.vekna.toml` imports this package first. This package
imports `wiring`, which binds the services every step reaches, and `steps`,
which registers every step. Both happen once, before any cast, wherever a
project starts from.
"""

from cabinet.rituals import steps, wiring

__all__ = ["steps", "wiring"]
