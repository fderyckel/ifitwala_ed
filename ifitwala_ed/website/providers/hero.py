# ifitwala_ed/website/providers/hero.py

from ifitwala_ed.website.utils import build_image_variants, validate_cta_link


def get_context(*, school, page, block_props):
	"""
	HERO block. SEO owner: <h1>.
	"""
	image = build_image_variants(block_props.get("background_image"), "school")
	return {
		"data": {
			"title": block_props.get("title"),
			"subtitle": block_props.get("subtitle"),
			"image": image,
			"cta_label": block_props.get("cta_label"),
			"cta_link": validate_cta_link(block_props.get("cta_link")),
			"variant": block_props.get("variant") or "default",
		}
	}
