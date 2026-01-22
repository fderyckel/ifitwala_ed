<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue -->

<template>
  <div class="space-y-6">
    <div>
      <p class="type-h2 text-ink">{{ __('Overview') }}</p>
      <p class="mt-1 type-caption text-ink/60">
        {{ __('Track your application progress and next steps.') }}
      </p>
    </div>

    <div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
      <div class="flex items-center gap-3">
        <Spinner class="h-4 w-4" />
        <p class="type-body-strong text-ink">{{ __('Loading overview…') }}</p>
      </div>
    </div>

    <div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
      <p class="type-body-strong text-rose-900">{{ __('Unable to load overview') }}</p>
      <p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
      <button
        type="button"
        class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
        @click="loadSnapshot"
      >
        {{ __('Try again') }}
      </button>
    </div>

    <div v-else>
      <div class="grid gap-4 md:grid-cols-2">
        <div
          v-for="card in completionCards"
          :key="card.key"
          class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
        >
          <p class="type-body-strong text-ink">{{ card.label }}</p>
          <p class="mt-1 type-caption" :class="card.tone">
            {{ card.statusLabel }}
          </p>
        </div>
      </div>

      <div class="mt-6 rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
        <p class="type-body-strong text-ink">{{ __('Next actions') }}</p>
        <p v-if="!snapshot?.next_actions?.length" class="mt-2 type-caption text-ink/60">
          {{ __('No outstanding tasks right now.') }}
        </p>
        <div v-else class="mt-3 flex flex-col gap-3">
          <div
            v-for="action in snapshot.next_actions"
            :key="action.label"
            class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/60 bg-sand/40 px-4 py-3"
          >
            <div>
              <p class="type-body text-ink">{{ action.label }}</p>
              <p v-if="action.is_blocking" class="type-caption text-ink/60">
                {{ __('Required before submission.') }}
              </p>
            </div>
            <RouterLink
              :to="{ name: action.route_name }"
              class="rounded-full bg-ink px-4 py-2 type-caption text-white"
            >
              {{ __('Open') }}
            </RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Spinner } from 'frappe-ui'

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService'
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals'
import type { Response as ApplicantSnapshot } from '@/types/contracts/admissions/get_applicant_snapshot'

const service = createAdmissionsService()

const snapshot = ref<ApplicantSnapshot | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

function statusLabel(state: string) {
  switch (state) {
    case 'complete':
      return __('Complete')
    case 'in_progress':
      return __('In progress')
    case 'optional':
      return __('Optional')
    case 'pending':
    default:
      return __('Pending')
  }
}

function statusTone(state: string) {
  switch (state) {
    case 'complete':
      return 'text-leaf'
    case 'in_progress':
      return 'text-sun'
    case 'optional':
      return 'text-ink/55'
    case 'pending':
    default:
      return 'text-ink/60'
  }
}

const completionCards = computed(() => {
  const completeness = snapshot.value?.completeness
  if (!completeness) return []
  return [
    { key: 'health', label: __('Health information'), state: completeness.health },
    { key: 'documents', label: __('Documents'), state: completeness.documents },
    { key: 'policies', label: __('Policies'), state: completeness.policies },
    { key: 'interviews', label: __('Interviews'), state: completeness.interviews },
  ].map((card) => ({
    ...card,
    statusLabel: statusLabel(card.state),
    tone: statusTone(card.state),
  }))
})

async function loadSnapshot() {
  loading.value = true
  error.value = null
  try {
    snapshot.value = await service.getSnapshot()
  } catch (err) {
    const message = err instanceof Error ? err.message : __('Unable to load overview.')
    error.value = message
  } finally {
    loading.value = false
  }
}

let unsubscribe: (() => void) | null = null

onMounted(async () => {
  await loadSnapshot()
  unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
    loadSnapshot()
  })
})

onBeforeUnmount(() => {
  if (unsubscribe) unsubscribe()
})
</script>
