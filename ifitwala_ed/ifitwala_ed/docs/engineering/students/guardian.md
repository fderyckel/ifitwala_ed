# Guardian DocType

## Purpose

The Guardian DocType represents a student's legal guardian or parent in the Ifitwala Ed system. It stores contact information, work details, and links to the guardian's associated students. This is a core entity for family-school communication and portal access.

---

## Automation & Triggers

### Contact Creation (`after_insert`)

When a Guardian record is created:
- A Contact record is automatically created (or reused if matching email exists)
- The Contact is linked to the Guardian via Dynamic Link
- This enables Frappe's standard address/contact functionality

### User Creation (`create_guardian_user`)

A whitelisted method creates a portal user for the guardian:

**Behavior:**
- Called via UI button "Create and Invite as User" (in `guardian.js`)
- Creates a `User` with `user_type = "Website User"`
- Assigns the "Guardian" role
- **Sets `home_page = "/portal/guardian"`** for automatic portal routing on login
- Sends welcome email with login credentials
- Links the User back to the Guardian record

**If User Already Exists:**
- Links the existing user to the guardian
- Does not modify the existing user's home_page

**Code Location:** `guardian.py::create_guardian_user()`

---

## Permission Implications

| Role | Permissions | Notes |
|------|-------------|-------|
| System Manager | Full access | All operations allowed |
| Academic Admin | Full access | Can create, edit, delete |
| Admission Officer | Full access | Can create, edit, delete |
| Academic Assistant | Create, Read, Write | Cannot delete |
| Academic Staff | Read only | View access for information |
| Instructor | Read only | View access |
| Nurse | Read only | Medical context access |
| Counsellor | Read only | Student support context |
| Guardian (own record) | Read only | Via portal, sees own data only |

**Portal Access:**
- Guardians with linked User accounts can access `/portal/guardian`
- Portal shows: Family Timeline, Attention Needed, Preparation & Support, Recent Activity
- Routes are protected by role checks in `portal/index.py`

---

## Data Integrity Rules

1. **Email Required for User Creation**
   - `guardian_email` must be set before `create_guardian_user()` can be called
   - Throws validation error if missing

2. **Unique User Link**
   - A Guardian can only have one linked User
   - A User can be linked to only one Guardian (via email match)

3. **Contact Synchronization**
   - Contact name/phone updates flow to Guardian (via Contact hooks)
   - Guardian updates do NOT flow back to Contact (one-way sync)

4. **Student Linkage**
   - Guardians are linked to Students via `Student Guardian` child table
   - `Guardian Student` is a read-only view on Guardian form
   - Actual relationships are managed from Student side

---

## Migration Sensitivities

**Fields Never to Rename/Casually Change:**

| Field | Why Sensitive |
|-------|---------------|
| `guardian_email` | Used as User.username; changing breaks login |
| `user` | Link to User DocType; critical for portal access |
| `guardian_full_name` | Display name across system; cached in multiple places |

**Contact Linkage:**
- Dynamic Link table entries connect Guardian to Contact
- Renaming Guardian name requires updating `link_title` in Dynamic Link

---

## Downstream System Surfaces

### Portal Pages
- `/portal/guardian` → Guardian Home (family snapshot)
- `/portal/guardian/students/:id` → Individual student view

### Reports
- Medical Info and Emergency Contact (references guardian data)
- Student Logs (shows guardian-linked students)

### Background Jobs
- None currently

### API Endpoints
- `get_guardian_home_snapshot` → Returns guardian portal data
- `create_guardian_user` → Creates/link guardian user

---

## Testing

**Key Test Cases:**

1. `test_create_guardian_user_sets_home_page`
   - Verifies user creation sets `home_page = "/portal/guardian"`
   - Ensures automatic portal routing works on login

2. `test_create_guardian_user_links_existing_user`
   - Verifies existing users are properly linked
   - No duplicate users created

**Run Tests:**
```bash
bench run-tests --doctype Guardian
```

---

## Related Files

| File | Purpose |
|------|---------|
| `guardian.py` | Controller logic, user creation |
| `guardian.js` | UI button for user creation |
| `test_guardian.py` | Test suite |
| `../ui-spa/src/pages/guardian/GuardianHome.vue` | Portal home page |
| `../ui-spa/src/router/index.ts` | Portal routing rules |
| `../../www/portal/index.py` | Portal entry point, role validation |
