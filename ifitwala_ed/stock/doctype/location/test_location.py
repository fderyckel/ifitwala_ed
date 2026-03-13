# Copyright (c) 2024, fdR and Contributors
# See license.txt

# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/stock/doctype/location/test_location.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.stock.doctype.location.location import Location


class TestLocation(TestCase):
    @patch("ifitwala_ed.stock.doctype.location.location.frappe.db.sql")
    @patch(
        "ifitwala_ed.stock.doctype.location.location.get_location_scope",
        return_value=["LOC-PARENT", "LOC-CHILD"],
    )
    def test_capacity_validation_uses_location_subtree(
        self,
        _mock_scope,
        mock_sql,
    ):
        mock_sql.side_effect = [
            [{"name": "SG-1"}],
            [{"name": "SG-1", "active_count": 12}],
        ]

        doc = frappe._dict({"name": "LOC-PARENT", "maximum_capacity": 10})

        with self.assertRaises(frappe.ValidationError):
            Location.validate_capacity_against_groups(doc)

        query, params = mock_sql.call_args_list[0].args[:2]
        self.assertIn("sgs.location IN %(locations)s", query)
        self.assertEqual(params["locations"], ("LOC-PARENT", "LOC-CHILD"))
