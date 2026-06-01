from __future__ import annotations

import frappe

from ifitwala_ed.assessment.api import outcome_publish as _impl


def __getattr__(name: str):
    return getattr(_impl, name)


@frappe.whitelist()
def publish_outcomes(payload=None, **kwargs):
    return _impl.publish_outcomes(payload=payload, **kwargs)


@frappe.whitelist()
def unpublish_outcomes(payload=None, **kwargs):
    return _impl.unpublish_outcomes(payload=payload, **kwargs)


__all__ = [
    "publish_outcomes",
    "unpublish_outcomes",
]
