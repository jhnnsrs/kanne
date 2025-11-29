from contextvars import ContextVar, Token
from kanne.registry import KanneRegistry, get_global_registry


current_kanne_registry: ContextVar[KanneRegistry | None] = ContextVar(
    "current_kanne_registry", default=None
)


def get_current_registry(allow_global: bool = True) -> KanneRegistry:
    """Get the current KanneRegistry from context, or create a new one."""
    registry = current_kanne_registry.get()
    if registry is None:
        if allow_global:
            registry = get_global_registry()
            return registry
        else:
            raise RuntimeError(
                "No KanneRegistry found in context. This is undefined behavior. Create and set a KanneRegistry before using Kanne or set allow_global=True."
            )
    return registry


def set_current_registry(registry: KanneRegistry) -> Token["KanneRegistry | None"]:
    """Set the current KanneRegistry in context."""
    return current_kanne_registry.set(registry)


def reset_current_registry(token: Token["KanneRegistry | None"]) -> None:
    """Reset the current KanneRegistry in context."""
    current_kanne_registry.reset(token)
