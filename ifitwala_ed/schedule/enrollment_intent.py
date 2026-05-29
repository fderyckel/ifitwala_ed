from __future__ import annotations

from frappe.utils import cint

INTENT_INTENDS_TO_ENROLL = "Intends to Enroll"
INTENT_DOES_NOT_INTEND = "Does Not Intend to Enroll"
INTENT_UNDECIDED = "Undecided"

ENROLLMENT_INTENT_OPTIONS = {
    INTENT_INTENDS_TO_ENROLL,
    INTENT_DOES_NOT_INTEND,
    INTENT_UNDECIDED,
}
NON_ENROLLING_INTENTS = {INTENT_DOES_NOT_INTEND, INTENT_UNDECIDED}


def normalize_enrollment_intent(value) -> str:
    return (value or "").strip()


def is_valid_enrollment_intent(value) -> bool:
    intent = normalize_enrollment_intent(value)
    return not intent or intent in ENROLLMENT_INTENT_OPTIONS


def collects_enrollment_intent(value) -> bool:
    return cint(value or 0) == 1


def is_enrollment_intent_missing(intent, *, collect_enrollment_intent=0) -> bool:
    return collects_enrollment_intent(collect_enrollment_intent) and not normalize_enrollment_intent(intent)


def is_enrollment_intent_affirmative(intent, *, collect_enrollment_intent=0) -> bool:
    normalized = normalize_enrollment_intent(intent)
    if normalized == INTENT_INTENDS_TO_ENROLL:
        return True
    return not normalized and not collects_enrollment_intent(collect_enrollment_intent)


def is_non_enrolling_intent(intent) -> bool:
    return normalize_enrollment_intent(intent) in NON_ENROLLING_INTENTS


def enrollment_intent_label(intent, *, collect_enrollment_intent=0) -> str:
    normalized = normalize_enrollment_intent(intent)
    if normalized:
        return normalized
    if collects_enrollment_intent(collect_enrollment_intent):
        return "No Response"
    return "Not Collected"
