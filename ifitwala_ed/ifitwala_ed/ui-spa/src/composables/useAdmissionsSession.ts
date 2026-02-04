// ifitwala_ed/ui-spa/src/composables/useAdmissionsSession.ts

import { inject, provide, ref, type Ref } from 'vue'
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService'
import type { Response as AdmissionsSession } from '@/types/contracts/admissions/get_admissions_session'

const AdmissionsSessionSymbol = Symbol('AdmissionsSession')

export type AdmissionsSessionContext = {
  session: Ref<AdmissionsSession | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  refresh: () => Promise<void>
}

export function provideAdmissionsSession(): AdmissionsSessionContext {
  const service = createAdmissionsService()
  const session = ref<AdmissionsSession | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      session.value = await service.getSession()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load admissions session.'
      error.value = message
    } finally {
      loading.value = false
    }
  }

  const ctx: AdmissionsSessionContext = { session, loading, error, refresh }
  provide(AdmissionsSessionSymbol, ctx)
  return ctx
}

export function useAdmissionsSession(): AdmissionsSessionContext {
  const ctx = inject<AdmissionsSessionContext>(AdmissionsSessionSymbol)
  if (!ctx) {
    throw new Error('Admissions session not provided')
  }
  return ctx
}
