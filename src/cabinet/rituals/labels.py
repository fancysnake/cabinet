"""Conjuration: ``labels`` brings the labels the other rituals need into being.

The steps live in ``cabinet.gates.ritual.vekna.labels``; this module is the
surface vekna sweeps, and the one place the services are wired.
"""

from cabinet.gates.ritual.vekna.labels import conjure, labels
from cabinet.inits.services import wire

wire()

__all__ = ["conjure", "labels"]
