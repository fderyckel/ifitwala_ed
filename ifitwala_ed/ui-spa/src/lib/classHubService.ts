import { createResource } from 'frappe-ui'
import type { ClassHubBundle, ClassHubQuickEvidencePayload, ClassHubSignal } from '@/types/classHub'

type ResourceResponse<T> = T | { message: T }

type BundlePayload = {
  student_group: string
  date?: string | null
  block_number?: number | null
}

type StartSessionResponse = {
  lesson_instance: string
  status: 'active'
  started_at?: string | null
}

type EndSessionResponse = {
  lesson_instance: string
  status: 'ended'
  ended_at?: string | null
}

type SaveSignalsResponse = {
  lesson_instance: string
  saved: number
}

type QuickEvidenceResponse = {
  created: number
  submission_origin: string
}

function unwrapMessage<T>(res: ResourceResponse<T>) {
  if (res && typeof res === 'object' && 'message' in res) {
    return (res as { message: T }).message
  }
  return res as T
}

export function createClassHubService() {
  const bundleResource = createResource<ClassHubBundle>({
    url: 'ifitwala_ed.api.class_hub.get_bundle',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const startSessionResource = createResource<StartSessionResponse>({
    url: 'ifitwala_ed.api.class_hub.start_session',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const endSessionResource = createResource<EndSessionResponse>({
    url: 'ifitwala_ed.api.class_hub.end_session',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const saveSignalsResource = createResource<SaveSignalsResponse>({
    url: 'ifitwala_ed.api.class_hub.save_signals',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const quickEvidenceResource = createResource<QuickEvidenceResponse>({
    url: 'ifitwala_ed.api.class_hub.quick_evidence',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  async function getBundle(payload: BundlePayload) {
    return bundleResource.submit(payload)
  }

  async function startSession(payload: BundlePayload) {
    return startSessionResource.submit(payload)
  }

  async function endSession(lessonInstance: string) {
    return endSessionResource.submit({ lesson_instance: lessonInstance })
  }

  async function saveSignals(lessonInstance: string, signals: ClassHubSignal[]) {
    return saveSignalsResource.submit({
      lesson_instance: lessonInstance,
      signals_json: JSON.stringify(signals || []),
    })
  }

  async function quickEvidence(payload: ClassHubQuickEvidencePayload) {
    return quickEvidenceResource.submit({
      payload_json: JSON.stringify(payload || {}),
    })
  }

  return {
    bundleResource,
    startSessionResource,
    endSessionResource,
    saveSignalsResource,
    quickEvidenceResource,
    getBundle,
    startSession,
    endSession,
    saveSignals,
    quickEvidence,
  }
}
