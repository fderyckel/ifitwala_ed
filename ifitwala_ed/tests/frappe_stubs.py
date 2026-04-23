# ifitwala_ed/tests/frappe_stubs.py

from __future__ import annotations

import importlib
import sys
import types
from contextlib import contextmanager
from html import escape as html_escape
from typing import Iterator
from unittest.mock import patch

_MISSING = object()
# Track fresh stubbed imports so the stub-bound module object does not leak into later real-Frappe tests.
_ACTIVE_IMPORT_TRACKERS: list[list[tuple[str, object, object | None, str | None, object, bool]]] = []


class StubValidationError(Exception):
    pass


class StubPermissionError(Exception):
    pass


def _raise(exc: type[Exception], message: str):
    raise exc(message)


def _whitelist(*args, **kwargs):
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]

    def decorator(fn):
        return fn

    return decorator


@contextmanager
def stubbed_frappe(extra_modules: dict[str, object] | None = None) -> Iterator[types.ModuleType]:
    frappe = types.ModuleType("frappe")
    frappe._ = lambda message: message
    frappe.PermissionError = StubPermissionError
    frappe.ValidationError = StubValidationError
    frappe.throw = lambda message, exc=StubValidationError, **kwargs: _raise(exc, message)
    frappe.whitelist = _whitelist
    frappe.parse_json = lambda value: value
    frappe.session = types.SimpleNamespace(user="unit.test@example.com")
    frappe.get_roles = lambda user: []
    frappe.get_meta = lambda doctype: types.SimpleNamespace(get_field=lambda fieldname: None)
    frappe.get_all = lambda *args, **kwargs: []
    frappe.get_doc = lambda *args, **kwargs: None
    frappe.new_doc = lambda doctype: None
    frappe.db = types.SimpleNamespace()
    frappe.permissions = types.SimpleNamespace(get_roles=lambda username=None: [])

    frappe_model = types.ModuleType("frappe.model")
    frappe_model.child_table_fields = ()
    frappe_model.default_fields = ()
    frappe_model.optional_fields = ()
    frappe_model_document = types.ModuleType("frappe.model.document")

    class Document:
        def __init__(self, *args, **kwargs):
            pass

    frappe_model_document.Document = Document
    frappe_model.document = frappe_model_document

    frappe_model_naming = types.ModuleType("frappe.model.naming")
    frappe_model_naming.make_autoname = lambda pattern: "AUTO-0001"

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.get_datetime = lambda value: value
    frappe_utils.now = lambda: "2026-03-12 17:45:04"
    frappe_utils.now_datetime = lambda: "2026-03-12 17:45:04"
    frappe_utils.escape_html = lambda value: html_escape("" if value is None else str(value))
    frappe_utils.sanitize_html = lambda value, **kwargs: value

    modules = {
        "frappe": frappe,
        "frappe.model": frappe_model,
        "frappe.model.document": frappe_model_document,
        "frappe.model.naming": frappe_model_naming,
        "frappe.utils": frappe_utils,
    }
    if extra_modules:
        modules.update(extra_modules)

    restored_package_attrs: list[tuple[object, str, object, bool]] = []
    imported_modules: list[tuple[str, object, object | None, str | None, object, bool]] = []

    with patch.dict(sys.modules, modules, clear=False):
        _ACTIVE_IMPORT_TRACKERS.append(imported_modules)
        if extra_modules:
            for module_name, module_obj in extra_modules.items():
                parent_name, _, attr_name = module_name.rpartition(".")
                if not parent_name or not attr_name:
                    continue
                parent_module = sys.modules.get(parent_name)
                if parent_module is None:
                    parent_module = importlib.import_module(parent_name)
                had_attr = hasattr(parent_module, attr_name)
                previous_value = getattr(parent_module, attr_name, None)
                restored_package_attrs.append((parent_module, attr_name, previous_value, had_attr))
                setattr(parent_module, attr_name, module_obj)

        try:
            yield frappe
        finally:
            _ACTIVE_IMPORT_TRACKERS.pop()
            for module_name, previous_module, parent_module, attr_name, previous_attr, had_attr in reversed(
                imported_modules
            ):
                sys.modules.pop(module_name, None)
                if previous_module is not _MISSING:
                    sys.modules[module_name] = previous_module
                if parent_module is None or not attr_name:
                    continue
                if had_attr:
                    setattr(parent_module, attr_name, previous_attr)
                elif hasattr(parent_module, attr_name):
                    delattr(parent_module, attr_name)
            for parent_module, attr_name, previous_value, had_attr in reversed(restored_package_attrs):
                if had_attr:
                    setattr(parent_module, attr_name, previous_value)
                else:
                    delattr(parent_module, attr_name)


def import_fresh(module_name: str):
    previous_module = sys.modules.get(module_name, _MISSING)
    parent_module = None
    attr_name = None
    previous_attr = _MISSING
    had_attr = False

    parent_name, _, attr_name = module_name.rpartition(".")
    if parent_name and attr_name:
        parent_module = sys.modules.get(parent_name)
        if parent_module is None:
            try:
                parent_module = importlib.import_module(parent_name)
            except Exception:
                parent_module = None
        if parent_module is not None:
            had_attr = hasattr(parent_module, attr_name)
            previous_attr = getattr(parent_module, attr_name, None)

    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)

    if _ACTIVE_IMPORT_TRACKERS:
        _ACTIVE_IMPORT_TRACKERS[-1].append(
            (module_name, previous_module, parent_module, attr_name or None, previous_attr, had_attr)
        )

    return module
