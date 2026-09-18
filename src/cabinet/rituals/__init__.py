"""The rituals a project casts, one facade per ritual.

Naming any facade in a `.vekna.toml` imports this package first, and this
package imports `wiring` — which is where the services every step reaches are
bound. The binding happens once, before any cast, wherever a project starts
from.
"""

from cabinet.rituals import wiring

__all__ = ["wiring"]
