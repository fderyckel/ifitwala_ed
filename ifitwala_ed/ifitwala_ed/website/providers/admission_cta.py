# ifitwala_ed/website/providers/admission_cta.py

import frappe
from frappe import _

from ifitwala_ed.website.utils import resolve_admissions_cta_url


INTENTS = {"inquire", "visit", "apply"}
STYLES = {"primary", "secondary", "outline"}
DEFAULT_LABELS = {
	"inquire": "Inquire",
	"visit": "Visit",
	"apply": "Apply",
}


def get_context(*, school, page, block_props):
	intent = block_props.get("intent")
	if intent not in INTENTS:
		frappe.throw(
			_("Invalid admission CTA intent: {0}").format(intent),
			frappe.ValidationError,
		)

	style = block_props.get("style") or "primary"
	if style not in STYLES:
		frappe.throw(
			_("Invalid admission CTA style: {0}").format(style),
			frappe.ValidationError,
		)

	label = block_props.get("label_override") or DEFAULT_LABELS[intent]
	url = resolve_admissions_cta_url(school=school, intent=intent)

	return {
		"data": {
			"intent": intent,
			"label": label,
			"url": url,
			"style": style,
			"icon": block_props.get("icon"),
			"tracking_id": block_props.get("tracking_id"),
		}
	}
