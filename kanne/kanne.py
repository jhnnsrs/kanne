from types import TracebackType
from typing import Any

from .registry import KanneRegistry
from pydantic import BaseModel, ConfigDict, Field
from .vars import set_current_registry, reset_current_registry
from .registry import get_global_registry


class Kanne(BaseModel):
    """Context manager that sets a `KanneRegistry` on entry and resets it on exit.
    by default, uses the global KanneRegistry.

    Example:
        registry = KanneRegistry()
        with Kanne(registry=registry):
            # registry is available via get_current_registry()
            ...
    """

    registry: KanneRegistry = Field(default_factory=get_global_registry)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # runtime token for contextvar reset
    _token: Any = None

    def __enter__(self) -> "Kanne":
        self._token = set_current_registry(self.registry)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # Ensure we always reset the token even if exceptions occur
        if self._token is not None:
            reset_current_registry(self._token)
            self._token = None
