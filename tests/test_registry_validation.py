"""Tests for cross-registry validation in :func:`kanne.scalars._to_quantity`.

Pint refuses to mix quantities from different :class:`~pint.UnitRegistry` instances,
and the registry Kanne validates/serializes against is the one bound to the current
context. A quantity built from a *foreign* registry is therefore pinned onto the
current registry (re-expressed) on the way in — and if the current registry does not
define the unit, or defines it with a different dimensionality, that is caught loudly
instead of silently storing a value tied to the wrong registry.
"""

import pint
import pytest
from pydantic import BaseModel, ConfigDict

from kanne.kanne import Kanne
from kanne.registry import KanneRegistry, get_global_registry
from kanne.helpers import define_unit
from kanne.scalars import Duration, Length, ElectricPotential
import kanne.units as u


# --- same-registry: the common, no-op case --------------------------------


def test_quantity_from_current_registry_is_accepted_and_kept():
    current = KanneRegistry()
    with Kanne(registry=current):
        q = current.Quantity(5, "millisecond")
        d = Duration(q)
        assert d.to("millisecond").magnitude == pytest.approx(5.0)
        # The stored quantity belongs to the current registry (no re-binding needed).
        assert d.quantity._REGISTRY is current


# --- foreign registry, unit known here: re-expressed onto current ----------


def test_foreign_quantity_with_known_unit_is_rebound_to_current_registry():
    current = KanneRegistry()
    foreign = KanneRegistry()
    foreign_q = foreign.Quantity(5, "millisecond")

    with Kanne(registry=current):
        d = Duration(foreign_q)
        # Value/unit preserved...
        assert d.to_pint_string() == "5 ms"
        assert d.to("second").magnitude == pytest.approx(0.005)
        # ...but it is now pinned to the current registry, not the foreign one.
        assert d.quantity._REGISTRY is current
        assert d.quantity._REGISTRY is not foreign


def test_rebound_foreign_quantity_can_do_arithmetic_with_current_quantities():
    # The point of re-binding: Pint allows arithmetic only within one registry.
    current = KanneRegistry()
    foreign = KanneRegistry()
    with Kanne(registry=current):
        d = Duration(foreign.Quantity(5, "millisecond"))
        result = d + Duration("1 s")  # would raise if d stayed on the foreign registry
        assert result.to("millisecond").magnitude == pytest.approx(1005.0)


# --- foreign registry, unit unknown here: explicit error -------------------


def test_foreign_quantity_with_unknown_unit_raises():
    current = KanneRegistry()
    foreign = KanneRegistry()
    # A unit that exists only in the foreign registry (and is not a real pint unit).
    foreign.define("zorblat = 1 second")
    foreign_q = foreign.Quantity(5, "zorblat")

    with Kanne(registry=current):
        with pytest.raises(ValueError, match="different pint registry"):
            Duration(foreign_q)


def test_foreign_unknown_unit_error_names_the_unit():
    current = KanneRegistry()
    foreign = KanneRegistry()
    foreign.define("zorblat = 1 second")

    with Kanne(registry=current):
        with pytest.raises(ValueError, match="zorblat"):
            Duration(foreign.Quantity(5, "zorblat"))


# --- foreign registry, unit defined *differently* here: dimension error ----


def test_foreign_unit_defined_with_different_dimension_is_caught():
    # Same name, different meaning in each registry. Re-expressing onto the current
    # registry reinterprets the unit; the dimensionality check then rejects it.
    current = KanneRegistry()
    foreign = KanneRegistry()
    current.define("wibble = 1 meter")  # a length here
    foreign.define("wibble = 1 second")  # a time there
    foreign_q = foreign.Quantity(5, "wibble")

    with Kanne(registry=current):
        with pytest.raises(ValueError, match="dimensionality"):
            Duration(foreign_q)  # Duration wants [time]; current reads wibble as [length]


# --- the recommended path: kanne.units on the global registry --------------


def test_kanne_units_validate_as_noop_under_global_registry():
    # kanne.units are bound to the global registry; using the global registry as the
    # current one is the intended, footgun-free path — no re-binding, no error.
    with Kanne(registry=get_global_registry()):
        d = Duration(5 * u.ms)
        v = ElectricPotential(-70 * u.mV)
        assert d.quantity._REGISTRY is get_global_registry()
        assert d.to_pint_string() == "5 ms"
        assert v.to_pint_string() == "-70 mV"


def test_custom_unit_defined_on_current_registry_is_accepted():
    current = KanneRegistry()
    with Kanne(registry=current):
        define_unit("frame = 10 millisecond")
        d = Duration("3 frame")
        assert d.to("millisecond").magnitude == pytest.approx(30.0)


# --- serializer guard: a raw value assigned past coercion -----------------
# Pydantic coerces on construction but not on plain attribute assignment, so a raw
# value assigned to a field is only detected at serialization time. The guard turns
# the opaque pint AttributeError into an explicit, actionable error.


def test_to_pint_string_on_raw_quantity_raises_typeerror():
    with Kanne(registry=get_global_registry()):
        with pytest.raises(TypeError, match="Cannot serialize"):
            # Calling the serializer with a raw pint.Quantity (what a stray
            # attribute assignment would leave in the field).
            ElectricPotential.to_pint_string(5 * u.mV)


def test_to_pint_string_on_bare_number_reports_missing_unit():
    with Kanne(registry=get_global_registry()):
        with pytest.raises(TypeError, match="no unit attached"):
            ElectricPotential.to_pint_string(5.0)


def test_model_dump_after_raw_assignment_raises_explicit_error():
    class M(BaseModel):
        v: ElectricPotential

    with Kanne(registry=get_global_registry()):
        m = M(v="-70 mV")
        m.v = 5 * u.mV  # raw assignment bypasses coercion
        # Pydantic wraps the guard's TypeError, but the actionable message survives.
        with pytest.raises(Exception, match="Cannot serialize"):
            m.model_dump()


def test_validate_assignment_coerces_so_dump_succeeds():
    class M(BaseModel):
        model_config = ConfigDict(validate_assignment=True)
        v: ElectricPotential

    with Kanne(registry=get_global_registry()):
        m = M(v="-70 mV")
        m.v = 5 * u.mV  # coerced on assignment because validate_assignment=True
        assert isinstance(m.v, ElectricPotential)
        assert m.model_dump() == {"v": "5 mV"}
