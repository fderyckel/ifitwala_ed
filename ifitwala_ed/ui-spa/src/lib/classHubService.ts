import { createResource } from 'frappe-ui'
import type {
  ClassHubBundle,
  ClassHubHomeEntryResolution,
  ClassHubQuickEvidencePayload,
  ClassHubSignal,
  ClassHubWheelResolution,
} from '@/types/classHub'

type ResourceResponse<T> = T | { message: T }

type BundlePayload = {
  student_group: string
  date?: string | null
  block_number?: number | null
}

type StartSessionResponse = {
  class_session: string
  status: 'active'
  session_status?: string | null
  created?: number
  started_at?: string | null
}

type EndSessionResponse = {
  class_session: string
  status: 'ended'
  session_status?: string | null
  ended_at?: string | null
}

type SaveSignalsResponse = {
  class_session: string
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

  const currentPickerContextResource = createResource<ClassHubWheelResolution>({
    url: 'ifitwala_ed.api.class_hub.resolve_current_picker_context',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  const staffHomeEntryResource = createResource<ClassHubHomeEntryResolution>({
    url: 'ifitwala_ed.api.class_hub.resolve_staff_home_entry',
    method: 'POST',
    auto: false,
    transform: unwrapMessage,
  })

  async function getBundle(payload: BundlePayload) {
    return unwrapMessage(await bundleResource.submit(payload))
  }

  async function startSession(payload: BundlePayload) {
    return unwrapMessage(await startSessionResource.submit(payload))
  }

  async function endSession(classSession: string) {
    return unwrapMessage(await endSessionResource.submit({ class_session: classSession }))
  }

  async function saveSignals(classSession: string, signals: ClassHubSignal[]) {
    return unwrapMessage(await saveSignalsResource.submit({
      class_session: classSession,
      signals_json: JSON.stringify(signals || []),
    }))
  }

  async function quickEvidence(payload: ClassHubQuickEvidencePayload) {
    return unwrapMessage(await quickEvidenceResource.submit({
      payload_json: JSON.stringify(payload || {}),
    }))
  }

  async function resolveCurrentPickerContext() {
    return unwrapMessage(await currentPickerContextResource.submit({}))
  }

  async function resolveStaffHomeEntry() {
    return unwrapMessage(await staffHomeEntryResource.submit({}))
  }

  return {
    bundleResource,
    startSessionResource,
    endSessionResource,
    saveSignalsResource,
    quickEvidenceResource,
    currentPickerContextResource,
    staffHomeEntryResource,
    getBundle,
    startSession,
    endSession,
    saveSignals,
    quickEvidence,
    resolveCurrentPickerContext,
    resolveStaffHomeEntry,
  }
}
