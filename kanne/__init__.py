# pyright: reportUnknownVariableType=false
# The re-exported ``*Coercible`` aliases contain ``pint.Quantity``, which resolves to
# a partially-unknown generic under strict type checkers; suppress at the import site.
from .scalars import (
    PintQuantity,
    PintScalar,
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
    CoercibleValue,
    Coercible,
    DurationCoercible,
    FrequencyCoercible,
    LengthCoercible,
    AreaCoercible,
    VolumeCoercible,
    VelocityCoercible,
    MassCoercible,
    TemperatureCoercible,
    AmountOfSubstanceCoercible,
    ConcentrationCoercible,
    ElectricCurrentCoercible,
    ElectricPotentialCoercible,
    ElectricChargeCoercible,
    CapacitanceCoercible,
    ElectricalConductanceCoercible,
    ElectricalResistanceCoercible,
    PowerCoercible,
    EnergyCoercible,
    PressureCoercible,
)
from .units import (
    registry,
    s, ms, us, ns, minute, hour,
    Hz, kHz, MHz,
    m, cm, mm, um, nm,
    L, mL, uL, nL,
    kg, g, mg, ug,
    K, degC,
    mol, mmol, umol, nmol,
    M, mM, uM, nM, pM,
    A, mA, uA, nA, pA,
    V, mV, uV,
    C, nC, pC,
    F, uF, nF, pF,
    S, mS, uS, nS,
    ohm, kohm, Mohm, Gohm,
    W, mW,
    J, mJ,
    Pa, kPa, bar,
)
from .helpers import define_unit
from .vars import get_current_registry

__all__ = [
    "define_unit",
    "get_current_registry",
    # base
    "PintQuantity",
    "PintScalar",
    # dimension types
    "Duration",
    "Frequency",
    "Length",
    "Area",
    "Volume",
    "Velocity",
    "Mass",
    "Temperature",
    "AmountOfSubstance",
    "Concentration",
    "ElectricCurrent",
    "ElectricPotential",
    "ElectricCharge",
    "Capacitance",
    "ElectricalConductance",
    "ElectricalResistance",
    "Power",
    "Energy",
    "Pressure",
    # coercible input aliases
    "CoercibleValue",
    "Coercible",
    "DurationCoercible",
    "FrequencyCoercible",
    "LengthCoercible",
    "AreaCoercible",
    "VolumeCoercible",
    "VelocityCoercible",
    "MassCoercible",
    "TemperatureCoercible",
    "AmountOfSubstanceCoercible",
    "ConcentrationCoercible",
    "ElectricCurrentCoercible",
    "ElectricPotentialCoercible",
    "ElectricChargeCoercible",
    "CapacitanceCoercible",
    "ElectricalConductanceCoercible",
    "ElectricalResistanceCoercible",
    "PowerCoercible",
    "EnergyCoercible",
    "PressureCoercible",
    # units registry
    "registry",
    # time
    "s", "ms", "us", "ns", "minute", "hour",
    # frequency
    "Hz", "kHz", "MHz",
    # length
    "m", "cm", "mm", "um", "nm",
    # volume
    "L", "mL", "uL", "nL",
    # mass
    "kg", "g", "mg", "ug",
    # temperature
    "K", "degC",
    # amount of substance
    "mol", "mmol", "umol", "nmol",
    # concentration
    "M", "mM", "uM", "nM", "pM",
    # electric current
    "A", "mA", "uA", "nA", "pA",
    # electric potential
    "V", "mV", "uV",
    # electric charge
    "C", "nC", "pC",
    # capacitance
    "F", "uF", "nF", "pF",
    # electrical conductance
    "S", "mS", "uS", "nS",
    # electrical resistance
    "ohm", "kohm", "Mohm", "Gohm",
    # power
    "W", "mW",
    # energy
    "J", "mJ",
    # pressure
    "Pa", "kPa", "bar",
]
