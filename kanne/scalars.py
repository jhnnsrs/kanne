from typing import Any, Awaitable, Callable, ClassVar, TypeVar, Union

import pint
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from kanne.vars import get_current_registry

_S = TypeVar("_S", bound="PintScalar")

#: Anything that can be coerced into a scalar at runtime: a number (assumed to
#: already be in the scalar's unit), a unit string Pint can parse (``"2 s"``), an
#: existing :class:`pint.Quantity`, or another :class:`PintScalar`.
CoercibleValue = Union[float, int, str, "pint.Quantity[Any]", "PintScalar"]


def unit_validator(target_unit: str) -> Callable[[Any], float]:
    """Return a validator that coerces any *coercible* value into the float
    magnitude expressed in ``target_unit``.

    Kept as a standalone helper; the :class:`PintScalar` subclasses use the same
    coercion rules.
    """

    def validate(v: Any) -> float:  # noqa: ANN401
        return _to_magnitude(v, target_unit)

    return validate


def _to_magnitude(v: Any, target_unit: str) -> float:  # noqa: ANN401
    """Coerce a *coercible* value to a plain float magnitude in ``target_unit``.

    Coercible inputs are: a :class:`PintScalar`, an existing
    :class:`pint.Quantity`, a string Pint can parse (``"1 mm"``), or a number
    (assumed to already be in ``target_unit``).
    """
    if isinstance(v, PintScalar):
        return float(v.to(target_unit).magnitude)
    if isinstance(v, pint.Quantity):
        return float(v.to(target_unit).magnitude)
    if isinstance(v, str):
        return float(get_current_registry()(v).to(target_unit).magnitude)
    if isinstance(v, (int, float)):
        return float(v)
    raise ValueError(f"Invalid input format for {target_unit}: {v!r}")


def _as_operand(value: Any) -> Any:  # noqa: ANN401
    """Promote a :class:`PintScalar` to a real ``pint.Quantity`` for arithmetic;
    leave everything else (numbers, quantities) untouched so Pint handles it."""
    if isinstance(value, PintScalar):
        return value.quantity
    return value


class PintScalar:
    """A dimensionful scalar.

    It is a thin wrapper around a single ``float`` *magnitude* expressed in
    :attr:`unit`. For Pydantic (and therefore turms / JSON) it presents as an
    ordinary number: it validates from a number/string/quantity and serializes
    back to a float.

    At runtime it is dimensionful — arithmetic and comparison operators promote
    it to a real :class:`pint.Quantity` (using the registry bound to the current
    context)::

        ms = Millisecond(5)            # magnitude 5.0, unit "millisecond"
        float(ms)                      # 5.0 — what gets serialized
        ms + Second(1)                 # <Quantity(1005.0, 'millisecond')>
        (ms * 2).to("second")          # <Quantity(0.01, 'second')>
        Millisecond(1000) == Second(1) # True — compared dimensionfully

    Unlike a ``float`` subclass this is *not* substitutable for ``float``: pass
    it to a ``float``-typed API via :func:`float` or :attr:`magnitude` so the
    conversion (and any dimension loss) is explicit.
    """

    #: The unit this scalar's magnitude is expressed in. Subclasses must set it.
    unit: ClassVar[str] = ""

    __slots__ = ("_magnitude",)

    def __init__(self, value: "float | PintScalar | pint.Quantity[Any] | str") -> None:
        self._magnitude = _to_magnitude(value, self.unit)

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init_subclass__(**kwargs)
        if not cls.unit:
            raise TypeError(f"{cls.__name__} must define a non-empty `unit`")

    # -- numeric / pint bridge -----------------------------------------
    @property
    def magnitude(self) -> float:
        """The raw float magnitude in :attr:`unit`."""
        return self._magnitude

    @property
    def quantity(self) -> "pint.Quantity[Any]":
        """This scalar as a real :class:`pint.Quantity` in :attr:`unit`."""
        return get_current_registry().Quantity(self._magnitude, self.unit)

    def to(self, unit: str) -> "pint.Quantity[Any]":
        """Convert to ``unit`` and return a :class:`pint.Quantity`."""
        return self.quantity.to(unit)

    def __float__(self) -> float:
        return self._magnitude

    def __int__(self) -> int:
        return int(self._magnitude)

    def __bool__(self) -> bool:
        return bool(self._magnitude)

    def __hash__(self) -> int:
        return hash((type(self).unit, self._magnitude))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._magnitude!r})"

    # -- pydantic ------------------------------------------------------
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Validate from any coercible value into ``cls`` and serialize to float.

        The schema is built on a ``float`` core schema so the field is a plain
        ``number`` in the generated JSON schema (what turms expects).
        """
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.no_info_before_validator_function(
                cls._coerce_magnitude,
                core_schema.float_schema(),
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                float, return_schema=core_schema.float_schema()
            ),
        )

    @classmethod
    def _coerce_magnitude(cls, v: Any) -> float:  # noqa: ANN401
        return _to_magnitude(v, cls.unit)

    @classmethod
    def validate(cls: type[_S], value: CoercibleValue) -> _S:
        """Coerce any *coercible* value into an instance of this scalar.

        Accepts a number (assumed to be in :attr:`unit`), a unit string
        (``"2 s"``), a :class:`pint.Quantity`, or another :class:`PintScalar`;
        the result is always an instance of ``cls`` with its magnitude in
        :attr:`unit`::

            Millisecond.validate(5)                 # Millisecond(5.0)
            Millisecond.validate("2 s")             # Millisecond(2000.0)
            Millisecond.validate(Second(1))         # Millisecond(1000.0)

        This is the same coercion Pydantic applies, exposed for use outside a
        model (and as the hook turms can call to build the scalar).
        """
        return cls(value)

    # -- arithmetic (returns dimensionful pint.Quantity) ---------------
    def __add__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return self.quantity + _as_operand(other)

    def __radd__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return _as_operand(other) + self.quantity

    def __sub__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return self.quantity - _as_operand(other)

    def __rsub__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return _as_operand(other) - self.quantity

    def __mul__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return self.quantity * _as_operand(other)

    def __rmul__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return _as_operand(other) * self.quantity

    def __truediv__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return self.quantity / _as_operand(other)

    def __rtruediv__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return _as_operand(other) / self.quantity

    def __pow__(self, other: Any) -> "pint.Quantity[Any]":  # noqa: ANN401
        return self.quantity ** _as_operand(other)

    def __neg__(self) -> "pint.Quantity[Any]":
        return -self.quantity

    def __pos__(self) -> "pint.Quantity[Any]":
        return +self.quantity

    def __abs__(self) -> "pint.Quantity[Any]":
        return abs(self.quantity)

    # -- comparisons (dimensionful against quantity-like operands) -----
    def __eq__(self, other: object) -> bool:
        if isinstance(other, (PintScalar, pint.Quantity)):
            return bool(self.quantity == _as_operand(other))
        if isinstance(other, (int, float)):
            return self._magnitude == other
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other: Any) -> bool:  # noqa: ANN401
        if isinstance(other, (PintScalar, pint.Quantity)):
            return bool(self.quantity < _as_operand(other))
        return self._magnitude < other

    def __le__(self, other: Any) -> bool:  # noqa: ANN401
        if isinstance(other, (PintScalar, pint.Quantity)):
            return bool(self.quantity <= _as_operand(other))
        return self._magnitude <= other

    def __gt__(self, other: Any) -> bool:  # noqa: ANN401
        if isinstance(other, (PintScalar, pint.Quantity)):
            return bool(self.quantity > _as_operand(other))
        return self._magnitude > other

    def __ge__(self, other: Any) -> bool:  # noqa: ANN401
        if isinstance(other, (PintScalar, pint.Quantity)):
            return bool(self.quantity >= _as_operand(other))
        return self._magnitude >= other


# Backwards-compatible alias for the original base-class name.
PintQuantity = PintScalar


# --- Concrete unit scalars ------------------------------------------------
# Each is a real, importable class so turms can reference it by name.


class Millisecond(PintScalar):
    """Scalar whose magnitude is expressed in milliseconds."""

    unit = "millisecond"


class Second(PintScalar):
    """Scalar whose magnitude is expressed in seconds."""

    unit = "second"


class Micrometer(PintScalar):
    """Scalar whose magnitude is expressed in micrometers."""

    unit = "micrometer"


class Microliter(PintScalar):
    """Scalar whose magnitude is expressed in microliters."""

    unit = "microliter"


class Milliliter(PintScalar):
    """Scalar whose magnitude is expressed in milliliters."""

    unit = "milliliter"


class Microgram(PintScalar):
    """Scalar whose magnitude is expressed in micrograms."""

    unit = "microgram"


class Milligram(PintScalar):
    """Scalar whose magnitude is expressed in milligrams."""

    unit = "milligram"


class Gram(PintScalar):
    """Scalar whose magnitude is expressed in grams."""

    unit = "gram"


class Kilogram(PintScalar):
    """Scalar whose magnitude is expressed in kilograms."""

    unit = "kilogram"


class Hertz(PintScalar):
    """Scalar whose magnitude is expressed in hertz."""

    unit = "hertz"


class Ampere(PintScalar):
    """Scalar whose magnitude is expressed in amperes."""

    unit = "ampere"


class Picoampere(PintScalar):
    """Scalar whose magnitude is expressed in picoamperes."""

    unit = "picoampere"


# --- Coercible aliases ----------------------------------------------------
# Use these as the *field / input* annotation (e.g. in turms-generated models)
# so model construction accepts a coercible value directly::
#
#     class Op(BaseModel):
#         exposure: MillisecondCoercible   # Op(exposure=5) and Op(exposure="2 s")
#                                           # both type-check and coerce to Millisecond
#
# These are field-usable: every member has a Pydantic core schema, and Pydantic's
# smart union coerces the input to the scalar at runtime (verified). A read of the
# field is typed as the union — narrow with ``cast`` if you need the scalar type.
# A real ``pint.Quantity`` is intentionally *not* a member (it has no core schema
# and would break field generation); pass one as ``Millisecond(quantity)`` or rely
# on the scalar's own validator, which still accepts a Quantity at runtime.
Coercible = Union[float, int, str, PintScalar]

MillisecondCoercible = Union[Millisecond, float, int, str]
SecondCoercible = Union[Second, float, int, str]
MicrometerCoercible = Union[Micrometer, float, int, str]
MicroliterCoercible = Union[Microliter, float, int, str]
MilliliterCoercible = Union[Milliliter, float, int, str]
MicrogramCoercible = Union[Microgram, float, int, str]
MilligramCoercible = Union[Milligram, float, int, str]
GramCoercible = Union[Gram, float, int, str]
KilogramCoercible = Union[Kilogram, float, int, str]
HertzCoercible = Union[Hertz, float, int, str]
AmpereCoercible = Union[Ampere, float, int, str]
PicoampereCoercible = Union[Picoampere, float, int, str]


# --- Serialization helpers (used by the rath contrib link) ----------------


def serialize_quantity(unit: str) -> Callable[[PintScalar], Awaitable[float]]:
    """Build an async serializer that renders a scalar as its float magnitude
    in ``unit`` (e.g. for sending GraphQL variables)."""

    async def aserialize_quantity(q: PintScalar) -> float:
        return float(q.to(unit).magnitude)

    return aserialize_quantity


Coercer = Callable[[Any], Awaitable[Any]]

DEFAULT_COERCERS: dict[Any, Coercer] = {
    Millisecond: serialize_quantity("millisecond"),
    Second: serialize_quantity("second"),
    Micrometer: serialize_quantity("micrometer"),
    Microliter: serialize_quantity("microliter"),
    Milliliter: serialize_quantity("milliliter"),
    Microgram: serialize_quantity("microgram"),
    Milligram: serialize_quantity("milligram"),
    Gram: serialize_quantity("gram"),
    Kilogram: serialize_quantity("kilogram"),
    Hertz: serialize_quantity("hertz"),
    Ampere: serialize_quantity("ampere"),
    Picoampere: serialize_quantity("picoampere"),
}
