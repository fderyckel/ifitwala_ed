---
title: "Organization: Your School Group's Legal Foundation"
slug: organization
category: Setup
doc_order: 1
version: "1.2.2"
last_change_date: "2026-04-25"
summary: "Create and manage legal entities that serve as the foundation for your entire school operation—from admissions and academics to HR, finance, and your public website."
seo_title: "Organization: Your School Group's Legal Foundation"
seo_description: "Learn how to set up Organizations in Ifitwala Ed—the legal entity root that powers multi-school management, policy governance, and public brand identity."

## What is an Organization?

An **Organization** is the legal entity that owns your schools. Think of it as the "parent company" or "school group" under which all your academic operations live.

Whether you run:
- A **single independent school**
- A **multi-campus school system** (elementary, middle, high school)
- A **school network** across multiple cities or countries

The Organization is where everything begins. It anchors your schools, your policies, your finances, and even your public website branding.

<Callout type="info" title="Why Ifitwala Ed is different">
Unlike platforms that treat each school as an isolated silo, Ifitwala Ed's Organization layer creates a unified ecosystem. Policies cascade naturally. Staff can work across campuses. Financials roll up to the group level. And your public website reflects one coherent brand—even if you have ten schools.
</Callout>

## Why Organizations Matter

### 1. **Unified Governance**
Policies created at the Organization level automatically apply to all schools within it. Create your Code of Conduct once, and it governs every campus. Need a variation for a specific school? No problem—school-level policies override gracefully.

### 2. **Financial Integration**
When you create an Organization, Ifitwala Ed automatically sets up a complete Chart of Accounts for it. Your accounting, billing, and financial reporting all roll up to this legal entity—giving you true multi-school financial consolidation that most education platforms simply cannot do.

### 3. **Staff Mobility**
Teachers and staff belong to the Organization, not just one school. A teacher can be assigned to multiple campuses. HR policies apply consistently. And when someone moves between schools, their history comes with them—no data fragmentation.

### 4. **Brand Coherence**
Your Organization logo appears on the login page, public website, and communications. You can spotlight a "featured school" on your homepage. And all your schools share a unified visual identity while maintaining their own unique pages.

### 5. **True Multi-Tenancy**
Each Organization is a secure boundary. Staff only see schools and data within their Organization scope. This isn't just "filtering"—it's architectural isolation that keeps sibling organizations completely separate. Perfect for school management companies or multi-academy trusts.

## Creating an Organization

### Before You Start
You'll need:
- **Organization Name** — The legal name (e.g., "Sunshine Education Group")
- **Abbreviation** — A short code (e.g., "SEG") used throughout the system
- **Optional**: Logo file, country, default currency, incorporation date

<Steps title="Setting up your Organization">
  <Step title="Navigate to Setup">
    Go to **Setup > Organization** (or search "Organization" in the search bar), then click **New**.
  </Step>
  <Step title="Enter Basic Information">
    Fill in the **Organization Name** (full legal name) and **Abbreviation** (2-10 characters, unique). Check **Is Group** only if you plan to have child organizations for complex multi-entity structures.
  </Step>
  <Step title="Set Parent (if applicable)">
    Most schools leave **Parent Organization** blank. Use this only if you're building a multi-level hierarchy (e.g., a holding company with subsidiary school groups).
  </Step>
  <Step title="Add Optional Details">
    Set **Country** for regulatory context, **Default Currency** for accounting, **Date of Incorporation** for your records, and **Default Staff Calendar** for HR.
  </Step>
  <Step title="Upload Your Logo">
    Click **Upload Organization Logo** in the Actions menu. This appears on your login page and public website. Ifitwala Ed uses governed media management for secure storage and versioning.
  </Step>
  <Step title="Set Featured School (Optional)">
    Choose a **Default Website School** to feature on your public homepage. This school must belong to your organization and can be changed anytime.
  </Step>
  <Step title="Save">
    Click **Save**. Your Chart of Accounts is created automatically—no manual setup required.
  </Step>
</Steps>

<Callout type="tip" title="What happens automatically">
The moment you save, Ifitwala Ed creates a complete Chart of Accounts for your organization—receivables, payables, cash accounts, the works. No manual setup. No accounting expertise required to get started.
</Callout>

## Organization Fields Explained

| Field | What It's For | Tips |
|-------|---------------|------|
| **Organization Name** | The legal name displayed everywhere | Use your official registered name |
| **Abbreviation** | Short code used in reports and lists | Keep it short (2-5 chars) and meaningful |
| **Is Group** | Allows this org to have child organizations | Only check if you need multi-level hierarchy |
| **Parent Organization** | Links to a parent entity | Leave blank for top-level organizations |
| **Country** | Determines regulatory context | Affects accounting standards and localization |
| **Default Currency** | Primary currency for financials | Set once—changing later requires care |
| **Organization Logo** | Your brand mark | Use a square or horizontal logo, PNG or SVG |
| **Get Inquiry** | Allows website inquiries | Enable if you want prospects to contact you |
| **Default Website School** | Featured school on homepage | Choose your flagship or most popular school |
| **Archived** | Hides from active operations | Use for defunct organizations (keeps history) |

## Where You'll Use Organizations

### Admissions & Enrollment
Every Student Applicant is anchored to an **Organization + School** pair. This means:
- A student's record stays with them if they transfer between your schools
- Admission policies apply consistently across your group
- Reporting shows true funnel metrics across your entire organization

### Policy Management
Create policies at the Organization level:
- **Code of Conduct**
- **Anti-Bullying Policy**
- **Data Privacy Policy**

These automatically apply to all schools. Individual schools can add specific policies that only apply to them. It's hierarchical governance that actually works.

### HR & Payroll
Employees belong to the Organization. This enables:
- Cross-campus staffing
- Unified leave policies
- Organization-wide professional development tracking
- Consolidated payroll (even if schools pay separately)

### Finance & Accounting
Your Chart of Accounts lives at the Organization level. This gives you:
- Consolidated financial reporting across all schools
- Inter-school transaction tracking
- Group-level budgeting and cash flow visibility
- Multi-currency support for international groups

### Communications
Send announcements to:
- **All staff** across the organization
- **Specific schools**
- **Teams** within schools

Organization-level communications are visible to all staff within the organization—perfect for all-hands announcements, policy updates, and crisis communications.

### Your Public Website
Your Organization powers your public presence:
- **Logo** appears on login and public pages
- **Name** is the site title
- **Default Website School** is featured on the homepage
- **Inquiry form** can be enabled per organization

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|------|------|-------|--------|--------|-------|
| `System Manager` | Yes | Yes | Yes | Yes | Full access |
| `HR Manager` | Yes | Yes | Yes | No | No delete permission in doctype |
| `HR User` | Yes | No | No | No | Descendant-scoped read access (self + children) |
| `Accounts Manager` | Yes | Yes | Yes | Yes | Full access |
| `Academic Admin` | Yes | Yes | No | No | Actions follow DocType row; records remain limited to scoped organization descendants |
| `Employee` | Yes | No | No | No | Read-only |
| `Academic Assistant` | Yes | No | No | No | Read-only |

## Related Docs

<RelatedDocs
  slugs="school,institutional-policy,student-applicant,org-communication"
  title="Continue With Related Setup Docs"
/>

## Technical Notes (IT)

- **DocType**: `Organization` — Located in Setup module
- **Tree Structure**: Supports hierarchical organization groups
- **Auto-Creation**: Chart of Accounts generated automatically on insert
- **Media**: Organization logo uses governed file classification
- **Hooks**: Permission query conditions and has_permission handlers enforce scope
