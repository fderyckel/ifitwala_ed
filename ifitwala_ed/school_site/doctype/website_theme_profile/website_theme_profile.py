# ifitwala_ed/school_site/doctype/website_theme_profile/website_theme_profile.py

import re

import frappe
from frappe import _
from frappe.model.document import Document


SCOPE_OPTIONS = ("Global", "Organization", "School")
PRESET_OPTIONS = ("K-12", "College", "Custom")
TYPE_SCALE_OPTIONS = ("compact", "standard", "large")
SPACING_DENSITY_OPTIONS = ("compact", "standard", "relaxed")
HERO_STYLE_OPTIONS = ("classic", "split", "spotlight")
COLOR_FIELDS = ("primary_color", "accent_color", "surface_color", "text_color")
HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

THEME_PRESET_RECORDS = (
	{
		"profile_name": "Default K-12 Theme",
		"scope_type": "Global",
		"preset_type": "K-12",
		"is_default": 1,
		"primary_color": "#1d4ed8",
		"accent_color": "#16a34a",
		"surface_color": "#f8fafc",
		"text_color": "#0f172a",
		"type_scale": "standard",
		"spacing_density": "standard",
		"hero_style": "spotlight",
		"enable_motion": 1,
	},
	{
		"profile_name": "Default College Theme",
		"scope_type": "Global",
		"preset_type": "College",
		"is_default": 0,
		"primary_color": "#1e293b",
		"accent_color": "#b45309",
		"surface_color": "#f8fafc",
		"text_color": "#0f172a",
		"type_scale": "large",
		"spacing_density": "relaxed",
		"hero_style": "split",
		"enable_motion": 1,
	},
)

PRESET_DEFAULTS = {
	"K-12": {
		"primary_color": "#1d4ed8",
		"accent_color": "#16a34a",
		"surface_color": "#f8fafc",
		"text_color": "#0f172a",
		"type_scale": "standard",
		"spacing_density": "standard",
		"hero_style": "spotlight",
		"enable_motion": 1,
	},
	"College": {
		"primary_color": "#1e293b",
		"accent_color": "#b45309",
		"surface_color": "#f8fafc",
		"text_color": "#0f172a",
		"type_scale": "large",
		"spacing_density": "relaxed",
		"hero_style": "split",
		"enable_motion": 1,
	},
}


def _normalize_choice(*, value: str | None, allowed: tuple[str, ...], default: str, label: str) -> str:
	text = (value or default).strip()
	if text not in allowed:
		frappe.throw(
			_("{0} must be one of: {1}.").format(label, ", ".join(allowed)),
			frappe.ValidationError,
		)
	return text


def normalize_scope_type(value: str | None) -> str:
	return _normalize_choice(
		value=value,
		allowed=SCOPE_OPTIONS,
		default="Global",
		label=_("Scope Type"),
	)


def normalize_preset_type(value: str | None) -> str:
	return _normalize_choice(
		value=value,
		allowed=PRESET_OPTIONS,
		default="Custom",
		label=_("Preset Type"),
	)


def normalize_type_scale(value: str | None) -> str:
	return _normalize_choice(
		value=value,
		allowed=TYPE_SCALE_OPTIONS,
		default="standard",
		label=_("Type Scale"),
	)


def normalize_spacing_density(value: str | None) -> str:
	return _normalize_choice(
		value=value,
		allowed=SPACING_DENSITY_OPTIONS,
		default="standard",
		label=_("Spacing Density"),
	)


def normalize_hero_style(value: str | None) -> str:
	return _normalize_choice(
		value=value,
		allowed=HERO_STYLE_OPTIONS,
		default="classic",
		label=_("Hero Style"),
	)


def normalize_hex_color(value: str | None, *, field_label: str) -> str:
	text = (value or "").strip().lower()
	if not text:
		frappe.throw(
			_("{0} is required.").format(field_label),
			frappe.ValidationError,
		)
	if not HEX_COLOR_PATTERN.match(text):
		frappe.throw(
			_("{0} must be a valid hex color (e.g. #1d4ed8).").format(field_label),
			frappe.ValidationError,
		)
	return text


def build_scope_filters(*, scope_type: str, organization: str | None = None, school: str | None = None) -> dict:
	scope_type = normalize_scope_type(scope_type)
	if scope_type == "Global":
		return {"scope_type": "Global"}
	if scope_type == "Organization":
		return {"scope_type": "Organization", "organization": (organization or "").strip()}
	return {"scope_type": "School", "school": (school or "").strip()}


def get_theme_preset_records() -> list[dict]:
	return [dict(row) for row in THEME_PRESET_RECORDS]


def ensure_theme_profile_presets() -> dict:
	if not frappe.db.exists("DocType", "Website Theme Profile"):
		return {"created": [], "skipped": []}

	created = []
	skipped = []
	for row in get_theme_preset_records():
		existing = frappe.db.get_value(
			"Website Theme Profile",
			{
				"profile_name": row["profile_name"],
				"scope_type": row["scope_type"],
			},
			"name",
		)
		if existing:
			skipped.append(row["profile_name"])
			continue
		frappe.get_doc(
			{
				"doctype": "Website Theme Profile",
				**row,
			}
		).insert(ignore_permissions=True)
		created.append(row["profile_name"])
	return {"created": created, "skipped": skipped}


class WebsiteThemeProfile(Document):
	def validate(self):
		self.profile_name = (self.profile_name or "").strip()
		if not self.profile_name:
			frappe.throw(_("Profile Name is required."), frappe.ValidationError)

		self.scope_type = normalize_scope_type(self.scope_type)
		self.preset_type = normalize_preset_type(self.preset_type)
		self.type_scale = normalize_type_scale(self.type_scale)
		self.spacing_density = normalize_spacing_density(self.spacing_density)
		self.hero_style = normalize_hero_style(self.hero_style)
		self.enable_motion = int(self.enable_motion or 0)
		self.is_default = int(self.is_default or 0)

		self.apply_preset_defaults()
		self.validate_scope()
		self.validate_color_tokens()
		self.validate_unique_default_for_scope()

	def apply_preset_defaults(self):
		defaults = PRESET_DEFAULTS.get(self.preset_type) or {}
		for fieldname, value in defaults.items():
			if fieldname in COLOR_FIELDS:
				if not (self.get(fieldname) or "").strip():
					self.set(fieldname, value)
				continue
			if fieldname == "enable_motion":
				if self.get(fieldname) in (None, ""):
					self.set(fieldname, int(value))
				continue
			if not (self.get(fieldname) or "").strip():
				self.set(fieldname, value)

	def validate_scope(self):
		if self.scope_type == "Global":
			self.organization = None
			self.school = None
			return

		if self.scope_type == "Organization":
			self.organization = (self.organization or "").strip() or None
			if not self.organization:
				frappe.throw(
					_("Organization is required when Scope Type is Organization."),
					frappe.ValidationError,
				)
			self.school = None
			return

		self.school = (self.school or "").strip() or None
		if not self.school:
			frappe.throw(
				_("School is required when Scope Type is School."),
				frappe.ValidationError,
			)
		self.organization = None

	def validate_color_tokens(self):
		for fieldname in COLOR_FIELDS:
			label = self.meta.get_label(fieldname) or fieldname.replace("_", " ").title()
			self.set(fieldname, normalize_hex_color(self.get(fieldname), field_label=label))

	def validate_unique_default_for_scope(self):
		if not self.is_default:
			return

		filters = build_scope_filters(
			scope_type=self.scope_type,
			organization=self.organization,
			school=self.school,
		)
		filters["is_default"] = 1
		filters["name"] = ["!=", self.name]
		if frappe.db.exists("Website Theme Profile", filters):
			frappe.throw(
				_("Only one default theme profile is allowed per scope."),
				frappe.ValidationError,
			)
