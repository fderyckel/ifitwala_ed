# ifitwala_ed/website/providers/hero.py

from frappe.utils import cint

from ifitwala_ed.website.utils import build_image_variants, validate_cta_link

FADE_MODES = {"none", "dark", "primary", "accent"}


def get_context(*, school, page, block_props):
    """
    HERO block. SEO owner: <h1>.
    """
    images = []
    for item in block_props.get("images") or []:
        image_url = item.get("image")
        if not image_url:
            continue
        images.append(
            {
                "image": build_image_variants(image_url, "school"),
                "alt": item.get("alt") or item.get("caption") or block_props.get("title"),
                "caption": item.get("caption"),
            }
        )

    if not images and school and school.get("gallery_image"):
        for row in school.gallery_image:
            if not row.school_image:
                continue
            images.append(
                {
                    "image": build_image_variants(row.school_image, "school"),
                    "alt": row.caption or block_props.get("title"),
                    "caption": row.caption,
                }
            )

    image = build_image_variants(block_props.get("background_image"), "school")
    image_fade_mode = (block_props.get("image_fade_mode") or "dark").strip().lower()
    if image_fade_mode not in FADE_MODES:
        image_fade_mode = "dark"
    image_fade_opacity = min(max(cint(block_props.get("image_fade_opacity") or 34), 0), 90)

    return {
        "data": {
            "title": block_props.get("title"),
            "subtitle": block_props.get("subtitle"),
            "image": image,
            "images": images,
            "autoplay": bool(block_props.get("autoplay", True)),
            "interval": max(cint(block_props.get("interval") or 5000), 1000),
            "cta_label": block_props.get("cta_label"),
            "cta_link": validate_cta_link(block_props.get("cta_link")),
            "variant": block_props.get("variant") or "default",
            "image_fade_mode": image_fade_mode,
            "image_fade_opacity": image_fade_opacity,
        }
    }
