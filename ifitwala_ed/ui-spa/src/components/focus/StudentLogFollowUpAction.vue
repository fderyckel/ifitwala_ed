<!-- ui-spa/src/components/focus/StudentLogFollowUpAction.vue -->
<template>
  <div class="space-y-4">
    <!-- ============================================================
         CONTEXT HEADER (small)
         - FocusRouterOverlay owns the main header.
         - This component shows workflow-specific context + actions.
       ============================================================ -->
    <div class="card-surface p-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="type-body font-medium">
            Student Log
            <span v-if="log?.name" class="text-muted"> • {{ log.name }}</span>
          </div>
          <div class="type-meta text-muted mt-1">
            <span v-if="log?.student_name">{{ log.student_name }}</span>
            <span v-if="log?.log_type"> • {{ log.log_type }}</span>
            <span v-if="log?.date"> • {{ log.date }}</span>
          </div>
          <div v-if="log?.follow_up_status" class="type-meta text-muted mt-1">
            Status: {{ log.follow_up_status }}
          </div>
        </div>

        <div class="shrink-0 flex items-center gap-2">
          <button
            v-if="log?.name"
            type="button"
            class="btn btn-quiet"
            @click="openInDesk('Student Log', log.name)"
          >
            Open in Desk
          </button>

          <!-- Advisory: does NOT block closing or workflows -->
          <button
            type="button"
            class="btn btn-quiet"
            @click="requestRefresh"
          >
            Refresh
          </button>
        </div>
      </div>

      <div v-if="log?.log_html" class="mt-3">
        <div class="type-meta text-muted mb-1">Log note</div>
        <div class="prose prose-sm max-w-none" v-html="trustedHtml(log.log_html)" />
      </div>
    </div>

    <!-- ============================================================
         FOLLOW-UPS LIST (both modes)
       ============================================================ -->
    <div class="card-surface p-4">
      <div class="type-body font-medium">Follow-ups</div>

      <div v-if="loading" class="type-body text-muted mt-3">
        Loading…
      </div>

      <div v-else-if="followUps.length === 0" class="type-body text-muted mt-3">
        No follow-ups yet.
      </div>

      <div v-else class="mt-3 space-y-3">
        <div v-for="fu in followUps" :key="fu.name" class="rounded-xl border border-ink/10 p-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="type-meta text-muted">
                <span v-if="fu.follow_up_author">{{ fu.follow_up_author }}</span>
                <span v-if="fu.date"> • {{ fu.date }}</span>
                <span v-if="fu.docstatus === 0"> • Draft</span>
                <span v-else> • Submitted</span>
              </div>
            </div>

            <button
              type="button"
              class="btn btn-quiet"
              @click="openInDesk('Student Log Follow Up', fu.name)"
            >
              Open
            </button>
          </div>

          <div
            v-if="fu.follow_up_html"
            class="mt-2 prose prose-sm max-w-none"
            v-html="trustedHtml(fu.follow_up_html)"
          />
        </div>
      </div>
    </div>

    <!-- ============================================================
         MODE: ASSIGNEE (submit follow-up)
       ============================================================ -->
    <div v-if="modeState === 'assignee'" class="card-surface p-4">
      <div class="type-body font-medium">Your follow-up</div>
      <div class="type-meta text-muted mt-1">
        Write what you did, what happened, and any next action.
      </div>

      <div class="mt-3">
        <textarea
          v-model="draftText"
          class="if-textarea w-full"
          rows="8"
          placeholder="Type your follow-up…"
          :disabled="busy"
        />
        <div class="type-meta text-muted mt-2">
          Keep it factual and actionable. No sensitive details beyond what’s necessary.
        </div>
        <div v-if="draftText.trim().length > 0 && !canSubmit" class="type-meta text-muted mt-2">
          Please write at least 5 characters.
        </div>
      </div>

      <div class="mt-4 flex items-center justify-end gap-2">
        <!-- A+: close must NEVER be blocked by busy -->
        <button type="button" class="btn btn-quiet" @click="emitClose">
          Cancel
        </button>

        <button
          type="button"
          class="btn btn-primary"
          :disabled="busy || submittedOnce || !canSubmit"
          @click="submitFollowUp"
        >
          {{ busy ? 'Submitting…' : 'Submit follow-up' }}
        </button>
      </div>
    </div>

    <!-- ============================================================
         MODE: AUTHOR (review outcome)
       ============================================================ -->
    <div v-else-if="modeState === 'author'" class="card-surface p-4">
      <div class="type-body font-medium">Review outcome</div>
      <div class="type-meta text-muted mt-1">
        Decide whether to close the log, or reassign follow-up.
      </div>

      <!-- Reassign -->
      <div class="mt-4">
        <div class="type-meta text-muted mb-1">Reassign to (User ID / email)</div>
        <input
          v-model="reassignTo"
          class="if-input w-full"
          type="text"
          placeholder="e.g. teacher@school.org"
          :disabled="busy"
        />
        <div
          v-if="reassignTo.trim().length > 0 && reassignTo.trim().length < 3"
          class="type-meta text-muted mt-2"
        >
          Please enter a valid user.
        </div>

        <div class="mt-3 flex items-center justify-end gap-2">
          <!-- A+: close must NEVER be blocked by busy -->
          <button type="button" class="btn btn-quiet" @click="emitClose">
            Close
          </button>

          <button
            type="button"
            class="btn btn-primary"
            :disabled="busy || submittedOnce || reassignTo.trim().length < 3"
            @click="reassignFollowUp"
          >
            {{ busy ? 'Processing…' : 'Reassign follow-up' }}
          </button>
        </div>
      </div>

      <!-- Complete -->
      <div class="mt-6 border-t border-ink/10 pt-4">
        <div class="type-meta text-muted">
          If you’re satisfied with the outcome, complete the log.
        </div>

        <div class="mt-3 flex items-center justify-end gap-2">
          <button
            type="button"
            class="btn btn-success"
            :disabled="busy || submittedOnce || !canComplete"
            @click="completeParentLog"
          >
            {{ busy ? 'Completing…' : 'Complete log' }}
          </button>
        </div>

        <div v-if="!canComplete" class="type-meta text-muted mt-2">
          This is disabled if the log is already Completed.
        </div>
      </div>
    </div>

    <!-- ============================================================
         FALLBACK (unknown mode)
       ============================================================ -->
    <div v-else class="rounded-2xl border border-slate-200 bg-white p-5">
      <p class="type-body-strong text-ink">Not supported yet</p>
      <p class="mt-2 type-body text-slate-token/75">
        Unknown Student Log focus mode: <span class="type-meta">{{ modeState }}</span>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { createResource, toast } from 'frappe-ui'

type Mode = 'assignee' | 'author'

type StudentLogRow = {
  name: string
  student?: string | null
  student_name?: string | null
  school?: string | null
  log_type?: string | null
  next_step?: string | null
  follow_up_person?: string | null
  follow_up_role?: string | null
  date?: string | null
  log_html?: string | null
  follow_up_status?: string | null
}

type FollowUpRow = {
  name: string
  date?: string | null
  follow_up_author?: string | null
  follow_up_html?: string | null
  docstatus: 0 | 1 | 2
}

export type FocusContext = {
  focus_item_id?: string | null
  action_type?: string | null
  reference_doctype: string
  reference_name: string
  mode: Mode
  log: StudentLogRow
  follow_ups: FollowUpRow[]
}

const props = defineProps<{
  focusItemId?: string | null
  context: FocusContext
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'done'): void
  (e: 'request-refresh'): void
}>()

function emitClose() {
  emit('close')
}

function requestRefresh() {
  emit('request-refresh')
}

/**
 * Local view state (derived from props.context)
 * - no auto-fetch here (router is source of truth)
 */
const modeState = ref<Mode>('assignee')
const log = ref<StudentLogRow | null>(null)
const followUps = ref<FollowUpRow[]>([])
const loading = ref(false)

const busy = ref(false)
const submittedOnce = ref(false)

const draftText = ref('')
const reassignTo = ref('')

const activeStudentLogName = computed(() => log.value?.name || null)

const canSubmit = computed(() => {
  return !!activeStudentLogName.value && (draftText.value || '').trim().length >= 5
})

const canComplete = computed(() => {
  const s = (log.value?.follow_up_status || '').toLowerCase()
  return !!activeStudentLogName.value && s !== 'completed'
})

function applyContext(ctx: FocusContext | null) {
  if (!ctx) return
  log.value = ctx.log ?? null
  followUps.value = Array.isArray(ctx.follow_ups) ? ctx.follow_ups : []
  modeState.value = ctx.mode === 'author' || ctx.mode === 'assignee' ? ctx.mode : 'assignee'
}

watch(
  () => props.context,
  (next) => {
    // reset action inputs on context change (prevents stale drafts)
    draftText.value = ''
    reassignTo.value = ''
    submittedOnce.value = false
    applyContext(next)
  },
  { immediate: true, deep: false }
)

/* API ---------------------------------------------------------- */
/**
 * NOTE: This is still direct API usage. In A+ final state, these calls
 * move into studentLogFollowUpService and will emit uiSignals there.
 */
const submitFollowUpApi = createResource({
  url: '/api/method/ifitwala_ed.api.focus.submit_student_log_follow_up',
  method: 'POST',
  auto: false,
})

const reviewOutcomeApi = createResource({
  url: '/api/method/ifitwala_ed.api.focus.review_student_log_outcome',
  method: 'POST',
  auto: false,
})

/* Helpers ------------------------------------------------------ */
function _newClientRequestId(prefix = 'req') {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function openInDesk(doctype: string, name: string) {
  if (!doctype || !name) return
  const route = String(doctype)
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9\-]/g, '')
    .replace(/\-+/g, '-')

  window.open(`/app/${route}/${encodeURIComponent(name)}`, '_blank', 'noopener')
}

function trustedHtml(html: string) {
  return html || ''
}

function _requireFocusItemId(): string | null {
  const id = (props.focusItemId || '').trim()
  if (!id) {
    toast({
      title: 'Missing focus item',
      text: 'Please close and reopen this item from the Focus list.',
      icon: 'x',
    })
    return null
  }
  return id
}

function _normalizeMessage(res: any) {
  // handles: res.message, res, nested objects
  const msg = res && typeof res === 'object' && 'message' in res ? res.message : res
  return msg
}

async function _aPlusSuccessCloseThenDone() {
  // A+: close immediately, then best-effort done.
  emitClose()
  await nextTick()
  try {
    emit('done')
  } catch (e) {
    // never block closing
  }
}

/* Actions ------------------------------------------------------ */
async function submitFollowUp() {
  if (busy.value || submittedOnce.value) return
  if (modeState.value !== 'assignee') return
  if (!canSubmit.value) return

  const focusItemId = _requireFocusItemId()
  if (!focusItemId) return

  const followUpText = (draftText.value || '').trim()
  if (followUpText.length < 5) return

  busy.value = true
  submittedOnce.value = true

  try {
    const client_request_id = _newClientRequestId('fu')

    const res = await submitFollowUpApi.submit({
      focus_item_id: focusItemId,
      follow_up: followUpText,
      client_request_id,
    })

    const msg = _normalizeMessage(res) as any
    if (!msg?.ok) {
      throw new Error(msg?.message || 'Submit failed.')
    }

    // Toast is best-effort; must not gate close.
    toast({
      title: msg.idempotent ? 'Already submitted' : 'Follow-up submitted',
      icon: 'check',
    })

    await _aPlusSuccessCloseThenDone()
  } catch (e: any) {
    // allow retry
    submittedOnce.value = false
    toast({
      title: 'Could not submit follow-up',
      text: e?.message || 'Please try again.',
      icon: 'x',
    })
  } finally {
    busy.value = false
  }
}

async function reassignFollowUp() {
  if (busy.value || submittedOnce.value) return
  if (modeState.value !== 'author') return

  const focusItemId = _requireFocusItemId()
  if (!focusItemId) return

  const target = (reassignTo.value || '').trim()
  if (target.length < 3) {
    toast({
      title: 'Missing assignee',
      text: 'Please enter a valid user (email / user id).',
      icon: 'x',
    })
    return
  }

  busy.value = true
  submittedOnce.value = true

  try {
    const client_request_id = _newClientRequestId('rvw')

    const res = await reviewOutcomeApi.submit({
      focus_item_id: focusItemId,
      decision: 'reassign',
      follow_up_person: target,
      client_request_id,
    })

    const msg = _normalizeMessage(res) as any
    if (!msg?.ok) {
      throw new Error(msg?.message || 'Reassign failed.')
    }

    toast({
      title: msg.idempotent ? 'Already processed' : 'Reassigned',
      icon: 'check',
    })

    await _aPlusSuccessCloseThenDone()
  } catch (e: any) {
    submittedOnce.value = false
    toast({
      title: 'Could not reassign',
      text: e?.message || 'Please try again.',
      icon: 'x',
    })
  } finally {
    busy.value = false
  }
}

async function completeParentLog() {
  if (busy.value || submittedOnce.value) return
  if (modeState.value !== 'author') return
  if (!canComplete.value) return

  const focusItemId = _requireFocusItemId()
  if (!focusItemId) return

  busy.value = true
  submittedOnce.value = true

  try {
    const client_request_id = _newClientRequestId('rvw')

    const res = await reviewOutcomeApi.submit({
      focus_item_id: focusItemId,
      decision: 'complete',
      client_request_id,
    })

    const msg = _normalizeMessage(res) as any
    if (!msg?.ok) {
      throw new Error(msg?.message || 'Complete failed.')
    }

    toast({
      title: msg.idempotent ? 'Already processed' : 'Log completed',
      icon: 'check',
    })

    await _aPlusSuccessCloseThenDone()
  } catch (e: any) {
    submittedOnce.value = false
    toast({
      title: 'Could not complete log',
      text: e?.message || 'Please try again.',
      icon: 'x',
    })
  } finally {
    busy.value = false
  }
}
</script>
