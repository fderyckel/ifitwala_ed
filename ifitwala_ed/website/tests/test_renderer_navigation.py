# ifitwala_ed/website/tests/test_renderer_navigation.py

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website.renderer import _navigation_sort_key


class TestRendererNavigation(FrappeTestCase):
    def test_navigation_sort_key_places_blank_orders_last(self):
        rows = [
            {"route": "/about", "navigation_order": None},
            {"route": "/contact", "navigation_order": "Null"},
            {"route": "/programs", "navigation_order": 2},
            {"route": "/", "navigation_order": 1},
            {"route": "/apply", "navigation_order": ""},
        ]

        ordered_routes = [row["route"] for row in sorted(rows, key=_navigation_sort_key)]
        self.assertEqual(
            ordered_routes,
            ["/", "/programs", "/about", "/apply", "/contact"],
        )
