import pytest
import pint
from kanne import Mass, Duration, Length, ElectricPotential
from kanne.kanne import Kanne


def test_get_current_registry_raises_when_unset():
    from kanne.vars import current_kanne_registry, get_current_registry

    # Ensure the context var is explicitly None for this test
    token = current_kanne_registry.set(None)
    try:
        with pytest.raises(RuntimeError):
            get_current_registry(allow_global=False)
    finally:
        current_kanne_registry.reset(token)


def test_define_unit_and_registry_parsing():
    from kanne.registry import KanneRegistry
    from kanne.helpers import define_unit
    from kanne.kanne import Kanne

    registry = KanneRegistry()
    # Use Kanne as the context manager to set the registry
    with Kanne(registry=registry):
        # Define a simple custom unit and verify the registry parses it
        define_unit("fo = 1")
        define_unit("foos = 3 fo")
        q = registry("3 fo")
        assert isinstance(q, pint.Quantity)
        assert q.magnitude == 3
        assert str(q.units) == "fo"


def test_to_quantity_with_various_inputs():
    from kanne.registry import KanneRegistry
    from kanne.scalars import _to_quantity

    registry = KanneRegistry()

    with Kanne(registry=registry):
        # Strings are parsed by Pint, unit preserved
        q = _to_quantity("1 mm", Length)
        assert q.to("micrometer").magnitude == pytest.approx(1000.0)

        # Pint Quantity input flows through, unit preserved
        q = _to_quantity(registry("2 mm"), Length)
        assert q.to("micrometer").magnitude == pytest.approx(2000.0)

        # Bare numbers are rejected (ambiguous without a unit)
        with pytest.raises(ValueError):
            _to_quantity(5, Length)

        # Wrong dimension is rejected
        with pytest.raises(ValueError):
            _to_quantity("2 s", Length)

        # Invalid input types raise
        with pytest.raises(ValueError):
            _to_quantity(object(), Length)


def test_package_exports_and_registry_defaults():
    from kanne.registry import KanneRegistry

    # Basic export sanity
    assert Mass is not None
    assert Duration is not None
    assert Length is not None
    assert ElectricPotential is not None

    # Registry defaults
    registry = KanneRegistry()
    q = registry("1 counts")
    assert isinstance(q, pint.Quantity)
    assert q.magnitude == 1
    # default_format and redefinition behavior
