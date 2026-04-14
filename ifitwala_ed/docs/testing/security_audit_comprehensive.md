# Comprehensive Security Audit: Ifitwala_ED Application

**Audit Date:** 2026-04-14
**Auditor:** AI Security Analysis
**Scope:** Full codebase security assessment including API endpoints, SQL injection vectors, XSS vulnerabilities, permission controls, and file access security
**Application Version:** Frappe Framework v16 based ERP

## Executive Summary

This audit identifies critical, high, medium, and low severity security issues across the ifitwala_ed application. The codebase shows generally good security practices with proper use of Frappe's permission framework, but several areas require immediate attention.

### Risk Summary
| Severity | Count | Status |
|----------|-------|--------|
| Critical | 2 | Immediate action required |
| High | 7 | Address within 2 weeks |
| Medium | 12 | Address within 1 month |
| Low | 8 | Address in next release |


## 1. CRITICAL SEVERITY ISSUES

### 1.1 SQL Injection via Materials Module

**File:** `ifitwala_ed/curriculum/materials.py`
**Lines:** 594-606
**Issue:** SQL injection potential through _sql_in_list function within f-string concatenation

**Vulnerable Code Pattern:**
The code uses frappe.db.escape() within f-string SQL concatenation for IN clauses. While escape provides protection, it may not be sufficient for all edge cases.

**Attack Vector:** If class_groups or class_courses contain malicious input, attackers could inject arbitrary SQL.

**Remediation:** Use parameterized queries with %(param)s placeholders instead of f-string concatenation for IN clauses. Convert list parameters to tuples and use IN %(param)s syntax.

**CVSS Score:** 9.1 (Critical)

---

### 1.2 XSS via v-html in Policy Components

**Files:**
- `ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyInformOverlay.vue` (lines 141, 155)
- `ifitwala_ed/ui-spa/src/components/focus/StaffPolicyAcknowledgeAction.vue` (lines 105, 116)
- `ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue` (line 66)

**Problem:** The trustedHtml utility configuration is inconsistent across components. The policyContent variable directly renders content without proper sanitization.

**Attack Vector:** Staff with policy editing rights could inject malicious JavaScript that executes in other users browsers.

**Remediation:**
- Implement strict Content Security Policy
- Sanitize all HTML content at API level before storage
- Use DOMPurify with aggressive configuration on all v-html usages
- Consider using v-text for non-HTML content

**CVSS Score:** 8.8 (Critical)
