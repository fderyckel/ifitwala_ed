// ifitwala_ed/ui-spa/src/composables/useAdmissionsSession.ts

import { computed, inject, provide, ref, watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService'
import type { Response as AdmissionsSession } from '@/types/contracts/admissions/get_admissions_session'

const AdmissionsSessionSymbol = Symbol('AdmissionsSession')

export type AdmissionsSessionContext = {
  session: Ref<AdmissionsSession | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  currentApplicantName: Ref<string>
  buildRouteLocation: (routeName: string) => { name: string; query: Record<string, unknown> }
  selectApplicant: (studentApplicant: string) => Promise<void>
  refresh: () => Promise<void>
}

export function provideAdmissionsSession(): AdmissionsSessionContext {
  const service = createAdmissionsService()
  const route = useRoute()
  const router = useRouter()
  const session = ref<AdmissionsSession | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentApplicantName = computed(() => session.value?.applicant?.name || '')

  function requestedApplicantFromRoute(): string {
    const raw = route.query.student_applicant
    if (typeof raw !== 'string') return ''
    return raw.trim()
  }

  function buildRouteLocation(routeName: string) {
    const query: Record<string, unknown> = { ...route.query }
    if (currentApplicantName.value) {
      query.student_applicant = currentApplicantName.value
    }
    return { name: routeName, query }
  }

  async function selectApplicant(studentApplicant: string) {
    const nextApplicant = String(studentApplicant || '').trim()
    if (!nextApplicant || nextApplicant === requestedApplicantFromRoute()) {
      return
    }
    await router.replace({
      name: String(route.name || 'admissions-overview'),
      query: {
        ...route.query,
        student_applicant: nextApplicant,
      },
    })
  }

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      const requestedApplicant = requestedApplicantFromRoute()
      try {
        session.value = await service.getSession(
          requestedApplicant ? { student_applicant: requestedApplicant } : {}
        )
      } catch (err) {
        if (!requestedApplicant) {
          throw err
        }
        session.value = await service.getSession()
      }

      const selectedApplicant = session.value?.applicant?.name || ''
      const currentRequestedApplicant = requestedApplicantFromRoute()
      if (selectedApplicant && selectedApplicant !== currentRequestedApplicant) {
        await router.replace({
          name: String(route.name || 'admissions-overview'),
          query: {
            ...route.query,
            student_applicant: selectedApplicant,
          },
        })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load admissions session.'
      error.value = message
    } finally {
      loading.value = false
    }
  }

  watch(
    () => route.query.student_applicant,
    () => {
      refresh()
    },
    { immediate: true }
  )

  const ctx: AdmissionsSessionContext = {
    session,
    loading,
    error,
    currentApplicantName,
    buildRouteLocation,
    selectApplicant,
    refresh,
  }
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
