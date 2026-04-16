# AGENTS_KIMI.md — Kimi Code CLI Learning & Memory for Ifitwala_Ed

This file captures lessons learned about Frappe Framework security and patterns specific to this codebase. This complements the main AGENTS.md, not replaces it.

---

## Learned: Frappe Security Model

### SQL Escape Behavior

`frappe.db.escape()` returns **quoted, escaped literals** — not raw strings.

```python
# escape("O'Brien") → 'O\'Brien'  (quotes INCLUDED in output)
# This makes f-string concatenation with escaped values SAFE from injection
```

**Lesson**: Code using `frappe.db.escape()` in SQL construction is protected against injection, even if stylistically questionable. Distinguish between "code smell" and "exploitable vulnerability."

**Real example from this codebase**:
```python
# ifitwala_ed/curriculum/materials.py line 594
conditions.append(
    f"({table_alias}.anchor_doctype = 'Class Teaching Plan' AND "
    f"{table_alias}.anchor_name in (SELECT name FROM `tabClass Teaching Plan` "
    f"WHERE student_group in ({group_list})))"  # group_list from escape()
)
# This is SAFE because escape() returns quoted literals
```

---

### HTML Sanitization Stack

Frappe uses **Bleach** internally for HTML sanitization:

```python
from frappe.utils import sanitize_html  # Bleach-based

# Strips: <script>, event handlers (onclick, onerror), javascript: URLs, dangerous data URIs
```

**Critical lesson**: Always trace the COMPLETE data flow before claiming XSS:
1. User input →
2. Controller hook sanitization? (`before_insert`, `before_save`, `validate`) →
3. API response →
4. UI rendering

**Example from this codebase - IS protected:**
```python
# ifitwala_ed/governance/doctype/policy_version/policy_version.py
class PolicyVersion(Document):
    def before_insert(self):
        self._sanitize_policy_text()  # Called here (line 342)

    def before_save(self):
        self._sanitize_policy_text()  # And here (line 354)

    def _sanitize_policy_text(self):
        from ifitwala_ed.utilities.html_sanitizer import sanitize_html
        self.policy_text = sanitize_html(self.policy_text or "", allow_headings_from="h2")
```

Even though `policy_text` flows to `v-html` in Vue components, it's sanitized at the controller level.

**What I got wrong**: Claimed stored XSS was possible without verifying the sanitization in controller hooks.

---

### Server-Generated Safe HTML

Content generated server-side with `html.escape()` is safe for `v-html`:

```python
from html import escape

def generate_diff_html(old, new):
    return f"<div>{escape(old)} → {escape(new)}</div>"  # Safe
```

The `html.escape()` function encodes `<`, `>`, `&`, and `"` — making injection impossible.

**Real example from this codebase**:
```python
# ifitwala_ed/governance/doctype/policy_version/policy_version.py line 56
def _render_added_paragraph(*, label: str, paragraph: str) -> str:
    return (
        '<article class="policy-diff-block policy-diff-block--added">'
        f'<div class="policy-diff-label">{escape(label)}</div>'  # Safe
        f'<div class="policy-diff-body"><ins>{escape(paragraph)}</ins></div>'  # Safe
        "</article>"
    )
```

The `diff_html` field that uses this is **NOT vulnerable** to XSS, despite being rendered with `v-html`.

---

### Framework-Aware Security Assessment

**DON'T**: See `v-html` in Vue + user input field → claim XSS

**DO**: Trace completely:
- User input →
- Controller hook sanitization? →
- API response →
- Vue rendering

What looks vulnerable in raw web frameworks may be **protected by Frappe's multi-layer defenses**:
- DocType controller hooks (`before_insert`, `before_save`, `validate`)
- Permission system
- Built-in sanitizers
- Query parameterization

**Before claiming a security vulnerability:**
1. Create an actual reproduction attempt with payloads
2. Verify the payload executes (for XSS) or query structure changes (for SQLi)
3. If protected by framework behavior, document as "defense in depth" not "critical vulnerability"

---

## Learned: Security Assessment Checklist

When auditing this codebase for security:

- [ ] For SQL injection: Check if `frappe.db.escape()` is used - if yes, not exploitable
- [ ] For XSS: Trace complete data flow including controller hooks
- [ ] Check `before_insert`, `before_save`, `validate` for sanitization
- [ ] Verify `sanitize_html` is actually called, not just imported
- [ ] Distinguish "code smell" from "exploitable vulnerability"
- [ ] Never claim CVSS 9+ without confirmed exploitability

---

## Learned: File Locations

Key files for security context:
- `ifitwala_ed/utilities/html_sanitizer.py` — Project-specific sanitization wrappers
- `ifitwala_ed/governance/doctype/policy_version/policy_version.py` — Example of proper sanitization
- `ifitwala_ed/curriculum/materials.py` — Example of safe SQL with escape()

---

## Mistakes Made & Corrected

| Mistake | Correction |
|---------|------------|
| Claimed SQL injection CVSS 9.1 in materials.py | Downgraded to "hardening" - escape() makes it safe |
| Claimed stored XSS in policy components | Downgraded - policy_text is sanitized in before_insert/save |
| Thought diff_html was vulnerable | Confirmed safe - uses html.escape() server-side |
| Didn't check controller hooks first | Now always trace complete data flow |

---

*Last updated: 2026-04-14*
*Context: Security audit feedback on policy_version and materials modules*
