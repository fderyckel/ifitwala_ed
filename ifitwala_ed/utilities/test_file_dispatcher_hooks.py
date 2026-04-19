from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _file_dispatcher_module():
    route_calls: list[tuple[object, object]] = []
    image_calls: list[tuple[str, object, object]] = []

    file_management = ModuleType("ifitwala_ed.utilities.file_management")
    file_management.route_uploaded_file = lambda doc, method=None, context_override=None: route_calls.append(
        (doc, method)
    )
    file_management.calculate_hash = lambda file_doc: None

    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.handle_file_after_insert = lambda doc, method=None: image_calls.append(("after_insert", doc, method))
    image_utils.handle_file_on_update = lambda doc, method=None: image_calls.append(("on_update", doc, method))

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.utilities.file_management": file_management,
            "ifitwala_ed.utilities.image_utils": image_utils,
        }
    ):
        yield import_fresh("ifitwala_ed.utilities.file_dispatcher"), route_calls, image_calls


class TestFileDispatcherHooks(TestCase):
    def test_after_insert_skips_drive_compat_projection(self):
        doc = SimpleNamespace(flags=SimpleNamespace(drive_compat_projection=True))

        with _file_dispatcher_module() as (file_dispatcher, route_calls, image_calls):
            file_dispatcher.handle_file_after_insert(doc, method="after_insert")

        self.assertEqual(route_calls, [])
        self.assertEqual(image_calls, [])

    def test_on_update_skips_drive_compat_projection(self):
        doc = SimpleNamespace(flags=SimpleNamespace(drive_compat_projection=True))

        with _file_dispatcher_module() as (file_dispatcher, route_calls, image_calls):
            file_dispatcher.handle_file_on_update(doc, method="on_update")

        self.assertEqual(route_calls, [])
        self.assertEqual(image_calls, [])
