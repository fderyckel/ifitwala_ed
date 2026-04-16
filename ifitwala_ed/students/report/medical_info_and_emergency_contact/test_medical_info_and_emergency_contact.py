import html
import importlib
import re
import sys
import types
from datetime import date, datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


class _Dict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def _cint(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _cstr(value):
    return "" if value is None else str(value)


def _escape_html(value):
    return html.escape("" if value is None else str(value))


def _getdate(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _strip_html_tags(value):
    return re.sub(r"<[^>]+>", "", str(value or ""))


def _today():
    return "2026-04-16"


fake_frappe = types.ModuleType("frappe")
fake_frappe._dict = _Dict
fake_frappe._ = lambda value: value
fake_frappe.db = types.SimpleNamespace(
    get_value=lambda *args, **kwargs: None,
    sql=lambda *args, **kwargs: [],
)
fake_frappe.get_all = lambda *args, **kwargs: []
fake_frappe.get_meta = lambda *args, **kwargs: types.SimpleNamespace(fields=[])
fake_frappe.throw = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(args[0] if args else "frappe.throw"))
fake_frappe.PermissionError = RuntimeError

fake_utils = types.ModuleType("frappe.utils")
fake_utils.cint = _cint
fake_utils.cstr = _cstr
fake_utils.escape_html = _escape_html
fake_utils.getdate = _getdate
fake_utils.strip_html_tags = _strip_html_tags
fake_utils.today = _today

fake_nestedset = types.ModuleType("frappe.utils.nestedset")
fake_nestedset.get_descendants_of = lambda *args, **kwargs: []

fake_school_tree = types.ModuleType("ifitwala_ed.utilities.school_tree")
fake_school_tree.get_descendant_schools = lambda *args, **kwargs: []

fake_frappe.utils = fake_utils

sys.modules.setdefault("frappe", fake_frappe)
sys.modules.setdefault("frappe.utils", fake_utils)
sys.modules.setdefault("frappe.utils.nestedset", fake_nestedset)
sys.modules.setdefault("ifitwala_ed.utilities.school_tree", fake_school_tree)

report = importlib.import_module(
    "ifitwala_ed.students.report.medical_info_and_emergency_contact.medical_info_and_emergency_contact"
)

TEMPLATE_PATH = Path(report.__file__).with_suffix(".html")


class TestMedicalInfoAndEmergencyContactReport(TestCase):
    @patch.object(
        report,
        "_medical_field_defs",
        return_value=[
            {"fieldname": "blood_group", "label": "Blood Group", "fieldtype": "Select"},
            {"fieldname": "allergies", "label": "Any allergies", "fieldtype": "Check"},
            {"fieldname": "medical_info", "label": "Medical Info", "fieldtype": "Text Editor"},
            {"fieldname": "diet_requirements", "label": "Diet Requirements", "fieldtype": "Small Text"},
        ],
    )
    def test_collect_medical_entries_only_keeps_populated_fields(self, _mock_defs):
        entries = report._collect_medical_entries(
            {
                "blood_group": "O Positive",
                "allergies": 0,
                "medical_info": "<p>Carry inhaler</p>",
                "diet_requirements": "",
            }
        )

        self.assertEqual([entry["fieldname"] for entry in entries], ["blood_group", "medical_info"])
        self.assertEqual(entries[0]["label"], "Blood Group")
        self.assertEqual(entries[0]["value_html"], "O Positive")
        self.assertEqual(entries[1]["value_html"], "Carry inhaler")

    @patch.object(
        report,
        "_medical_field_defs",
        return_value=[{"fieldname": "blood_group", "label": "Blood Group", "fieldtype": "Select"}],
    )
    @patch.object(
        report,
        "_fetch_guardian_contacts",
        return_value={
            "STU-001": {
                "html": "<div class='guardian-block'>Guardian</div>",
                "count": 1,
                "primary_name": "Parent One",
                "primary_phone": "555-0101",
            }
        },
    )
    @patch.object(
        report,
        "_fetch_patients",
        return_value={"STU-001": _Dict({"student": "STU-001", "blood_group": "O Positive"})},
    )
    @patch.object(
        report,
        "_fetch_group_students",
        return_value=[
            _Dict(
                {
                    "student": "STU-001",
                    "student_name": "Student One",
                    "student_date_of_birth": None,
                    "student_image": None,
                }
            )
        ],
    )
    def test_build_rows_exposes_structured_print_flags(
        self,
        _mock_students,
        _mock_patients,
        _mock_guardians,
        _mock_defs,
    ):
        rows = report._build_rows(
            _Dict(
                {
                    "_student_group": _Dict(
                        {
                            "name": "GRP-001",
                            "student_group_name": "Group 1",
                            "program": None,
                            "school": None,
                            "academic_year": "2025-2026",
                        }
                    )
                }
            )
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["_has_medical_info"])
        self.assertEqual(row["_medical_entry_count"], 1)
        self.assertEqual(row["_medical_entries"][0]["label"], "Blood Group")
        self.assertTrue(row["_has_guardian_contacts"])
        self.assertEqual(row["_guardian_contact_count"], 1)

    def test_print_template_uses_compact_medical_panel_tokens(self):
        html_text = TEMPLATE_PATH.read_text(encoding="utf-8")

        for token in (
            "row._has_medical_info",
            "medicalEntries = row._medical_entries || []",
            "panel panel--medical",
            "medical-entry",
            "row._guardian_contact_count",
        ):
            self.assertIn(token, html_text)

        self.assertNotIn("med-box", html_text)
