from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.normalize_default_admissions_page_blocks import (
    _build_legacy_default_admissions_blocks,
    _looks_like_legacy_default_admissions_page,
)


class TestNormalizeDefaultAdmissionsPageBlocks(FrappeTestCase):
    def test_detects_legacy_default_admissions_page(self):
        school = frappe._dict(
            {
                "school_name": "Ifitwala International School",
                "label_cta_inquiry": "Get more info",
                "label_cta_roi": "Book a School Visit",
            }
        )
        page = frappe._dict(
            {
                "route": "admissions",
                "page_type": "Admissions",
                "blocks": [
                    frappe._dict(
                        {
                            "block_type": block["block_type"],
                            "props": frappe.as_json(block["props"]),
                        }
                    )
                    for block in _build_legacy_default_admissions_blocks(school=school)
                ],
            }
        )

        self.assertTrue(_looks_like_legacy_default_admissions_page(page=page, school=school))

    def test_rejects_customized_admissions_page(self):
        school = frappe._dict(
            {
                "school_name": "Ifitwala International School",
                "label_cta_inquiry": "Get more info",
                "label_cta_roi": "Book a School Visit",
            }
        )
        page = frappe._dict(
            {
                "route": "admissions",
                "page_type": "Admissions",
                "blocks": [
                    frappe._dict(
                        {
                            "block_type": "admission_cta",
                            "props": frappe.as_json(
                                {
                                    "intent": "visit",
                                    "style": "secondary",
                                    "label_override": "Tour the Campus",
                                }
                            ),
                        }
                    )
                ],
            }
        )

        self.assertFalse(_looks_like_legacy_default_admissions_page(page=page, school=school))
