from __future__ import annotations

import ast
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _module():
    with stubbed_frappe() as frappe:
        module = import_fresh("ifitwala_ed.contacts.contact_privacy")
        module._normalize_email_value = lambda value: str(value or "").strip().lower()
        yield module, frappe


class TestContactPrivacyService(TestCase):
    def test_purpose_is_required(self):
        with _module() as (contact_privacy, frappe):
            with self.assertRaises(frappe.PermissionError):
                contact_privacy.require_purpose("")

    def test_applicant_contact_options_deny_when_scope_cannot_be_proven(self):
        with _module() as (contact_privacy, frappe):
            with (
                patch.object(contact_privacy, "_user_can_access_student_applicant", return_value=False),
                patch.object(contact_privacy, "_has_scoped_staff_access_to_student_applicant", return_value=False),
            ):
                with self.assertRaises(frappe.PermissionError):
                    contact_privacy.get_raw_contact_email_options_for_applicant_invite(
                        contact="CONTACT-1",
                        student_applicant="APP-OTHER",
                        purpose="applicant_invite_contact_options",
                        user="admissions@example.com",
                    )

    def test_applicant_contact_options_are_minimal_when_scope_is_proven(self):
        with _module() as (contact_privacy, frappe):
            created_logs: list[dict] = []

            class _FakeLogDoc:
                def __init__(self, payload):
                    self.payload = payload
                    self.name = "CAL-1"
                    self.flags = {}

                def insert(self, ignore_permissions=True):
                    created_logs.append(self.payload)
                    return self

            frappe.get_doc = lambda payload: _FakeLogDoc(payload)
            frappe.get_all = Mock(
                return_value=[
                    {"email_id": "Primary@Example.com", "is_primary": 1, "idx": 1},
                    {"email_id": "other@example.com", "is_primary": 0, "idx": 2},
                    {"email_id": "primary@example.com", "is_primary": 0, "idx": 3},
                ]
            )
            with (
                patch.object(contact_privacy, "_user_can_access_student_applicant", return_value=False),
                patch.object(contact_privacy, "_has_scoped_staff_access_to_student_applicant", return_value=True),
            ):
                payload = contact_privacy.get_raw_contact_email_options_for_applicant_invite(
                    contact="CONTACT-1",
                    student_applicant="APP-1",
                    purpose="applicant_invite_contact_options",
                    user="admissions@example.com",
                )

        self.assertEqual(payload, ["primary@example.com", "other@example.com"])
        self.assertEqual(created_logs[0]["access_type"], "recipient_resolution")
        self.assertEqual(created_logs[0]["result"], "allowed")
        frappe.get_all.assert_called_once()
        self.assertEqual(frappe.get_all.call_args.args[0], "Contact Email")

    def test_raw_family_consent_contact_read_creates_access_log(self):
        with _module() as (contact_privacy, frappe):
            created_logs: list[dict] = []

            class _FakeLogDoc:
                def __init__(self, payload):
                    self.payload = payload
                    self.name = "CAL-1"
                    self.flags = {}

                def insert(self, ignore_permissions=True):
                    created_logs.append(self.payload)
                    return self

            frappe.get_doc = lambda payload: _FakeLogDoc(payload)
            frappe.db.exists = lambda doctype, name=None: doctype == "Contact" and name == "CONTACT-1"
            frappe.db.get_value = lambda *args, **kwargs: {
                "email_id": "guardian@example.com",
                "mobile_no": "+66812345678",
            }

            def get_all(doctype, **kwargs):
                if doctype == "Contact Email":
                    return [{"email_id": "guardian@example.com", "is_primary": 1, "idx": 1}]
                if doctype == "Contact Phone":
                    return [{"phone": "+66812345678", "is_primary_mobile_no": 1, "idx": 1}]
                return []

            frappe.get_all = get_all

            values = contact_privacy.get_raw_contact_primary_values_for_portal_context(
                contact="CONTACT-1",
                purpose="family_consent_profile_context",
                subject_doctype="Guardian",
                subject_name="GRD-1",
                workflow="family_consent_profile_context",
            )

        self.assertEqual(values["primary_email"], "guardian@example.com")
        self.assertEqual(created_logs[0]["doctype"], "Contact Access Log")
        self.assertEqual(created_logs[0]["access_type"], "raw_read")
        self.assertEqual(created_logs[0]["subject_doctype"], "Guardian")
        self.assertEqual(created_logs[0]["owner_name"], "CONTACT-1")

    def test_family_consent_writeback_creates_raw_write_log(self):
        with _module() as (contact_privacy, frappe):
            created_logs: list[dict] = []

            class _FakeLogDoc:
                def __init__(self, payload):
                    self.payload = payload
                    self.name = "CAL-1"
                    self.flags = {}

                def insert(self, ignore_permissions=True):
                    created_logs.append(self.payload)
                    return self

            class _FakeContactDoc:
                email_id = ""

                def __init__(self):
                    self.email_ids = []
                    self.phone_nos = []
                    self.saved = False

                def get(self, fieldname):
                    return getattr(self, fieldname, None)

                def append(self, fieldname, row):
                    target = self.email_ids if fieldname == "email_ids" else self.phone_nos
                    target.append(SimpleNamespace(**row))

                def save(self, ignore_permissions=True):
                    self.saved = True

            contact_doc = _FakeContactDoc()

            def get_doc(*args, **kwargs):
                if args and args[0] == "Contact":
                    return contact_doc
                return _FakeLogDoc(args[0])

            frappe.get_doc = get_doc
            frappe.db.exists = lambda *args, **kwargs: True
            frappe.db.get_value = lambda *args, **kwargs: {"email_id": "guardian@example.com", "mobile_no": ""}
            frappe.get_all = lambda *args, **kwargs: [{"email_id": "guardian@example.com", "is_primary": 1}]

            values = contact_privacy.update_family_contact_from_portal_context(
                context_doctype="Guardian",
                context_name="GRD-1",
                payload={"contact": "CONTACT-1", "channel_type": "email", "value": "guardian@example.com"},
                purpose="family_consent_profile_writeback",
            )

        self.assertEqual(values["primary_email"], "guardian@example.com")
        self.assertEqual(created_logs[0]["access_type"], "raw_write")
        self.assertEqual(created_logs[0]["channel_type"], "email")
        self.assertEqual(created_logs[0]["result"], "allowed")

    def test_student_contact_summary_masks_values_by_default(self):
        with _module() as (contact_privacy, frappe):
            student_doc = SimpleNamespace(name="STU-1")
            frappe.has_permission = lambda *args, **kwargs: True
            frappe.get_doc = lambda doctype, name: student_doc

            def exists(doctype, name=None):
                return (doctype, name) in {("Student", "STU-1"), ("Contact", "CONTACT-1")}

            def get_value(doctype, filters=None, fieldname=None, as_dict=False):
                if doctype == "Dynamic Link":
                    return "CONTACT-1"
                if doctype == "Contact":
                    return {
                        "first_name": "Amina",
                        "last_name": "Example",
                        "email_id": "amina@example.com",
                        "mobile_no": "+66812345678",
                    }
                return None

            def get_all(doctype, **kwargs):
                if doctype == "Contact Email":
                    return [{"email_id": "amina@example.com", "is_primary": 1, "idx": 1}]
                if doctype == "Contact Phone":
                    return [{"phone": "+66812345678", "is_primary_mobile_no": 1, "idx": 1}]
                return []

            frappe.db.exists = exists
            frappe.db.get_value = get_value
            frappe.get_all = get_all

            summary = contact_privacy.get_masked_student_contact_summary(
                "STU-1",
                purpose="student_crm_summary",
            )

        self.assertEqual(summary["name"], "CONTACT-1")
        self.assertEqual(summary["display_name"], "Amina Example")
        self.assertEqual(summary["emails"], [{"value": "a****@example.com", "is_primary": 1}])
        self.assertEqual(summary["phones"], [{"value": "+66 *** *** 5678", "is_primary": 1}])
        self.assertNotIn("email_id", summary)
        self.assertNotIn("mobile_no", summary)

    def test_student_guardian_summary_denies_unreadable_student(self):
        with _module() as (contact_privacy, frappe):
            frappe.db.exists = lambda doctype, name=None: doctype == "Student" and name == "STU-2"
            frappe.get_doc = lambda doctype, name: SimpleNamespace(name=name)
            frappe.has_permission = lambda *args, **kwargs: False
            frappe.get_all = Mock()

            with self.assertRaises(frappe.PermissionError):
                contact_privacy.get_masked_guardian_contacts_for_student(
                    "STU-2",
                    purpose="student_guardian_summary",
                )

        frappe.get_all.assert_not_called()

    def test_family_writeback_rejects_unlinked_contact(self):
        with _module() as (contact_privacy, frappe):
            frappe.db.exists = lambda *args, **kwargs: False
            frappe.get_doc = Mock()

            with self.assertRaises(frappe.PermissionError):
                contact_privacy.update_family_contact_from_portal_context(
                    context_doctype="Guardian",
                    context_name="GRD-1",
                    payload={"contact": "CONTACT-OTHER", "channel_type": "email", "value": "guardian@example.com"},
                    purpose="family_consent_profile_writeback",
                )

        frappe.get_doc.assert_not_called()

    def test_inquiry_reuse_rejects_contact_linked_to_protected_education_record(self):
        with _module() as (contact_privacy, frappe):
            created_logs: list[dict] = []

            class _FakeLogDoc:
                def __init__(self, payload):
                    self.payload = payload
                    self.name = "CAL-1"
                    self.flags = {}

                def insert(self, ignore_permissions=True):
                    created_logs.append(self.payload)
                    return self

            frappe.get_doc = lambda payload: _FakeLogDoc(payload)
            frappe.get_all = Mock(return_value=[{"link_doctype": "Guardian", "link_name": "GRD-1"}])

            with self.assertRaises(frappe.PermissionError):
                contact_privacy.assert_contact_not_protected_for_inquiry_reuse(
                    "CONTACT-1",
                    purpose="inquiry_contact_reuse",
                    subject_doctype="Inquiry",
                    subject_name="INQ-1",
                )

        self.assertEqual(created_logs[0]["access_type"], "denied_attempt")
        self.assertEqual(created_logs[0]["result"], "denied")
        frappe.get_all.assert_called_once()

    def test_out_of_scope_applicant_contact_access_creates_denied_attempt_log(self):
        with _module() as (contact_privacy, frappe):
            created_logs: list[dict] = []

            class _FakeLogDoc:
                def __init__(self, payload):
                    self.payload = payload
                    self.name = "CAL-1"
                    self.flags = {}

                def insert(self, ignore_permissions=True):
                    created_logs.append(self.payload)
                    return self

            frappe.get_doc = lambda payload: _FakeLogDoc(payload)
            with (
                patch.object(contact_privacy, "_user_can_access_student_applicant", return_value=False),
                patch.object(contact_privacy, "_has_scoped_staff_access_to_student_applicant", return_value=False),
            ):
                with self.assertRaises(frappe.PermissionError):
                    contact_privacy.get_raw_contact_email_options_for_applicant_invite(
                        contact="CONTACT-OTHER",
                        student_applicant="APP-OTHER",
                        purpose="applicant_invite_contact_options",
                        user="admissions@example.com",
                    )

        self.assertEqual(created_logs[0]["access_type"], "denied_attempt")
        self.assertEqual(created_logs[0]["subject_name"], "APP-OTHER")
        self.assertEqual(created_logs[0]["owner_name"], "CONTACT-OTHER")


class TestContactAuditHelper(TestCase):
    def test_log_entry_details_do_not_store_raw_contact_values(self):
        with stubbed_frappe() as frappe:
            contact_audit = import_fresh("ifitwala_ed.contacts.contact_audit")
            created_logs: list[dict] = []

            class _FakeLogDoc:
                def __init__(self, payload):
                    self.payload = payload
                    self.name = "CAL-1"
                    self.flags = {}

                def insert(self, ignore_permissions=True):
                    created_logs.append(self.payload)
                    return self

            frappe.get_doc = lambda payload: _FakeLogDoc(payload)

            contact_audit.log_contact_access(
                access_type="raw_read",
                purpose="unit_test",
                workflow="unit_test",
                result="allowed",
                details={
                    "email": "guardian@example.com",
                    "mobile_number": "+66812345678",
                    "address_line1": "123 Secret Street",
                    "reason": "operator typed guardian@example.com",
                    "row_count": 1,
                },
                require_success=True,
            )

        details = created_logs[0]["details"]
        self.assertNotIn("guardian@example.com", details)
        self.assertNotIn("+66812345678", details)
        self.assertNotIn("123 Secret Street", details)
        self.assertIn("row_count", details)


class TestContactAccessLogController(TestCase):
    def test_manual_insert_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.contacts.doctype.contact_access_log.contact_access_log")
            doc = module.ContactAccessLog.__new__(module.ContactAccessLog)
            doc.flags = {}

            with self.assertRaises(frappe.PermissionError):
                doc.before_insert()

    def test_edit_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.contacts.doctype.contact_access_log.contact_access_log")
            doc = module.ContactAccessLog.__new__(module.ContactAccessLog)
            doc.is_new = lambda: False

            with self.assertRaises(frappe.ValidationError):
                doc.before_save()

    def test_delete_is_blocked(self):
        with stubbed_frappe() as frappe:
            module = import_fresh("ifitwala_ed.contacts.doctype.contact_access_log.contact_access_log")
            doc = module.ContactAccessLog.__new__(module.ContactAccessLog)

            with self.assertRaises(frappe.ValidationError):
                doc.before_delete()


class TestContactPrivacyStaticBoundary(TestCase):
    def _function_source(self, relative_path: str, function_name: str) -> str:
        package_root = Path(__file__).resolve().parents[1]
        source = package_root.joinpath(relative_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                return ast.get_source_segment(source, node) or ""
        raise AssertionError(f"{function_name} not found in {relative_path}")

    def test_sensitive_read_entrypoints_do_not_read_native_contact_directly(self):
        targets = [
            ("api/admissions_portal.py", "_applicant_contact_prefill_payload"),
            ("api/admissions_portal.py", "_invite_contact_email_options"),
            ("api/family_consent.py", "_get_contact_primary_values"),
            ("api/family_consent.py", "_apply_profile_writeback"),
            ("admission/doctype/inquiry/inquiry.py", "create_contact_from_inquiry"),
            ("students/doctype/student/student.py", "get_student_crm_summary"),
            ("students/doctype/student/student.py", "get_student_guardians"),
        ]
        forbidden_tokens = (
            'frappe.get_doc("Contact"',
            "frappe.get_doc('Contact'",
            'frappe.get_all("Contact"',
            "frappe.get_all('Contact'",
            'frappe.db.get_all("Contact"',
            "frappe.db.get_all('Contact'",
            '"Contact Email"',
            "'Contact Email'",
            '"Contact Phone"',
            "'Contact Phone'",
        )
        violations: list[str] = []

        for relative_path, function_name in targets:
            body = self._function_source(relative_path, function_name)
            for token in forbidden_tokens:
                if token in body:
                    violations.append(f"{relative_path}::{function_name}: {token}")

        self.assertEqual(violations, [])
