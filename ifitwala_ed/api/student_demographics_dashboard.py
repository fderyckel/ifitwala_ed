# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_demographics_dashboard.py

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

import frappe
from frappe.utils import getdate, nowdate

from ifitwala_ed.utilities.employee_utils import get_user_base_school
from ifitwala_ed.utilities.school_tree import get_descendant_schools

ALLOWED_ANALYTICS_ROLES = {
    "Academic Admin",
    "Pastoral Lead",
    "Counsellor",
    "Curriculum Coordinator",
    "Admissions Officer",
    "Marketing Manager",
    "System Manager",
    "Administrator",
}


def _ensure_demographics_access(user: str | None = None) -> str:
    """Gate analytics to authorized staff roles."""
    ctx = _get_demographics_access_context(user)
    return ctx["user"]


def _get_demographics_access_context(user: str | None = None) -> dict:
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw("You need to sign in to access Student Demographic Analytics.", frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_ANALYTICS_ROLES:
        return {"user": user, "mode": "full"}

    teaching_roles = {"Instructor"}
    if roles & teaching_roles:
        has_students = frappe.db.sql(
            """
			SELECT 1
			FROM `tabStudent Group Instructor` sgi
			JOIN `tabStudent Group Student` sgs ON sgi.parent = sgs.parent
			JOIN `tabStudent Group` sg ON sg.name = sgs.parent
			WHERE sgi.user_id = %(user)s
				AND COALESCE(sgs.active, 0) = 1
				AND IFNULL(sg.status, 'Active') = 'Active'
			LIMIT 1
			""",
            {"user": user},
        )
        if has_students:
            return {"user": user, "mode": "instructor"}

    frappe.throw("You do not have permission to access Student Demographic Analytics.", frappe.PermissionError)
    return {"user": user, "mode": "full"}


def _safe_percent(part: float, total: float) -> float:
    return round((part / total) * 100, 1) if total else 0


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


def _get_active_students(filters: dict, ctx: dict | None = None):
    ctx = ctx or _get_demographics_access_context()
    mode = ctx["mode"]
    user = ctx["user"]

    conditions = ["st.enabled = 1"]
    params = {}
    joins = ""

    if mode == "instructor":
        joins = """
			JOIN `tabStudent Group Student` sgs ON sgs.student = st.name
			JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sgs.parent
			JOIN `tabStudent Group` sg ON sg.name = sgs.parent
		"""
        conditions.append("sgi.user_id = %(user)s")
        conditions.append("COALESCE(sgs.active, 0) = 1")
        conditions.append("IFNULL(sg.status, 'Active') = 'Active'")
        params["user"] = user

    if filters.get("school"):
        root = filters["school"]
        descendants = get_descendant_schools(root) or [root]
        conditions.append("st.anchor_school in %(schools)s")
        params["schools"] = tuple(descendants)

    if filters.get("cohort"):
        conditions.append("st.cohort = %(cohort)s")
        params["cohort"] = filters["cohort"]

    where = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
		SELECT
			DISTINCT st.name,
			st.student_full_name,
			st.anchor_school,
			st.cohort,
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
    """Group students by primary guardian (fallback: first guardian)."""
    by_student = defaultdict(list)
    for row in guardians:
        by_student[row["student"]].append(row)

    student_family = {}
    families = defaultdict(set)

    for student, links in by_student.items():
        primary = next((link for link in links if link.get("is_primary_guardian")), None)
        if primary:
            family_id = primary["guardian"]
        elif links:
            family_id = links[0]["guardian"]
        else:
            family_id = None

        if family_id:
            student_family[student] = family_id
            families[family_id].add(student)

    # Prepare sibling classification using DOB ordering inside each family
    sibling_flags = {}
    for family_id, members in families.items():
        # sort by dob (oldest first); missing dob last
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


def _build_slice_hits(students: list[dict], sibling_flags: dict[str, set], guardian_links: list[dict]):
    """
    Return a dict mapping slice_key -> list of ids (student or guardian) for drill-down.
    This ensures get_dashboard and get_slice_entities stay aligned.
    """
    hits = defaultdict(list)

    def add(key: str, value):
        hits[key].append(value)
        hits[key.lower()].append(value)  # case-insensitive lookup

    for s in students:
        sid = s["name"]
        cohort = s.get("cohort")

        # Nationalities (primary/secondary) + optional cohort
        for nat_field in ("student_nationality", "student_second_nationality"):
            nat = (s.get(nat_field) or "").strip()
            if nat:
                add(f"student:nationality:{nat}", sid)
                if cohort:
                    add(f"student:nationality:{nat}:cohort:{cohort}", sid)

        # Gender (with cohort)
        g = (s.get("student_gender") or "Other").strip()
        add(f"student:gender:{g}", sid)
        if cohort:
            add(f"student:gender:{g}:cohort:{cohort}", sid)

        # Residency
        res = (s.get("residency_status") or "Other").strip()
        key = res
        if res == "Local Resident":
            key = "local"
        elif res == "Expat Resident":
            key = "expat"
        elif res == "Boarder":
            key = "boarder"
        else:
            key = "other"
        add(f"student:residency:{key}", sid)

        # Age bucket
        age = _calculate_age(s.get("student_date_of_birth"))
        bucket = _bucket_age(age)
        if bucket:
            add(f"student:age_bucket:{bucket}", sid)

        # Home language
        lang = (s.get("student_first_language") or s.get("student_second_language") or "").strip()
        if lang:
            add(f"student:home_language:{lang}", sid)

        # Multilingual
        langs = [s.get("student_first_language"), s.get("student_second_language")]
        cnt = len([lang for lang in langs if lang])
        label = "3+ languages" if cnt >= 3 else "2 languages" if cnt == 2 else "1 language" if cnt >= 1 else "0"
        add(f"student:multilingual:{label}", sid)

        # Siblings per cohort
        flags = sibling_flags.get(sid, set())
        if cohort:
            if not flags:
                add(f"student:siblings:none:cohort:{cohort}", sid)
            if "older" in flags:
                add(f"student:siblings:older:cohort:{cohort}", sid)
            if "younger" in flags:
                add(f"student:siblings:younger:cohort:{cohort}", sid)

    # Guardian slices
    for row in guardian_links:
        gid = row.get("guardian")
        if not gid:
            continue
        sector = (row.get("employment_sector") or "").strip()
        if sector:
            add(f"guardian:sector:{sector}", gid)
        if row.get("is_financial_guardian"):
            rel = (row.get("relation") or "Other").strip()
            if rel == "Mother":
                label = "Mother"
            elif rel == "Father":
                label = "Father"
            else:
                label = "Other"
            add(f"guardian:financial:{label}", gid)

    return hits


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
        "slices": {},
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
    try:
        base_school = get_user_base_school(user)
    except Exception:
        pass

    school_names = []
    if base_school:
        descendants = get_descendant_schools(base_school) or []
        if base_school not in descendants:
            descendants.insert(0, base_school)
        school_names = descendants
    else:
        school_names = [s.name for s in frappe.get_all("School")]

    schools = []
    if school_names:
        schools = frappe.get_all(
            "School",
            fields=["name as name", "school_name as label"],
            filters={"name": ["in", school_names]},
            order_by="name asc",
        )

    cohorts = (
        frappe.get_all(
            "Student Cohort",
            fields=["name as name", "cohort_name as label"],
            order_by="name asc",
        )
        if frappe.db.table_exists("Student Cohort")
        else []
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

    slices = {}
    total_students = len(students)
    student_names = [s["name"] for s in students]
    student_dobs = {s["name"]: s.get("student_date_of_birth") for s in students}

    # Guardians
    guardian_links = _get_guardian_links(student_names)

    # Families via primary guardians
    families, student_family, sibling_flags = _build_family_groups(guardian_links, student_dobs)
    _slice_hits = _build_slice_hits(students, sibling_flags, guardian_links)

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

    kpis = {
        "total_students": total_students,
        "cohorts_represented": len(cohorts),
        "unique_nationalities": len(nationalities),
        "unique_home_languages": len(home_languages),
        "residency_split_pct": {
            "local": _safe_percent(residency_counts["local"], total_students),
            "expat": _safe_percent(residency_counts["expat"], total_students),
            "boarder": _safe_percent(residency_counts["boarder"], total_students),
            "other": _safe_percent(residency_counts["other"], total_students),
        },
        "pct_with_siblings": _safe_percent(
            sum(1 for s in student_names if len(families.get(student_family.get(s), set())) > 1),
            total_students,
        ),
        "guardian_diversity_score": 0,  # Guardian nationality not captured on the doctype yet
    }

    def register_slice(key: str, entity: str, title: str):
        if key not in slices:
            slices[key] = {"entity": entity, "title": title}

    # Nationality distribution (top 10 + Other) using both nationalities
    nat_counter = Counter()
    for s in students:
        for nat_field in ("student_nationality", "student_second_nationality"):
            nat = (s.get(nat_field) or "").strip()
            if nat:
                nat_counter[nat] += 1

    nat_items = []
    if nat_counter:
        top_items = nat_counter.most_common(10)
        other_count = sum(count for _, count in nat_counter.items()) - sum(x[1] for x in top_items)
        for nat, count in top_items:
            slice_key = f"student:nationality:{nat}"
            register_slice(slice_key, "student", f"Students with nationality {nat}")
            nat_items.append(
                {"label": nat, "count": count, "pct": _safe_percent(count, total_students), "sliceKey": slice_key}
            )
        if other_count > 0:
            nat_items.append(
                {"label": "Other", "count": other_count, "pct": _safe_percent(other_count, total_students)}
            )

    # Nationality by cohort heatmap (primary nationality only)
    cohort_nat = defaultdict(Counter)
    for s in students:
        if s.get("cohort") and s.get("student_nationality"):
            cohort_nat[s["cohort"]][s["student_nationality"]] += 1

    nat_by_cohort = []
    for cohort, counter in cohort_nat.items():
        buckets = []
        for nat, count in counter.items():
            slice_key = f"student:nationality:{nat}:cohort:{cohort}"
            register_slice(slice_key, "student", f"{cohort} · {nat}")
            buckets.append({"label": nat, "count": count, "sliceKey": slice_key})
        nat_by_cohort.append({"cohort": cohort, "buckets": buckets})

    # Gender split by cohort
    gender_by_cohort = []
    for cohort in sorted(cohorts):
        group = [s for s in students if s.get("cohort") == cohort]
        counts = Counter((s.get("student_gender") or "Other") for s in group)
        row = {
            "cohort": cohort,
            "female": counts.get("Female", 0),
            "male": counts.get("Male", 0),
            "other": counts.get("Other", 0),
            "sliceKeys": {},
        }
        for key, label in (("female", "Female"), ("male", "Male"), ("other", "Other")):
            slice_key = f"student:gender:{label}:cohort:{cohort}"
            row["sliceKeys"][key] = slice_key
            register_slice(slice_key, "student", f"{cohort} · {label}")
        gender_by_cohort.append(row)

    # Residency status
    residency_items = []
    for key, label in [
        ("local", "Local Resident"),
        ("expat", "Expat Resident"),
        ("boarder", "Boarder"),
        ("other", "Other"),
    ]:
        count = residency_counts.get(key, 0)
        slice_key = f"student:residency:{key}"
        register_slice(slice_key, "student", f"{label} students")
        residency_items.append(
            {"label": label, "count": count, "pct": _safe_percent(count, total_students), "sliceKey": slice_key}
        )

    # Age distribution
    age_counter = Counter()
    age_slice_keys = {}
    for s in students:
        age = _calculate_age(s.get("student_date_of_birth"))
        bucket = _bucket_age(age)
        if bucket:
            age_counter[bucket] += 1

    age_buckets = []
    for bucket, count in age_counter.items():
        slice_key = f"student:age_bucket:{bucket}"
        age_slice_keys[bucket] = slice_key
        register_slice(slice_key, "student", f"Students age {bucket}")
        age_buckets.append({"bucket": bucket, "count": count, "sliceKey": slice_key})

    # Home language distribution (primary language, fallback to second if missing)
    lang_counter = Counter()
    for s in students:
        lang = (s.get("student_first_language") or s.get("student_second_language") or "").strip()
        if lang:
            lang_counter[lang] += 1

    lang_items = []
    if lang_counter:
        top_langs = lang_counter.most_common(10)
        other_count = sum(lang_counter.values()) - sum(x[1] for x in top_langs)
        for lang, count in top_langs:
            slice_key = f"student:home_language:{lang}"
            register_slice(slice_key, "student", f"Home language {lang}")
            lang_items.append(
                {"label": lang, "count": count, "pct": _safe_percent(count, total_students), "sliceKey": slice_key}
            )
        if other_count > 0:
            lang_items.append(
                {"label": "Other", "count": other_count, "pct": _safe_percent(other_count, total_students)}
            )

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

    multilingual_profile = []
    for label in ["1 language", "2 languages", "3+ languages"]:
        count = multi_counts[label]
        slice_key = f"student:multilingual:{label}"
        register_slice(slice_key, "student", f"{label} students")
        multilingual_profile.append(
            {"label": label, "count": count, "pct": _safe_percent(count, total_students), "sliceKey": slice_key}
        )

    # Family KPIs using primary guardians
    family_sizes = [len(members) for members in families.values()]
    family_count = len(family_sizes)
    family_kpis = {
        "family_count": family_count,
        "avg_children_per_family": round(sum(family_sizes) / family_count, 2) if family_count else 0,
        "pct_families_with_2_plus": _safe_percent(sum(1 for size in family_sizes if size >= 2), family_count),
    }

    # Sibling distribution per cohort (none / has older / has younger based on family dob ordering)
    sibling_distribution = []
    for cohort in sorted(cohorts):
        group = [s for s in students if s.get("cohort") == cohort]
        row = {"cohort": cohort, "none": 0, "older": 0, "younger": 0, "sliceKeys": {}}
        for s in group:
            flags = sibling_flags.get(s["name"], set())
            if "older" in flags:
                row["older"] += 1
            elif "younger" in flags:
                row["younger"] += 1
            else:
                row["none"] += 1
        for key, label in (
            ("none", "No siblings"),
            ("older", "Has older siblings"),
            ("younger", "Has younger siblings"),
        ):
            slice_key = f"student:siblings:{key}:cohort:{cohort}"
            row["sliceKeys"][key] = slice_key
            register_slice(slice_key, "student", f"{cohort} · {label}")
        sibling_distribution.append(row)

    # Family size histogram
    family_histogram = []
    for bucket_label, bucket_fn in [
        ("1", lambda x: x == 1),
        ("2", lambda x: x == 2),
        ("3", lambda x: x == 3),
        ("4+", lambda x: x >= 4),
    ]:
        count = sum(1 for size in family_sizes if bucket_fn(size))
        slice_key = f"family:size:{bucket_label}"
        register_slice(slice_key, "student", f"Families with {bucket_label} children")
        family_histogram.append({"bucket": bucket_label, "count": count, "sliceKey": slice_key})

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

    guardian_sector = []
    for label, count in guardian_sector_counts.most_common():
        slice_key = f"guardian:sector:{label}"
        register_slice(slice_key, "guardian", f"Guardians in {label}")
        guardian_sector.append(
            {
                "label": label,
                "count": count,
                "pct": _safe_percent(count, sum(guardian_sector_counts.values())),
                "sliceKey": slice_key,
            }
        )

    financial_guardian = []
    for label in ["Mother", "Father", "Other"]:
        count = financial_guardian_counts.get(label, 0)
        slice_key = f"guardian:financial:{label}"
        register_slice(slice_key, "guardian", f"Financial guardians: {label}")
        financial_guardian.append(
            {
                "label": label,
                "count": count,
                "pct": _safe_percent(count, sum(financial_guardian_counts.values())),
                "sliceKey": slice_key,
            }
        )

    return {
        "kpis": kpis,
        "nationality_distribution": nat_items,
        "nationality_by_cohort": nat_by_cohort,
        "gender_by_cohort": gender_by_cohort,
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
        "slices": slices,
    }


@frappe.whitelist()
def get_slice_entities(slice_key: str | None = None, filters=None, start: int = 0, page_length: int = 50):
    """
    Drill-down implementation that returns student or guardian rows for a given slice key.
    We *do not* depend on the precomputed hit map here; we re-interpret the slice_key structure.
    """
    ctx = _get_demographics_access_context()

    # Defensive: accept several param names if slice_key wasn't bound by name
    if not slice_key:
        fd = frappe.form_dict
        slice_key = fd.get("slice_key") or fd.get("sliceKey") or fd.get("slice") or fd.get("key") or slice_key

    if not slice_key:
        return []

    # Normalize filters (string or object from frappe-ui)
    filters = _get_filters(filters or frappe.form_dict.get("filters"))

    students = _get_active_students(filters, ctx)
    if not students:
        return []

    student_by_name = {s["name"]: s for s in students}
    guardian_links = _get_guardian_links(list(student_by_name.keys()))

    def norm(val: str | None) -> str:
        return (val or "").strip().lower()

    def student_row(name: str):
        s = student_by_name[name]
        return {
            "id": name,
            "name": s.get("student_full_name") or name,
            "cohort": s.get("cohort"),
            "nationality": s.get("student_nationality"),
        }

    results: list[dict] = []

    slice_key = (slice_key or "").strip()
    parts = slice_key.split(":")

    # --- STUDENT SLICES ---
    if len(parts) >= 2 and parts[0] == "student":
        domain = parts[1]

        if domain == "nationality":
            # student:nationality:<nat>[:cohort:<cohort>]
            target = parts[2] if len(parts) > 2 else ""
            target_n = norm(target)
            cohort = parts[4] if len(parts) > 4 and parts[3] == "cohort" else None

            for s in students:
                if cohort and s.get("cohort") != cohort:
                    continue

                nats = {
                    norm(s.get("student_nationality")),
                    norm(s.get("student_second_nationality")),
                }
                if target_n and target_n in nats:
                    results.append(student_row(s["name"]))

        elif domain == "gender":
            # student:gender:<Female|Male|Other>[:cohort:<cohort>]
            target = parts[2] if len(parts) > 2 else ""
            target_n = norm(target)
            cohort = parts[4] if len(parts) > 4 and parts[3] == "cohort" else None

            for s in students:
                if cohort and s.get("cohort") != cohort:
                    continue
                gender = norm(s.get("student_gender") or "Other")
                if gender == target_n:
                    results.append(student_row(s["name"]))

        elif domain == "residency":
            # student:residency:<local|expat|boarder|other>
            target = parts[2] if len(parts) > 2 else ""
            label_map = {
                "local": "Local Resident",
                "expat": "Expat Resident",
                "boarder": "Boarder",
                "other": "Other",
            }
            target_label = label_map.get(target)

            for s in students:
                status = (s.get("residency_status") or "").strip()
                if not target_label:
                    continue

                if target != "other" and norm(status) == norm(target_label):
                    results.append(student_row(s["name"]))
                elif target == "other" and norm(status) not in {norm(v) for v in label_map.values()}:
                    results.append(student_row(s["name"]))

        elif domain == "age_bucket":
            # student:age_bucket:<bucket>
            target = parts[2] if len(parts) > 2 else ""
            for s in students:
                age = _calculate_age(s.get("student_date_of_birth"))
                if _bucket_age(age) == target:
                    results.append(student_row(s["name"]))

        elif domain == "home_language":
            # student:home_language:<lang>
            target = parts[2] if len(parts) > 2 else ""
            target_n = norm(target)
            for s in students:
                lang = norm(s.get("student_first_language") or s.get("student_second_language"))
                if lang == target_n:
                    results.append(student_row(s["name"]))

        elif domain == "multilingual":
            # student:multilingual:<1 language|2 languages|3+ languages>
            target = parts[2] if len(parts) > 2 else ""
            for s in students:
                langs = [s.get("student_first_language"), s.get("student_second_language")]
                cnt = len([lang for lang in langs if lang])
                label = "3+ languages" if cnt >= 3 else "2 languages" if cnt == 2 else "1 language" if cnt >= 1 else "0"
                if label == target:
                    results.append(student_row(s["name"]))

        elif domain == "siblings":
            # student:siblings:<none|older|younger>:cohort:<cohort>
            target = parts[2] if len(parts) > 2 else ""
            cohort = parts[4] if len(parts) > 4 and parts[3] == "cohort" else None

            # Build sibling flags from current dataset
            _, _, sibling_flags = _build_family_groups(
                guardian_links, {s["name"]: s.get("student_date_of_birth") for s in students}
            )

            for s in students:
                if cohort and s.get("cohort") != cohort:
                    continue
                flags = sibling_flags.get(s["name"], set())
                if target == "none" and not flags:
                    results.append(student_row(s["name"]))
                elif target == "older" and "older" in flags:
                    results.append(student_row(s["name"]))
                elif target == "younger" and "younger" in flags:
                    results.append(student_row(s["name"]))

    # --- GUARDIAN SLICES ---
    elif len(parts) >= 2 and parts[0] == "guardian":
        if parts[1] == "sector":
            # guardian:sector:<sector_label>
            target = parts[2] if len(parts) > 2 else ""
            for row in guardian_links:
                if row.get("employment_sector") == target:
                    results.append(
                        {
                            "id": row["guardian"],
                            "name": row["guardian"],
                            "subtitle": row.get("employment_sector"),
                        }
                    )

        elif parts[1] == "financial":
            # guardian:financial:<Mother|Father|Other>
            target = parts[2] if len(parts) > 2 else ""
            for row in guardian_links:
                if not row.get("is_financial_guardian"):
                    continue
                relation = row.get("relation") or "Other"
                if target in ("Mother", "Father") and relation == target:
                    results.append(
                        {
                            "id": row["guardian"],
                            "name": row["guardian"],
                            "subtitle": relation,
                        }
                    )
                elif target == "Other" and relation not in ("Mother", "Father"):
                    results.append(
                        {
                            "id": row["guardian"],
                            "name": row["guardian"],
                            "subtitle": relation,
                        }
                    )

    # Pagination + debug logging
    try:
        raw_filters = frappe.form_dict.get("filters")
        frappe.logger().info(
            "SDD slice_entities | slice_key=%s | filters=%s | raw_filters=%s | total_results=%s",
            slice_key,
            filters,
            raw_filters,
            len(results),
        )
    except Exception:
        pass

    return results[start : start + page_length]
