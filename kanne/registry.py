import pint

GLOBAL_REGISTRY = None


class KanneRegistry(pint.UnitRegistry):
    """Custom Pint UnitRegistry for Kanne with predefined units."""


def get_global_registry() -> KanneRegistry:
    """Get or create the global KanneRegistry instance."""
    global GLOBAL_REGISTRY
    if GLOBAL_REGISTRY is None:
        GLOBAL_REGISTRY = KanneRegistry()
    return GLOBAL_REGISTRY


def reset_global_registry() -> None:
    """Reset the global KanneRegistry instance."""
    global GLOBAL_REGISTRY
    GLOBAL_REGISTRY = None
