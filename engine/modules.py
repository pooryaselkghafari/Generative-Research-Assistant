# Simple module registry so apps can plug into the engine.

from typing import Dict, Any, Tuple
from importlib import import_module

_REGISTRY = {}

def register(name: str, module_path: str):
    """Register a module by dotted path to an object providing `ui_schema()` and `run()`."""
    _REGISTRY[name] = module_path

def get_registry():
    return _REGISTRY

def get_module(name: str):
    path = _REGISTRY.get(name)
    if not path:
        raise ValueError(f"Module '{name}' not registered")
    mod_name, obj_name = path.rsplit(':', 1)
    mod = import_module(mod_name)
    return getattr(mod, obj_name)
