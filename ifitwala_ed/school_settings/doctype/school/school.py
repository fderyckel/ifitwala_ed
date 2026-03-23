# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school/school.py

import frappe
from frappe import _
from frappe.cache_manager import clear_defaults_cache
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet

from ifitwala_ed.school_settings.doctype.academic_load_policy.academic_load_policy import (
    ensure_default_policy_for_school,
)
from ifitwala_ed.utilities.organization_media import (
    ensure_organization_media_files_visible_to_school,
)


class School(NestedSet):
    nsm_parent_field = "parent_school"

    def onload(self):
        load_address_and_contact(self, "school")

    def validate(self):
        # Core identity + hierarchy integrity
        self.validate_abbr()
        self.validate_parent_school()  # parent must be group
        self.validate_parent_school_organization()  # parent/child must share org
        self.apply_parent_attendance_threshold_defaults()
        self.validate_attendance_thresholds()
        self.validate_website_publication()
        self.validate_governed_public_media()

        # prevent changing Organization on a node that has children.
        # Rationale: avoids accidental cross-org subtree drift and keeps "effective record" resolution sane.
        self.validate_organization_change_policy_a()

    def validate_governed_public_media(self):
        self._sync_school_logo_media()
        self._sync_gallery_media_rows()

    def _sync_school_logo_media(self):
        logo_file = (self.school_logo_file or "").strip()
        logo_url = (self.school_logo or "").strip()

        if not logo_file and logo_url:
            frappe.throw(
                _(
                    "School Logo must use governed Organization Media. "
                    "Re-upload it with Upload School Logo or relink it from Manage Organization Media."
                )
            )

        if not logo_file:
            if not logo_url:
                self.school_logo_file = None
            return

        media_rows = ensure_organization_media_files_visible_to_school(
            school=self.name,
            file_names=[logo_file],
        )
        media_row = media_rows[logo_file]
        media_url = (media_row.get("file_url") or "").strip()
        if not media_url:
            frappe.throw(_("School Logo file '{0}' is missing a file URL.").format(logo_file))

        self.school_logo_file = logo_file
        self.school_logo = media_url

    def _sync_gallery_media_rows(self):
        governed_files: list[str] = []

        for row in self.gallery_image or []:
            governed_file = (row.governed_file or "").strip()
            row_image = (row.school_image or "").strip()

            if not governed_file and row_image:
                frappe.throw(
                    _(
                        "Gallery Image rows must use governed Organization Media. "
                        "Re-upload the image with Upload Gallery Image or relink it from Manage Organization Media."
                    )
                )

            if governed_file:
                governed_files.append(governed_file)

        if not governed_files:
            return

        visible_rows = ensure_organization_media_files_visible_to_school(
            school=self.name,
            file_names=governed_files,
        )

        for row in self.gallery_image or []:
            governed_file = (row.governed_file or "").strip()
            if not governed_file:
                continue

            media_row = visible_rows[governed_file]
            media_url = (media_row.get("file_url") or "").strip()
            if not media_url:
                frappe.throw(_("Gallery Image file '{0}' is missing a file URL.").format(governed_file))

            row.governed_file = governed_file
            row.school_image = media_url

    def on_update(self):
        NestedSet.on_update(self)

    def after_save(self):
        if self.has_value_changed("is_published") or self.has_value_changed("website_slug"):
            self.sync_website_page_publication()
            if int(self.is_published or 0) == 1 and (self.website_slug or "").strip():
                from ifitwala_ed.website.bootstrap import ensure_default_school_website

                ensure_default_school_website(
                    school_name=self.name,
                    set_default_organization=True,
                )

    def after_insert(self):
        ensure_default_policy_for_school(self.name, ignore_permissions=True)

    def on_trash(self):
        NestedSet.validate_if_child_exists(self)
        frappe.utils.nestedset.update_nsm(self)

    def after_rename(self, olddn, newdn, merge=False):
        # when merging, let the target keep its own title; only force-update on regular renames
        if not merge:
            # cheap single-field DB write; avoids extra fetch/save
            self.db_set("school_name", newdn, update_modified=False)
        clear_defaults_cache()

    def validate_abbr(self):
        if not self.abbr:
            self.abbr = "".join([c[0] for c in self.school_name.split()]).upper()

        self.abbr = self.abbr.strip()

        if self.get("__islocal") and len(self.abbr) > 5:
            frappe.throw(_("Abbreviation cannot have more than 5 characters"))

        if not self.abbr.strip():
            frappe.throw(_("Abbreviation is mandatory"))

        # Keep existing behavior; avoid broader refactors here.
        if frappe.db.exists("School", {"abbr": self.abbr, "name": ["!=", self.name]}):
            frappe.throw(_("Abbreviation {0} is already used for another school.").format(self.abbr))

    def validate_parent_school(self):
        if self.parent_school:
            is_group = frappe.db.get_value("School", self.parent_school, "is_group")
            if not is_group:
                frappe.throw(_("Parent School must be a group school."))

    def validate_parent_school_organization(self):
        """
        Hard invariant:
        If a School has a parent_school, both MUST belong to the same Organization.

        This protects:
        - permission logic that assumes a coherent school tree
        - "effective record" resolution that climbs school ancestors then (optionally) org ancestors
        - multi-school governance where org boundaries are meaningful
        """
        if not self.parent_school:
            return

        parent_org, parent_school_name = frappe.db.get_value(
            "School",
            self.parent_school,
            ["organization", "school_name"],
        ) or (None, None)

        # Defensive: if parent is missing or has no org, let Frappe/DB integrity handle it elsewhere.
        if not parent_org:
            return

        child_org = (self.organization or "").strip()
        parent_org = (parent_org or "").strip()

        if child_org and parent_org and child_org != parent_org:
            frappe.throw(
                _(
                    'School "{child}" belongs to Organization "{child_org}", '
                    'but its Parent School "{parent}" belongs to Organization "{parent_org}".\n\n'
                    "Parent and child schools must belong to the same Organization.\n"
                    'Fix: either change this School’s Organization to "{parent_org}" '
                    'or choose a different Parent School under "{child_org}".'
                ).format(
                    child=self.school_name or self.name,
                    child_org=child_org,
                    parent=parent_school_name or self.parent_school,
                    parent_org=parent_org,
                )
            )

    def validate_organization_change_policy_a(self):
        """
        Block changing a School's Organization if it has children.

        Reason:
        Changing org on a parent would either:
        - silently strand children in a different org (invalid), or
        - require a subtree migration workflow (out of scope for now).

        So we force the user to:
        - migrate the subtree intentionally (future tool), or
        - only change org when the node is a leaf.
        """
        # New docs: nothing to compare
        if self.get("__islocal"):
            return

        # Only act when Organization is being changed
        if not self.has_value_changed("organization"):
            return

        # If this node has children, block the change.
        # (cheap existence check; avoids loading nestedset ranges)
        has_children = frappe.db.exists("School", {"parent_school": self.name})
        if not has_children:
            return

        before = self.get_doc_before_save()
        old_org = (before.organization or "").strip() if before else ""
        new_org = (self.organization or "").strip()

        frappe.throw(
            _(
                'Cannot change Organization for School "{school}" because it has child schools.\n\n'
                'Current Organization: "{old_org}"\n'
                'Requested Organization: "{new_org}"\n\n'
                "Policy: a School with children cannot change Organization (to prevent cross-organization trees).\n"
                "Fix: move/re-parent child schools first (or use a future subtree migration tool), "
                "then change the Organization when this School becomes a leaf."
            ).format(
                school=self.school_name or self.name,
                old_org=old_org,
                new_org=new_org,
            )
        )

    def validate_website_publication(self):
        if not getattr(self, "is_published", 0):
            return
        if not (self.website_slug or "").strip():
            from ifitwala_ed.website.bootstrap import _next_available_school_slug

            self.website_slug = _next_available_school_slug(
                self.abbr or self.school_name or self.name,
                school_name=self.name or self.school_name,
            )

    def apply_parent_attendance_threshold_defaults(self):
        """
        On child-school creation, inherit attendance thresholds from parent school.
        """
        if not self.parent_school:
            return
        if not self.get("__islocal"):
            return

        parent_row = frappe.db.get_value(
            "School",
            self.parent_school,
            ["attendance_warning_threshold", "attendance_critical_threshold"],
            as_dict=True,
        )
        if not parent_row:
            return

        if parent_row.get("attendance_warning_threshold") is not None:
            self.attendance_warning_threshold = parent_row.get("attendance_warning_threshold")
        if parent_row.get("attendance_critical_threshold") is not None:
            self.attendance_critical_threshold = parent_row.get("attendance_critical_threshold")

    def validate_attendance_thresholds(self):
        warning = flt(self.attendance_warning_threshold or 0)
        critical = flt(self.attendance_critical_threshold or 0)

        if warning < 0 or warning > 100:
            frappe.throw(_("Warning Threshold (%) must be between 0 and 100."))
        if critical < 0 or critical > 100:
            frappe.throw(_("Critical Threshold (%) must be between 0 and 100."))
        if warning < critical:
            frappe.throw(_("Warning Threshold (%) must be greater than or equal to Critical Threshold (%)."))

        self.attendance_warning_threshold = warning
        self.attendance_critical_threshold = critical

    def sync_website_page_publication(self):
        page_names = frappe.get_all(
            "School Website Page",
            filters={"school": self.name},
            pluck="name",
        )
        if not page_names:
            return

        should_publish = bool((self.website_slug or "").strip()) and int(self.is_published or 0) == 1
        status = "Published" if should_publish else "Draft"
        is_published = 1 if should_publish else 0

        for name in page_names:
            frappe.db.set_value(
                "School Website Page",
                name,
                {"status": status, "is_published": is_published},
                update_modified=False,
            )


@frappe.whitelist()
def enqueue_replace_abbr(school, old, new):
    kwargs = dict(school=school, old=old, new=new)
    frappe.enqueue("ifitwala_ed.school_settings.doctype.school.school.replace_abbr", **kwargs)


@frappe.whitelist()
def replace_abbr(school, old, new):
    new = new.strip()
    if not new:
        frappe.throw(_("Abbr can not be blank or space"))

    frappe.only_for("System Manager")

    frappe.db.set_value("School", school, "abbr", new)

    def _rename_record(doc):
        parts = doc[0].rsplit(" - ", 1)
        if len(parts) == 1 or parts[1].lower() == old.lower():
            frappe.rename_doc(dt, doc[0], parts[0] + " - " + new)  # noqa: F821  # dt from outer scope

    def _rename_records(dt):
        # rename is expensive so let's be economical with memory usage
        doc = (d for d in frappe.db.sql("select name from `tab%s` where school=%s" % (dt, "%s"), school))
        for d in doc:
            _rename_record(d)


def get_name_with_abbr(name, school):
    school_abbr = frappe.db.get_value("School", school, "abbr")
    parts = name.split(" - ")
    if parts[-1].lower() != school_abbr.lower():
        parts.append(school_abbr)
    return " - ".join(parts)


@frappe.whitelist()
def get_children(doctype, parent=None, school=None, is_root=False):
    # TreeView behavior:
    # - "All Schools" is a UI sentinel (not a real School record)
    # - When a School is selected in the tree filter, TreeView sets BOTH:
    #     parent=<selected_school> and school=<selected_school>
    # - We intentionally use `parent` as the expansion root. `school` is redundant.
    if parent is None or parent == "All Schools":
        parent = ""

    return frappe.db.sql(
        """
		SELECT
			name as value,
			is_group as expandable
		FROM
			`tab{doctype}` comp
		WHERE
			ifnull(parent_school, "")={parent}
		""".format(
            doctype=doctype,
            parent=frappe.db.escape(parent),
        ),
        as_dict=1,
    )


@frappe.whitelist()
def add_node():
    from frappe.desk.treeview import make_tree_args

    args = frappe.form_dict
    args = make_tree_args(**args)

    if args.parent_school == "All Schools":
        args.parent_school = None

    frappe.get_doc(args).insert()
