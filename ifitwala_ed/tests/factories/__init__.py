# ifitwala_ed/tests/factories/__init__.py

from ifitwala_ed.tests.factories.academic import make_academic_year, make_term
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user

__all__ = [
    "make_academic_year",
    "make_term",
    "make_organization",
    "make_school",
    "make_user",
]
