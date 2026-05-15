# ifitwala_ed/website/providers/course_intro.py

import frappe
from frappe import _

from ifitwala_ed.utilities.html_sanitizer import sanitize_html
from ifitwala_ed.website.utils import build_image_variants, resolve_admissions_cta_url

INTENTS = {"inquire", "visit", "apply"}
DEFAULT_LABELS = {
    "inquire": "Inquire",
    "visit": "Visit",
    "apply": "Apply",
}


def get_context(*, school, page, block_props):
    if page.doctype != "Course Website Profile":
        frappe.throw(
            _("Course Intro block is only allowed on Course pages."),
            frappe.ValidationError,
        )

    heading = (block_props.get("heading") or "").strip()
    if not heading:
        frappe.throw(
            _("Course Intro requires a heading."),
            frappe.ValidationError,
        )

    content_html = block_props.get("content_html") or page.intro_text or ""
    hero_image = block_props.get("hero_image") or page.hero_image

    cta_intent = block_props.get("cta_intent")
    cta = None
    if cta_intent:
        if cta_intent not in INTENTS:
            frappe.throw(
                _("Invalid CTA intent on Course Intro."),
                frappe.ValidationError,
            )
        cta = {
            "label": DEFAULT_LABELS[cta_intent],
            "url": resolve_admissions_cta_url(school=school, intent=cta_intent),
        }

    return {
        "data": {
            "heading": heading,
            "content": sanitize_html(content_html, allow_headings_from="h2"),
            "hero_image": build_image_variants(hero_image, "course") if hero_image else None,
            "overview_heading": (block_props.get("overview_heading") or "Overview").strip(),
            "overview": sanitize_html(page.overview_html or "", allow_headings_from="h3"),
            "aims_heading": (block_props.get("aims_heading") or "What Students Will Develop").strip(),
            "aims": sanitize_html(page.aims_html or "", allow_headings_from="h3"),
            "assessment_heading": (block_props.get("assessment_heading") or "Assessment Approach").strip(),
            "assessment_summary": sanitize_html(page.assessment_summary_html or "", allow_headings_from="h3"),
            "cta": cta,
        }
    }
