# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_demographics_dashboard.py

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.students.doctype.student.student import get_instructor_student_scope_condition
from ifitwala_ed.utilities.employee_utils import get_user_base_school, get_user_visible_schools
from ifitwala_ed.utilities.school_tree import get_descendant_schools

ALLOWED_ANALYTICS_ROLES = {
    "Academic Admin",
    "Academic Assistant",
    "Pastoral Lead",
    "Counselor",
    "Curriculum Coordinator",
    "Accreditation Visitor",
    "Marketing User",
    "Marketing Manager",
    "System Manager",
    "Administrator",
} | ADMISSIONS_ROLES

SYSTEM_WIDE_ANALYTICS_ROLES = {"System Manager", "Administrator"}
MIN_DEMOGRAPHIC_CELL_COUNT = 5
SUPPRESSED_BUCKET_LABEL = "Other / Suppressed"
SUPPRESSED_SERIES_KEY = "suppressed"


def _is_system_wide_analytics_user(user: str, roles: set[str]) -> bool:
    return user == "Administrator" or bool(roles & SYSTEM_WIDE_ANALYTICS_ROLES)


def _ensure_demographics_access(user: str | None = None) -> str:
    """Gate analytics to authorized staff roles."""
    ctx = _get_demographics_access_context(user)
    return ctx["user"]


def _get_demographics_access_context(user: str | None = None) -> dict:
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Student Demographic Analytics."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if _is_system_wide_analytics_user(user, roles) or roles & ALLOWED_ANALYTICS_ROLES:
        school_scope = None if _is_system_wide_analytics_user(user, roles) else get_user_visible_schools(user)
        return {"user": user, "mode": "full", "school_scope": school_scope}

    teaching_roles = {"Instructor"}
    if roles & teaching_roles:
        has_students = frappe.db.sql(
            f"""
            SELECT 1
            FROM `tabStudent` st
            WHERE st.enabled = 1
                AND {get_instructor_student_scope_condition(user, table_alias="st")}
            LIMIT 1
            """
        )
        if has_students:
            return {"user": user, "mode": "instructor"}

    frappe.throw(_("You do not have permission to access Student Demographic Analytics."), frappe.PermissionError)
    return {"user": user, "mode": "full"}


def _safe_percent(part: float, total: float) -> float:
    return round((part / total) * 100, 1) if total else 0


def _suppressed_counter_items(
    counter: Counter,
    total: int,
    *,
    labels: list[str] | None = None,
    max_items: int | None = None,
    label_key: str = "label",
    include_pct: bool = True,
) -> list[dict]:
    if labels is None:
        rows = counter.most_common()
    else:
        rows = [(label, counter.get(label, 0)) for label in labels]

    items = []
    suppressed_count = 0
    emitted_count = 0
    for label, count in rows:
        if not count:
            continue
        if count < MIN_DEMOGRAPHIC_CELL_COUNT or (max_items is not None and emitted_count >= max_items):
            suppressed_count += count
            continue

        item = {label_key: label, "count": count}
        if include_pct:
            item["pct"] = _safe_percent(count, total)
        items.append(item)
        emitted_count += 1

    if suppressed_count >= MIN_DEMOGRAPHIC_CELL_COUNT:
        item = {label_key: SUPPRESSED_BUCKET_LABEL, "count": suppressed_count}
        if include_pct:
            item["pct"] = _safe_percent(suppressed_count, total)
        items.append(item)

    return items


def _suppressed_fixed_values(counter: Counter, keys: list[str]) -> dict[str, int]:
    values: dict[str, int] = {}
    suppressed_count = 0
    for key in keys:
        count = counter.get(key, 0)
        if 0 < count < MIN_DEMOGRAPHIC_CELL_COUNT:
            values[key] = 0
            suppressed_count += count
        else:
            values[key] = count

    if suppressed_count >= MIN_DEMOGRAPHIC_CELL_COUNT:
        values[SUPPRESSED_SERIES_KEY] = suppressed_count

    return values


def _suppressed_residency_kpi_counts(counter: Counter) -> dict[str, int]:
    counts = {key: counter.get(key, 0) for key in ("local", "expat", "boarder", "other")}
    suppressed_count = 0
    for key in ("local", "expat", "boarder"):
        count = counts[key]
        if 0 < count < MIN_DEMOGRAPHIC_CELL_COUNT:
            counts[key] = 0
            suppressed_count += count

    other_count = counts["other"]
    if 0 < other_count < MIN_DEMOGRAPHIC_CELL_COUNT:
        counts["other"] = 0
        suppressed_count += other_count

    if suppressed_count >= MIN_DEMOGRAPHIC_CELL_COUNT:
        counts["other"] += suppressed_count

    return counts


def _normalize_filter_value(val):
    if isinstance(val, dict):
        # Try value/name/label in that order
        return val.get("value") or val.get("name") or val.get("label")
    return val


def _get_filters(filters) -> dict:
    if isinstance(filters, str):
        try:
            filters = frappe.parse_json(filters) or {}
        except Exception:
            filters = {}
    else:
        filters = filters or {}

    for key in ("school", "cohort"):
        if key in filters:
            filters[key] = _normalize_filter_value(filters[key])

    # Hard default to employee base school if nothing specified
    if not filters.get("school"):
        try:
            user = frappe.session.user
            base_school = get_user_base_school(user)
            if base_school:
                filters["school"] = base_school
        except Exception:
            pass

    return filters


def _context_school_scope(ctx: dict) -> list[str] | None:
    if "school_scope" in ctx:
        return ctx.get("school_scope")

    user = ctx.get("user")
    roles = set(frappe.get_roles(user)) if user else set()
    if _is_system_wide_analytics_user(user, roles):
        return None
    return get_user_visible_schools(user) if user else []


def _requested_school_scope(school: str | None) -> list[str]:
    if not school:
        return []
    return get_descendant_schools(school) or [school]


def _get_active_students(filters: dict, ctx: dict | None = None):
    ctx = ctx or _get_demographics_access_context()
    mode = ctx["mode"]
    user = ctx["user"]

    conditions = ["st.enabled = 1"]
    params = {}
    joins = ""

    if mode == "instructor":
        conditions.append(get_instructor_student_scope_condition(user, table_alias="st"))

    school_scope = _context_school_scope(ctx) if mode == "full" else None
    requested_schools = _requested_school_scope(filters.get("school"))

    if mode == "full" and school_scope is not None:
        if requested_schools:
            allowed_schools = [school for school in requested_schools if school in set(school_scope)]
        else:
            allowed_schools = list(school_scope or [])

        if not allowed_schools:
            return []

        conditions.append("st.anchor_school in %(schools)s")
        params["schools"] = tuple(allowed_schools)

    elif requested_schools:
        conditions.append("st.anchor_school in %(schools)s")
        params["schools"] = tuple(requested_schools)

    if filters.get("cohort"):
        conditions.append("st.cohort = %(cohort)s")
        params["cohort"] = filters["cohort"]

    where = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
		SELECT
			DISTINCT st.name,
			st.cohort,
			st.student_house,
			st.student_gender,
			st.student_nationality,
			st.student_second_nationality,
			st.student_first_language,
			st.student_second_language,
			st.residency_status,
			st.student_date_of_birth
		FROM `tabStudent` st
		{joins}
		WHERE {where}
		""",
        params,
        as_dict=True,
    )


def _get_guardian_links(student_names: list[str]):
    if not student_names:
        return []

    return frappe.db.sql(
        """
		SELECT
			sg.parent AS student,
			sg.guardian,
			sg.relation,
			g.is_primary_guardian,
			g.is_financial_guardian,
			g.employment_sector
		FROM `tabStudent Guardian` sg
		LEFT JOIN `tabGuardian` g ON sg.guardian = g.name
		WHERE sg.parent in %(students)s
		""",
        {"students": tuple(student_names)},
        as_dict=True,
    )


def _calculate_age(dob: date | str | None) -> int | None:
    if not dob:
        return None
    try:
        d = getdate(dob)
    except Exception:
        return None
    today = getdate(nowdate())
    years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    return max(years, 0)


def _bucket_age(age: int | None) -> str | None:
    if age is None:
        return None
    buckets = [
        (0, 5, "0-5"),
        (6, 8, "6-8"),
        (9, 11, "9-11"),
        (12, 14, "12-14"),
        (15, 17, "15-17"),
        (18, 99, "18+"),
    ]
    for low, high, label in buckets:
        if low <= age <= high:
            return label
    return "Other"


def _build_family_groups(guardians: list[dict], student_dobs: dict[str, date | None]):
    """
    Group students into families based on shared guardians.

    Students belong to the same family if they share at least one guardian.
    This correctly handles:
    - Traditional families (both parents as guardians for all children)
    - Divorced with shared custody (both parents as guardians)
    - Divorced with separate custody (different guardians = different families)

    Uses Union-Find for efficient connected component grouping.
    """
    from collections import defaultdict

    # Build student -> set of guardians mapping
    student_guardians = defaultdict(set)
    for row in guardians:
        student_guardians[row["student"]].add(row["guardian"])

    # Union-Find data structure
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])  # Path compression
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Build guardian -> students mapping for efficient lookup
    guardian_students = defaultdict(set)
    for student, guards in student_guardians.items():
        for guardian in guards:
            guardian_students[guardian].add(student)

    # Union all students who share any guardian
    for guardian, students in guardian_students.items():
        students_list = list(students)
        for i in range(1, len(students_list)):
            union(students_list[0], students_list[i])

    # Build families from union-find structure
    families = defaultdict(set)
    student_family = {}

    for student in student_guardians:
        family_id = find(student)
        families[family_id].add(student)
        student_family[student] = family_id

    # Prepare sibling classification using DOB ordering inside each family
    sibling_flags = {}
    for family_id, members in families.items():
        if len(members) <= 1:
            continue  # No siblings in single-child families
        # Sort by dob (oldest first); missing dob last
        sorted_members = sorted(
            list(members),
            key=lambda s: student_dobs.get(s) or date(2999, 1, 1),
        )
        for idx, student in enumerate(sorted_members):
            has_older = idx > 0
            has_younger = idx < len(sorted_members) - 1
            if has_older:
                sibling_flags.setdefault(student, set()).add("older")
            if has_younger:
                sibling_flags.setdefault(student, set()).add("younger")

    return families, student_family, sibling_flags


def _empty_dashboard():
    return {
        "kpis": {
            "total_students": 0,
            "cohorts_represented": 0,
            "unique_nationalities": 0,
            "unique_home_languages": 0,
            "residency_split_pct": {"local": 0, "expat": 0, "boarder": 0, "other": 0},
            "pct_with_siblings": 0,
            "guardian_diversity_score": 0,
        },
        "nationality_distribution": [],
        "nationality_by_cohort": [],
        "gender_by_cohort": [],
        "student_house_by_cohort": [],
        "residency_status": [],
        "age_distribution": [],
        "home_language": [],
        "multilingual_profile": [],
        "family_kpis": {
            "family_count": 0,
            "avg_children_per_family": 0,
            "pct_families_with_2_plus": 0,
        },
        "sibling_distribution": [],
        "family_size_histogram": [],
        "guardian_nationality": [],
        "guardian_comm_language": [],
        "guardian_residence_country": [],
        "guardian_residence_city": [],
        "guardian_sector": [],
        "financial_guardian": [],
    }


@frappe.whitelist()
def get_filter_meta():
    """
    Return filter metadata used by the demographics dashboard.
    Scoped to the employee's base school + its descendant schools.
    """
    ctx = _get_demographics_access_context()
    user = ctx["user"]

    base_school = None
    school_names = []

    if ctx.get("mode") == "instructor":
        instructor_condition = get_instructor_student_scope_condition(user, table_alias="st")
        school_rows = frappe.db.sql(
            f"""
            SELECT DISTINCT st.anchor_school AS name
            FROM `tabStudent` st
            WHERE st.enabled = 1
                AND st.anchor_school IS NOT NULL
                AND st.anchor_school != ''
                AND {instructor_condition}
            ORDER BY st.anchor_school ASC
            """,
            as_dict=True,
        )
        school_names = [row.get("name") for row in school_rows if row.get("name")]
        base_school = school_names[0] if school_names else None
    else:
        school_scope = _context_school_scope(ctx)
        if school_scope is None:
            school_names = [s.name for s in frappe.get_all("School")]
        else:
            school_names = list(school_scope or [])
        try:
            candidate_school = get_user_base_school(user)
            if candidate_school in school_names:
                base_school = candidate_school
            elif school_names:
                base_school = school_names[0]
        except Exception:
            base_school = school_names[0] if school_names else None

    schools = []
    if school_names:
        schools = frappe.get_all(
            "School",
            fields=["name as name", "school_name as label"],
            filters={"name": ["in", school_names]},
            order_by="name asc",
        )

    cohort_names = []
    if frappe.db.table_exists("Student Cohort"):
        if ctx.get("mode") == "instructor":
            instructor_condition = get_instructor_student_scope_condition(user, table_alias="st")
            cohort_rows = frappe.db.sql(
                f"""
                SELECT DISTINCT st.cohort AS name
                FROM `tabStudent` st
                WHERE st.enabled = 1
                    AND st.cohort IS NOT NULL
                    AND st.cohort != ''
                    AND {instructor_condition}
                ORDER BY st.cohort ASC
                """,
                as_dict=True,
            )
            cohort_names = [row.get("name") for row in cohort_rows if row.get("name")]
        elif school_names:
            cohort_rows = frappe.get_all(
                "Student",
                fields=["cohort"],
                filters={"enabled": 1, "anchor_school": ["in", school_names], "cohort": ["is", "set"]},
                distinct=True,
                limit=0,
            )
            cohort_names = [row.get("cohort") for row in cohort_rows if row.get("cohort")]

    cohorts = []
    if cohort_names:
        cohorts = frappe.get_all(
            "Student Cohort",
            fields=["name as name", "cohort_name as label"],
            filters={"name": ["in", list(dict.fromkeys(cohort_names))]},
            order_by="name asc",
        )

    return {
        "default_school": base_school,
        "schools": schools,
        "cohorts": cohorts,
    }


@frappe.whitelist()
def get_dashboard(filters=None):
    """
    Aggregate demographics analytics for active students.
    """
    ctx = _get_demographics_access_context()
    filters = _get_filters(filters)

    students = _get_active_students(filters, ctx)
    if not students:
        return _empty_dashboard()

    total_students = len(students)
    student_names = [s["name"] for s in students]
    student_dobs = {s["name"]: s.get("student_date_of_birth") for s in students}

    # Guardians
    guardian_links = _get_guardian_links(student_names)

    # Families via primary guardians
    families, student_family, sibling_flags = _build_family_groups(guardian_links, student_dobs)

    # KPI counts
    cohorts = {s["cohort"] for s in students if s.get("cohort")}
    nationalities = set()
    home_languages = set()

    for s in students:
        if s.get("student_nationality"):
            nationalities.add(s["student_nationality"])
        if s.get("student_second_nationality"):
            nationalities.add(s["student_second_nationality"])
        primary_lang = s.get("student_first_language")
        if primary_lang:
            home_languages.add(primary_lang)
        elif s.get("student_second_language"):
            home_languages.add(s["student_second_language"])

    residency_counts = Counter()
    for s in students:
        status = (s.get("residency_status") or "").strip()
        if status == "Local Resident":
            residency_counts["local"] += 1
        elif status == "Expat Resident":
            residency_counts["expat"] += 1
        elif status == "Boarder":
            residency_counts["boarder"] += 1
        else:
            residency_counts["other"] += 1

    residency_kpi_counts = _suppressed_residency_kpi_counts(residency_counts)
    students_with_siblings = sum(1 for s in student_names if len(families.get(student_family.get(s), set())) > 1)
    safe_students_with_siblings = (
        0 if 0 < students_with_siblings < MIN_DEMOGRAPHIC_CELL_COUNT else students_with_siblings
    )
    kpis = {
        "total_students": total_students,
        "cohorts_represented": len(cohorts),
        "unique_nationalities": len(nationalities),
        "unique_home_languages": len(home_languages),
        "residency_split_pct": {
            "local": _safe_percent(residency_kpi_counts["local"], total_students),
            "expat": _safe_percent(residency_kpi_counts["expat"], total_students),
            "boarder": _safe_percent(residency_kpi_counts["boarder"], total_students),
            "other": _safe_percent(residency_kpi_counts["other"], total_students),
        },
        "pct_with_siblings": _safe_percent(safe_students_with_siblings, total_students),
        "guardian_diversity_score": 0,  # Guardian nationality not captured on the doctype yet
    }

    # Nationality distribution (top 10 + Other) using both nationalities
    nat_counter = Counter()
    for s in students:
        for nat_field in ("student_nationality", "student_second_nationality"):
            nat = (s.get(nat_field) or "").strip()
            if nat:
                nat_counter[nat] += 1

    nat_items = _suppressed_counter_items(nat_counter, total_students, max_items=10)

    # Nationality by cohort heatmap (primary nationality only)
    cohort_nat = defaultdict(Counter)
    for s in students:
        if s.get("cohort") and s.get("student_nationality"):
            cohort_nat[s["cohort"]][s["student_nationality"]] += 1

    nat_by_cohort = []
    for cohort, counter in cohort_nat.items():
        buckets = _suppressed_counter_items(counter, sum(counter.values()), include_pct=False)
        if buckets:
            nat_by_cohort.append({"cohort": cohort, "buckets": buckets})

    # Gender split by cohort
    gender_by_cohort = []
    for cohort in sorted(cohorts):
        group = [s for s in students if s.get("cohort") == cohort]
        counts = Counter((s.get("student_gender") or "Other") for s in group)
        safe_counts = _suppressed_fixed_values(counts, ["Female", "Male", "Other"])
        row = {
            "cohort": cohort,
            "female": safe_counts["Female"],
            "male": safe_counts["Male"],
            "other": safe_counts["Other"],
        }
        if safe_counts.get(SUPPRESSED_SERIES_KEY):
            row[SUPPRESSED_SERIES_KEY] = safe_counts[SUPPRESSED_SERIES_KEY]
        if any(row.get(key, 0) for key in ("female", "male", "other", SUPPRESSED_SERIES_KEY)):
            gender_by_cohort.append(row)

    # Student house by cohort
    house_by_cohort = []
    for cohort in sorted(cohorts):
        counter = Counter()
        for student in students:
            if student.get("cohort") != cohort:
                continue
            house = (student.get("student_house") or "").strip()
            if house:
                counter[house] += 1

        buckets = _suppressed_counter_items(counter, sum(counter.values()), include_pct=False)
        if buckets:
            house_by_cohort.append({"cohort": cohort, "buckets": buckets})

    # Residency status
    residency_items = _suppressed_counter_items(
        Counter(
            {
                "Local Resident": residency_counts.get("local", 0),
                "Expat Resident": residency_counts.get("expat", 0),
                "Boarder": residency_counts.get("boarder", 0),
                "Other": residency_counts.get("other", 0),
            }
        ),
        total_students,
        labels=["Local Resident", "Expat Resident", "Boarder", "Other"],
    )

    # Age distribution
    age_counter = Counter()
    for s in students:
        age = _calculate_age(s.get("student_date_of_birth"))
        bucket = _bucket_age(age)
        if bucket:
            age_counter[bucket] += 1

    age_buckets = _suppressed_counter_items(age_counter, total_students, label_key="bucket", include_pct=False)

    # Home language distribution (primary language, fallback to second if missing)
    lang_counter = Counter()
    for s in students:
        lang = (s.get("student_first_language") or s.get("student_second_language") or "").strip()
        if lang:
            lang_counter[lang] += 1

    lang_items = _suppressed_counter_items(lang_counter, total_students, max_items=10)

    # Multilingual profile (1 / 2 / 3+ languages captured)
    multi_counts = {"1 language": 0, "2 languages": 0, "3+ languages": 0}
    for s in students:
        langs = [s.get("student_first_language"), s.get("student_second_language")]
        lang_count = len([lang for lang in langs if lang])
        if lang_count >= 3:
            multi_counts["3+ languages"] += 1
        elif lang_count == 2:
            multi_counts["2 languages"] += 1
        elif lang_count >= 1:
            multi_counts["1 language"] += 1

    multilingual_profile = _suppressed_counter_items(
        Counter(multi_counts),
        total_students,
        labels=["1 language", "2 languages", "3+ languages"],
    )

    # Family KPIs using primary guardians
    family_sizes = [len(members) for members in families.values()]
    family_count = len(family_sizes)
    families_with_2_plus = sum(1 for size in family_sizes if size >= 2)
    safe_family_count = 0 if 0 < family_count < MIN_DEMOGRAPHIC_CELL_COUNT else family_count
    safe_families_with_2_plus = 0 if 0 < families_with_2_plus < MIN_DEMOGRAPHIC_CELL_COUNT else families_with_2_plus
    family_kpis = {
        "family_count": safe_family_count,
        "avg_children_per_family": round(sum(family_sizes) / family_count, 2) if safe_family_count else 0,
        "pct_families_with_2_plus": _safe_percent(safe_families_with_2_plus, family_count),
    }

    # Sibling distribution per cohort (none / has older / has younger based on family dob ordering)
    sibling_distribution = []
    for cohort in sorted(cohorts):
        group = [s for s in students if s.get("cohort") == cohort]
        sibling_counts = Counter()
        for s in group:
            flags = sibling_flags.get(s["name"], set())
            if "older" in flags:
                sibling_counts["older"] += 1
            elif "younger" in flags:
                sibling_counts["younger"] += 1
            else:
                sibling_counts["none"] += 1
        safe_counts = _suppressed_fixed_values(sibling_counts, ["none", "older", "younger"])
        row = {
            "cohort": cohort,
            "none": safe_counts["none"],
            "older": safe_counts["older"],
            "younger": safe_counts["younger"],
        }
        if safe_counts.get(SUPPRESSED_SERIES_KEY):
            row[SUPPRESSED_SERIES_KEY] = safe_counts[SUPPRESSED_SERIES_KEY]
        if any(row.get(key, 0) for key in ("none", "older", "younger", SUPPRESSED_SERIES_KEY)):
            sibling_distribution.append(row)

    # Family size histogram
    family_histogram_counter = Counter()
    for bucket_label, bucket_fn in [
        ("1", lambda x: x == 1),
        ("2", lambda x: x == 2),
        ("3", lambda x: x == 3),
        ("4+", lambda x: x >= 4),
    ]:
        family_histogram_counter[bucket_label] = sum(1 for size in family_sizes if bucket_fn(size))
    family_histogram = _suppressed_counter_items(
        family_histogram_counter,
        family_count,
        labels=["1", "2", "3", "4+"],
        label_key="bucket",
        include_pct=False,
    )

    # Guardian analytics (limited to available doctype fields)
    guardian_sector_counts = Counter()
    financial_guardian_counts = Counter()

    # Avoid double-counting same guardian across multiple students when relevant
    for row in guardian_links:
        if row.get("employment_sector"):
            guardian_sector_counts[row["employment_sector"]] += 1
        if row.get("is_financial_guardian"):
            rel = (row.get("relation") or "Other").strip()
            if rel == "Mother":
                key = "Mother"
            elif rel == "Father":
                key = "Father"
            else:
                key = "Other"
            financial_guardian_counts[key] += 1

    guardian_sector = _suppressed_counter_items(
        guardian_sector_counts,
        sum(guardian_sector_counts.values()),
    )

    financial_guardian = _suppressed_counter_items(
        financial_guardian_counts,
        sum(financial_guardian_counts.values()),
        labels=["Mother", "Father", "Other"],
    )

    return {
        "kpis": kpis,
        "nationality_distribution": nat_items,
        "nationality_by_cohort": nat_by_cohort,
        "gender_by_cohort": gender_by_cohort,
        "student_house_by_cohort": house_by_cohort,
        "residency_status": residency_items,
        "age_distribution": age_buckets,
        "home_language": lang_items,
        "multilingual_profile": multilingual_profile,
        "family_kpis": family_kpis,
        "sibling_distribution": sibling_distribution,
        "family_size_histogram": family_histogram,
        "guardian_nationality": [],  # field not present on Guardian doctype
        "guardian_comm_language": [],  # field not present on Guardian doctype
        "guardian_residence_country": [],  # field not present on Guardian doctype
        "guardian_residence_city": [],  # field not present on Guardian doctype
        "guardian_sector": guardian_sector,
        "financial_guardian": financial_guardian,
    }


@frappe.whitelist()
def get_slice_entities(slice_key: str | None = None, filters=None, start: int = 0, page_length: int = 50):
    frappe.throw(
        _("Student Demographic Analytics is aggregate-only. Use the scoped Student list for named student review."),
        frappe.PermissionError,
    )
    return []
