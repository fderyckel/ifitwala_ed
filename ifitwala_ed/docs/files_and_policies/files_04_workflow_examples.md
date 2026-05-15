# Governed Upload Workflow Examples

Status: Current examples, non-authoritative companion
Last updated: 2026-04-27
Code refs:
- `ifitwala_ed/integrations/drive/workflow_specs.py`
- `ifitwala_ed/integrations/drive/bridge.py`
- `../ifitwala_drive/ifitwala_drive/api/uploads.py`
- `../ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md`
Test refs:
- `ifitwala_ed/integrations/drive/test_tasks.py`
- `ifitwala_ed/api/test_file_access.py`
- `ifitwala_ed/api/test_admissions_portal.py`

## Bottom Line

These examples show the current governed upload shape. They do not override the canonical contract in `files_01`, `files_03`, `files_07`, or Drive `06_api_contracts`.

Every governed upload starts with a `workflow_id` and a workflow-specific payload. Ed resolves workflow meaning and permissions. Drive owns upload session creation, binary ingress, finalize, file/version/binding records, derivatives, grants, audit, and erasure execution.

## 1. Shared Flow

1. Ed authorizes the actor in the product workflow.
2. Ed or a thin Drive wrapper calls Drive session creation with:
   - `workflow_id`
   - `workflow_payload`
   - `filename_original`
   - `mime_type_hint`
   - `expected_size_bytes`
   - `upload_source`
   - `idempotency_key`
3. Drive asks Ed to resolve the `GovernedUploadSpec`.
4. Drive persists the resolved owner, subject, slot, purpose, retention, organization, school, `workflow_id`, and `contract_version`.
5. Bytes are uploaded through the Drive-owned ingress path.
6. Drive finalizes the file, creates authoritative Drive records, and runs the Ed post-finalize mutation when the workflow defines one.
7. Read surfaces expose server-owned `open_url`, optional `preview_url`, and optional `thumbnail_url`; they do not expose storage paths.

## 2. Minimal API Shape

Target Drive API:

```python
create_upload_session(
    workflow_id="task.submission",
    workflow_payload={"task_submission": task_submission_name},
    filename_original=filename,
    mime_type_hint=mime_type,
    expected_size_bytes=size_bytes,
    upload_source="Student Portal",
    idempotency_key=idempotency_key,
)
```

The exact `workflow_payload` keys are defined by `ifitwala_ed/integrations/drive/workflow_specs.py`.

## 3. Current Workflow Examples

Task submission evidence:

```python
workflow_id = "task.submission"
workflow_payload = {
    "task_submission": task_submission_name,
}
```

Supporting material file:

```python
workflow_id = "supporting_material.file"
workflow_payload = {
    "material": supporting_material_name,
}
```

Admissions applicant document:

```python
workflow_id = "admissions.applicant_document"
workflow_payload = {
    "student_applicant": applicant_name,
    "document_type": applicant_document_type,
    "applicant_document_item": applicant_document_item_name,
}
```

Organization communication attachment:

```python
workflow_id = "org_communication.attachment"
workflow_payload = {
    "org_communication": communication_name,
    "row_name": attachment_row_name,
}
```

Student Log evidence attachment:

```python
workflow_id = "student_log.evidence_attachment"
workflow_payload = {
    "student_log": student_log_name,
    "row_name": evidence_row_name,
}
```

Student self-referral attachment:

```python
workflow_id = "student_referral.attachment"
workflow_payload = {
    "student_referral": referral_name,
    "slot": attachment_slot,
}
```

Organization media asset:

```python
workflow_id = "organization_media.asset"
workflow_payload = {
    "organization": organization_name,
    "scope": "organization",
    "media_key": media_key,
}
```

These examples intentionally omit derived governance fields such as `owner_doctype`, `purpose`, `retention_policy`, and `slot`. Those values are resolved by the workflow spec, not hand-authored by each caller.

## 4. Read DTO Example

Business read models should return stable, server-owned actions:

```json
{
  "file_id": "DRV-FILE-0001",
  "filename": "evidence.pdf",
  "open_url": "/api/method/ifitwala_ed.api.file_access.open_governed_file?...",
  "preview_url": "/api/method/ifitwala_ed.api.file_access.preview_governed_file?...",
  "thumbnail_url": null,
  "can_open": true,
  "can_preview": true
}
```

The browser must not receive or construct raw storage paths.

## 5. Retired Patterns

Do not copy older examples that:

- create a native `File` row directly for governed business workflows
- rely on the retired Ed-local file dispatcher
- use `File Classification` as runtime authority
- hand-author owner, slot, purpose, and retention data in each surface
- treat folders as permission, retention, or erasure truth
- return `/private/...` paths as SPA/API product contracts

Wrapper-specific Drive APIs may still exist for compatibility, but they are transitional facades over the `workflow_id + workflow_payload` contract.
