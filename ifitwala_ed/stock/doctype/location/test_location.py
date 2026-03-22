# Copyright (c) 2024, fdR and Contributors
# See license.txt

# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/stock/doctype/location/test_location.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.stock.doctype.location.location import Location, get_valid_parent_locations
from ifitwala_ed.utilities.location_utils import get_visible_location_rows_for_school


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

    @patch("ifitwala_ed.stock.doctype.location.location.frappe.get_all")
    @patch(
        "ifitwala_ed.stock.doctype.location.location.get_ancestor_schools",
        return_value=["Leaf School", "Parent School"],
    )
    def test_parent_location_query_uses_search_link_signature_and_scope_filters(
        self,
        _mock_ancestors,
        mock_get_all,
    ):
        mock_get_all.return_value = [
            frappe._dict({"name": "Bathroom Wing", "school": "Parent School"}),
            frappe._dict({"name": "Building Root", "school": None}),
            frappe._dict({"name": "Science Block", "school": "Sibling School"}),
        ]

        results = get_valid_parent_locations(
            "Location",
            "bath",
            "name",
            0,
            10,
            '{"organization":"Ifitwala Roots Campus","school":"Leaf School"}',
        )

        mock_get_all.assert_called_once_with(
            "Location",
            filters={"is_group": 1, "organization": "Ifitwala Roots Campus"},
            fields=["name", "school"],
        )
        self.assertEqual(results, [["Bathroom Wing"]])

    def test_shared_visibility_requires_school(self):
        doc = frappe._dict(
            {
                "shared_with_descendant_schools": 1,
                "school": None,
            }
        )

        with self.assertRaises(frappe.ValidationError):
            Location._validate_shared_visibility_requires_school(doc)

    @patch("ifitwala_ed.utilities.location_utils.get_location_scope")
    @patch("ifitwala_ed.utilities.location_utils.get_ancestor_schools")
    @patch("ifitwala_ed.utilities.location_utils.get_descendant_schools")
    @patch("ifitwala_ed.utilities.location_utils.frappe.db.has_column", return_value=True)
    @patch("ifitwala_ed.utilities.location_utils.frappe.get_all")
    def test_visible_location_rows_include_ancestor_shared_locations(
        self,
        mock_get_all,
        _mock_has_column,
        mock_descendants,
        mock_ancestors,
        mock_location_scope,
    ):
        mock_descendants.return_value = ["ISS-SHARED-TEST"]
        mock_ancestors.return_value = ["ISS-SHARED-TEST", "IIS-SHARED-TEST"]
        mock_location_scope.side_effect = lambda location, include_children=True: {
            "CENTRAL-BUILDING": ["CENTRAL-BUILDING", "EVENT-HALL"],
        }.get(location, [location])

        def _fake_get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype == "Location Type":
                return [
                    frappe._dict({"name": "Classroom", "location_type_name": "Classroom", "is_schedulable": 1}),
                    frappe._dict({"name": "Hall", "location_type_name": "Hall", "is_schedulable": 1}),
                ]
            self.assertEqual(doctype, "Location")
            if filters == {"school": ["in", ["ISS-SHARED-TEST"]]}:
                return [frappe._dict({"name": "ISS-ROOM", "is_group": 0})]
            if filters == {
                "school": ["in", ["ISS-SHARED-TEST", "IIS-SHARED-TEST"]],
                "shared_with_descendant_schools": 1,
            }:
                return [frappe._dict({"name": "CENTRAL-BUILDING"})]
            if filters == {"name": ["in", ["ISS-ROOM", "CENTRAL-BUILDING", "EVENT-HALL"]]}:
                return [
                    frappe._dict(
                        {
                            "name": "ISS-ROOM",
                            "location_name": "ISS Room",
                            "location_type": "Classroom",
                            "maximum_capacity": 20,
                            "is_group": 0,
                        }
                    ),
                    frappe._dict(
                        {
                            "name": "CENTRAL-BUILDING",
                            "location_name": "Central Building",
                            "location_type": None,
                            "maximum_capacity": None,
                            "is_group": 1,
                        }
                    ),
                    frappe._dict(
                        {
                            "name": "EVENT-HALL",
                            "location_name": "Event Hall",
                            "location_type": "Hall",
                            "maximum_capacity": 200,
                            "is_group": 0,
                        }
                    ),
                ]
            raise AssertionError(f"Unexpected get_all call: {doctype=} {filters=}")

        mock_get_all.side_effect = _fake_get_all

        rows = get_visible_location_rows_for_school(
            "ISS-SHARED-TEST",
            include_groups=False,
            only_schedulable=True,
            fields=["name", "location_name", "location_type", "maximum_capacity", "is_group"],
            order_by="location_name asc",
            limit=20,
        )

        self.assertEqual([row["name"] for row in rows], ["ISS-ROOM", "EVENT-HALL"])
