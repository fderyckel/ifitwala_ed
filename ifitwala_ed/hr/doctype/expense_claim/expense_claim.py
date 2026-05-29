# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.model.document import Document

from ifitwala_ed.hr.expense_claims import validate_expense_claim


class ExpenseClaim(Document):
    def validate(self):
        validate_expense_claim(self)
