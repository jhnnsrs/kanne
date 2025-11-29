from typing import Annotated, Any
from pydantic import (
    BaseModel,
    BeforeValidator,
    GetCoreSchemaHandler,
    PlainSerializer,
    Field,
)
import pint
from pydantic_core import CoreSchema, core_schema

from kanne.vars import get_current_registry


def unit_validator(target_unit: str):
    """
    Returns a validator function that converts input to the target_unit
    and returns the float magnitude.
    """

    def validate(v: Any) -> pint.Quantity:
        # If it's already a number, assume it's already in the target unit
        if isinstance(v, (int, float)):
            quantity = pint.Quantity(v, target_unit)
            return quantity

        # If it's a string, let Pint parse and convert it
        if isinstance(v, str):
            quantity: pint.Quantity = get_current_registry()(v)
            return quantity

        if isinstance(v, pint.Quantity):
            return v

        raise ValueError(f"Invalid input format for {target_unit}")

    return validate


class PintQuantity(pint.Quantity):
    """A Pint Quantity subclass that integrates with Pydantic."""

    _class = None

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401
        handler: GetCoreSchemaHandler,  # noqa: ANN401
    ) -> CoreSchema:
        """Get the pydantic core schema for the validator function"""
        return core_schema.no_info_after_validator_function(
            cls.validate, handler(object)
        )

    @classmethod
    def validate(cls, v: Any) -> "PintQuantity":
        """Validate and convert input to PintQuantity"""
        if isinstance(v, pint.Quantity):
            return v
        raise TypeError("Invalid type for PintQuantity")


class Millisecond(PintQuantity):
    """A Pint Quantity subclass representing microseconds."""

    _class = None

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401
        handler: GetCoreSchemaHandler,  # noqa: ANN401
    ) -> CoreSchema:
        """Get the pydantic core schema for the validator function"""
        return core_schema.no_info_after_validator_function(
            cls.validate, handler(object)
        )

    @classmethod
    def validate(cls, v: Any) -> "PintQuantity":
        # If it's already a plain number, interpret it as milliseconds
        if isinstance(v, (int, float)):
            return cls(v, "millisecond")

        # If it's a string, let Pint parse it and convert to milliseconds
        if isinstance(v, str):
            quantity: pint.Quantity = get_current_registry()(v)
            q = quantity.to("millisecond")
            return cls(q.magnitude, "millisecond")

        # If it's already a Pint Quantity, convert to milliseconds
        if isinstance(v, pint.Quantity):
            q = v.to("millisecond")
            return cls(q.magnitude, "millisecond")

        raise ValueError("Invalid input format for Millisecond")


Micrometer = Annotated[PintQuantity, BeforeValidator(unit_validator("micrometer"))]
Microliter = Annotated[PintQuantity, BeforeValidator(unit_validator("microliter"))]
Milliliter = Annotated[PintQuantity, BeforeValidator(unit_validator("milliliter"))]
Microgram = Annotated[PintQuantity, BeforeValidator(unit_validator("microgram"))]
Milligram = Annotated[PintQuantity, BeforeValidator(unit_validator("milligram"))]
Gram = Annotated[PintQuantity, BeforeValidator(unit_validator("gram"))]
Kilogram = Annotated[PintQuantity, BeforeValidator(unit_validator("kilogram"))]
Second = Annotated[PintQuantity, BeforeValidator(unit_validator("second"))]
Hertz = Annotated[PintQuantity, BeforeValidator(unit_validator("hertz"))]
Ampere = Annotated[PintQuantity, BeforeValidator(unit_validator("ampere"))]
Picoampere = Annotated[PintQuantity, BeforeValidator(unit_validator("picoampere"))]


MillisecondCoercible = float | Millisecond
HertzCoercible = float | Hertz


# Elect

# --- 3. Usage in Pydantic ---


def serialize_quantity(unit: str) -> float:
    async def aserialize_quantity(q: PintQuantity) -> float:
        return q.to(unit).magnitude

    return aserialize_quantity


DEFAULT_COERCERS = {
    Millisecond: serialize_quantity("millisecond"),
}
