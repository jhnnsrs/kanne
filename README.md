# kanne

[![codecov](https://codecov.io/gh/jhnnsrs/kanne/branch/master/graph/badge.svg?token=UGXEA2THBV)](https://codecov.io/gh/jhnnsrs/kanne)
[![PyPI version](https://badge.fury.io/py/kanne.svg)](https://pypi.org/project/kanne/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/kanne.svg)](https://pypi.python.org/pypi/kanne/)
[![PyPI status](https://img.shields.io/pypi/status/kanne.svg)](https://pypi.python.org/pypi/kanne/)
[![PyPI download day](https://img.shields.io/pypi/dm/kanne.svg)](https://pypi.python.org/pypi/kanne/)


# kanne



Kanne is a small utility package to help manage unit-aware quantities and a simple registry/context pattern for parsing and validating units using Pint. It provides convenience helpers, validators, and a minimal context manager (`Kanne`) to make working with Pint registries explicit and testable.

Key ideas:
- Keep unit parsing and validation ergonomic.
- Provide a lightweight context aware registry (`Kanne`) for libraries.
- Export commonly-used units and small helpers for convenience.
## 📦 Installation


```bash
uv add kanne
```

## ⚡ Quick Start

Kanne provides a context manager to manage Pint registries easily.



Fields are typed by **physical dimension** (`Duration`, `Length`, …), not by a fixed
unit. A field accepts *any* unit-bearing value of the right dimension, preserves the
unit you gave it, and serializes to an abbreviated **pint string** that the matching
server library parses back. A bare number (no unit) is rejected, and so is a value of
the wrong dimension.

```python

from kanne.kanne import Kanne
from kanne import Duration, Length
from kanne.registry import KanneRegistry
from pydantic import BaseModel


class Event(BaseModel):
    duration: Duration   # any time quantity
    extent: Length       # any spatial length


with Kanne(registry=KanneRegistry()):
    event = Event(duration="1500 ms", extent="2.5 um")

    event.model_dump()       # {'duration': '1500 ms', 'extent': '2.5 µm'} — unit preserved
    event.duration.to("s")   # <Quantity(1.5, 'second')>

    Event(duration="3 m", extent="1 m")   # raises — a length is not a duration
    Event(duration=1500, extent="1 m")    # raises — bare numbers are ambiguous

    # arithmetic stays dimensionful
    event.duration + event.extent          # raises — incompatible dimensions
```

