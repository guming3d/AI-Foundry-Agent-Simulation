from __future__ import annotations


class FoundryDemoError(RuntimeError):
    """Base error for this repo's demo application."""


class MissingDependencyError(FoundryDemoError):
    """Raised when optional dependencies are required but not installed."""

