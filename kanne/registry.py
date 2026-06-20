from typing import Any

import pint

GLOBAL_REGISTRY: "KanneRegistry | None" = None


class KanneRegistry(pint.UnitRegistry[Any]):
    """Custom Pint UnitRegistry for Kanne with predefined units."""


def get_global_registry() -> KanneRegistry:
    """Get or create the global KanneRegistry instance."""
    global GLOBAL_REGISTRY
    if GLOBAL_REGISTRY is None:
        # ``autoconvert_offset_to_baseunit`` lets offset units (degC, degF) be used
        # in multiplication and string parsing — so ``"37 degC"`` / ``37 * degC``
        # work like any other unit instead of raising OffsetUnitCalculusError.
        GLOBAL_REGISTRY = KanneRegistry(autoconvert_offset_to_baseunit=True)
    return GLOBAL_REGISTRY


def reset_global_registry() -> None:
    """Reset the global KanneRegistry instance."""
    global GLOBAL_REGISTRY
    GLOBAL_REGISTRY = None
