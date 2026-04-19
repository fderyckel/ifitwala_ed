// ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts

import { createResource } from 'frappe-ui'

import { apiPostWithProgress } from '@/lib/client'
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals'
import type { UploadProgressCallback } from '@/lib/uploadProgress'

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
import type {
  Request as UploadApplicantProfileImageRequest,
  Response as UploadApplicantProfileImageResponse,
} from '@/types/contracts/admissions/upload_applicant_profile_image'
import type {
  Request as UploadApplicantGuardianImageRequest,
  Response as UploadApplicantGuardianImageResponse,
} from '@/types/contracts/admissions/upload_applicant_guardian_image'
import type { Request as PoliciesRequest, Response as PoliciesResponse } from '@/types/contracts/admissions/get_applicant_policies'
import type { Request as AcknowledgePolicyRequest, Response as AcknowledgePolicyResponse } from '@/types/contracts/admissions/acknowledge_policy'
import type { Request as SubmitRequest, Response as SubmitResponse } from '@/types/contracts/admissions/submit_application'
import type { Request as AcceptEnrollmentOfferRequest, Response as AcceptEnrollmentOfferResponse } from '@/types/contracts/admissions/accept_enrollment_offer'
import type { Request as DeclineEnrollmentOfferRequest, Response as DeclineEnrollmentOfferResponse } from '@/types/contracts/admissions/decline_enrollment_offer'
import type { Request as MessagesRequest, Response as MessagesResponse } from '@/types/contracts/admissions/get_applicant_messages'
import type { Request as SendMessageRequest, Response as SendMessageResponse } from '@/types/contracts/admissions/send_applicant_message'
import type {
  Request as MarkMessagesReadRequest,
  Response as MarkMessagesReadResponse,
} from '@/types/contracts/admissions/mark_applicant_messages_read'
import type {
  Request as EnrollmentChoicesRequest,
  Response as EnrollmentChoicesResponse,
} from '@/types/contracts/admissions/get_applicant_enrollment_choices'
import type {
  Request as UpdateEnrollmentChoicesRequest,
  Response as UpdateEnrollmentChoicesResponse,
} from '@/types/contracts/admissions/update_applicant_enrollment_choices'

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

  const acceptEnrollmentOfferResource = createResource<AcceptEnrollmentOfferResponse>({
    url: 'ifitwala_ed.api.admissions_portal.accept_enrollment_offer',
    method: 'POST',
    auto: false,
  })

  const declineEnrollmentOfferResource = createResource<DeclineEnrollmentOfferResponse>({
    url: 'ifitwala_ed.api.admissions_portal.decline_enrollment_offer',
    method: 'POST',
    auto: false,
  })

  const enrollmentChoicesResource = createResource<EnrollmentChoicesResponse>({
    url: 'ifitwala_ed.api.admissions_portal.get_applicant_enrollment_choices',
    method: 'POST',
    auto: false,
  })

  const updateEnrollmentChoicesResource = createResource<UpdateEnrollmentChoicesResponse>({
    url: 'ifitwala_ed.api.admissions_portal.update_applicant_enrollment_choices',
    method: 'POST',
    auto: false,
  })

  const messagesResource = createResource<MessagesResponse>({
    url: 'ifitwala_ed.api.admissions_communication.get_admissions_case_thread',
    method: 'POST',
    auto: false,
  })

  const sendMessageResource = createResource<SendMessageResponse>({
    url: 'ifitwala_ed.api.admissions_communication.send_admissions_case_message',
    method: 'POST',
    auto: false,
  })

  const markMessagesReadResource = createResource<MarkMessagesReadResponse>({
    url: 'ifitwala_ed.api.admissions_communication.mark_admissions_case_thread_read',
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

  async function uploadApplicantProfileImage(
    payload: UploadApplicantProfileImageRequest,
    options: { onProgress?: UploadProgressCallback } = {}
  ): Promise<UploadApplicantProfileImageResponse> {
    const result = await apiPostWithProgress<UploadApplicantProfileImageResponse>(
      'ifitwala_ed.api.admissions_portal.upload_applicant_profile_image',
      payload,
      options
    )
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function uploadApplicantGuardianImage(
    payload: UploadApplicantGuardianImageRequest,
    options: { onProgress?: UploadProgressCallback } = {}
  ): Promise<UploadApplicantGuardianImageResponse> {
    const result = await apiPostWithProgress<UploadApplicantGuardianImageResponse>(
      'ifitwala_ed.api.admissions_portal.upload_applicant_guardian_image',
      payload,
      options
    )
    return result
  }

  async function listDocuments(payload: DocumentsRequest = {}): Promise<DocumentsResponse> {
    return documentsResource.submit(payload)
  }

  async function listDocumentTypes(payload: DocumentTypesRequest = {}): Promise<DocumentTypesResponse> {
    return documentTypesResource.submit(payload)
  }

  async function uploadDocument(
    payload: UploadDocumentRequest,
    options: { onProgress?: UploadProgressCallback } = {}
  ): Promise<UploadDocumentResponse> {
    const result = await apiPostWithProgress<UploadDocumentResponse>(
      'ifitwala_ed.api.admissions_portal.upload_applicant_document',
      payload,
      options
    )
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

  async function acceptEnrollmentOffer(
    payload: AcceptEnrollmentOfferRequest = {}
  ): Promise<AcceptEnrollmentOfferResponse> {
    const result = await acceptEnrollmentOfferResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function declineEnrollmentOffer(
    payload: DeclineEnrollmentOfferRequest = {}
  ): Promise<DeclineEnrollmentOfferResponse> {
    const result = await declineEnrollmentOfferResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function getApplicantEnrollmentChoices(
    payload: EnrollmentChoicesRequest = {}
  ): Promise<EnrollmentChoicesResponse> {
    return enrollmentChoicesResource.submit(payload)
  }

  async function updateApplicantEnrollmentChoices(
    payload: UpdateEnrollmentChoicesRequest
  ): Promise<UpdateEnrollmentChoicesResponse> {
    const result = await updateEnrollmentChoicesResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function getMessages(payload: MessagesRequest = {}): Promise<MessagesResponse> {
    return messagesResource.submit(payload)
  }

  async function sendMessage(payload: SendMessageRequest): Promise<SendMessageResponse> {
    const result = await sendMessageResource.submit(payload)
    uiSignals.emit(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE)
    return result
  }

  async function markMessagesRead(payload: MarkMessagesReadRequest = {}): Promise<MarkMessagesReadResponse> {
    return markMessagesReadResource.submit(payload)
  }

  return {
    getSession,
    getSnapshot,
    getHealth,
    updateHealth,
    getProfile,
    updateProfile,
    uploadApplicantProfileImage,
    uploadApplicantGuardianImage,
    listDocuments,
    listDocumentTypes,
    uploadDocument,
    listPolicies,
    acknowledgePolicy,
    submitApplication,
    acceptEnrollmentOffer,
    declineEnrollmentOffer,
    getApplicantEnrollmentChoices,
    updateApplicantEnrollmentChoices,
    getMessages,
    sendMessage,
    markMessagesRead,
  }
}
