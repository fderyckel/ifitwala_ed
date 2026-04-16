import html
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jinja2 import Environment

from ifitwala_ed.printing.letter_head import sync as letter_head_sync
from ifitwala_ed.printing.letter_head.sync import (
    DEFAULT_SCHOOL_LETTER_HEAD_CSS_PATH,
    DEFAULT_SCHOOL_LETTER_HEAD_PATH,
    DEFAULT_SCHOOL_LETTER_HEAD_TEMPLATE_PATH,
    get_default_school_letter_head_values,
    load_default_school_letter_head_payload,
)


class TestDefaultSchoolLetterHead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DEFAULT_SCHOOL_LETTER_HEAD_PATH.read_text(encoding="utf-8"))
        cls.template = DEFAULT_SCHOOL_LETTER_HEAD_TEMPLATE_PATH.read_text(encoding="utf-8")
        cls.css = DEFAULT_SCHOOL_LETTER_HEAD_CSS_PATH.read_text(encoding="utf-8")

    def test_sync_module_targets_exported_paths(self):
        self.assertTrue(DEFAULT_SCHOOL_LETTER_HEAD_PATH.exists())
        self.assertTrue(DEFAULT_SCHOOL_LETTER_HEAD_TEMPLATE_PATH.exists())
        self.assertTrue(DEFAULT_SCHOOL_LETTER_HEAD_CSS_PATH.exists())

    def test_exported_metadata_matches_contract(self):
        self.assertEqual(self.payload["doctype"], "Letter Head")
        self.assertEqual(self.payload["letter_head_name"], "Ifitwala Default School Letter Head")
        self.assertEqual(self.payload["source"], "HTML")
        self.assertEqual(self.payload["footer_source"], "HTML")
        self.assertTrue(self.payload["is_default"])
        self.assertFalse(self.payload["disabled"])

    def test_template_parses_as_valid_jinja(self):
        Environment().parse(self.template)

    def test_sync_helpers_load_expected_payload(self):
        payload = load_default_school_letter_head_payload()
        values = get_default_school_letter_head_values()

        self.assertEqual(payload["letter_head_name"], "Ifitwala Default School Letter Head")
        self.assertEqual(values["source"], "HTML")
        self.assertEqual(values["footer_source"], "HTML")
        self.assertEqual(values["is_default"], 1)
        self.assertIn("<style>", payload["content"])
        self.assertIn("ifitwala-letterhead__name", payload["content"])

    def test_sync_reconciles_new_insert_back_to_managed_html_state(self):
        fake_frappe = _FakeSyncFrappe()
        values = get_default_school_letter_head_values()

        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            changed = letter_head_sync.sync_default_school_letter_head()

        self.assertTrue(changed)
        self.assertEqual(fake_frappe.doc["source"], "HTML")
        self.assertEqual(fake_frappe.doc["content"], values["content"])
        self.assertEqual(fake_frappe.doc.save_count, 1)

    def test_template_uses_only_in_scope_school_and_organization_fallbacks(self):
        for token in (
            'doc.get("school")',
            'doc.get("anchor_school")',
            'doc.get("organization")',
            '"All Organizations"',
            "school_tagline",
            "organization_logo",
            'name": ["!=", "All Organizations"]',
        ):
            self.assertIn(token, self.template)

        for token in (
            "resolve_public_brand_organization",
            "get_public_brand_identity",
            "WEBSITE_FALLBACK_LOGO",
            "default_website_school",
        ):
            self.assertNotIn(token, self.template)

    def test_renders_school_ancestor_logo_and_tagline(self):
        rendered = self._render(
            doc={"doctype": "Leave Application", "school": "SCH-CHILD"},
            schools={
                "SCH-PARENT": {
                    "name": "SCH-PARENT",
                    "school_name": "Lwitwala Academy",
                    "school_logo": "/files/lwitwala-academy.png",
                    "school_tagline": "Learning with purpose",
                    "organization": "ORG-CAMPUS",
                    "lft": 1,
                    "rgt": 4,
                },
                "SCH-CHILD": {
                    "name": "SCH-CHILD",
                    "school_name": "Lwitwala Academy Downtown",
                    "school_logo": "",
                    "school_tagline": "",
                    "organization": "ORG-CAMPUS",
                    "lft": 2,
                    "rgt": 3,
                },
            },
            organizations={
                "ORG-CAMPUS": {
                    "name": "ORG-CAMPUS",
                    "organization_name": "Lwitwala Education Network",
                    "organization_logo": "/files/org-campus.png",
                    "lft": 10,
                    "rgt": 11,
                }
            },
        )

        self.assertIn("Lwitwala Academy Downtown", rendered)
        self.assertIn("/files/lwitwala-academy.png", rendered)
        self.assertIn("Learning with purpose", rendered)
        self.assertNotIn("/files/org-campus.png", rendered)

    def test_renders_organization_logo_without_crossing_into_global_root(self):
        rendered = self._render(
            doc={"doctype": "Leave Application", "school": "SCH-CHILD"},
            schools={
                "SCH-PARENT": {
                    "name": "SCH-PARENT",
                    "school_name": "East Campus",
                    "school_logo": "",
                    "school_tagline": "",
                    "organization": "ORG-CAMPUS",
                    "lft": 1,
                    "rgt": 4,
                },
                "SCH-CHILD": {
                    "name": "SCH-CHILD",
                    "school_name": "East Campus Lower School",
                    "school_logo": "",
                    "school_tagline": "",
                    "organization": "ORG-CAMPUS",
                    "lft": 2,
                    "rgt": 3,
                },
            },
            organizations={
                "ORG-CAMPUS": {
                    "name": "ORG-CAMPUS",
                    "organization_name": "East Campus Group",
                    "organization_logo": "/files/east-campus-group.png",
                    "lft": 2,
                    "rgt": 3,
                },
                "All Organizations": {
                    "name": "All Organizations",
                    "organization_name": "All Organizations",
                    "organization_logo": "/files/root-logo.png",
                    "lft": 1,
                    "rgt": 4,
                },
            },
        )

        self.assertIn("/files/east-campus-group.png", rendered)
        self.assertNotIn("/files/root-logo.png", rendered)
        self.assertIn("East Campus Lower School", rendered)

    def test_renders_text_only_when_no_logo_exists_in_scope(self):
        rendered = self._render(
            doc={"doctype": "Leave Application", "school": "SCH-CHILD"},
            schools={
                "SCH-CHILD": {
                    "name": "SCH-CHILD",
                    "school_name": "Harbor School",
                    "school_logo": "",
                    "school_tagline": "",
                    "organization": "ORG-HARBOR",
                    "lft": 2,
                    "rgt": 3,
                }
            },
            organizations={
                "ORG-HARBOR": {
                    "name": "ORG-HARBOR",
                    "organization_name": "Harbor Education Trust",
                    "organization_logo": "",
                    "lft": 2,
                    "rgt": 3,
                },
                "All Organizations": {
                    "name": "All Organizations",
                    "organization_name": "All Organizations",
                    "organization_logo": "/files/root-logo.png",
                    "lft": 1,
                    "rgt": 4,
                },
            },
        )

        self.assertIn("Harbor School", rendered)
        self.assertNotIn('class="ifitwala-letterhead__logo"', rendered)
        self.assertNotIn("/files/root-logo.png", rendered)

    def test_renders_organization_context_when_no_school_is_available(self):
        rendered = self._render(
            doc={"doctype": "Dunning Notice", "organization": "ORG-CAMPUS"},
            schools={},
            organizations={
                "ORG-CAMPUS": {
                    "name": "ORG-CAMPUS",
                    "organization_name": "Lakeside Education Trust",
                    "organization_logo": "/files/lakeside.png",
                    "lft": 2,
                    "rgt": 3,
                }
            },
        )

        self.assertIn("Lakeside Education Trust", rendered)
        self.assertIn("/files/lakeside.png", rendered)
        self.assertNotIn("ifitwala-letterhead__tagline", rendered)

    def test_css_includes_compact_professional_letterhead_tokens(self):
        for token in (
            ".ifitwala-letterhead",
            ".ifitwala-letterhead__ribbon",
            ".ifitwala-letterhead__panel",
            ".ifitwala-letterhead__logo",
            "Baskerville, Georgia, serif",
            '"Avenir Next", "Helvetica Neue", Arial, sans-serif',
        ):
            self.assertIn(token, self.css)

    def _render(self, *, doc, schools, organizations):
        template = Environment().from_string(self.template)
        return template.render(
            doc=doc,
            frappe=_FakeFrappe(schools=schools, organizations=organizations),
        )


class _FakeFrappe:
    def __init__(self, *, schools, organizations):
        self.db = _FakeFrappeDB(schools=schools, organizations=organizations)
        self.utils = _FakeUtils()

    def get_all(self, doctype, filters=None, fields=None, order_by=None):
        return self.db.get_all(doctype, filters=filters, fields=fields, order_by=order_by)


class _FakeFrappeDB:
    def __init__(self, *, schools, organizations):
        self._schools = schools
        self._organizations = organizations

    def get_value(self, doctype, name, fields, as_dict=False):
        rows = self._rows_for(doctype)
        row = rows.get(name)
        if not row:
            return None

        if isinstance(fields, (list, tuple)):
            if as_dict:
                return {field: row.get(field) for field in fields}
            if len(fields) == 1:
                return row.get(fields[0])
            return tuple(row.get(field) for field in fields)

        return row.get(fields)

    def get_all(self, doctype, filters=None, fields=None, order_by=None):
        filters = filters or {}
        fields = fields or []
        rows = list(self._rows_for(doctype).values())
        matched = [row for row in rows if self._matches(row, filters)]

        if order_by == "lft desc":
            matched.sort(key=lambda row: row.get("lft", 0), reverse=True)
        elif order_by == "lft asc":
            matched.sort(key=lambda row: row.get("lft", 0))

        return [{field: row.get(field) for field in fields} for row in matched]

    def _rows_for(self, doctype):
        if doctype == "School":
            return self._schools
        if doctype == "Organization":
            return self._organizations
        raise AssertionError(f"Unexpected doctype: {doctype}")

    def _matches(self, row, filters):
        for key, expected in filters.items():
            actual = row.get(key)
            if isinstance(expected, list) and len(expected) == 2:
                operator, operand = expected
                if operator == "<=" and not (actual is not None and actual <= operand):
                    return False
                if operator == ">=" and not (actual is not None and actual >= operand):
                    return False
                if operator == "!=" and actual == operand:
                    return False
                if operator == "in" and actual not in operand:
                    return False
                continue

            if actual != expected:
                return False

        return True


class _FakeUtils:
    @staticmethod
    def escape_html(value):
        return "" if value is None else html.escape(str(value), quote=True)


class _FakeLetterHeadDoc(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.flags = SimpleNamespace(ignore_permissions=False)
        self.save_count = 0

    def get(self, key, default=None):
        return super().get(key, default)

    def set(self, key, value):
        self[key] = value

    def save(self):
        self.save_count += 1
        return self


class _FakeSyncDB:
    def __init__(self):
        self.created = False

    def exists(self, doctype, name):
        if doctype != "Letter Head":
            raise AssertionError(f"Unexpected doctype: {doctype}")
        return name if self.created and name == "Ifitwala Default School Letter Head" else None


class _FakeSyncFrappe:
    def __init__(self):
        self.db = _FakeSyncDB()
        self.doc = None

    def get_doc(self, *args):
        if len(args) == 2:
            doctype, name = args
            if doctype == "Letter Head" and name == "Ifitwala Default School Letter Head" and self.doc is not None:
                return self.doc
            raise AssertionError(f"Unexpected get_doc lookup: {args}")

        if len(args) == 1 and isinstance(args[0], dict):
            payload = dict(args[0])
            doc = _FakeLetterHeadDoc(**payload)

            def _insert(ignore_permissions=False):
                doc["source"] = "Image"
                doc["content"] = ""
                self.doc = doc
                self.db.created = True
                return doc

            doc.insert = _insert
            return doc

        raise AssertionError(f"Unexpected get_doc call: {args}")


if __name__ == "__main__":
    unittest.main()
