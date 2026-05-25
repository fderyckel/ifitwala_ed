from __future__ import annotations

from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _new_contact_point(module, **overrides):
    values = {
        "name": "CCP-1",
        "owner_doctype": "Guardian",
        "owner_name": "GRD-1",
        "subject_doctype": "Guardian",
        "subject_name": "GRD-1",
        "organization": "ORG-1",
        "school": "SCHOOL-1",
        "channel_type": "email",
        "purpose": "school_communication",
        "value_encrypted": "encrypted-value",
        "normalized_hash": "hash-value",
        "masked_display": "g****@example.com",
        "is_primary": 0,
        "disabled": 0,
        "flags": {"from_contact_point_service": True},
    }
    values.update(overrides)
    doc = module.CommunicationContactPoint.__new__(module.CommunicationContactPoint)
    doc.__dict__.update(values)
    doc.is_new = lambda: False
    return doc


class TestCommunicationContactPointController(TestCase):
    def test_manual_insert_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            doc = _new_contact_point(module, flags={})

            with self.assertRaises(frappe.PermissionError):
                doc.before_insert()

    def test_manual_update_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            doc = _new_contact_point(module, flags={})

            with self.assertRaises(frappe.PermissionError):
                doc.before_save()

    def test_delete_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            doc = _new_contact_point(module)

            with self.assertRaises(frappe.ValidationError):
                doc.before_delete()

    def test_guardian_contact_point_requires_school(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            doc = _new_contact_point(module, school=None)

            with self.assertRaises(frappe.ValidationError):
                doc.validate()

    def test_unapproved_owner_doctype_is_rejected(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            doc = _new_contact_point(module, owner_doctype="Contact", subject_doctype="Contact")

            with self.assertRaises(frappe.ValidationError):
                doc.validate()

    def test_active_contact_point_requires_protected_values(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            doc = _new_contact_point(module, value_encrypted="")

            with self.assertRaises(frappe.ValidationError):
                doc.validate()

    def test_primary_duplicate_is_rejected(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            frappe.db.exists = Mock(return_value="CCP-OTHER")
            doc = _new_contact_point(module, is_primary=1)

            with self.assertRaises(frappe.ValidationError):
                doc.validate()

        frappe.db.exists.assert_called_once()
        filters = frappe.db.exists.call_args.args[1]
        self.assertEqual(filters["organization"], "ORG-1")
        self.assertEqual(filters["school"], "SCHOOL-1")

    def test_primary_duplicate_check_is_school_scoped(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            frappe.db.exists = Mock(return_value=None)
            doc = _new_contact_point(module, is_primary=1, school="SCHOOL-2")

            doc.validate()

        filters = frappe.db.exists.call_args.args[1]
        self.assertEqual(filters["school"], "SCHOOL-2")

    def test_on_doctype_update_adds_expected_indexes(self):
        with stubbed_frappe() as frappe:
            module = import_fresh(
                "ifitwala_ed.governance.doctype.communication_contact_point.communication_contact_point"
            )
            frappe.db.add_index = Mock()

            module.on_doctype_update()

        self.assertEqual(frappe.db.add_index.call_count, 5)
        index_names = {call.kwargs["index_name"] for call in frappe.db.add_index.call_args_list}
        self.assertEqual(
            index_names,
            {
                "idx_ccp_owner_channel",
                "idx_ccp_subject_channel",
                "idx_ccp_scope_resolution",
                "idx_ccp_hash_scope",
                "idx_ccp_owner_primary",
            },
        )
        primary_index = next(
            call for call in frappe.db.add_index.call_args_list if call.kwargs["index_name"] == "idx_ccp_owner_primary"
        )
        self.assertEqual(
            primary_index.kwargs["fields"],
            ["owner_doctype", "owner_name", "school", "purpose", "channel_type", "is_primary", "disabled"],
        )


class TestCommunicationContactPointMetadata(TestCase):
    def test_metadata_uses_governance_module_and_hides_raw_storage(self):
        import json
        from pathlib import Path

        metadata_path = Path(__file__).resolve().parent / "communication_contact_point.json"
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        fields = {field["fieldname"]: field for field in payload["fields"]}

        self.assertEqual(payload["module"], "Governance")
        self.assertEqual(payload["autoname"], "CCP-.YY.-.MM.-.#####")
        self.assertEqual(payload["permissions"], [])
        self.assertEqual(fields["value_encrypted"]["hidden"], 1)
        self.assertEqual(fields["value_encrypted"]["report_hide"], 1)
        self.assertEqual(fields["normalized_hash"]["hidden"], 1)
        self.assertNotIn("Contacts", payload["module"])
