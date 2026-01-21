The right sequence from here (locked)

✅ Architecture note (done)

✅ Block registry (done)

👉 Provider contracts (NOW)

Page DocType schema

Migration mapping

Editor UX

Builder evaluation / adoption decision

Code refactor





Policies

Good — stepping back to **policy development itself** is exactly right now.
You’ve **locked authority, schema, and guards**. What’s missing is *content governance and rollout*, not data modeling.

Below is a **clear, best-practice next-steps roadmap** used by mature ERPs (PowerSchool, Workday, SAP SuccessFactors), adapted to **your current state** as reflected in your attached notes  .

---

# Policy System — Next Development Steps (Post-Schema, Pre-Portal)

## Where you are (important grounding)

You already have:

✅ Canonical objects (Policy → Version → Acknowledgement)
✅ Locked authority matrix
✅ Locked schema
✅ Locked controller guards
✅ Phase-02-safe usage for Applicants

So **no more structural work** is needed right now.

What’s missing is **policy lifecycle discipline** and **institutional operability**.

---

## Step 1 — Define the *Policy Taxonomy* (Content Governance)

This is the **first real policy-development step**, not technical.

### Why this comes first

Without taxonomy:

* policies sprawl
* requirements become inconsistent
* readiness logic becomes untrustworthy later

### Deliverable (non-code)

A **fixed list of policy categories + intended audience**, for example:

| Category     | Typical Policies                      | Applies To                   |
| ------------ | ------------------------------------- | ---------------------------- |
| Safeguarding | Child Protection, Reporting Duty      | Staff, Student               |
| Privacy      | Data Privacy, Media Consent           | Applicant, Student, Guardian |
| Admissions   | Admissions Terms, Medical Disclosure  | Applicant, Guardian          |
| Academic     | Academic Integrity, Assessment Policy | Student                      |
| Conduct      | Code of Conduct                       | Student, Staff               |
| Handbooks    | Parent Handbook, Staff Handbook       | Guardian, Staff              |

**Rule**

> A policy category defines *why* it exists — not where it is used.

You already hinted at this with `policy_category`; now you must **lock the list**.

---

## Step 2 — Authoritative Policy Inventory (Org-Wide)

Before writing new policies, **inventory what exists** today.

### Concrete action

Create a **policy inventory table** (even in Markdown / spreadsheet):

| policy_key   | Title                   | Category     | Applies To | Exists? | Needs Rewrite? |
| ------------ | ----------------------- | ------------ | ---------- | ------- | -------------- |
| safeguarding | Child Protection Policy | Safeguarding | Staff      | ✅       | ⚠️             |
| data_privacy | Data Privacy Notice     | Privacy      | All        | ✅       | ❌              |
| medical      | Medical Disclosure      | Admissions   | Applicant  | ❌       | ✅              |

This prevents:

* duplicate policies
* accidental semantic overlap
* rushed drafting

**PowerSchool practice:** policy consolidation before digitization.

---

## Step 3 — Draft *Policy Version v1* Content (No UX Yet)

Now you actually **write policy text**, but with constraints.

### Best-practice constraints (important)

Each **Policy Version v1** should:

* be written as **standalone legal text**
* avoid references to UI (“click”, “portal”, “checkbox”)
* avoid system behavior claims (“the system will…”)
* be stable for **multiple years**

### Why this matters

Once acknowledged:

* text is immutable
* mistakes require new versions
* legal teams care

So slower writing = fewer versions later.

---

## Step 4 — Define “Required vs Optional” *Outside* the Policy System

This is subtle and critical.

### What not to do

❌ Do NOT add “required” flags to Policy
❌ Do NOT encode requirement logic in Policy Version
❌ Do NOT special-case admissions here

### Correct pattern (PowerSchool-style)

Requirements belong to **process configuration**, not policy definition.

Examples:

* “Applicants must acknowledge X” → Admissions rules
* “Staff must sign Y annually” → HR rules
* “Students must sign Z per year” → Academic governance

**Policy system answers only:**

> “What was acknowledged?”

Not:

> “What must be acknowledged?”

This keeps Phase 03 clean.

---

## Step 5 — Define Supersession & Sunset Rules (Governance)

You already blocked deletion.
Now define **replacement discipline**.

### Recommended institutional rules

* Only **one active Policy Version** per Institutional Policy
* New version:

  * explicitly supersedes previous
  * does NOT invalidate old acknowledgements
* Old versions:

  * remain visible historically
  * never auto-re-acknowledged

This mirrors:

* PowerSchool
* Workday attestations
* ISO compliance systems

---

## Step 6 — Internal Review & Approval Ritual (Human, Not Code)

Before policies go live, define **who signs off**.

Minimal governance:

| Role           | Responsibility      |
| -------------- | ------------------- |
| Policy Owner   | Draft content       |
| Org Admin      | Approve activation  |
| System Manager | Legal override only |

This can live as:

* internal SOP
* not enforced in code (yet)

Avoid premature workflow engines.

---

## Step 7 — Seed Initial Policies (Controlled Data Entry)

Only after Steps 1–6:

1. Create **Institutional Policy**
2. Create **Policy Version v1**
3. Activate version
4. Do **not** create acknowledgements yet

This creates a **stable baseline**.

---

## What NOT to do next (explicitly)

❌ Do not build portal flows
❌ Do not enforce readiness yet
❌ Do not auto-assign policies
❌ Do not backfill acknowledgements
❌ Do not merge handbook + policy logic

All of those depend on **Phase 03 authority**.

---

## Why this order is correct

This sequence matches how serious systems are rolled out:

1. **Define meaning**
2. **Control authorship**
3. **Stabilize text**
4. **Only then collect consent**

Most systems fail by reversing this.

You didn’t.

---

## Final answer to “what are the next steps?”

**In order, no skipping:**

1. Lock policy taxonomy
2. Inventory existing policies
3. Draft v1 policy content carefully
4. Keep “requirements” out of policy system
5. Define supersession rules
6. Establish human approval ritual
7. Seed initial policies (no acknowledgements)

O
