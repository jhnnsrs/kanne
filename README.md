# kanne

[![codecov](https://codecov.io/gh/jhnnsrs/kanne/branch/master/graph/badge.svg?token=UGXEA2THBV)](https://codecov.io/gh/jhnnsrs/kanne)
[![PyPI version](https://badge.fury.io/py/kanne.svg)](https://pypi.org/project/kanne/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/kanne.svg)](https://pypi.python.org/pypi/kanne/)
[![PyPI status](https://img.shields.io/pypi/status/kanne.svg)](https://pypi.python.org/pypi/kanne/)
[![PyPI download day](https://img.shields.io/pypi/dm/kanne.svg)](https://pypi.python.org/pypi/kanne/)

Quick: is `0.0000001` one nanosecond? (...how many nanoseconds *are* in a second
again?) A bare number is a riddle. **kanne** makes you write `"100 ns"` and keeps it
that way — across Pydantic, JSON, GraphQL, the whole trip.

```python
from kanne import Duration, Length
from kanne.kanne import Kanne
from pydantic import BaseModel


class Acquisition(BaseModel):
    exposure: Duration      # any time, your choice of unit
    pixel_size: Length      # any length


with Kanne():
    a = Acquisition(exposure="100 ms", pixel_size="2.5 um")

    a.model_dump()              # {'exposure': '100 ms', 'pixel_size': '2.5 µm'}
    a.exposure.to("s")          # <Quantity(0.1, 'second')>  — convert when *you* ask
    a.exposure + a.pixel_size   # 💥 can't add a time to a length
    Acquisition(exposure=100, pixel_size="1 m")   # 💥 100 what?
    Acquisition(exposure="3 m", pixel_size="1 m") # 💥 a metre isn't a duration
```

Fields are typed by **dimension** (`Duration`, `Length`, `ElectricPotential`), not by a
fixed unit. They take any unit of the right dimension, keep the one you gave, and reject
bare numbers and nonsense at the door.

## The point

One value, one self-describing token. No second `_unit` field to drift out of sync, no
"everyone just knows it's milliseconds" convention living in a docstring:

```jsonc
{ "exposure": 1500, "exposure_unit": "ms" }   // 😬 two facts, can desync
{ "exposure": "1500 ms" }                      // 🎉 one fact, can't
```

And **provenance**: if the user typed `100 ms`, it stays `100 ms` — not `0.1 s`, not
`2.4999999999999996` from a round-trip through some base unit. The number you sent is
the number that arrives, bit for bit. Convert only when you mean to.

> **kanne is a wire protocol, not a database protocol.** It moves quantities across
> boundaries intact. Storing them is the backend's job:
> [`kanne_server`](https://github.com/jhnnsrs) splits each value into `{magnitude, unit}`
> columns so SQL can `SUM()`/`AVG()`/range-query the number while keeping the original
> unit, and the GraphQL API serves it back either way — `duration` as the Pint string,
> `durationAs("ms")` as a plain number for clients that don't speak Pint. So: **send the
> string, store the pair.**

## "Why not just store milliseconds as a float?"

Honestly? Often you should. A float is tiny, numeric, dependency-free, and a fixed unit
is a perfectly good contract — NEURON runs the world's biophysical models on exactly
that (`dt`, `v`, `tstop` = ms, mV) at huge scale. *Inside* a component that agrees on
the unit, the float wins, and that's literally how `kanne_server` stores things.

The float only cracks at the **boundary**, where the "it's in ms" convention has to
travel out-of-band and isn't in the data:

- **Wrong-unit bugs are silent.** A reader assumes seconds, lands 1000× off, nothing
  complains. kanne raises instead.
- **Your canonical unit ages badly.** ms → µs spike timing, µm → nm optics, nM → pM
  assays — every resolution bump means awkward sub-unit floats or a lockstep migration.
  `"25 ns"` just... still works.

Float between your own functions; self-describing quantity between systems. kanne is
only about the second half.

## Install

```bash
uv add kanne
```

## Built-in dimensions

Each is a real importable class (so codegen can name it), accepting any unit of its
dimension:

| Type | e.g. | Type | e.g. |
| --- | --- | --- | --- |
| `Duration` | `"5 ms"` | `ElectricCurrent` | `"5 pA"` |
| `Frequency` | `"1 kHz"` | `ElectricPotential` | `"-70 mV"` |
| `Length` | `"2.5 µm"` | `ElectricCharge` | `"2 nC"` |
| `Area` | `"4 µm**2"` | `Capacitance` | `"100 nF"` |
| `Volume` | `"5 µL"` | `ElectricalConductance` | `"2 µS"` |
| `Velocity` | `"3 µm/s"` | `ElectricalResistance` | `"100 MΩ"` |
| `Mass` | `"5 mg"` | `Power` | `"5 mW"` |
| `Temperature` | `"37 degC"` | `Energy` | `"5 mJ"` |
| `AmountOfSubstance` | `"5 mmol"` | `Pressure` | `"2 bar"` |
| `Concentration` | `"1 mM"` | | |

Need another? One line:

```python
from kanne import PintQuantity

class Acceleration(PintQuantity):
    reference_unit = "meter / second ** 2"   # declares the *dimension*, never a conversion target
```

## Good to know

- **The wire form is always a string** — JSON schema is `string`, JSON input must be a
  string, bare numbers are rejected. In Python a `pint.Quantity` or another dimension
  instance is also accepted.
- **Still dimensionful at runtime** — `Duration("5 ms") + Duration("1 s")` →
  `1005 ms`; `Duration("1000 ms") == Duration("1 s")` → `True`. Wrong dimensions raise.
- **Context-aware registry** — `Kanne()` sets the active Pint registry on a `contextvar`
  for the `with` block (defaults to a shared global; `degC` & friends work out of the
  box). Mixing registries raises rather than silently misbehaving.
