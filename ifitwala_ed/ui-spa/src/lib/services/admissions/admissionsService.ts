// ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts

import { createResource } from 'frappe-ui'

import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals'

import type { Request as SessionRequest, Response as SessionResponse } from '@/types/contracts/admissions/get_admissions_session'
import type { Request as SnapshotRequest, Response as SnapshotResponse } from '@/types/contracts/admissions/get_applicant_snapshot'
import type { Request as HealthRequest, Response as HealthResponse } from '@/types/contracts/admissions/get_applicant_health'
import type { Request as UpdateHealthRequest, Response as UpdateHealthResponse } from '@/types/contracts/admissions/update_applicant_health'
import type { Request as ProfileRequest, Response as ProfileResponse } from '@/types/contracts/admissions/get_applicant_profile'
import type {
  Request as UpdateProfileRequest,
  Response as UpdateProfileResponse,
} from '@/types/contracts/admissions/update_applicant_profile'
import type { Request as DocumentsRequest, Response as DocumentsResponse } from '@/types/contracts/admissions/list_applicant_documents'
import type {
  Request as DocumentTypesRequest,
  Response as DocumentTypesResponse,
} from '@/types/contracts/admissions/list_applicant_document_types'
import type { Request as UploadDocumentRequest, Response as UploadDocumentResponse } from '@/types/contracts/admissions/upload_applicant_document'
import type { Request as PoliciesRequest, Response as PoliciesResponse } from '@/types/contracts/admissions/get_applicant_policies'
import type { Request as AcknowledgePolicyRequest, Response as AcknowledgePolicyResponse } from '@/types/contracts/admissions/acknowledge_policy'
import type { Request as SubmitRequest, Response as SubmitResponse } from '@/types/contracts/admissions/submit_application'

export function createAdmissionsService() {
  const sessionResource = createResource<SessionResponse>({
    url: 'ifitwala_ed.api.admissions_portal.get_admissions_session',
    method: 'POST',
    auto: false,
  })

  const snapshotResource = createResource<SnapshotResponse>({
    url: 'ifitwala_ed.api.admissions_portal.get_applicant_snapshot',
    method: 'POST',
    auto: false,
  })

  const healthResource = createResource<HealthResponse>({
    url: 'ifitwala_ed.api.admissions_portal.get_applicant_health',
    method: 'POST',
    auto: false,
  })

  const updateHealthResource = createResource<UpdateHealthResponse>({
    url: 'ifitwala_ed.api.admissions_portal.update_applicant_health',
    method: 'POST',
    auto: false,
  })

  const profileResource = createResource<ProfileResponse>({
    url: 'ifitwala_ed.api.admissions_portal.get_applicant_profile',
    method: 'POST',
    auto: false,
  })

  const updateProfileResource = createResource<UpdateProfileResponse>({
    url: 'ifitwala_ed.api.admissions_portal.update_applicant_profile',
    method: 'POST',
    auto: false,
  })

  const documentsResource = createResource<DocumentsResponse>({
    url: 'ifitwala_ed.api.admissions_portal.list_applicant_documents',
    method: 'POST',
    auto: false,
  })

  const uploadDocumentResource = createResource<UploadDocumentResponse>({
    url: 'ifitwala_ed.api.admissions_portal.upload_applicant_document',
    method: 'POST',
    auto: false,
  })

  const documentTypesResource = createResource<DocumentTypesResponse>({
    url: 'ifitwala_ed.api.admissions_portal.list_applicant_document_types',
    method: 'POST',
    auto: false,
  })

  const policiesResource = createResource<PoliciesResponse>({
    url: 'ifitwala_ed.api.admissions_portal.get_applicant_policies',
    method: 'POST',
    auto: false,
  })

  const acknowledgePolicyResource = createResource<AcknowledgePolicyResponse>({
    url: 'ifitwala_ed.api.admissions_portal.acknowledge_policy',
    method: 'POST',
    auto: false,
  })

  const submitResource = createResource<SubmitResponse>({
    url: 'ifitwala_ed.api.admissions_portal.submit_application',
    method: 'POST',
    auto: false,
  })

  async function getSession(payload: SessionRequest = {}): Promise<SessionResponse> {
    return sessionResource.submit(payload)
  }

  async function getSnapshot(payload: SnapshotRequest = {}): Promise<SnapshotResponse> {
    return snapshotResource.submit(payload)
  }

  async function getHealth(payload: HealthRequest = {}): Promise<HealthResponse> {
    return healthResource.submit(payload)
  }

  async function updateHealth(payload: UpdateHealthRequest): Promise<UpdateHealthResponse> {
    const result = await updateHealthResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function getProfile(payload: ProfileRequest = {}): Promise<ProfileResponse> {
    return profileResource.submit(payload)
  }

  async function updateProfile(payload: UpdateProfileRequest): Promise<UpdateProfileResponse> {
    const result = await updateProfileResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function listDocuments(payload: DocumentsRequest = {}): Promise<DocumentsResponse> {
    return documentsResource.submit(payload)
  }

  async function listDocumentTypes(payload: DocumentTypesRequest = {}): Promise<DocumentTypesResponse> {
    return documentTypesResource.submit(payload)
  }

  async function uploadDocument(payload: UploadDocumentRequest): Promise<UploadDocumentResponse> {
    const result = await uploadDocumentResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function listPolicies(payload: PoliciesRequest = {}): Promise<PoliciesResponse> {
    return policiesResource.submit(payload)
  }

  async function acknowledgePolicy(payload: AcknowledgePolicyRequest): Promise<AcknowledgePolicyResponse> {
    const result = await acknowledgePolicyResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function submitApplication(payload: SubmitRequest = {}): Promise<SubmitResponse> {
    const result = await submitResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  return {
    getSession,
    getSnapshot,
    getHealth,
    updateHealth,
    getProfile,
    updateProfile,
    listDocuments,
    listDocumentTypes,
    uploadDocument,
    listPolicies,
    acknowledgePolicy,
    submitApplication,
  }
}
