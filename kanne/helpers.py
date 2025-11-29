from .vars import get_current_registry


def define_unit(definition: str | type) -> None:
    """Define a new unit in the current KanneRegistry."""
    registry = get_current_registry()
    return registry.define(definition)
