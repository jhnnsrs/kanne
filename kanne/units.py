"""Common physical units, pre-bound to Kanne's **global** registry.

Importing units from here avoids the most common footgun with Pint: building
quantities from a *separate* :class:`~pint.UnitRegistry`. Pint will not let you
mix quantities from different registries, and a stray ``pint.UnitRegistry()`` is
not the registry Kanne validates and serializes against — so a value built from
it can slip into a model field unconverted and blow up only at serialization
time. Everything here comes from :func:`kanne.registry.get_global_registry`, so
arithmetic with these units yields quantities Kanne already understands::

    from kanne.units import mV, ms, um, pA

    v_init = -70 * mV          # <Quantity(-70, 'millivolt')>
    exposure = 5 * ms          # <Quantity(5, 'millisecond')>
    amp = 100 * pA             # <Quantity(100, 'picoampere')>

Each name is a unit *quantity* of magnitude 1 (e.g. ``mV`` is one millivolt),
so the idiomatic ``number * unit`` produces a dimensionful
:class:`pint.Quantity` that a :class:`~kanne.scalars.PintQuantity` field
(``ElectricPotential``, ``Duration``, ...) will accept and coerce.

To define your own units, use :func:`kanne.helpers.define_unit` (it registers
on the current registry) and read them back off :data:`registry`.
"""

from kanne.registry import get_global_registry

#: The global :class:`~kanne.registry.KanneRegistry` every unit below is bound to.
registry = get_global_registry()


def _u(name: str):
    """One unit ``name`` as a quantity drawn from the global registry.

    Deliberately unannotated: the result is a :class:`pint.Quantity`, but pint's
    ``Quantity`` resolves to a partially-unknown generic under strict type checkers,
    so annotating it would flag every unit below. Leaving ``getattr``'s ``Any`` to
    propagate keeps the public unit names clean.
    """
    return getattr(registry, name)


# -- time ----------------------------------------------------------------
s = _u("second")
ms = _u("millisecond")
us = _u("microsecond")
ns = _u("nanosecond")
minute = _u("minute")
hour = _u("hour")

# -- frequency -----------------------------------------------------------
Hz = _u("hertz")
kHz = _u("kilohertz")
MHz = _u("megahertz")

# -- length --------------------------------------------------------------
m = _u("meter")
cm = _u("centimeter")
mm = _u("millimeter")
um = _u("micrometer")
nm = _u("nanometer")

# -- volume --------------------------------------------------------------
L = _u("liter")
mL = _u("milliliter")
uL = _u("microliter")
nL = _u("nanoliter")

# -- mass ----------------------------------------------------------------
kg = _u("kilogram")
g = _u("gram")
mg = _u("milligram")
ug = _u("microgram")

# -- temperature ---------------------------------------------------------
K = _u("kelvin")
degC = _u("degC")

# -- amount of substance -------------------------------------------------
mol = _u("mole")
mmol = _u("millimole")
umol = _u("micromole")
nmol = _u("nanomole")

# -- concentration -------------------------------------------------------
M = _u("molar")
mM = _u("millimolar")
uM = _u("micromolar")
nM = _u("nanomolar")
pM = _u("picomolar")

# -- electric current ----------------------------------------------------
A = _u("ampere")
mA = _u("milliampere")
uA = _u("microampere")
nA = _u("nanoampere")
pA = _u("picoampere")

# -- electric potential --------------------------------------------------
V = _u("volt")
mV = _u("millivolt")
uV = _u("microvolt")

# -- electric charge -----------------------------------------------------
C = _u("coulomb")
nC = _u("nanocoulomb")
pC = _u("picocoulomb")

# -- capacitance ---------------------------------------------------------
F = _u("farad")
uF = _u("microfarad")
nF = _u("nanofarad")
pF = _u("picofarad")

# -- electrical conductance ----------------------------------------------
S = _u("siemens")
mS = _u("millisiemens")
uS = _u("microsiemens")
nS = _u("nanosiemens")

# -- electrical resistance -----------------------------------------------
ohm = _u("ohm")
kohm = _u("kiloohm")
Mohm = _u("megaohm")
Gohm = _u("gigaohm")

# -- power ---------------------------------------------------------------
W = _u("watt")
mW = _u("milliwatt")

# -- energy --------------------------------------------------------------
J = _u("joule")
mJ = _u("millijoule")

# -- pressure ------------------------------------------------------------
Pa = _u("pascal")
kPa = _u("kilopascal")
bar = _u("bar")


__all__ = [
    "registry",
    # time
    "s",
    "ms",
    "us",
    "ns",
    "minute",
    "hour",
    # frequency
    "Hz",
    "kHz",
    "MHz",
    # length
    "m",
    "cm",
    "mm",
    "um",
    "nm",
    # volume
    "L",
    "mL",
    "uL",
    "nL",
    # mass
    "kg",
    "g",
    "mg",
    "ug",
    # temperature
    "K",
    "degC",
    # amount of substance
    "mol",
    "mmol",
    "umol",
    "nmol",
    # concentration
    "M",
    "mM",
    "uM",
    "nM",
    "pM",
    # electric current
    "A",
    "mA",
    "uA",
    "nA",
    "pA",
    # electric potential
    "V",
    "mV",
    "uV",
    # electric charge
    "C",
    "nC",
    "pC",
    # capacitance
    "F",
    "uF",
    "nF",
    "pF",
    # electrical conductance
    "S",
    "mS",
    "uS",
    "nS",
    # electrical resistance
    "ohm",
    "kohm",
    "Mohm",
    "Gohm",
    # power
    "W",
    "mW",
    # energy
    "J",
    "mJ",
    # pressure
    "Pa",
    "kPa",
    "bar",
]
