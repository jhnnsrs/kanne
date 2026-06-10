import pytest
import pint
from pydantic import BaseModel

from typing import Optional

from kanne.kanne import Kanne
from kanne.scalars import (
    Millisecond,
    Second,
    Hertz,
    PintScalar,
    MillisecondCoercible,
)


class Model(BaseModel):
    t: Millisecond
    f: Hertz


class CoercibleModel(BaseModel):
    """Uses the coercible union so construction accepts raw values directly
    (this is what turms-generated models should use for the field type)."""

    t: MillisecondCoercible
    opt: Optional[MillisecondCoercible] = None


@pytest.fixture(autouse=True)
def _registry():
    """Bind a fresh registry for every test in this module."""
    from kanne.registry import KanneRegistry

    with Kanne(registry=KanneRegistry()):
        yield


# --- validation / coercion ------------------------------------------------


def test_validates_from_number_assumed_in_unit():
    m = Model(t=Millisecond(5), f=Hertz(10))
    assert m.t.magnitude == 5.0
    assert m.t.unit == "millisecond"
    assert m.f.magnitude == 10.0


def test_validates_from_string_and_converts_unit():
    m = Model(t="2 s", f="1 kHz")
    assert m.t.magnitude == pytest.approx(2000.0)  # 2 s -> 2000 ms
    assert m.f.magnitude == pytest.approx(1000.0)  # 1 kHz -> 1000 Hz


def test_validates_from_quantity_and_converts_unit(_registry):
    q = pint.Quantity(3, "second")
    m = Model(t=q, f=5)
    assert m.t.magnitude == pytest.approx(3000.0)


def test_validates_from_another_scalar():
    m = Model(t=Second(1), f=5)
    assert m.t.magnitude == pytest.approx(1000.0)


def test_invalid_input_raises():
    with pytest.raises(Exception):
        Model(t=object(), f=5)


def test_subclass_without_unit_is_rejected():
    with pytest.raises(TypeError):

        class Bad(PintScalar):
            pass


# --- pydantic round-trip / serialization ----------------------------------


def test_serializes_as_plain_float():
    m = Model(t="2 s", f=5)
    assert m.model_dump() == {"t": 2000.0, "f": 5.0}


def test_json_schema_is_a_number():
    schema = Model.model_json_schema()
    assert schema["properties"]["t"]["type"] == "number"
    assert schema["properties"]["f"]["type"] == "number"


def test_round_trip_through_dump_and_validate():
    m = Model(t="2 s", f=5)
    again = Model.model_validate(m.model_dump())
    assert again.t == m.t
    assert again.t.magnitude == pytest.approx(2000.0)


# --- dimensionful runtime behavior ----------------------------------------


def test_addition_is_dimensionful():
    result = Millisecond(5) + Second(1)
    assert isinstance(result, pint.Quantity)
    assert result.to("millisecond").magnitude == pytest.approx(1005.0)


def test_multiplication_and_conversion():
    result = (Millisecond(2000) * 2).to("second")
    assert result.magnitude == pytest.approx(4.0)


def test_cross_unit_equality_compares_dimensionfully():
    assert Millisecond(1000) == Second(1)
    assert Millisecond(500) < Second(1)
    assert Second(1) > Millisecond(500)


def test_equality_against_plain_number_uses_magnitude():
    assert Millisecond(5) == 5.0
    assert Millisecond(5) != 6.0


def test_explicit_float_conversion():
    assert float(Millisecond(5)) == 5.0
    assert int(Millisecond(5)) == 5


def test_not_a_float_subclass():
    # The standalone design intentionally is NOT substitutable for float.
    assert not isinstance(Millisecond(5), float)
    assert isinstance(Millisecond(5), PintScalar)


# --- coercible-union field (the turms-friendly field type) ----------------


def test_coercible_field_accepts_raw_number_and_coerces():
    # Model(t=5) type-checks AND coerces to Millisecond at runtime.
    m = CoercibleModel(t=5)
    assert isinstance(m.t, Millisecond)
    assert m.t.magnitude == 5.0


def test_coercible_field_accepts_string_and_coerces():
    m = CoercibleModel(t="2 s")
    assert isinstance(m.t, Millisecond)
    assert m.t.magnitude == pytest.approx(2000.0)


def test_coercible_field_accepts_quantity_via_scalar_validator():
    # A real Quantity flows through even though it isn't a union member.
    m = CoercibleModel(t=pint.Quantity(2, "second"))
    assert isinstance(m.t, Millisecond)
    assert m.t.magnitude == pytest.approx(2000.0)


def test_coercible_optional_field_default_and_value():
    # The optional case that breaks descriptors works with the union.
    assert CoercibleModel(t=1).opt is None
    m = CoercibleModel(t=1, opt=3)
    assert isinstance(m.opt, Millisecond)
    assert m.opt.magnitude == 3.0


def test_coercible_field_serializes_as_float():
    m = CoercibleModel(t="2 s", opt=3)
    assert m.model_dump() == {"t": 2000.0, "opt": 3.0}


# --- validate() classmethod -----------------------------------------------


def test_validate_from_number():
    ms = Millisecond.validate(5)
    assert isinstance(ms, Millisecond)
    assert ms.magnitude == 5.0


def test_validate_from_string_converts_unit():
    ms = Millisecond.validate("2 s")
    assert isinstance(ms, Millisecond)
    assert ms.magnitude == pytest.approx(2000.0)


def test_validate_from_other_scalar_converts_unit():
    ms = Millisecond.validate(Second(1))
    assert isinstance(ms, Millisecond)
    assert ms.magnitude == pytest.approx(1000.0)


def test_validate_from_quantity():
    ms = Millisecond.validate(pint.Quantity(2, "second"))
    assert isinstance(ms, Millisecond)
    assert ms.magnitude == pytest.approx(2000.0)


def test_validate_returns_subclass_type():
    # Each subclass's validate returns its own type, in its own unit.
    assert isinstance(Second.validate("500 ms"), Second)
    assert Second.validate("500 ms").magnitude == pytest.approx(0.5)
