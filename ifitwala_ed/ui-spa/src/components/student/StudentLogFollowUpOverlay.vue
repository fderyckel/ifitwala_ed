<!-- ui-spa/src/components/student/StudentLogFollowUpOverlay.vue -->
<template>
  <TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
    <Dialog as="div" class="if-overlay if-overlay--student-log-follow-up" @close="emitClose">
      <div class="if-overlay__backdrop" />

      <div class="if-overlay__wrap" :style="{ zIndex: zIndex ?? 3000 }">
        <TransitionChild
          as="template"
          enter="if-overlay__panel-enter"
          enter-from="if-overlay__panel-from"
          enter-to="if-overlay__panel-to"
          leave="if-overlay__panel-leave"
          leave-from="if-overlay__panel-to"
          leave-to="if-overlay__panel-from"
        >
          <DialogPanel class="if-overlay__panel">
            <!-- Header -->
            <div class="if-overlay__header">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <DialogTitle class="type-h2">
                    {{ modeState === 'author' ? 'Review outcome' : 'Follow up' }}
                  </DialogTitle>
                  <div class="type-meta text-muted mt-1">
                    <span v-if="log?.student_name">{{ log.student_name }}</span>
                    <span v-if="log?.log_type"> • {{ log.log_type }}</span>
                    <span v-if="log?.date"> • {{ log.date }}</span>
                  </div>
                </div>

                <button type="button" class="btn btn-quiet" @click="emitClose">
                  Close
                </button>
              </div>
            </div>

            <!-- Body -->
            <div class="if-overlay__body">
              <div v-if="loading" class="py-6">
                <div class="type-body text-muted">Loading…</div>
              </div>

              <div v-else class="space-y-4">
                <!-- Parent log preview -->
                <div class="card-surface p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="type-body font-medium">
                        Student Log
                        <span v-if="log?.name" class="text-muted"> • {{ log.name }}</span>
                      </div>
                      <div v-if="log?.follow_up_status" class="type-meta text-muted mt-1">
                        Status: {{ log.follow_up_status }}
                      </div>
                    </div>

                    <button
                      v-if="log?.name"
                      type="button"
                      class="btn btn-quiet"
                      @click="openInDesk('Student Log', log.name)"
                    >
                      Open in Desk
                    </button>
                  </div>

                  <div v-if="log?.log_html" class="mt-3">
                    <div class="type-meta text-muted mb-1">Log note</div>
                    <div class="prose prose-sm max-w-none" v-html="safeHtml(log.log_html)" />
                  </div>
                </div>

                <!-- Follow ups list (both modes can see) -->
                <div class="card-surface p-4">
                  <div class="flex items-center justify-between gap-3">
                    <div class="type-body font-medium">Follow-ups</div>
                    <button type="button" class="btn btn-quiet" @click="reload">
                      Refresh
                    </button>
                  </div>

                  <div v-if="followUps.length === 0" class="type-body text-muted mt-3">
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

                <!-- Assignee action: write follow-up -->
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

                <!-- Author action: complete log -->
                <div v-if="modeState === 'author'" class="card-surface p-4">
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
              </div>
            </div>

            <!-- Footer (optional; keep calm) -->
            <div class="if-overlay__footer" />
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
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

type FocusContext = {
  focus_item_id?: string | null
  reference_doctype: string
  reference_name: string
  mode: Mode
  log: StudentLogRow
  follow_ups: FollowUpRow[]
}

const props = defineProps<{
  open: boolean
  zIndex?: number
  mode: Mode
  studentLog: string
  focusItemId?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'after-leave'): void
}>()

function emitClose() {
  emit('close')
}
function emitAfterLeave() {
  emit('after-leave')
}

const modeState = ref<Mode>(props.mode)

const log = ref<StudentLogRow | null>(null)
const followUps = ref<FollowUpRow[]>([])
const loading = ref(false)
const busy = ref(false)

const draftText = ref('')

const canSubmit = computed(() => {
  return !!props.studentLog && (draftText.value || '').trim().length >= 5
})

const canComplete = computed(() => {
  const s = (log.value?.follow_up_status || '').toLowerCase()
  return !!props.studentLog && s !== 'completed'
})

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
  if (!props.studentLog && !props.focusItemId) return
  loading.value = true
  try {
    const payload = props.focusItemId
      ? { focus_item_id: props.focusItemId }
      : { reference_doctype: 'Student Log', reference_name: props.studentLog }
    const res = await getContext.submit(payload)
    const ctx = ((res as any)?.message ?? res) as FocusContext
    if (!ctx || !ctx.log) {
      throw new Error('Missing focus context.')
    }
    log.value = ctx.log
    followUps.value = Array.isArray(ctx.follow_ups) ? ctx.follow_ups : []
    if (ctx.mode && ctx.mode !== modeState.value) {
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
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    // reset local UI state each open
    draftText.value = ''
    modeState.value = props.mode
    reload()
  },
  { immediate: false }
)

async function submitFollowUp() {
  if (!canSubmit.value) return
  busy.value = true
  try {
    // 1) insert draft follow-up doc (docstatus 0)
    const doc = {
      doctype: 'Student Log Follow Up',
      student_log: props.studentLog,
      date: new Date().toISOString().slice(0, 10),
      follow_up: draftText.value,
    }

    const ins = await insertDoc.submit({ doc })
    const insertedName = (ins as any)?.message?.name as string | undefined
    if (!insertedName) {
      throw new Error('Insert failed (no doc name returned).')
    }

    // 2) submit it (docstatus 1) so controller side effects run
    await submitDoc.submit({
      doc: {
        doctype: 'Student Log Follow Up',
        name: insertedName,
      },
    })

    toast({ title: 'Follow-up submitted', icon: 'check' })

    // refresh local view
    await reload()

    // close overlay (Focus layer will remove item on refresh later)
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
  busy.value = true
  try {
    await completeLog.submit({ log_name: props.studentLog })
    toast({ title: 'Log completed', icon: 'check' })
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

function openInDesk(doctype: string, name: string) {
  // SPA internal nav should not hardcode /portal; this is leaving SPA intentionally.
  window.open(`/app/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`, '_blank', 'noopener')
}

function safeHtml(html: string) {
  // Minimal: trust server-side content here because Student Log uses Text Editor.
  // If you later want strict sanitization, do it server-side in focus.get_context.
  return html || ''
}
</script>
