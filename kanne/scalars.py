# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
# pint's ``Quantity`` resolves to a partially-unknown generic under strict type
# checkers, so any annotation referencing it would otherwise be flagged here.
from typing import Any, Awaitable, Callable, ClassVar, TypeAlias, TypeVar, Union

import pint
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from kanne.vars import get_current_registry

_Q = TypeVar("_Q", bound="PintQuantity")

#: Anything that can be coerced into a dimension quantity at runtime: a unit-bearing
#: string Pint can parse (``"2 s"``), an existing :class:`pint.Quantity`, or another
#: :class:`PintQuantity`. A bare number is intentionally *not* coercible — without a
#: unit it is dimensionless and ambiguous.
CoercibleValue: TypeAlias = Union[str, "pint.Quantity[Any]", "PintQuantity"]


def _to_quantity(
    v: Any, cls: "type[PintQuantity]"
) -> "pint.Quantity[Any]":  # noqa: ANN401
    """Coerce a *coercible* value into a :class:`pint.Quantity` of the dimension
    declared by ``cls``, preserving whatever unit the value carries.

    Coercible inputs are: a :class:`PintQuantity`, an existing
    :class:`pint.Quantity`, or a unit-bearing string Pint can parse (``"1 mm"``).
    A bare number is rejected — there is no canonical unit to attach it to.
    """
    registry = get_current_registry()
    if isinstance(v, PintQuantity):
        q: "pint.Quantity[Any]" = v._quantity
    elif isinstance(v, pint.Quantity):
        q = v
    elif isinstance(v, str):
        q = registry(v)
    else:
        raise ValueError(
            f"Invalid input for {cls.__name__}: {v!r}. Pass a unit-bearing string "
            f'(e.g. "2 s"), a pint.Quantity, or another PintQuantity — not a bare number.'
        )
    # Pin the value onto the *current* registry. A quantity built from a different
    # pint.UnitRegistry may carry unit/dimension definitions that disagree with
    # ours, and Pint refuses arithmetic across registries — so a foreign quantity
    # would either break later or have its dimensionality compared unreliably
    # (the check below uses the current registry's notion of dimensions). Re-express
    # it here, and fail loudly now if the foreign registry defined the unit
    # differently — or not at all — instead of letting it slip through.
    q = _into_current_registry(q, registry, v, cls)
    expected = registry.get_dimensionality(cls.reference_unit)
    if q.dimensionality != expected:
        raise ValueError(
            f"{v!r} has dimensionality {q.dimensionality} but {cls.__name__} "
            f"requires {expected}"
        )
    return q


def _into_current_registry(
    q: "pint.Quantity[Any]",
    registry: Any,  # noqa: ANN401
    original: Any,  # noqa: ANN401
    cls: "type[PintQuantity]",
) -> "pint.Quantity[Any]":
    """Re-express ``q`` on ``registry`` if it came from a different one.

    A no-op when ``q`` already belongs to ``registry`` (the common case). Otherwise
    the unit is re-parsed against the current registry: if that registry defines the
    unit differently — a mismatched dimensionality is caught by the caller — or does
    not define it at all, raise an explicit error rather than store a value tied to a
    foreign registry.
    """
    if q._REGISTRY is registry:
        return q
    try:
        return registry.Quantity(q.magnitude, str(q.units))
    except pint.UndefinedUnitError as e:
        raise ValueError(
            f"{original!r} comes from a different pint registry: its unit "
            f"{str(q.units)!r} is not defined in {cls.__name__}'s registry, so the "
            "two registries describe units differently. Build the value from the "
            "current registry — e.g. units from `kanne.units` — rather than a "
            "separate pint.UnitRegistry()."
        ) from e


def _as_operand(value: Any) -> Any:  # noqa: ANN401
    """Promote a :class:`PintQuantity` to a real ``pint.Quantity`` for arithmetic;
    leave everything else (numbers, quantities) untouched so Pint handles it."""
    if isinstance(value, PintQuantity):
        return value.quantity
    return value


class PintQuantity:
    """A dimensionful quantity constrained to a single physical *dimension*.

    Unlike a unit-pegged scalar, a ``PintQuantity`` subclass is not tied to one
    unit: it accepts *any* value of the right dimensionality and preserves the unit
    it was given. The dimension is declared via :attr:`reference_unit` — a unit
    whose dimensionality defines what the type accepts (it is never used as a
    conversion target)::

        Duration("5 ms")              # <Quantity(5, 'millisecond')>, unit preserved
        Duration("1 hour")            # <Quantity(1, 'hour')>
        Duration("3 m")               # raises — wrong dimension
        Duration(5)                   # raises — bare numbers are ambiguous

    For Pydantic (and therefore turms / JSON) it presents as a **string**: it
    validates from a unit-bearing pint string and serializes back to one (abbreviated
    pint format, e.g. ``"5 ms"``), so the matching server library can parse it back
    into a real quantity.

    At runtime it is dimensionful — arithmetic and comparison operators promote it to
    a real :class:`pint.Quantity` (using the registry bound to the current context)::

        Duration("5 ms") + Duration("1 s")        # <Quantity(1005.0, 'millisecond')>
        (Duration("2 s") * 2).to("second")        # <Quantity(4.0, 'second')>
        Duration("1000 ms") == Duration("1 s")    # True — compared dimensionfully
    """

    #: A unit whose *dimensionality* defines what this type accepts. Subclasses must
    #: set it. It is NOT a conversion target — values keep the unit they were given.
    reference_unit: ClassVar[str] = ""

    __slots__ = ("_quantity",)

    def __init__(self, value: "CoercibleValue") -> None:
        self._quantity: "pint.Quantity[Any]" = _to_quantity(value, type(self))

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init_subclass__(**kwargs)
        if not cls.reference_unit:
            raise TypeError(f"{cls.__name__} must define a non-empty `reference_unit`")

    # -- numeric / pint bridge -----------------------------------------
    @property
    def quantity(self) -> "pint.Quantity[Any]":
        """This value as a real :class:`pint.Quantity`, in its own unit."""
        return self._quantity

    @property
    def magnitude(self) -> float:
        """The raw magnitude, in the value's own unit."""
        return float(self._quantity.magnitude)

    def to(self, unit: str) -> "pint.Quantity[Any]":
        """Convert to ``unit`` and return a :class:`pint.Quantity`."""
        return self._quantity.to(unit)

    def to_pint_string(self) -> str:
        """Render as an abbreviated pint string (the wire form), e.g. ``"5 ms"``.

        This doubles as the Pydantic serializer, so ``self`` is whatever sits in
        the field at dump time — which is *not* guaranteed to be a coerced
        :class:`PintQuantity`. Pydantic coerces on construction but not on plain
        attribute assignment, so a later ``obj.field = 5 * ureg.um`` stores the
        raw value untouched and it only blows up here. Detect that and raise an
        explicit error instead of the opaque ``'float' object has no attribute
        '_quantity'`` that Pint would surface.
        """
        if isinstance(self, PintQuantity):
            return f"{self._quantity:~}"
        if isinstance(self, pint.Quantity):
            cause = (
                f"a raw pint.Quantity ({self!r}) was assigned straight to the "
                "field. Pydantic only coerces on construction, so a later "
                "`obj.field = 5 * ureg.um` is stored as-is and never wrapped."
            )
        else:
            cause = (
                f"a bare {type(self).__name__} ({self!r}) reached the field with "
                "no unit attached."
            )
        raise TypeError(
            "Cannot serialize a dimension-quantity field: " + cause + " Build the "
            "value through the field so it gets coerced — pass a unit-bearing "
            'string ("5 um"), a pint.Quantity, or a unit from kanne.units — or set '
            "`validate_assignment=True` on the model so assignments are coerced too."
        )

    def __float__(self) -> float:
        return float(self._quantity.magnitude)

    def __int__(self) -> int:
        return int(self._quantity.magnitude)

    def __bool__(self) -> bool:
        return bool(self._quantity.magnitude)

    def __hash__(self) -> int:
        return hash((type(self).reference_unit, self._quantity))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.to_pint_string()!r})"

    # -- pydantic ------------------------------------------------------
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Validate from a unit-bearing pint string into ``cls`` and serialize back
        to an abbreviated pint string.

        The wire form is a ``string``: the generated JSON schema is a ``string`` (what
        turms expects) and JSON input must be a string — bare numbers are rejected. In
        Python an existing :class:`pint.Quantity` or :class:`PintQuantity` is also
        accepted.
        """
        ser = core_schema.plain_serializer_function_ser_schema(
            cls.to_pint_string,
            return_schema=core_schema.str_schema(),
            when_used="always",
        )
        return core_schema.json_or_python_schema(
            json_schema=core_schema.no_info_after_validator_function(
                cls._coerce, core_schema.str_schema()
            ),
            python_schema=core_schema.no_info_before_validator_function(
                cls._coerce, core_schema.any_schema()
            ),
            serialization=ser,
        )

    @classmethod
    def _coerce(cls: type[_Q], v: Any) -> _Q:  # noqa: ANN401
        return v if isinstance(v, cls) else cls(v)

    @classmethod
    def validate(cls: type[_Q], value: CoercibleValue) -> _Q:
        """Coerce any *coercible* value into an instance of this dimension type.

        Accepts a unit-bearing string (``"2 s"``), a :class:`pint.Quantity`, or
        another :class:`PintQuantity`; the unit is preserved and the dimensionality
        is checked. This is the same coercion Pydantic applies, exposed for use
        outside a model (and as the hook turms can call)::

            Duration.validate("2 s")          # Duration("2 s")
            Duration.validate("3 m")          # raises — wrong dimension
        """
        return cls(value)

    # -- arithmetic (returns dimensionful pint.Quantity) ---------------
    def __add__(self, other: Any) -> "pint.Quantity[Any]":  # pyright: ignore[reportUnknownMemberType] # noqa: ANN401
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
        if isinstance(other, (PintQuantity, pint.Quantity)):
            return bool(self.quantity == _as_operand(other))
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    def __lt__(self, other: Any) -> bool:  # noqa: ANN401
        return bool(self.quantity < _as_operand(other))

    def __le__(self, other: Any) -> bool:  # noqa: ANN401
        return bool(self.quantity <= _as_operand(other))

    def __gt__(self, other: Any) -> bool:  # noqa: ANN401
        return bool(self.quantity > _as_operand(other))

    def __ge__(self, other: Any) -> bool:  # noqa: ANN401
        return bool(self.quantity >= _as_operand(other))


# Backwards-compatible alias for the original base-class name.
PintScalar = PintQuantity


# --- Concrete dimension types ---------------------------------------------
# Each is a real, importable class so turms can reference it by name. Adding a new
# dimension is a one-liner: subclass and set `reference_unit` to any unit of that
# dimension (its *dimensionality* — not the unit itself — is what gets enforced).


class Duration(PintQuantity):
    """A quantity of time (``"5 ms"``, ``"2 s"``, ``"1 hour"``)."""

    reference_unit = "second"


class Frequency(PintQuantity):
    """A quantity of frequency (``"50 Hz"``, ``"1 kHz"``)."""

    reference_unit = "hertz"


class Length(PintQuantity):
    """A spatial length (``"2.5 µm"``, ``"1 mm"``, ``"3 m"``)."""

    reference_unit = "meter"


class Area(PintQuantity):
    """An area (``"4 µm ** 2"``, ``"2 mm^2"``)."""

    reference_unit = "meter ** 2"


class Volume(PintQuantity):
    """A volume (``"5 µL"``, ``"2 mL"``)."""

    reference_unit = "liter"


class Velocity(PintQuantity):
    """A velocity / speed (``"3 µm/s"``, ``"2 m/s"``)."""

    reference_unit = "meter / second"


class Mass(PintQuantity):
    """A mass (``"5 mg"``, ``"2 kg"``)."""

    reference_unit = "gram"


class Temperature(PintQuantity):
    """A temperature (``"310 K"``, ``"37 degC"``)."""

    reference_unit = "kelvin"


class AmountOfSubstance(PintQuantity):
    """An amount of substance (``"5 mmol"``, ``"2 mol"``)."""

    reference_unit = "mole"


class Concentration(PintQuantity):
    """A molar concentration (``"5 nM"``, ``"2 µM"``, ``"1 mM"``)."""

    reference_unit = "molar"


class ElectricCurrent(PintQuantity):
    """An electric current (``"5 pA"``, ``"2 nA"``)."""

    reference_unit = "ampere"


class ElectricPotential(PintQuantity):
    """An electric potential / voltage (``"-70 mV"``, ``"5 V"``)."""

    reference_unit = "volt"


class ElectricCharge(PintQuantity):
    """An electric charge (``"5 pC"``, ``"2 nC"``)."""

    reference_unit = "coulomb"


class Capacitance(PintQuantity):
    """A capacitance (``"5 pF"``, ``"100 nF"``)."""

    reference_unit = "farad"


class ElectricalConductance(PintQuantity):
    """An electrical conductance (``"5 nS"``, ``"2 µS"``)."""

    reference_unit = "siemens"


class ElectricalResistance(PintQuantity):
    """An electrical resistance (``"100 MΩ"``, ``"5 GΩ"``)."""

    reference_unit = "ohm"


class Power(PintQuantity):
    """A power (``"5 mW"``, ``"2 W"``)."""

    reference_unit = "watt"


class Energy(PintQuantity):
    """An energy (``"5 mJ"``, ``"2 J"``)."""

    reference_unit = "joule"


class Pressure(PintQuantity):
    """A pressure (``"5 kPa"``, ``"2 bar"``)."""

    reference_unit = "pascal"


class Resistivity(PintQuantity):
    """An axial resistivity (NEURON Ra, ``"35.4 Ω*cm"``, ``"100 Ω*cm"``)."""

    reference_unit = "ohm * centimeter"


class SpecificCapacitance(PintQuantity):
    """A specific membrane capacitance (NEURON cm, ``"1 µF/cm**2"``)."""

    reference_unit = "farad / centimeter ** 2"


# --- Coercible aliases ----------------------------------------------------
# Stable public names describing what each dimension type accepts as runtime input:
# a unit-bearing pint string (``"2 s"``), a :class:`pint.Quantity`, or another
# :class:`PintQuantity`. They are all :data:`CoercibleValue`.
#
# These are *input typing hints* — e.g. for the signature of a helper that builds a
# quantity — not Pydantic field annotations: ``CoercibleValue`` is a Union containing
# ``pint.Quantity``, which has no Pydantic core schema, so a model field annotated with
# one would fail to build. Use the dimension type directly as a field type
# (``exposure: Duration``); its validator already accepts a string and coerces it.
Coercible: TypeAlias = CoercibleValue

DurationCoercible: TypeAlias = CoercibleValue
FrequencyCoercible: TypeAlias = CoercibleValue
LengthCoercible: TypeAlias = CoercibleValue
AreaCoercible: TypeAlias = CoercibleValue
VolumeCoercible: TypeAlias = CoercibleValue
VelocityCoercible: TypeAlias = CoercibleValue
MassCoercible: TypeAlias = CoercibleValue
TemperatureCoercible: TypeAlias = CoercibleValue
AmountOfSubstanceCoercible: TypeAlias = CoercibleValue
ConcentrationCoercible: TypeAlias = CoercibleValue
ElectricCurrentCoercible: TypeAlias = CoercibleValue
ElectricPotentialCoercible: TypeAlias = CoercibleValue
ElectricChargeCoercible: TypeAlias = CoercibleValue
CapacitanceCoercible: TypeAlias = CoercibleValue
ElectricalConductanceCoercible: TypeAlias = CoercibleValue
ElectricalResistanceCoercible: TypeAlias = CoercibleValue
PowerCoercible: TypeAlias = CoercibleValue
EnergyCoercible: TypeAlias = CoercibleValue
PressureCoercible: TypeAlias = CoercibleValue
ResistivityCoercible: TypeAlias = CoercibleValue
SpecificCapacitanceCoercible: TypeAlias = CoercibleValue


# --- Serialization helpers (used by the rath contrib link) ----------------


async def aserialize_pint(q: PintQuantity) -> str:
    """Render a dimension quantity as its abbreviated pint string for the wire
    (e.g. when sending GraphQL variables). The unit is preserved."""
    return q.to_pint_string()


Coercer = Callable[[Any], Awaitable[Any]]

#: Map every dimension type to the shared string serializer. Serialization no longer
#: depends on a target unit, so they all share :func:`aserialize_pint`.
DEFAULT_COERCERS: dict[Any, Coercer] = {
    cls: aserialize_pint
    for cls in (
        Duration,
        Frequency,
        Length,
        Area,
        Volume,
        Velocity,
        Mass,
        Temperature,
        AmountOfSubstance,
        Concentration,
        ElectricCurrent,
        ElectricPotential,
        ElectricCharge,
        Capacitance,
        ElectricalConductance,
        ElectricalResistance,
        Power,
        Energy,
        Pressure,
        Resistivity,
        SpecificCapacitance,
    )
}
