from __future__ import annotations

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.setup import DEFAULT_ADDRESS_TEMPLATE, ensure_default_address_template


class TestDefaultAddressTemplate(FrappeTestCase):
    def test_ensure_default_address_template_creates_fallback_template_when_missing(self):
        created_doc = MagicMock()

        with (
            patch("ifitwala_ed.setup.setup.frappe.db.table_exists", return_value=True) as mocked_table_exists,
            patch("ifitwala_ed.setup.setup.frappe.db.exists", return_value=False) as mocked_exists,
            patch("ifitwala_ed.setup.setup._get_address_template_seed_country", return_value="Thailand"),
            patch("ifitwala_ed.setup.setup.frappe.get_doc", return_value=created_doc) as mocked_get_doc,
            patch("ifitwala_ed.setup.setup.frappe.clear_cache") as mocked_clear_cache,
        ):
            ensure_default_address_template()

        mocked_table_exists.assert_called_once_with("Address Template")
        mocked_exists.assert_called_once_with("Address Template", {"is_default": 1})
        mocked_get_doc.assert_called_once_with(
            {
                "doctype": "Address Template",
                "country": "Thailand",
                "is_default": 1,
                "template": DEFAULT_ADDRESS_TEMPLATE,
            }
        )
        created_doc.insert.assert_called_once_with(ignore_permissions=True, ignore_if_duplicate=True)
        mocked_clear_cache.assert_called_once_with(doctype="Address Template")

    def test_ensure_default_address_template_promotes_existing_template_when_no_country_is_available(self):
        existing_doc = MagicMock()
        existing_doc.is_default = 0
        existing_doc.template = "Existing Template"

        with (
            patch("ifitwala_ed.setup.setup.frappe.db.table_exists", return_value=True),
            patch("ifitwala_ed.setup.setup.frappe.db.exists", return_value=False),
            patch("ifitwala_ed.setup.setup._get_address_template_seed_country", return_value=None),
            patch("ifitwala_ed.setup.setup._get_existing_address_template_to_promote", return_value="India"),
            patch("ifitwala_ed.setup.setup.frappe.get_doc", return_value=existing_doc) as mocked_get_doc,
            patch("ifitwala_ed.setup.setup.frappe.clear_cache") as mocked_clear_cache,
        ):
            ensure_default_address_template()

        mocked_get_doc.assert_called_once_with("Address Template", "India")
        self.assertEqual(existing_doc.is_default, 1)
        self.assertEqual(existing_doc.template, "Existing Template")
        existing_doc.save.assert_called_once_with(ignore_permissions=True)
        mocked_clear_cache.assert_called_once_with(doctype="Address Template")

    def test_ensure_default_address_template_is_noop_when_default_already_exists(self):
        with (
            patch("ifitwala_ed.setup.setup.frappe.db.table_exists", return_value=True),
            patch("ifitwala_ed.setup.setup.frappe.db.exists", return_value=True) as mocked_exists,
            patch("ifitwala_ed.setup.setup.frappe.get_doc") as mocked_get_doc,
        ):
            ensure_default_address_template()

        mocked_exists.assert_called_once_with("Address Template", {"is_default": 1})
        mocked_get_doc.assert_not_called()
