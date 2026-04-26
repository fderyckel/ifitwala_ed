from __future__ import annotations

from dataclasses import dataclass

import frappe

TEST_ORGANIZATION = "_Test Ifitwala Organization"
TEST_ROOT_SCHOOL = "_Test Ifitwala School"
TEST_CHILD_SCHOOL = "_Test Ifitwala Child School"
TEST_ACADEMIC_YEAR = "_Test Ifitwala AY"
TEST_TERM = "_Test Ifitwala Term"
TEST_GRADE_SCALE = "_Test Ifitwala Grade Scale"


@dataclass(frozen=True)
class IfitwalaBootstrapRecords:
    organization: str
    root_school: str
    child_school: str
    academic_year: str
    term: str
    grade_scale: str


class IfitwalaBootstrapTestData:
    """Persistent, app-owned reference data for DB-backed tests."""

    _records: IfitwalaBootstrapRecords | None = None

    @classmethod
    def ensure(cls) -> IfitwalaBootstrapRecords:
        if cls._records:
            return cls._records

        organization = cls._ensure_organization()
        root_school = cls._ensure_school(
            TEST_ROOT_SCHOOL,
            organization=organization,
            abbr="ITST",
            is_group=1,
        )
        child_school = cls._ensure_school(
            TEST_CHILD_SCHOOL,
            organization=organization,
            abbr="ITCH",
            parent_school=root_school,
            is_group=0,
        )
        academic_year = cls._ensure_academic_year(TEST_ACADEMIC_YEAR, school=root_school)
        term = cls._ensure_term(TEST_TERM, academic_year=academic_year, school=root_school)
        grade_scale = cls._ensure_grade_scale()

        frappe.db.commit()

        cls._records = IfitwalaBootstrapRecords(
            organization=organization,
            root_school=root_school,
            child_school=child_school,
            academic_year=academic_year,
            term=term,
            grade_scale=grade_scale,
        )
        return cls._records

    @staticmethod
    def _values_match(actual, expected) -> bool:
        if expected is None:
            return actual in (None, "")
        return actual == expected

    @staticmethod
    def _assert_existing_record(doctype: str, name: str, expected: dict[str, object]) -> None:
        values = frappe.db.get_value(doctype, name, list(expected), as_dict=True)
        if not values:
            raise AssertionError(f"Bootstrap record {doctype} {name} was not found.")

        mismatched = {
            fieldname: {"expected": expected_value, "actual": values.get(fieldname)}
            for fieldname, expected_value in expected.items()
            if not IfitwalaBootstrapTestData._values_match(values.get(fieldname), expected_value)
        }
        if mismatched:
            raise AssertionError(f"Bootstrap record {doctype} {name} has drifted: {mismatched}")

    @staticmethod
    def _ensure_organization() -> str:
        if frappe.db.exists("Organization", TEST_ORGANIZATION):
            IfitwalaBootstrapTestData._assert_existing_record(
                "Organization",
                TEST_ORGANIZATION,
                {
                    "organization_name": TEST_ORGANIZATION,
                    "abbr": "ITED",
                    "is_group": 1,
                },
            )
            return TEST_ORGANIZATION

        previous_skip_coa = bool(getattr(frappe.flags, "skip_org_coa_setup", False))
        frappe.flags.skip_org_coa_setup = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Organization",
                    "organization_name": TEST_ORGANIZATION,
                    "abbr": "ITED",
                    "is_group": 1,
                }
            )
            doc.flags.skip_coa_setup = True
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.skip_org_coa_setup = previous_skip_coa

        return doc.name

    @staticmethod
    def _ensure_school(
        school_name: str,
        *,
        organization: str,
        abbr: str,
        parent_school: str | None = None,
        is_group: int = 0,
    ) -> str:
        if frappe.db.exists("School", school_name):
            IfitwalaBootstrapTestData._assert_existing_record(
                "School",
                school_name,
                {
                    "school_name": school_name,
                    "abbr": abbr,
                    "organization": organization,
                    "parent_school": parent_school,
                    "is_group": is_group,
                },
            )
            return school_name

        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name,
                "abbr": abbr,
                "organization": organization,
                "parent_school": parent_school,
                "is_group": is_group,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _ensure_academic_year(academic_year_name: str, *, school: str) -> str:
        existing = frappe.db.get_value(
            "Academic Year",
            {
                "academic_year_name": academic_year_name,
                "school": school,
            },
            "name",
        )
        if existing:
            return existing

        doc = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": academic_year_name,
                "school": school,
                "archived": 0,
                "visible_to_admission": 1,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _ensure_term(term_name: str, *, academic_year: str, school: str) -> str:
        existing = frappe.db.get_value(
            "Term",
            {
                "academic_year": academic_year,
                "term_name": term_name,
                "school": school,
            },
            "name",
        )
        if existing:
            return existing

        doc = frappe.get_doc(
            {
                "doctype": "Term",
                "academic_year": academic_year,
                "term_name": term_name,
                "school": school,
                "term_type": "Academic",
                "archived": 0,
                "visible_to_admission": 1,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _ensure_grade_scale() -> str:
        if frappe.db.exists("Grade Scale", TEST_GRADE_SCALE):
            IfitwalaBootstrapTestData._assert_existing_record(
                "Grade Scale",
                TEST_GRADE_SCALE,
                {
                    "grade_scale_name": TEST_GRADE_SCALE,
                    "maximum_grade": 100,
                },
            )
            return TEST_GRADE_SCALE

        doc = frappe.get_doc(
            {
                "doctype": "Grade Scale",
                "grade_scale_name": TEST_GRADE_SCALE,
                "maximum_grade": 100,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name
