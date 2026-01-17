<!-- ui-spa/src/overlays/focus/FocusRouterOverlay.vue -->

 <!--
Used by:
- StaffHome.vue
- FocusListItem.vue
-->

<template>
  <TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
    <Dialog
      as="div"
      class="if-overlay if-overlay--focus"
      :style="overlayStyle"
      :initialFocus="initialFocusEl"
      @close="onDialogClose"
    >
      <div class="if-overlay__backdrop" />

      <div class="if-overlay__wrap">
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
            <!-- ============================================================
                 HEADER (align to meeting-modal rhythm)
               ============================================================ -->
            <div class="meeting-modal__header">
              <div class="meeting-modal__headline min-w-0">
                <div class="type-overline">
                  {{ headerKicker }}
                </div>

                <div class="mt-1 flex items-start gap-3 min-w-0">
                  <DialogTitle class="type-h2 text-canopy truncate">
                    {{ headerTitle }}
                  </DialogTitle>
                </div>

                <p v-if="headerSubtitle" class="type-caption mt-1 truncate">
                  {{ headerSubtitle }}
                </p>
              </div>

              <div class="meeting-modal__header-actions">
                <!--
                  A+ FocusTrap Option B (locked):
                  - Always have at least one real, semantic, always-present focusable element.
                  - Use native <button> + initialFocus so HeadlessUI can lock focus immediately.
                  - Avoid fake tabindex or hidden focus hacks.
                -->
                <button
                  ref="closeBtnEl"
                  type="button"
                  class="if-overlay__icon-button"
                  @click="requestClose"
                  aria-label="Close"
                >
                  <FeatherIcon name="x" class="h-4 w-4" />
                </button>
              </div>
            </div>

            <!-- ============================================================
                 BODY (calmer spacing + surfaces)
               ============================================================ -->
            <section class="if-overlay__body custom-scrollbar">
              <!-- Loading -->
              <div v-if="loading" class="py-10 space-y-3">
                <div class="if-skel if-skel--title" />
                <div class="if-skel if-skel--sub" />
                <div class="if-skel h-28 rounded-xl" />
              </div>

              <!-- Error -->
              <div v-else-if="errorText" class="card-panel p-5">
                <p class="type-body-strong text-ink">Couldn’t open this item</p>
                <p class="mt-2 type-body text-ink/70">
                  {{ errorText }}
                </p>

                <div class="mt-5 flex flex-wrap justify-end gap-2">
                  <Button variant="ghost" @click="requestClose">Close</Button>
                  <Button variant="solid" @click="reload">Retry</Button>
                </div>
              </div>

              <div v-else class="space-y-5">
                <StudentLogFollowUpAction
                  v-if="isStudentLogFollowUp && ctx"
                  :focus-item-id="resolvedFocusItemId"
                  :context="ctx"
                  @close="requestClose"
                  @done="onWorkflowDone"
                  @request-refresh="reload"
                />

                <!-- Not implemented -->
                <div v-else class="card-panel p-5">
                  <p class="type-body-strong text-ink">Not supported yet</p>
                  <p class="mt-2 type-body text-ink/70">
                    This focus action type isn’t wired yet:
                    <span class="type-meta">{{ actionType }}</span>
                  </p>

                  <div class="mt-5 flex justify-end">
                    <Button variant="ghost" @click="requestClose">Close</Button>
                  </div>
                </div>
              </div>
            </section>

            <!-- ============================================================
                 FOOTER (keep, just soften)
               ============================================================ -->
            <footer class="if-overlay__footer justify-between">
              <p class="type-caption text-ink/60">
                Focus is a router. Completion happens inside the workflow.
              </p>

              <div class="hidden md:flex items-center gap-2">
                <span class="type-caption" style="color: rgb(var(--slate-rgb) / 0.65)">
                  {{ referenceDoctype }} · {{ referenceName }}
                </span>
              </div>
            </footer>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { Button, FeatherIcon } from 'frappe-ui'

import StudentLogFollowUpAction from '@/components/focus/StudentLogFollowUpAction.vue'
import { createFocusService } from '@/lib/services/focus/focusService'

import type { Request as GetFocusContextRequest, Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context'

/**
 * Props (OverlayHost contract) — A+ ID-only routing
 */
const props = defineProps<{
	open: boolean
	zIndex?: number
	focusItemId?: string | null
}>()

const emit = defineEmits<{
	(e: 'close'): void
	(e: 'after-leave'): void
}>()

/**
 * A+ invariants:
 * - Close must NEVER be blocked by busy states.
 * - Router owns modal lifecycle; workflows own completion.
 * - Router state resets only on after-leave to prevent “flash” on next open.
 *
 * A+ invalidation rule (locked):
 * - Overlays do NOT dispatch custom window events for SPA refresh.
 * - Workflow completion emits uiSignals from the service layer.
 * - Pages subscribe to uiSignals and refresh what they own.
 */
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }))

/**
 * FocusTrap (A+ Option B):
 * - Always provide a stable semantic focus anchor.
 * - Explicitly pass initialFocus to HeadlessUI Dialog to avoid “no focusable elements”
 *   and spurious close events on interaction (especially during transitions).
 */
const closeBtnEl = ref<HTMLButtonElement | null>(null)
const initialFocusEl = computed(() => closeBtnEl.value ?? undefined)

/**
 * Service (A+)
 * - router/view never unwraps Axios-ish shapes
 */
const focusService = createFocusService()

/**
 * State
 */
const loading = ref(false)
const errorText = ref<string | null>(null)
const workflowCompleted = ref(false)

const ctx = ref<GetFocusContextResponse | null>(null)

/* Derived ------------------------------------------------------ */
const actionType = computed(() => (ctx.value?.action_type ?? null) as string | null)
const referenceDoctype = computed(() => ctx.value?.reference_doctype ?? null)
const referenceName = computed(() => ctx.value?.reference_name ?? null)
const studentLogMode = computed<'assignee' | 'author'>(() => (ctx.value?.mode ?? 'assignee') as 'assignee' | 'author')

const resolvedFocusItemId = computed(() => {
	return (ctx.value?.focus_item_id ?? props.focusItemId ?? null) as string | null
})

/* HEADER ------------------------------------------------------- */
const headerTitle = computed(() => {
	if (referenceDoctype.value === 'Student Log') {
		return studentLogMode.value === 'assignee' ? 'Follow up' : 'Review outcome'
	}
	return 'Focus'
})

const headerSubtitle = computed(() => {
	if (referenceDoctype.value && referenceName.value) {
		return `${referenceDoctype.value} • ${referenceName.value}`
	}
	return null
})

const headerKicker = computed(() => {
	if (referenceDoctype.value === 'Student Log') return 'Student wellbeing'
	return 'Focus'
})

/* ROUTING ------------------------------------------------------ */
const isStudentLogFollowUp = computed(() => {
	if (referenceDoctype.value !== 'Student Log') return false
	if (!actionType.value) return false
	return (
		actionType.value === 'student_log.follow_up.act.submit' ||
		actionType.value === 'student_log.follow_up.review.decide'
	)
})

/* API ---------------------------------------------------------- */
function resetState() {
	loading.value = false
	errorText.value = null
	ctx.value = null
	workflowCompleted.value = false
}

function requireFocusItemId(): string {
	const id = String(props.focusItemId || '').trim()
	if (!id) {
		// A+ invariant: ID-only routing. Missing ID is a hard error.
		throw new Error('Missing focus item id. Please reopen from the Focus list.')
	}
	return id
}

function buildContextPayload(): GetFocusContextRequest {
	return { focus_item_id: requireFocusItemId() }
}

async function reload() {
	errorText.value = null
	loading.value = true
	ctx.value = null
	workflowCompleted.value = false

	try {
		const payload = buildContextPayload()
		const result = await focusService.getFocusContext(payload)
		loading.value = false
		errorText.value = null
		ctx.value = (result ?? null) as GetFocusContextResponse | null
	} catch (err: any) {
		loading.value = false
		ctx.value = null
		const msg = err?.message || 'The server refused this request or the item no longer exists.'
		errorText.value = String(msg)
	}
}

function requestClose() {
	emit('close')
}

function emitAfterLeave() {
	resetState()
	emit('after-leave')
}

function onDialogClose() {
	requestClose()
}

/**
 * Workflow completion handler (A+):
 * - Close immediately.
 */
function onWorkflowDone() {
	if (workflowCompleted.value) return
	workflowCompleted.value = true
	requestClose()
}

/**
 * CRITICAL FIX:
 * - When the overlay is first mounted, props.open is already true.
 * - A non-immediate watcher will not fire, so reload() never runs.
 * - Make it immediate so the initial open triggers get_focus_context.
 */
watch(
	() => props.open,
	(next) => {
		if (!next) return
		reload()
	},
	{ immediate: true }
)

watch(
	() => props.focusItemId,
	(next, prev) => {
		if (!props.open) return
		const a = (next || '').trim()
		const b = (prev || '').trim()
		if (a && a !== b) reload()
	}
)
</script>
