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



```python

# Global Pattern
from kanne import Kanne, Millisecond, Millimeter, define_unit
from pydantic import BaseModel


class Event(BaseModel):
    duration: Millisecond

class OtherEvent(BaseModel):
    length: Millimeter


Event(duration="1500 ms")  # works fine
OtherEvent(length="1500 mm")  # raises a validation error
event = Event(duration="1500 ms")  # works fine
other = OtherEvent(length="1500 mm")  # raises a validation error


event.duration + other.length  # raises an error since they are not compatible

```

