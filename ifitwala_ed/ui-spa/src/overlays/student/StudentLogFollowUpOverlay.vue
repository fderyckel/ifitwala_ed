<!-- ui-spa/src/overlays/student/StudentLogFollowUpOverlay.vue -->

<!--
Used by:
- FocusRouterOverlay.vue
- Student Log follow-up workflows
-->

<template>
  <TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
    <Dialog
      as="div"
      class="if-overlay if-overlay--student-log-follow-up"
      :initialFocus="closeBtnEl"
      @close="onDialogClose"
    >
      <!--
        A+ close semantics:
        - Backdrop clicks must be tagged as 'backdrop' so OverlayHost can enforce closeOnBackdrop.
        - HeadlessUI @close is ambiguous (can be triggered by outside click / focus portal issues).
          DO NOT forward it into OverlayHost or close from it.
        - ESC is handled explicitly via document keydown.
      -->
      <div class="if-overlay__backdrop" @click="emitClose('backdrop')" />

      <div class="if-overlay__wrap" :style="wrapStyle">
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
            <!-- Header (calm, consistent with other overlays) -->
            <div class="meeting-modal__header">
              <div class="meeting-modal__headline min-w-0">
                <div class="type-overline">
                  {{ modeState === 'author' ? __('Review') : __('Follow-up') }}
                </div>

                <DialogTitle class="type-h2 text-canopy truncate">
                  {{ modeState === 'author' ? __('Review outcome') : __('Follow up') }}
                </DialogTitle>

                <div class="type-caption mt-1 truncate">
                  <span v-if="log?.student_name">{{ log.student_name }}</span>
                  <span v-if="log?.log_type"> • {{ log.log_type }}</span>
                  <span v-if="log?.date"> • {{ log.date }}</span>
                </div>
              </div>

              <div class="meeting-modal__header-actions">
                <button
                  ref="closeBtnEl"
                  type="button"
                  class="if-overlay__icon-button"
                  @click="emitClose('programmatic')"
                  aria-label="Close"
                >
                  <span class="sr-only">Close</span>
                  <span aria-hidden="true" class="text-ink/70">×</span>
                </button>
              </div>
            </div>

            <!-- Body -->
            <div class="if-overlay__body custom-scrollbar">
              <!-- A+ UX: overlays never toast. Errors show inline. -->
              <div
                v-if="errorMessage"
                class="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
                role="alert"
              >
                <p class="type-body-strong text-rose-900">
                  {{ __('Something went wrong') }}
                </p>
                <p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
                  {{ errorMessage }}
                </p>
              </div>

              <div v-if="loading" class="py-10">
                <div class="type-body text-ink/70">Loading…</div>
              </div>

              <div v-else class="space-y-6">
                <!-- Parent log preview -->
                <div class="card-panel p-5">
                  <div class="flex items-start justify-between gap-4">
                    <div class="min-w-0">
                      <div class="type-label">Student log</div>

                      <div class="mt-1 type-body-strong text-ink truncate">
                        <span>Log</span>
                        <span v-if="log?.name" class="text-ink/60"> • {{ log.name }}</span>
                      </div>

                      <div v-if="log?.log_author_name || log?.log_author" class="type-caption mt-1">
                        By:
                        <span class="text-ink/80">
                          {{ log?.log_author_name || log?.log_author }}
                        </span>
                      </div>

                      <div v-if="log?.follow_up_status" class="type-caption mt-1">
                        Status: {{ log.follow_up_status }}
                      </div>
                    </div>

                    <button
                      v-if="log?.name"
                      type="button"
                      class="if-action"
                      @click="openInDesk('Student Log', log.name)"
                    >
                      Open in Desk
                    </button>
                  </div>

                  <div v-if="log?.log_html" class="mt-5">
                    <div class="type-label mb-2">Log note</div>
                    <div class="rounded-2xl border border-ink/10 bg-surface-soft p-4">
                      <div class="prose prose-sm max-w-none" v-html="htmlOrEmpty(log.log_html)" />
                    </div>
                  </div>
                </div>

                <!-- Follow ups list (both modes can see) -->
                <div class="card-panel p-5">
                  <div class="flex items-center justify-between gap-3">
                    <div class="min-w-0">
                      <div class="type-label">History</div>
                      <div class="mt-1 type-body-strong text-ink">Follow-ups</div>
                    </div>

                    <button
                      type="button"
                      class="if-pill type-button-label"
                      :disabled="busy"
                      @click="reload"
                    >
                      Refresh
                    </button>
                  </div>

                  <div v-if="followUps.length === 0" class="mt-4 type-body text-ink/70">
                    No follow-ups yet.
                  </div>

                  <div v-else class="mt-4 space-y-3">
                    <div
                      v-for="fu in followUps"
                      :key="fu.name"
                      class="rounded-2xl border border-ink/10 bg-surface-soft p-4"
                    >
                      <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0">
                          <div class="type-caption">
                            <span v-if="fu.follow_up_author">{{ fu.follow_up_author }}</span>
                            <span v-if="fu.date"> • {{ fu.date }}</span>
                            <span v-if="fu.docstatus === 0"> • Draft</span>
                            <span v-else> • Submitted</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          class="if-pill type-button-label"
                          @click="openInDesk('Student Log Follow Up', fu.name)"
                        >
                          Open
                        </button>
                      </div>

                      <div
                        v-if="fu.follow_up_html"
                        class="mt-3 rounded-2xl border border-ink/10 bg-white/70 p-4"
                      >
                        <div class="prose prose-sm max-w-none" v-html="htmlOrEmpty(fu.follow_up_html)" />
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Assignee action: write follow-up -->
                <div v-if="modeState === 'assignee'" class="card-panel p-5">
                  <div class="type-label">Your response</div>
                  <div class="mt-1 type-body-strong text-ink">Your follow-up</div>
                  <div class="type-caption mt-1">
                    Write what you did, what happened, and any next action.
                  </div>

                  <div class="mt-4">
                    <textarea
                      v-model="draftText"
                      class="if-textarea w-full"
                      rows="8"
                      placeholder="Type your follow-up…"
                      :disabled="busy"
                    />
                    <div class="type-caption mt-2">
                      Keep it factual and actionable. No sensitive details beyond what’s necessary.
                    </div>
                  </div>

                  <div class="mt-5 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      class="if-pill type-button-label"
                      :disabled="busy"
                      @click="emitClose('programmatic')"
                    >
                      Cancel
                    </button>

                    <button
                      type="button"
                      class="if-action"
                      :disabled="busy || !canSubmit"
                      @click="submitFollowUp"
                    >
                      {{ busy ? 'Submitting…' : 'Submit follow-up' }}
                    </button>
                  </div>
                </div>

                <!-- Author action: complete log -->
                <div v-if="modeState === 'author'" class="card-panel p-5">
                  <div class="type-label">Author actions</div>
                  <div class="mt-1 type-body-strong text-ink">Complete this log</div>
                  <div class="type-caption mt-1">
                    When you’re satisfied, mark the Student Log as completed.
                  </div>

                  <div class="mt-5 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      class="if-pill type-button-label"
                      :disabled="busy"
                      @click="emitClose('programmatic')"
                    >
                      Close
                    </button>

                    <button
                      type="button"
                      class="if-action"
                      :disabled="busy || !canComplete"
                      @click="completeParentLog"
                    >
                      {{ busy ? 'Completing…' : 'Complete log' }}
                    </button>
                  </div>

                  <div v-if="!canComplete" class="type-caption mt-3 text-ink/70">
                    This is disabled if the log is already Completed.
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer (keep calm, no extra content) -->
            <div class="if-overlay__footer" />
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { __ } from '@/lib/i18n'
import { createFocusService } from '@/lib/services/focus/focusService'
import { useOverlayStack } from '@/composables/useOverlayStack'
import type {
	Request as GetFocusContextRequest,
	Response as GetFocusContextResponse,
} from '@/types/contracts/focus/get_focus_context'
import type { Request as SubmitStudentLogFollowUpRequest } from '@/types/contracts/focus/submit_student_log_follow_up'
import type { Request as ReviewStudentLogOutcomeRequest } from '@/types/contracts/focus/review_student_log_outcome'

/**
 * StudentLogFollowUpOverlay (A+ workflow shell)
 * ------------------------------------------------------------
 * This overlay:
 * - Loads context for display
 * - Calls workflow actions via focusService
 * - Closes immediately on success
 *
 * A+ invalidation rule (locked):
 * - This overlay does NOT refresh pages directly
 * - This overlay does NOT dispatch custom window events
 * - focusService emits uiSignals on successful workflow completion
 * - Pages subscribe to uiSignals and refresh what they own
 */

type Mode = GetFocusContextResponse['mode']
type CloseReason = 'backdrop' | 'esc' | 'programmatic'

const props = defineProps<{
	open: boolean
	zIndex?: number
	mode: Mode
	studentLog: string
	focusItemId?: string | null
	overlayId?: string | null
}>()

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void
	(e: 'after-leave'): void
}>()

const overlay = useOverlayStack()
const focusService = createFocusService()

const baseZ = computed(() => props.zIndex ?? 3000)
const wrapStyle = computed(() => ({ zIndex: baseZ.value }))

type FocusLog = GetFocusContextResponse['log']
type FocusFollowUp = GetFocusContextResponse['follow_ups'][number]

const closeBtnEl = ref<HTMLButtonElement | null>(null)

const modeState = ref<Mode>(props.mode)

const log = ref<FocusLog | null>(null)
const followUps = ref<FocusFollowUp[]>([])
const loading = ref(false)
const busy = ref(false)
const submittedOnce = ref(false)

const draftText = ref('')
const errorMessage = ref('')

const canSubmit = computed(() => {
	return !!props.studentLog && (draftText.value || '').trim().length >= 5
})

const canComplete = computed(() => {
	const s = (log.value?.follow_up_status || '').toLowerCase()
	return !!props.studentLog && s !== 'completed'
})

function setError(err: unknown, fallback: string) {
	const msg =
		(typeof err === 'object' && err && 'message' in (err as any) ? String((err as any).message) : '') ||
		(typeof err === 'string' ? err : '') ||
		fallback
	errorMessage.value = msg
}

function clearError() {
	errorMessage.value = ''
}

function _newClientRequestId(prefix = 'req') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function emitClose(reason: CloseReason) {
	// If this overlay is mounted in OverlayHost, prefer closing the stack entry.
	const id = (props.overlayId || '').trim()
	if (id) {
		try {
			overlay.close(id)
			return
		} catch (e) {
			// fall back to parent emit
		}
	}
	emit('close', reason)
}

function emitAfterLeave() {
	emit('after-leave')
}

/**
 * HeadlessUI Dialog @close is ambiguous.
 * Under A+ we DO NOT forward it or close from it.
 * Backdrop + ESC + explicit buttons are the only closing paths.
 */
function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return
	if (e.key === 'Escape') emitClose('esc')
}

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) {
			document.addEventListener('keydown', onKeydown, true)
		} else {
			document.removeEventListener('keydown', onKeydown, true)
		}
	},
	{ immediate: true }
)

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true)
})

/* API ---------------------------------------------------------- */
async function reload() {
	if (!props.studentLog && !props.focusItemId) return
	clearError()
	loading.value = true
	try {
		const payload: GetFocusContextRequest = (props.focusItemId || '').trim()
			? { focus_item_id: (props.focusItemId || '').trim() }
			: { reference_doctype: 'Student Log', reference_name: props.studentLog }

		const ctx: GetFocusContextResponse = await focusService.getFocusContext(payload)

		if (!ctx || !ctx.log) throw new Error(__('Missing focus context.'))

		log.value = ctx.log
		followUps.value = Array.isArray(ctx.follow_ups) ? ctx.follow_ups : []
		if (ctx.mode && ctx.mode !== modeState.value) modeState.value = ctx.mode
	} catch (e: any) {
		setError(e, __('Could not load follow-up context. Please try again.'))
	} finally {
		loading.value = false
	}
}

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return
		// reset local UI state each open
		clearError()
		draftText.value = ''
		submittedOnce.value = false
		modeState.value = props.mode
		reload()
	},
	{ immediate: true }
)

/* Actions ------------------------------------------------------ */
async function submitFollowUp() {
	if (busy.value || submittedOnce.value) return
	if (!canSubmit.value) return
	clearError()

	const focusItemId = (props.focusItemId || '').trim()
	if (!focusItemId) {
		setError(__('Missing focus item'), __('Please close and reopen this item from the Focus list.'))
		return
	}

	busy.value = true
	submittedOnce.value = true

	try {
		const payload: SubmitStudentLogFollowUpRequest = {
			focus_item_id: focusItemId,
			follow_up: (draftText.value || '').trim(),
			client_request_id: _newClientRequestId('fu'),
		}

		const msg = await focusService.submitStudentLogFollowUp(payload)
		if (!msg?.ok) throw new Error(__('Submit failed.'))

		emitClose('programmatic')
	} catch (e: any) {
		submittedOnce.value = false
		setError(e, __('Could not submit follow-up. Please try again.'))
	} finally {
		busy.value = false
	}
}

async function completeParentLog() {
	if (busy.value || submittedOnce.value) return
	if (!canComplete.value) return
	clearError()

	const focusItemId = (props.focusItemId || '').trim()
	if (!focusItemId) {
		setError(__('Missing focus item'), __('Please close and reopen this item from the Focus list.'))
		return
	}

	busy.value = true
	submittedOnce.value = true

	try {
		const payload: ReviewStudentLogOutcomeRequest = {
			focus_item_id: focusItemId,
			decision: 'complete',
			client_request_id: _newClientRequestId('rvw'),
		}

		const msg = await focusService.reviewStudentLogOutcome(payload)
		if (!msg?.ok) throw new Error(__('Complete failed.'))

		emitClose('programmatic')
	} catch (e: any) {
		submittedOnce.value = false
		setError(e, __('Could not complete log. Please try again.'))
	} finally {
		busy.value = false
	}
}

/* Helpers ------------------------------------------------------ */
function openInDesk(doctype: string, name: string) {
	const safeDoctype = String(doctype || '').trim()
	if (!safeDoctype || !name) return

	const url = `/app/${encodeURIComponent(safeDoctype)}/${encodeURIComponent(name)}`
	window.open(url, '_blank', 'noopener')
}

function htmlOrEmpty(html: string) {
	return html || ''
}
</script>
