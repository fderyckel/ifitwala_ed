# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/stock/doctype/location/location.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.utilities.school_tree import get_ancestor_schools


class Location(Document):
    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def before_insert(self):
        """
        Insert-time normalization only.
        We inherit Organization from parent when available.
        """
        self._inherit_org_from_parent()

    def validate(self):
        """
        Main validation entrypoint.

        Order matters:
        - Structural integrity first (tree shape, parent, school lineage, type constraints)
        - Governance constraints next (org/school membership)
        - Operational constraints last (capacity vs usage)
        - Soft warnings last (avoid spam)
        """
        # 1) Structural integrity first
        self._validate_parent_is_group()
        self._validate_school_lineage_against_parent()
        self._validate_location_type_capabilities()

        # 2) Governance constraints
        self._validate_org_against_parent()
        self._validate_school_organization_membership()

        # 3) Operational constraints
        self.validate_capacity_against_groups()

        # 4) Soft warnings (only when relevant)
        self._warn_on_stock_location_without_school()

    # -------------------------------------------------------------------------
    # Small internal cache helpers (reduces repeated DB hits inside validate)
    # -------------------------------------------------------------------------

    def _get_parent_value(self, fieldname):
        if not self.parent_location:
            return None
        key = f"parent:{self.parent_location}:{fieldname}"
        if not hasattr(self, "_validate_cache"):
            self._validate_cache = {}
        if key not in self._validate_cache:
            self._validate_cache[key] = frappe.db.get_value("Location", self.parent_location, fieldname)
        return self._validate_cache[key]

    def _get_location_type_row(self):
        if not self.location_type:
            return None
        key = f"lt:{self.location_type}"
        if not hasattr(self, "_validate_cache"):
            self._validate_cache = {}
        if key not in self._validate_cache:
            self._validate_cache[key] = frappe.db.get_value(
                "Location Type",
                self.location_type,
                ["is_container", "is_schedulable", "can_hold_stock"],
                as_dict=True,
            )
        return self._validate_cache[key]

    def _has_value_changed_safe(self, fieldname):
        """
        Guard: has_value_changed exists in modern Frappe, but keep safe.
        """
        fn = getattr(self, "has_value_changed", None)
        if callable(fn):
            return fn(fieldname)
        # Fallback: for new docs, treat as changed so warnings can fire once.
        return self.is_new()

    # -------------------------------------------------------------------------
    # Organization inheritance & integrity
    # -------------------------------------------------------------------------

    def _inherit_org_from_parent(self):
        """
        If a parent is set, adopt its Organization when missing or different.

        This is insert-time only to avoid destructive updates on existing trees.
        """
        if not getattr(self, "parent_location", None):
            return

        parent_org = frappe.db.get_value("Location", self.parent_location, "organization")

        if not parent_org:
            # Allow save but warn: parent should be fixed first
            frappe.msgprint(
                _("Parent Location {0} has no Organization set; please fix the parent first.").format(
                    frappe.utils.get_link_to_form("Location", self.parent_location)
                ),
                title=_("Parent Missing Organization"),
                indicator="orange",
            )
            return

        if not self.organization or self.organization != parent_org:
            self.organization = parent_org

    def _validate_org_against_parent(self):
        """
        A child Location cannot have an Organization different from its parent.

        This is a hard rule to prevent cross-org contamination of the Location tree.
        """
        if not getattr(self, "parent_location", None):
            return

        parent_org = self._get_parent_value("organization")

        if not parent_org:
            frappe.throw(
                _("Parent Location {0} has no Organization set. Set it on the parent first.").format(
                    frappe.utils.get_link_to_form("Location", self.parent_location)
                ),
                title=_("Parent Missing Organization"),
            )

        if self.organization and self.organization != parent_org:
            frappe.throw(
                _("Child Location Organization must match its parent. Parent: <b>{0}</b>, Child: <b>{1}</b>.").format(
                    parent_org, self.organization
                ),
                title=_("Organization Mismatch"),
            )

        # Normalize to parent just in case
        self.organization = parent_org

    # -------------------------------------------------------------------------
    # Capacity enforcement
    # -------------------------------------------------------------------------

    def validate_capacity_against_groups(self):
        """
        Highly efficient capacity check.

        Design goals:
        - No N+1 queries
        - Skip when capacity <= 0 (no limit)
        - Hard-block only when real active enrollment exceeds capacity

        Process:
        1) Find active Student Groups scheduling this Location
        2) Count active students per group in a single grouped query
        3) Fail loudly if any group exceeds capacity
        """
        cap = cint(self.maximum_capacity or 0)
        if cap <= 0:
            return

        # 1) Find active Student Groups that reference this Location
        sg_rows = frappe.db.sql(
            """
			SELECT DISTINCT sg.name AS name
			FROM `tabStudent Group Schedule` AS sgs
			INNER JOIN `tabStudent Group` AS sg
				ON sg.name = sgs.parent
			WHERE sgs.location = %s
			  AND sg.status = 'Active'
			""",
            (self.name,),
            as_dict=True,
        )

        if not sg_rows:
            return

        sg_names = [r["name"] for r in sg_rows]

        # 2) Count active students per Student Group
        count_rows = frappe.db.sql(
            """
			SELECT parent AS name, COUNT(*) AS active_count
			FROM `tabStudent Group Student`
			WHERE parent IN %(groups)s
			  AND COALESCE(active, 0) = 1
			GROUP BY parent
			""",
            {"groups": tuple(sg_names)},
            as_dict=True,
        )

        if not count_rows:
            return

        # 3) Detect violations
        over_capacity = [(r["name"], cint(r["active_count"])) for r in count_rows if cint(r["active_count"]) > cap]

        if over_capacity:
            lines = "\n".join(f"- {sg}: active students {count} > capacity {cap}" for sg, count in over_capacity)
            frappe.throw(
                _(
                    "Cannot set maximum capacity below active enrollment for Student Groups using this Location:\n{0}"
                ).format(lines),
                title=_("Capacity Too Low"),
            )

    # -------------------------------------------------------------------------
    # School ↔ Organization governance
    # -------------------------------------------------------------------------

    def _validate_school_organization_membership(self):
        """
        If a school is set:
        - Find the first ancestor school (including self) that has an Organization.
        - Auto-fill Location.organization from that if blank.
        - Else require that Location.organization is the same Org OR an ancestor
                of that Org in the Organization NestedSet.
        """
        if not self.school:
            return

        # 1) find effective school organization up the school tree
        school_chain = get_ancestor_schools(self.school) or [self.school]
        school_org = None
        org_source_school = None

        for sch in school_chain:
            org = frappe.db.get_value("School", sch, "organization")
            if org:
                school_org = org
                org_source_school = sch
                break

        if not school_org:
            # This is a configuration error; we cannot safely validate membership.
            link = frappe.utils.get_link_to_form("School", self.school)
            frappe.throw(
                _(
                    "School {0} and its ancestor schools have no Organization set. "
                    "Set an Organization on the School tree before assigning it to a Location."
                ).format(link),
                title=_("Missing School Organization"),
            )

        # 2) if Location.organization is empty → auto-fill from school_org
        if not self.organization:
            self.organization = school_org
            return

        # 3) if exact match, we are good
        if self.organization == school_org:
            return

        # 4) otherwise, require Location.organization to be an ancestor of school_org
        loc_org_row = frappe.db.get_value(
            "Organization",
            self.organization,
            ["lft", "rgt"],
            as_dict=True,
        )
        school_org_row = frappe.db.get_value(
            "Organization",
            school_org,
            ["lft", "rgt"],
            as_dict=True,
        )

        # If either org is misconfigured, fail loudly
        if not loc_org_row or not school_org_row:
            frappe.throw(
                _(
                    "Cannot validate Organization membership because one of the Organizations "
                    "({0} or {1}) is missing or corrupted."
                ).format(self.organization, school_org),
                title=_("Organization Tree Error"),
            )

        is_ancestor = loc_org_row.lft <= school_org_row.lft and loc_org_row.rgt >= school_org_row.rgt

        if not is_ancestor:
            school_link = frappe.utils.get_link_to_form("School", org_source_school or self.school)
            org_link = frappe.utils.get_link_to_form("Organization", self.organization)
            school_org_link = frappe.utils.get_link_to_form("Organization", school_org)

            frappe.throw(
                _(
                    "Invalid School / Organization combination for this Location.<br>"
                    "Selected School {school} belongs to Organization {school_org}, "
                    "which is not under Organization {loc_org}."
                ).format(
                    school=school_link,
                    school_org=school_org_link,
                    loc_org=org_link,
                ),
                title=_("School Does Not Belong to Organization"),
            )

    # -------------------------------------------------------------------------
    # Structural validations added for the Location tree
    # -------------------------------------------------------------------------

    def _validate_parent_is_group(self):
        """
        Hard rule:
        Parent must be a group node.

        This must run before any other parent-dependent validation.
        """
        if not self.parent_location:
            return

        is_group = self._get_parent_value("is_group")
        if not is_group:
            frappe.throw(
                _("Parent Location must be a group."),
                title=_("Invalid Parent Location"),
            )

    def _validate_school_lineage_against_parent(self):
        """
        Hard rule:
        When both child.school and parent.school are set,
        the parent school must be the same school OR an ancestor of the child school.

        This explicitly disallows sibling/cousin parenting.
        """
        if not self.parent_location or not self.school:
            return

        parent_school = self._get_parent_value("school")
        if not parent_school:
            return

        allowed = get_ancestor_schools(self.school) or [self.school]
        if parent_school not in allowed:
            frappe.throw(
                _("Parent Location belongs to School {0}, which is not in the lineage of School {1}.").format(
                    parent_school, self.school
                ),
                title=_("School Lineage Mismatch"),
            )

        # Guard: prevent changing school on a node that already has children.
        # This avoids corrupting descendants silently.
        if not self.is_new() and self._has_value_changed_safe("school"):
            if frappe.db.exists("Location", {"parent_location": self.name}):
                frappe.throw(
                    _(
                        "Cannot change School for a Location that already has child Locations. "
                        "Move or update child Locations first."
                    ),
                    title=_("School Change Not Allowed"),
                )

    def _validate_location_type_capabilities(self):
        """
        Hard + soft rules derived from Location Type capability flags.

        Refactor rule:
        - Do not silently mutate critical structural fields without a warning.
        - Enforce schedulable-as-leaf (cannot have children).
        """
        lt = self._get_location_type_row()
        if not lt:
            return

        # Containers imply group nodes.
        # We keep the auto-fix behavior, but we must not do it silently.
        if lt.is_container and not self.is_group:
            frappe.msgprint(
                _("Location Type implies this Location must be a group. 'Is Group' has been enabled."),
                title=_("Location Converted to Group"),
                indicator="orange",
            )
            self.is_group = 1

        # Schedulable locations must not be grouping nodes.
        if lt.is_schedulable and self.is_group:
            frappe.throw(
                _("Schedulable locations must not be grouping nodes."),
                title=_("Invalid Scheduling Location"),
            )

        # Schedulable = leaf in practice: cannot have children.
        # This protects against future edits where a room becomes a container by mistake.
        if lt.is_schedulable and self.name:
            if frappe.db.exists("Location", {"parent_location": self.name}):
                frappe.throw(
                    _("Schedulable locations cannot have child Locations."),
                    title=_("Invalid Location Structure"),
                )

    # -------------------------------------------------------------------------
    # Soft warnings
    # -------------------------------------------------------------------------

    def _warn_on_stock_location_without_school(self):
        """
        Warn only (no block):
        Stock-capable locations should usually be school-scoped.

        Refactor rule:
        - Do not spam warnings on every save.
        - Warn only when location_type or school changed (or on new doc).
        """
        lt = self._get_location_type_row()
        if not lt:
            return

        if not lt.can_hold_stock:
            return

        should_warn = (
            self.is_new() or self._has_value_changed_safe("location_type") or self._has_value_changed_safe("school")
        )

        if should_warn and not self.school:
            frappe.msgprint(
                _(
                    "This Location Type can hold stock but no School is set. "
                    "Inventory tracking is usually school-scoped."
                ),
                title=_("Stock Location Without School"),
                indicator="orange",
            )


@frappe.whitelist()
def get_valid_parent_locations(organization=None, school=None):
    """
    Return valid parent Locations for a given Organization + School context.

    Rules:
    - is_group = 1
    - organization must match
    - school must be in lineage (parent_school ∈ ancestors(child_school))
    """
    filters = {"is_group": 1}

    if organization:
        filters["organization"] = organization

    locations = frappe.get_all(
        "Location",
        filters=filters,
        fields=["name", "school"],
    )

    if not school:
        return locations

    allowed_schools = set(get_ancestor_schools(school) or [school])

    return [loc for loc in locations if not loc.school or loc.school in allowed_schools]
