"""Shared Student Overview access roles.

Keep this module dependency-free so portal capability checks and the dashboard
endpoint can share the same contract without import-order coupling.
"""

ALLOWED_STAFF_ROLES = frozenset(
    {
        "Academic Admin",
        "Counselor",
        "Curriculum Coordinator",
        "Attendance",
        "Pastoral Lead",
        "System Manager",
        "Administrator",
        "Academic Staff",
        "Instructor",
    }
)
