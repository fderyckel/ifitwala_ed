from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.accounting.account_holder_contacts import create_account_holder_for_student_group
from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.utilities.employee_utils import get_schools_for_organization_scope, get_user_visible_schools
from ifitwala_ed.utilities.school_tree import get_descendant_schools

FINANCE_TOOL_ROLES = {"Accounts Manager", "Accounts User", "System Manager", "Administrator"}
MAX_STUDENT_CANDIDATES = 5000
MAX_SIBLING_EXPANSION = 10000


class StudentAccountHolderTool(Document):
    def validate(self):
        _require_finance_tool_actor()
        self._resolve_from_source_plan()
        self._validate_filter_scope()
        self._refresh_counts()

    @frappe.whitelist()
    def load_students(self) -> dict[str, Any]:
        _require_finance_tool_actor()
        self._resolve_from_source_plan()
        self._validate_filter_scope()

        candidate_school_scope = _resolve_tool_school_scope(self.organization, self.school)
        if not candidate_school_scope:
            frappe.throw(_("No permitted schools are available for this Account Holder setup."))

        finance_school_scope = _resolve_tool_school_scope(self.organization, None)
        candidates = self._get_candidate_students(candidate_school_scope)
        candidates, group_context = _prepare_family_group_rows(
            candidates,
            self.organization,
            finance_school_scope,
        )
        self.set("students", [])
        for row in _build_tool_rows(candidates, group_context):
            self.append("students", row)

        self.status = "Loaded" if self.students else "Draft"
        self.created_count = 0
        self.linked_count = 0
        self.failed_count = 0
        self.result_summary = ""
        self._refresh_counts()
        self.save(ignore_permissions=True)
        return self._summary()

    @frappe.whitelist()
    def create_account_holders(self) -> dict[str, Any]:
        _require_finance_tool_actor()
        self._resolve_from_source_plan()
        self._validate_filter_scope()

        selected_groups = self._selected_rows_by_group()
        if not selected_groups:
            frappe.throw(_("Select at least one student row before creating Account Holders."))

        created_count = 0
        linked_count = 0
        failed_count = 0

        for rows in selected_groups.values():
            blocked_rows = [row for row in rows if (row.action or "").strip() == "Blocked"]
            if blocked_rows:
                continue

            student_names = [row.student for row in rows if row.student]
            existing_account_holder = _group_existing_account_holder(rows)
            try:
                result = create_account_holder_for_student_group(
                    student_names,
                    account_holder=existing_account_holder,
                )
                account_holder = (result.get("account_holder") or {}).get("name")
                if result.get("created"):
                    created_count += 1
                linked_count += len(result.get("linked_students") or [])
                for row in rows:
                    row.action = "Processed"
                    row.created_account_holder = account_holder
                    row.issue = ""
            except Exception as exc:
                failed_count += len(rows)
                message = _error_message(exc)
                for row in rows:
                    row.issue = message

        self.status = "Processed"
        self.created_count = created_count
        self.linked_count = linked_count
        self.failed_count = failed_count
        self.blocked_count = _count_blocked_rows(self.students or [])
        self.result_summary = _(
            "Created {created_count} Account Holder(s), linked {linked_count} Student(s), "
            "blocked {blocked_count}, failed {failed_count}."
        ).format(
            created_count=created_count,
            linked_count=linked_count,
            blocked_count=self.blocked_count,
            failed_count=failed_count,
        )
        self._refresh_counts()
        self.save(ignore_permissions=True)
        return self._summary()

    def _resolve_from_source_plan(self) -> None:
        source_plan = _clean_data(self.source_program_billing_plan)
        if not source_plan:
            return

        row = frappe.db.get_value(
            "Program Billing Plan",
            source_plan,
            ["name", "organization", "program_offering", "academic_year"],
            as_dict=True,
        )
        if not row:
            frappe.throw(_("Source Program Billing Plan was not found."))

        self.organization = row.get("organization")
        self.program_offering = row.get("program_offering")
        self.academic_year = row.get("academic_year")

    def _validate_filter_scope(self) -> None:
        if not self.organization:
            frappe.throw(_("Organization is required."))

        if self.school:
            school_org = get_school_organization(self.school)
            if school_org != self.organization:
                frappe.throw(_("School must belong to the selected Organization."))

        if bool(self.program_offering) != bool(self.academic_year):
            frappe.throw(_("Program Offering and Academic Year must be selected together."))

        if self.program_offering:
            offering = frappe.db.get_value(
                "Program Offering",
                self.program_offering,
                ["school"],
                as_dict=True,
            )
            if not offering:
                frappe.throw(_("Program Offering was not found."))
            if get_school_organization(offering.get("school")) != self.organization:
                frappe.throw(_("Program Offering must belong to the selected Organization."))

    def _get_candidate_students(self, school_scope: list[str]) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "organization": self.organization,
            "school_scope": tuple(school_scope),
            "student_cohort": self.student_cohort,
            "limit": MAX_STUDENT_CANDIDATES,
        }
        cohort_clause = ""
        if self.student_cohort:
            cohort_clause = "AND st.cohort = %(student_cohort)s"

        if self.program_offering and self.academic_year:
            params.update(
                {
                    "program_offering": self.program_offering,
                    "academic_year": self.academic_year,
                }
            )
            return frappe.db.sql(
                f"""
                SELECT DISTINCT
                    st.name AS student,
                    st.student_id AS student_id,
                    st.student_full_name AS student_name,
                    st.student_preferred_name AS student_preferred_name,
                    st.anchor_school AS anchor_school,
                    st.cohort AS student_cohort,
                    st.account_holder AS account_holder
                FROM `tabProgram Enrollment` pe
                INNER JOIN `tabStudent` st ON st.name = pe.student
                INNER JOIN `tabSchool` school ON school.name = st.anchor_school
                WHERE pe.program_offering = %(program_offering)s
                    AND pe.academic_year = %(academic_year)s
                    AND IFNULL(pe.archived, 0) = 0
                    AND pe.docstatus < 2
                    AND IFNULL(st.enabled, 1) = 1
                    AND IFNULL(st.account_holder, '') = ''
                    AND school.organization = %(organization)s
                    AND st.anchor_school IN %(school_scope)s
                    {cohort_clause}
                ORDER BY st.student_full_name ASC, st.name ASC
                LIMIT %(limit)s
                """,
                params,
                as_dict=True,
            )

        return frappe.db.sql(
            f"""
            SELECT
                st.name AS student,
                st.student_id AS student_id,
                st.student_full_name AS student_name,
                st.student_preferred_name AS student_preferred_name,
                st.anchor_school AS anchor_school,
                st.cohort AS student_cohort,
                st.account_holder AS account_holder
            FROM `tabStudent` st
            INNER JOIN `tabSchool` school ON school.name = st.anchor_school
            WHERE IFNULL(st.enabled, 1) = 1
                AND IFNULL(st.account_holder, '') = ''
                AND school.organization = %(organization)s
                AND st.anchor_school IN %(school_scope)s
                {cohort_clause}
            ORDER BY st.student_full_name ASC, st.name ASC
            LIMIT %(limit)s
            """,
            params,
            as_dict=True,
        )

    def _selected_rows_by_group(self) -> dict[str, list[Any]]:
        groups: dict[str, list[Any]] = defaultdict(list)
        selected_keys: set[str] = set()
        for row in self.students or []:
            family_group_key = _clean_data(row.get("family_group_key")) or _clean_data(row.get("student"))
            if not family_group_key:
                continue
            groups[family_group_key].append(row)
            if cint(row.get("selected")):
                selected_keys.add(family_group_key)
        return {family_group_key: groups[family_group_key] for family_group_key in sorted(selected_keys)}

    def _refresh_counts(self) -> None:
        rows = list(self.students or [])
        self.loaded_count = len(rows)
        self.selected_count = sum(1 for row in rows if cint(row.get("selected")))
        self.blocked_count = _count_blocked_rows(rows)

    def _summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "loaded_count": cint(self.loaded_count),
            "selected_count": cint(self.selected_count),
            "blocked_count": cint(self.blocked_count),
            "created_count": cint(self.created_count),
            "linked_count": cint(self.linked_count),
            "failed_count": cint(self.failed_count),
            "result_summary": self.result_summary or "",
        }


@frappe.whitelist()
def load_students(name: str | None = None, doc=None) -> dict[str, Any]:
    tool = _get_tool_doc_for_action(name=name, doc=doc)
    return tool.load_students()


@frappe.whitelist()
def create_account_holders(name: str | None = None, doc=None) -> dict[str, Any]:
    tool = _get_tool_doc_for_action(name=name, doc=doc)
    return tool.create_account_holders()


def _get_tool_doc_for_action(name: str | None = None, doc=None):
    tool_name = _resolve_requested_tool_name(name=name, doc=doc)
    if not tool_name:
        frappe.throw(_("Save the Student Account Holder Tool before running this action."))

    tool = frappe.get_doc("Student Account Holder Tool", tool_name)
    tool.check_permission("write")
    return tool


def _resolve_requested_tool_name(name: str | None = None, doc=None) -> str:
    for value in (
        name,
        _form_dict_value("name"),
        _form_dict_value("docname"),
        _name_from_doc_payload(doc),
        _name_from_doc_payload(_form_dict_value("doc")),
        _name_from_doc_payload(_form_dict_value("docs")),
    ):
        cleaned = _clean_data(value)
        if cleaned:
            return cleaned
    return ""


def _form_dict_value(key: str):
    form_dict = getattr(frappe, "form_dict", None)
    if not form_dict:
        return None
    if hasattr(form_dict, "get"):
        return form_dict.get(key)
    return getattr(form_dict, key, None)


def _name_from_doc_payload(doc) -> str:
    if not doc:
        return ""
    payload = frappe.parse_json(doc) if isinstance(doc, str) else doc
    if isinstance(payload, dict):
        return _clean_data(payload.get("name"))
    return _clean_data(getattr(payload, "name", ""))


def _require_finance_tool_actor() -> None:
    user = _clean_data(getattr(frappe.session, "user", ""))
    roles = set(frappe.get_roles(user) or [])
    if user == "Administrator" or roles & FINANCE_TOOL_ROLES:
        return
    frappe.throw(_("Only finance users can use the Student Account Holder Tool."), frappe.PermissionError)


def _resolve_tool_school_scope(organization: str, school: str | None) -> list[str]:
    organization_schools = set(get_schools_for_organization_scope(organization) or [])
    if school:
        requested = set(get_descendant_schools(school) or [school])
        requested &= organization_schools
    else:
        requested = organization_schools

    if _is_system_wide_user():
        return sorted(requested)

    visible_schools = set(get_user_visible_schools(frappe.session.user) or [])
    return sorted(requested & visible_schools)


def _is_system_wide_user() -> bool:
    user = _clean_data(getattr(frappe.session, "user", ""))
    roles = set(frappe.get_roles(user) or [])
    return user == "Administrator" or "System Manager" in roles


def _prepare_family_group_rows(
    candidates: list[dict[str, Any]],
    organization: str,
    finance_school_scope: list[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    candidate_names = [_clean_data(row.get("student")) for row in candidates if _clean_data(row.get("student"))]
    if not candidate_names:
        return [], {}

    components = _collect_sibling_components(candidate_names)
    all_students = sorted({student for component in components for student in component})
    student_meta = _student_meta_by_name(all_students)
    expanded_candidates = _expand_candidates_with_scoped_missing_siblings(
        candidates,
        components,
        student_meta,
        organization,
        finance_school_scope,
    )
    group_context = _build_family_group_context(
        components,
        student_meta,
        organization,
        finance_school_scope,
    )
    return expanded_candidates, group_context


def _expand_candidates_with_scoped_missing_siblings(
    candidates: list[dict[str, Any]],
    components: list[set[str]],
    student_meta: dict[str, dict[str, Any]],
    organization: str,
    finance_school_scope: list[str],
) -> list[dict[str, Any]]:
    candidates_by_student = {
        _clean_data(row.get("student")): dict(row) for row in candidates if _clean_data(row.get("student"))
    }
    for component in components:
        for student in sorted(component):
            if student in candidates_by_student:
                continue
            meta = student_meta.get(student, {})
            if not _student_in_finance_scope(meta, organization, finance_school_scope):
                continue
            if not _student_is_enabled(meta):
                continue
            if _clean_data(meta.get("account_holder")):
                continue
            candidates_by_student[student] = {
                "student": student,
                "student_id": _clean_data(meta.get("student_id")),
                "student_name": _clean_data(meta.get("student_full_name")) or student,
                "student_preferred_name": _clean_data(meta.get("student_preferred_name")),
                "anchor_school": _clean_data(meta.get("anchor_school")),
                "student_cohort": _clean_data(meta.get("cohort")),
                "account_holder": "",
            }
    return list(candidates_by_student.values())


def _build_family_group_context(
    components: list[set[str]],
    student_meta: dict[str, dict[str, Any]],
    organization: str,
    finance_school_scope: list[str],
) -> dict[str, dict[str, Any]]:
    visible_students = {
        student
        for component in components
        for student in component
        if _student_in_finance_scope(student_meta.get(student, {}), organization, finance_school_scope)
    }
    guardians_by_component = _guardian_context_by_component(components, visible_students)

    context_by_student: dict[str, dict[str, Any]] = {}
    for component in components:
        component_students = sorted(component)
        component_key = _family_group_key(component_students)
        component_meta = [student_meta.get(student, {}) for student in component_students]
        visible_meta = [student_meta.get(student, {}) for student in component_students if student in visible_students]
        active_meta = [row for row in component_meta if _student_is_enabled(row)]
        organizations = sorted(
            {_clean_data(row.get("organization")) for row in active_meta if _clean_data(row.get("organization"))}
        )
        out_of_scope_students = [
            _clean_data(row.get("name"))
            for row in active_meta
            if not _student_in_finance_scope(row, organization, finance_school_scope)
        ]
        account_holders = sorted(
            {_clean_data(row.get("account_holder")) for row in active_meta if _clean_data(row.get("account_holder"))}
        )
        guardians = guardians_by_component.get(component_key, [])
        proposed_name = _proposed_account_holder_name(visible_meta, guardians)
        action = "Create New Account Holder"
        issue = ""
        existing_account_holder = ""

        if len(organizations) > 1:
            action = "Blocked"
            issue = _("Sibling group crosses Organizations. Resolve the family links manually.")
        elif out_of_scope_students:
            action = "Blocked"
            issue = _(
                "Sibling group includes students outside your permitted finance school scope. "
                "Ask an authorized finance user to process the full family."
            )
        elif len(account_holders) > 1:
            action = "Blocked"
            issue = _("Sibling group already has multiple Account Holders. Resolve manually before batching.")
        elif len(account_holders) == 1:
            action = "Link Existing Account Holder"
            existing_account_holder = account_holders[0]
        elif not guardians:
            action = "Blocked"
            issue = _("No linked Guardians were found. Add Guardian rows before creating an Account Holder.")

        label = _family_group_label(visible_meta)
        guardian_summary = _guardian_summary(guardians)
        for student in component_students:
            context_by_student[student] = {
                "family_group_key": component_key,
                "family_group_label": label,
                "action": action,
                "issue": issue,
                "existing_account_holder": existing_account_holder,
                "proposed_account_holder_name": proposed_name,
                "guardian_summary": guardian_summary,
            }

    return context_by_student


def _collect_sibling_components(seed_students: list[str]) -> list[set[str]]:
    known = set(seed_students)
    edges: list[tuple[str, str]] = []
    frontier = set(seed_students)

    while frontier and len(known) < MAX_SIBLING_EXPANSION:
        rows = frappe.db.sql(
            """
            SELECT parent, student
            FROM `tabStudent Sibling`
            WHERE parenttype = 'Student'
                AND parentfield = 'siblings'
                AND (parent IN %(frontier)s OR student IN %(frontier)s)
            """,
            {"frontier": tuple(frontier)},
            as_dict=True,
        )
        next_frontier: set[str] = set()
        for row in rows:
            parent = _clean_data(row.get("parent"))
            student = _clean_data(row.get("student"))
            if not parent or not student:
                continue
            edges.append((parent, student))
            for name in (parent, student):
                if name not in known:
                    known.add(name)
                    next_frontier.add(name)
        frontier = next_frontier

    parent_by_student = {student: student for student in known}

    def find(student: str) -> str:
        while parent_by_student[student] != student:
            parent_by_student[student] = parent_by_student[parent_by_student[student]]
            student = parent_by_student[student]
        return student

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent_by_student[right_root] = left_root

    for left, right in edges:
        if left in parent_by_student and right in parent_by_student:
            union(left, right)

    groups: dict[str, set[str]] = defaultdict(set)
    for student in known:
        groups[find(student)].add(student)
    return list(groups.values())


def _student_meta_by_name(student_names: list[str]) -> dict[str, dict[str, Any]]:
    if not student_names:
        return {}

    student_rows = frappe.get_all(
        "Student",
        filters={"name": ["in", student_names]},
        fields=[
            "name",
            "student_id",
            "student_full_name",
            "student_preferred_name",
            "anchor_school",
            "cohort",
            "account_holder",
            "enabled",
        ],
        limit=0,
    )
    school_names = sorted(
        {_clean_data(row.get("anchor_school")) for row in student_rows if _clean_data(row.get("anchor_school"))}
    )
    schools = {
        row.get("name"): row.get("organization")
        for row in frappe.get_all(
            "School",
            filters={"name": ["in", school_names]},
            fields=["name", "organization"],
            limit=0,
        )
    }
    return {
        _clean_data(row.get("name")): {
            **row,
            "organization": schools.get(row.get("anchor_school")),
        }
        for row in student_rows
        if _clean_data(row.get("name"))
    }


def _guardian_context_by_component(
    components: list[set[str]],
    visible_students: set[str],
) -> dict[str, list[dict[str, Any]]]:
    all_students = sorted({student for component in components for student in component if student in visible_students})
    if not all_students:
        return {}

    links = frappe.get_all(
        "Student Guardian",
        filters={"parent": ["in", all_students], "parenttype": "Student", "parentfield": "guardians"},
        fields=["parent", "guardian", "guardian_name", "relation", "can_consent", "idx"],
        limit=0,
    )
    guardian_names = sorted({_clean_data(row.get("guardian")) for row in links if _clean_data(row.get("guardian"))})
    guardian_rows = (
        frappe.get_all(
            "Guardian",
            filters={"name": ["in", guardian_names]},
            fields=[
                "name",
                "guardian_full_name",
                "guardian_first_name",
                "guardian_last_name",
                "is_financial_guardian",
                "is_primary_guardian",
            ],
            limit=0,
        )
        if guardian_names
        else []
    )
    guardians_by_name = {_clean_data(row.get("name")): row for row in guardian_rows if _clean_data(row.get("name"))}
    component_key_by_student = {}
    for component in components:
        component_key = _family_group_key(sorted(component))
        for student in component:
            component_key_by_student[student] = component_key

    by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_by_component: dict[str, set[str]] = defaultdict(set)
    for link in links:
        component_key = component_key_by_student.get(_clean_data(link.get("parent")))
        guardian = _clean_data(link.get("guardian"))
        if not component_key or not guardian or guardian in seen_by_component[component_key]:
            continue
        guardian_row = guardians_by_name.get(guardian, {})
        seen_by_component[component_key].add(guardian)
        by_component[component_key].append(
            {
                "guardian": guardian,
                "guardian_name": _guardian_display_name(guardian_row)
                or _clean_data(link.get("guardian_name"))
                or guardian,
                "relation": _clean_data(link.get("relation")),
                "can_consent": cint(link.get("can_consent")),
                "idx": cint(link.get("idx")),
                "is_financial_guardian": cint(guardian_row.get("is_financial_guardian")),
                "is_primary_guardian": cint(guardian_row.get("is_primary_guardian")),
            }
        )

    for component_key, rows in by_component.items():
        rows.sort(key=_guardian_priority)
    return dict(by_component)


def _build_tool_rows(
    candidates: list[dict[str, Any]],
    group_context: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        student = _clean_data(candidate.get("student"))
        context = group_context.get(student, {})
        rows.append(
            {
                "selected": 0 if context.get("action") == "Blocked" else 1,
                "student": student,
                "student_name": _clean_data(candidate.get("student_name")) or student,
                "anchor_school": _clean_data(candidate.get("anchor_school")),
                "student_cohort": _clean_data(candidate.get("student_cohort")),
                "family_group_key": _clean_data(context.get("family_group_key")) or student,
                "family_group_label": _clean_data(context.get("family_group_label")) or _("Single student"),
                "action": _clean_data(context.get("action")) or "Create New Account Holder",
                "existing_account_holder": _clean_data(context.get("existing_account_holder")),
                "proposed_account_holder_name": _clean_data(context.get("proposed_account_holder_name")),
                "guardian_summary": _clean_data(context.get("guardian_summary")),
                "issue": _clean_data(context.get("issue")),
            }
        )

    rows.sort(key=lambda row: (row["family_group_label"], row["student_name"], row["student"]))
    return rows


def _group_existing_account_holder(rows: list[Any]) -> str:
    account_holders = sorted(
        {
            _clean_data(row.get("existing_account_holder"))
            for row in rows
            if _clean_data(row.get("existing_account_holder"))
        }
    )
    if len(account_holders) > 1:
        frappe.throw(_("Sibling group has multiple Account Holders. Refresh and resolve manually."))
    return account_holders[0] if account_holders else ""


def _student_in_finance_scope(
    row: dict[str, Any],
    organization: str,
    finance_school_scope: list[str],
) -> bool:
    return bool(
        _clean_data(row.get("organization")) == _clean_data(organization)
        and _clean_data(row.get("anchor_school")) in set(finance_school_scope or [])
    )


def _student_is_enabled(row: dict[str, Any]) -> bool:
    return cint(row.get("enabled", 1)) != 0


def _family_group_key(students: list[str]) -> str:
    digest = hashlib.sha1("|".join(sorted(students)).encode("utf-8")).hexdigest()[:12]
    return f"FG-{digest}"


def _family_group_label(component_meta: list[dict[str, Any]]) -> str:
    names = sorted(_clean_data(row.get("student_full_name")) or _clean_data(row.get("name")) for row in component_meta)
    names = [name for name in names if name]
    if len(names) <= 1:
        return _("Single student")
    return _("{first_student} family ({count} students)").format(
        first_student=names[0],
        count=len(names),
    )


def _proposed_account_holder_name(component_meta: list[dict[str, Any]], guardians: list[dict[str, Any]]) -> str:
    selected = _selected_guardians_for_display(guardians)
    if len(selected) == 1:
        return selected[0]["guardian_name"]
    if len(selected) == 2:
        return _("{first_guardian} and {second_guardian}").format(
            first_guardian=selected[0]["guardian_name"],
            second_guardian=selected[1]["guardian_name"],
        )

    student_names = sorted(
        _clean_data(row.get("student_full_name")) or _clean_data(row.get("name")) for row in component_meta
    )
    first_student = next((name for name in student_names if name), "")
    if first_student:
        return _("{student_name} Family").format(student_name=first_student)
    return _("Family Account Holder")


def _guardian_summary(guardians: list[dict[str, Any]]) -> str:
    selected = _selected_guardians_for_display(guardians)
    if not selected:
        return ""

    parts = []
    for guardian in selected:
        labels = []
        if cint(guardian.get("is_financial_guardian")):
            labels.append(_("financial"))
        if cint(guardian.get("is_primary_guardian")):
            labels.append(_("primary"))
        relation = _clean_data(guardian.get("relation"))
        if relation:
            labels.append(relation)
        suffix = f" ({', '.join(labels)})" if labels else ""
        parts.append(f"{guardian['guardian_name']}{suffix}")
    return "; ".join(parts)


def _selected_guardians_for_display(guardians: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not guardians:
        return []
    financial = [guardian for guardian in guardians if cint(guardian.get("is_financial_guardian"))]
    return financial or [sorted(guardians, key=_guardian_priority)[0]]


def _guardian_priority(guardian: dict[str, Any]) -> tuple:
    return (
        0 if cint(guardian.get("is_financial_guardian")) else 1,
        0 if cint(guardian.get("is_primary_guardian")) else 1,
        0 if cint(guardian.get("can_consent")) else 1,
        cint(guardian.get("idx")) or 9999,
        _clean_data(guardian.get("guardian_name")),
    )


def _guardian_display_name(row: dict[str, Any]) -> str:
    full_name = _clean_data(row.get("guardian_full_name"))
    if full_name:
        return full_name
    parts = [_clean_data(row.get("guardian_first_name")), _clean_data(row.get("guardian_last_name"))]
    return " ".join(part for part in parts if part).strip()


def _count_blocked_rows(rows) -> int:
    return sum(1 for row in rows if (row.get("action") or "").strip() == "Blocked")


def _clean_data(value: Any) -> str:
    return str(value or "").strip()


def _error_message(exc: Exception) -> str:
    message = _clean_data(getattr(exc, "message", "")) or _clean_data(str(exc))
    return message or _("Unable to create or link Account Holder.")
