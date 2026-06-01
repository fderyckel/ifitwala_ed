# ifitwala_ed/admission/api/recommendation_intake/constants.py

from __future__ import annotations

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
RECOMMENDATION_TEMPLATE_DOCTYPE = "Recommendation Template"
RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE = "Recommendation Template Field"
RECOMMENDATION_REQUEST_DOCTYPE = "Recommendation Request"
RECOMMENDATION_SUBMISSION_DOCTYPE = "Recommendation Submission"
REQUEST_STATUS_OPEN = {"Sent", "Opened"}
REQUEST_STATUS_TERMINAL = {"Submitted", "Revoked", "Expired"}
REQUEST_STATUS_ALL = REQUEST_STATUS_OPEN | REQUEST_STATUS_TERMINAL
TOKEN_DEFAULT_EXPIRY_DAYS = 14
TOKEN_MAX_EXPIRY_DAYS = 60
OTP_TTL_MINUTES = 10
OTP_MAX_FAILED_ATTEMPTS = 5
IDEMPOTENCY_TTL_SECONDS = 60 * 15
RECOMMENDATION_UPLOAD_ALLOWED_MIME_TYPES = {"application/pdf", "image/png"}
RECOMMENDATION_UPLOAD_ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
}
RECOMMENDATION_UPLOAD_GENERIC_MIME_TYPES = {
    "application/octet-stream",
    "binary/octet-stream",
    "multipart/form-data",
}
