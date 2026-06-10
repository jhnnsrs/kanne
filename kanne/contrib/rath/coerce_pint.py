from rath.links.base import ContinuationLink
from rath.links.parsing import ParsingLink, Operation, apply_typemap_recursive
from pydantic import Field, BaseModel
from typing import Any, Callable, Dict, Awaitable
from kanne.scalars import DEFAULT_COERCERS


class CoercePintLink(ParsingLink):
    coercers: Dict[Any, Callable[[Any], Awaitable[Any]]] = Field(
        default=DEFAULT_COERCERS
    )

    async def aparse(self, operation: Operation) -> Operation:
        operation.variables = await apply_typemap_recursive(
            operation.variables, self.coercers
        )

        return operation
