import pytest
import pint
from pydantic import BaseModel

from kanne.kanne import Kanne
from kanne.scalars import (
    Duration,
    Frequency,
    Length,
    PintQuantity,
)


class Model(BaseModel):
    t: Duration
    f: Frequency


@pytest.fixture(autouse=True)
def _registry():
    """Bind a fresh registry for every test in this module."""
    from kanne.registry import KanneRegistry

    with Kanne(registry=KanneRegistry()):
        yield


# --- validation / coercion ------------------------------------------------


def test_validates_from_string_preserving_unit():
    m = Model(t="2 s", f="1 kHz")
    assert m.t.to("second").magnitude == pytest.approx(2.0)
    assert m.t.magnitude == pytest.approx(2.0)  # unit preserved: still seconds
    assert str(m.t.quantity.units) == "second"
    assert m.f.to("hertz").magnitude == pytest.approx(1000.0)


def test_validates_from_quantity_preserving_unit(_registry):
    q = pint.Quantity(3, "second")
    m = Model(t=q, f="5 Hz")
    assert m.t.to("millisecond").magnitude == pytest.approx(3000.0)
    assert str(m.t.quantity.units) == "second"


def test_validates_from_another_quantity_type():
    m = Model(t=Duration("1 s"), f="5 Hz")
    assert m.t.to("millisecond").magnitude == pytest.approx(1000.0)


def test_bare_number_is_rejected():
    with pytest.raises(Exception):
        Model(t=5, f="5 Hz")
    with pytest.raises(Exception):
        Duration(5)


def test_wrong_dimension_is_rejected():
    # A length is not a duration.
    with pytest.raises(Exception):
        Model(t="3 m", f="5 Hz")
    with pytest.raises(Exception):
        Duration("3 m")


def test_invalid_input_raises():
    with pytest.raises(Exception):
        Model(t=object(), f="5 Hz")


def test_subclass_without_reference_unit_is_rejected():
    with pytest.raises(TypeError):

        class Bad(PintQuantity):
            pass


# --- pydantic round-trip / serialization ----------------------------------


def test_serializes_as_pint_string():
    m = Model(t="2 s", f="1 kHz")
    assert m.model_dump() == {"t": "2 s", "f": "1 kHz"}


def test_serialization_preserves_input_unit():
    # The unit the user supplied round-trips — no normalization.
    assert Model(t="1 hour", f="50 Hz").model_dump() == {"t": "1 h", "f": "50 Hz"}


def test_json_schema_is_a_string():
    schema = Model.model_json_schema()
    assert schema["properties"]["t"]["type"] == "string"
    assert schema["properties"]["f"]["type"] == "string"


def test_round_trip_through_dump_and_validate():
    m = Model(t="2 s", f="5 Hz")
    again = Model.model_validate(m.model_dump())
    assert again.t == m.t
    assert again.t.to("second").magnitude == pytest.approx(2.0)


def test_round_trip_through_json():
    m = Model(t="1500 ms", f="1 kHz")
    again = Model.model_validate_json(m.model_dump_json())
    assert again.t == m.t
    assert again.f == m.f


def test_dump_json_emits_pint_strings():
    import json

    m = Model(t="2 s", f="1 kHz")
    js = m.model_dump_json()
    # Every field is a JSON string carrying the (unit-preserved) pint string.
    assert json.loads(js) == {"t": "2 s", "f": "1 kHz"}


def test_json_round_trip_preserves_non_ascii_unit_symbols():
    # Abbreviated pint symbols include non-ASCII (µ, Ω). They must survive a
    # JSON encode/decode round-trip intact.
    class W(BaseModel):
        d: Length

    with_micro = W(d="2.5 um")
    js = with_micro.model_dump_json()
    assert "µm" in js  # serialized with the micro sign, not "um"
    # The non-ASCII char is real UTF-8, not an \\uXXXX escape.
    assert "\\u" not in js
    back = W.model_validate_json(js)
    assert back.d == with_micro.d
    assert back.d.to("micrometer").magnitude == pytest.approx(2.5)


# --- dimensionful runtime behavior ----------------------------------------


def test_addition_is_dimensionful():
    result = Duration("5 ms") + Duration("1 s")
    assert isinstance(result, pint.Quantity)
    assert result.to("millisecond").magnitude == pytest.approx(1005.0)


def test_multiplication_and_conversion():
    result = (Duration("2000 ms") * 2).to("second")
    assert result.magnitude == pytest.approx(4.0)


def test_cross_unit_equality_compares_dimensionfully():
    assert Duration("1000 ms") == Duration("1 s")
    assert Duration("500 ms") < Duration("1 s")
    assert Duration("1 s") > Duration("500 ms")


def test_equality_against_bare_number_is_not_equal():
    # No canonical unit to compare a bare number against.
    assert (Duration("5 s") == 5.0) is False


def test_explicit_float_conversion_uses_own_unit():
    assert float(Duration("5 s")) == 5.0
    assert int(Duration("5 s")) == 5


def test_not_a_float_subclass():
    assert not isinstance(Duration("5 s"), float)
    assert isinstance(Duration("5 s"), PintQuantity)


# --- validate() classmethod -----------------------------------------------


def test_validate_from_string_preserves_unit():
    d = Duration.validate("2 s")
    assert isinstance(d, Duration)
    assert d.to("second").magnitude == pytest.approx(2.0)


def test_validate_from_other_quantity_type():
    d = Duration.validate(Duration("1 s"))
    assert isinstance(d, Duration)
    assert d.to("millisecond").magnitude == pytest.approx(1000.0)


def test_validate_from_quantity():
    d = Duration.validate(pint.Quantity(2, "second"))
    assert isinstance(d, Duration)
    assert d.to("second").magnitude == pytest.approx(2.0)


def test_validate_rejects_wrong_dimension():
    with pytest.raises(Exception):
        Length.validate("2 s")
