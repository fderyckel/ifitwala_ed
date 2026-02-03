# Phase 5 Audit Report

## 1. DTO Definitions & Type Safety
The following DTOs are referenced but not fully defined in `phase050_admission_portal.md`. A coding agent would need these specific structures to implement the frontend correctly without guessing.

### 1.1 Missing `NextAction` Definition
The `ApplicantSnapshot` DTO references `next_actions: NextAction[]`.
**Ambiguity**: The structure of `NextAction` is undefined.
**Required Definition**:
```ts
export type NextAction = {
  label: string
  route_name: string      // The vue router name to navigate to
  intent: 'primary' | 'secondary' | 'neutral'
  is_blocking: boolean    // Does this prevent submission?
  icon?: string           // Optional icon identifier
}
```

### 1.2 Missing `CompletionState` Definition
`ApplicantSnapshot` uses `CompletionState` for health, documents, etc.
**Ambiguity**: Is this an enum or an object?
**Required Definition**:
```ts
export type CompletionState = 'pending' | 'in_progress' | 'complete' | 'optional'
```
*Alternatively, if it requires detailed stats:*
```ts
export type CompletionState = {
  status: 'pending' | 'complete'
  missing_count: number
}
```
*Recommendation*: Stick to the simpler enum if separate `NextAction` items handle the specific "what is missing" logic.

### 1.3 Missing `ApplicantStatus` Enum
Referenced in `AdmissionsSession` and `ApplicantSnapshot`.
**Ambiguity**: The UI needs to know the exact string values to render status badges and gate logic.
**Required Definition**:
```ts
export type ApplicantStatus = 
  | 'Draft'
  | 'In Review'
  | 'Action Required'
  | 'Accepted'
  | 'Waitlisted'
  | 'Rejected'
  | 'Withdrawn'
```

### 1.4 Missing `ApplicantDocument` DTO Details
The document references `ApplicantDocument` but doesn't specify if `file_url` is included or if there's a separate mechanism to fetch the file content/preview.
**Clarification Needed**: Does the `ApplicantDocument` DTO include a viewable URL (signed or static)?

## 2. Logic & UX Gaps

### 2.1 Read-Only Reasoning
**Requirement**: "UX must explain why editing is locked."
**Gap**: The `AdmissionsSession` DTO only includes `is_read_only: boolean`.
**Ambiguity**: The UI cannot explain *why* it is locked (e.g., "Application Submitted" vs "Deadline Passed") without a specific reason field.
**Recommendation**: Add `read_only_reason: string | null` to `AdmissionsSession` and `ApplicantSnapshot`.

### 2.2 Policy Acknowledgement Versioning
**Gap**: The endpoint `GET /api/admissions/policies/:applicant` is mentioned, but its return type is not defined.
**Ambiguity**: The UI needs to know the structure of the policy to display (title, body, version ID).
**Requirement**: Define the `ApplicantPolicy` DTO.
```ts
export type ApplicantPolicy = {
  name: string
  policy_version: string
  content_html: string
  is_acknowledged: boolean
  acknowledged_at?: string
}
```

## 3. Implementation Specifics

### 3.1 User Creation Workflow
**Gap**: The document states "Admissions staff creates a User".
**Ambiguity**: Is this a manual process in Desk, or is there a specific "Invite Applicant" server method that handles the atomic creation of User + Role + Applicant Link?
**Recommendation**: Explicitly define the `invite_applicant(email, student_applicant)` server method to ensure the `Admissions Applicant` role and permission scoping are applied correctly and consistently, avoiding manual error.

### 3.2 Frontend/Backend Wrapper
**Verification**: `spa_architecture_and_rules.md` (Section 2.5) requires strict wrapper handling.
**Note**: Ensure the `AdmissionsSession` endpoint implementation in `api/admissions` correctly wraps the response in the standard Frappe/Ifitwala envelope so the transport layer handles it uniformly.

## 4. Conclusion
The Phase 5 documentation is robust regarding permission boundaries and roles. The primary obstacles for a coding agent are the missing DTO structures (`NextAction`, `CompletionState`, `ApplicantPolicy`). Defining these will allow for a drift-free implementation.
