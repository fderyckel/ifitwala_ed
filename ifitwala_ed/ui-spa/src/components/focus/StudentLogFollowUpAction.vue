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
          <button v-if="log?.name" type="button" class="btn btn-quiet" @click="openInDesk('Student Log', log.name)">
            Open in Desk
          </button>
          <button type="button" class="btn btn-quiet" :disabled="loading" @click="reload">
            Refresh
          </button>
        </div>
      </div>

      <div v-if="log?.log_html" class="mt-3">
        <div class="type-meta text-muted mb-1">Log note</div>
        <div class="prose prose-sm max-w-none" v-html="safeHtml(log.log_html)" />
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
        <div
          v-for="fu in followUps"
          :key="fu.name"
          class="rounded-xl border border-ink/10 p-3"
        >
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
            v-html="safeHtml(fu.follow_up_html)"
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
        />
        <div class="type-meta text-muted mt-2">
          Keep it factual and actionable. No sensitive details beyond what’s necessary.
        </div>
      </div>

      <div class="mt-4 flex items-center justify-end gap-2">
        <button type="button" class="btn btn-quiet" :disabled="busy" @click="emitClose">
          Cancel
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="busy || !canSubmit"
          @click="submitFollowUp"
        >
          {{ busy ? 'Submitting…' : 'Submit follow-up' }}
        </button>
      </div>
    </div>

    <!-- ============================================================
         MODE: AUTHOR (complete log)
       ============================================================ -->
    <div v-else-if="modeState === 'author'" class="card-surface p-4">
      <div class="type-body font-medium">Author actions</div>
      <div class="type-meta text-muted mt-1">
        When you’re satisfied, mark the Student Log as completed.
      </div>

      <div class="mt-4 flex items-center justify-end gap-2">
        <button type="button" class="btn btn-quiet" :disabled="busy" @click="emitClose">
          Close
        </button>
        <button
          type="button"
          class="btn btn-success"
          :disabled="busy || !canComplete"
          @click="completeParentLog"
        >
          {{ busy ? 'Completing…' : 'Complete log' }}
        </button>
      </div>

      <div v-if="!canComplete" class="type-meta text-muted mt-2">
        This is disabled if the log is already Completed.
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
import { computed, ref, watch } from 'vue'
import { createResource, toast } from 'frappe-ui'

type Mode = 'assignee' | 'author'

type StudentLogRow = {
  name: string
  student_name?: string | null
  log_type?: string | null
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

/**
 * Focus context returned by ifitwala_ed.api.focus.get_context
 * - Server stays authoritative (mode, permissions, visibility).
 */
type FocusContext = {
  focus_item_id?: string | null
  action_type?: string | null
  reference_doctype: string
  reference_name: string
  mode: Mode
  log: StudentLogRow
  follow_ups: FollowUpRow[]
}

const props = defineProps<{
  /**
   * Prefer focusItemId (deterministic ID). This is the stable Focus contract.
   * studentLog is a fallback for debug / direct opening.
   */
  focusItemId?: string | null
  studentLog?: string | null

  /**
   * Mode is allowed as a hint, but the server can override it in get_context.
   */
  mode?: Mode
}>()

const emit = defineEmits<{
  /**
   * Tell FocusRouterOverlay to close itself.
   * (FocusRouterOverlay owns the overlay; this is content-only.)
   */
  (e: 'close'): void

  /**
   * Optional: tell parent that workflow likely completed, so parent can refresh focus list.
   * (We keep it soft: parent decides what to do.)
   */
  (e: 'done'): void
}>()

function emitClose() {
  emit('close')
}

const modeState = ref<Mode>(props.mode ?? 'assignee')

const log = ref<StudentLogRow | null>(null)
const followUps = ref<FollowUpRow[]>([])
const loading = ref(false)
const busy = ref(false)

const draftText = ref('')

const canSubmit = computed(() => {
  const name = props.studentLog || log.value?.name
  return !!name && (draftText.value || '').trim().length >= 5
})

const canComplete = computed(() => {
  const name = props.studentLog || log.value?.name
  const s = (log.value?.follow_up_status || '').toLowerCase()
  return !!name && s !== 'completed'
})

/* API ---------------------------------------------------------- */
const getContext = createResource({
  url: 'ifitwala_ed.api.focus.get_context',
  method: 'POST',
  auto: false,
})

const insertDoc = createResource({
  url: '/api/method/frappe.client.insert',
  method: 'POST',
})

const submitDoc = createResource({
  url: '/api/method/frappe.client.submit',
  method: 'POST',
})

const completeLog = createResource({
  url: '/api/method/ifitwala_ed.students.doctype.student_log.student_log.complete_log',
  method: 'POST',
})

async function reload() {
  const refName = props.studentLog || log.value?.name || null
  if (!props.focusItemId && !refName) return

  loading.value = true
  try {
    const payload = props.focusItemId
      ? { focus_item_id: props.focusItemId }
      : { reference_doctype: 'Student Log', reference_name: refName }

    const res = await getContext.submit(payload)
    const ctx = ((res as any)?.message ?? res) as FocusContext

    if (!ctx || !ctx.log) {
      throw new Error('Missing focus context.')
    }

    log.value = ctx.log
    followUps.value = Array.isArray(ctx.follow_ups) ? ctx.follow_ups : []

    if (ctx.mode === 'assignee' || ctx.mode === 'author') {
      modeState.value = ctx.mode
    }
  } catch (e: any) {
    toast({
      title: 'Could not load follow-up context',
      text: e?.message || 'Please try again.',
      icon: 'x',
    })
  } finally {
    loading.value = false
  }
}

watch(
  () => props.focusItemId,
  () => {
    // Reset local state when routing changes
    draftText.value = ''
    modeState.value = props.mode ?? modeState.value
    reload()
  }
)

watch(
  () => props.studentLog,
  () => {
    draftText.value = ''
    modeState.value = props.mode ?? modeState.value
    reload()
  }
)

/* ACTIONS ------------------------------------------------------ */
async function submitFollowUp() {
  if (!canSubmit.value) return

  const studentLogName = props.studentLog || log.value?.name
  if (!studentLogName) return

  busy.value = true
  try {
    // 1) insert follow-up doc (draft)
    const doc = {
      doctype: 'Student Log Follow Up',
      student_log: studentLogName,
      date: new Date().toISOString().slice(0, 10),
      follow_up: draftText.value,
    }

    const ins = await insertDoc.submit({ doc })
    const insertedName = (ins as any)?.message?.name as string | undefined
    if (!insertedName) {
      throw new Error('Insert failed (no doc name returned).')
    }

    // 2) submit it so controller side effects run
    await submitDoc.submit({
      doc: { doctype: 'Student Log Follow Up', name: insertedName },
    })

    toast({ title: 'Follow-up submitted', icon: 'check' })

    // Refresh local context (optional but nice)
    await reload()

    // Notify parent that workflow likely changed state (Focus list should refresh)
    emit('done')

    // Close the router overlay
    emitClose()
  } catch (e: any) {
    toast({
      title: 'Could not submit follow-up',
      text: e?.message || 'Please try again.',
      icon: 'x',
    })
  } finally {
    busy.value = false
  }
}

async function completeParentLog() {
  if (!canComplete.value) return

  const studentLogName = props.studentLog || log.value?.name
  if (!studentLogName) return

  busy.value = true
  try {
    await completeLog.submit({ log_name: studentLogName })
    toast({ title: 'Log completed', icon: 'check' })

    emit('done')
    emitClose()
  } catch (e: any) {
    toast({
      title: 'Could not complete log',
      text: e?.message || 'Please try again.',
      icon: 'x',
    })
  } finally {
    busy.value = false
  }
}

/* HELPERS ------------------------------------------------------ */
function openInDesk(doctype: string, name: string) {
  // Leaving SPA intentionally; ok to open /app/...
  window.open(`/app/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`, '_blank', 'noopener')
}

function safeHtml(html: string) {
  return html || ''
}

// initial load
reload()
</script>
