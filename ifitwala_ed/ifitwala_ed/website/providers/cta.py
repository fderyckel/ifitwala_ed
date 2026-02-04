# ifitwala_ed/website/providers/cta.py

from ifitwala_ed.website.utils import validate_cta_link


def get_context(*, school, page, block_props):
	"""
	Call-to-action block. No data fetching.
	"""
	return {
		"data": {
			"title": block_props.get("title"),
			"text": block_props.get("text"),
			"button_label": block_props.get("button_label"),
			"button_link": validate_cta_link(block_props.get("button_link")),
		}
	}
