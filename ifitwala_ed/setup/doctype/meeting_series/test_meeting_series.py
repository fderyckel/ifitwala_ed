import frappe


def test_smoke():
    """Basic sanity check to ensure the DocType is installable."""
    assert frappe.get_meta("Meeting Series")
