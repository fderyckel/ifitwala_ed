# ifitwala_ed/api/admissions_review.py

from __future__ import annotations

from ifitwala_ed.admission.api.review_endpoints import (
    review_applicant_document_submission,
    set_document_requirement_override,
)

__all__ = [
    "review_applicant_document_submission",
    "set_document_requirement_override",
]
