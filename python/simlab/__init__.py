"""Compatibility alias for the renamed gan_simlab package."""

from __future__ import annotations

import importlib

_gan_simlab = importlib.import_module("gan_simlab")

__all__ = getattr(_gan_simlab, "__all__", [])
__path__ = list(getattr(_gan_simlab, "__path__", []))
__version__ = getattr(_gan_simlab, "__version__", None)


def __getattr__(name: str):
    return getattr(_gan_simlab, name)
