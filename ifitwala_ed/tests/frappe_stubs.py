# ifitwala_ed/tests/frappe_stubs.py

from __future__ import annotations

import importlib
import sys
import types
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import patch


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
    frappe.throw = lambda message, exc=StubValidationError: _raise(exc, message)
    frappe.whitelist = _whitelist
    frappe.parse_json = lambda value: value
    frappe.session = types.SimpleNamespace(user="unit.test@example.com")
    frappe.get_roles = lambda user: []
    frappe.get_meta = lambda doctype: types.SimpleNamespace(get_field=lambda fieldname: None)
    frappe.get_all = lambda *args, **kwargs: []
    frappe.get_doc = lambda *args, **kwargs: None
    frappe.new_doc = lambda doctype: None
    frappe.db = types.SimpleNamespace()

    frappe_model = types.ModuleType("frappe.model")
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

    modules = {
        "frappe": frappe,
        "frappe.model": frappe_model,
        "frappe.model.document": frappe_model_document,
        "frappe.model.naming": frappe_model_naming,
        "frappe.utils": frappe_utils,
    }
    if extra_modules:
        modules.update(extra_modules)

    with patch.dict(sys.modules, modules, clear=False):
        yield frappe


def import_fresh(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)
