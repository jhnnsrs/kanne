import pytest
import pint
from kanne import Microgram, Milligram, Gram, Kilogram
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


def test_unit_validator_with_various_inputs():
    from kanne.registry import KanneRegistry
    from kanne.scalars import unit_validator

    registry = KanneRegistry()

    with Kanne(registry=registry):
        validate_micrometer = unit_validator("micrometer")

        # Numeric inputs are returned as floats unchanged
        assert validate_micrometer(5) == 5.0
        assert validate_micrometer(5.5) == 5.5

        # Strings are parsed by Pint and converted to the target unit
        assert validate_micrometer("1 mm") == pytest.approx(1000.0)

        # Pint Quantity input is converted
        q = registry("2 mm")
        assert validate_micrometer(q) == pytest.approx(2000.0)

        # Invalid input types raise
        with pytest.raises(ValueError):
            validate_micrometer(object())


def test_package_exports_and_registry_defaults():
    from kanne.registry import KanneRegistry

    # Basic export sanity
    assert Microgram is not None
    assert Milligram is not None
    assert Gram is not None
    assert Kilogram is not None

    # Registry defaults
    registry = KanneRegistry()
    q = registry("1 counts")
    assert isinstance(q, pint.Quantity)
    assert q.magnitude == 1
    # default_format and redefinition behavior
