"""Leaf-action implementations.

Auto-discovers every module in this package and imports it for its
side-effect of calling ``@register``. Add a new action by dropping a
``.py`` file here — no edits needed to this ``__init__``.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

_pkg_path = Path(__file__).parent
for _mod in pkgutil.iter_modules([str(_pkg_path)]):
    if _mod.name.startswith("_"):
        continue
    importlib.import_module(f"{__name__}.{_mod.name}")

del importlib, pkgutil, Path, _pkg_path, _mod
