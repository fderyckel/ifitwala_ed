<!-- ui-spa/src/components/focus/FocusRouterOverlay.vue -->
<template>
  <TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
    <Dialog
      as="div"
      class="if-overlay if-overlay--focus"
      :style="overlayStyle"
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
                 HEADER
                 - FocusRouterOverlay is the single overlay entry point.
                 - It renders a stable header, then mounts workflow-specific body content.
               ============================================================ -->
            <header class="if-overlay__header">
              <div class="min-w-0">
                <p class="type-overline text-slate-token/70">
                  {{ headerKicker }}
                </p>

                <DialogTitle class="type-h2 text-ink truncate">
                  {{ headerTitle }}
                </DialogTitle>

                <p v-if="headerSubtitle" class="mt-1 type-caption text-slate-token/70 truncate">
                  {{ headerSubtitle }}
                </p>
              </div>

              <div class="shrink-0 flex items-center gap-2">
                <Button variant="ghost" class="rounded-full" @click="requestClose">
                  <FeatherIcon name="x" class="h-4 w-4" />
                </Button>
              </div>
            </header>

            <!-- ============================================================
                 BODY
                 - No nested overlays inside FocusRouterOverlay.
                 - Workflow body components must be "content only" components.
               ============================================================ -->
            <section class="if-overlay__body">
              <!-- Loading -->
              <div v-if="loading" class="space-y-3">
                <div class="if-skel if-skel--title" />
                <div class="if-skel if-skel--sub" />
                <div class="if-skel h-28 rounded-xl" />
              </div>

              <!-- Error -->
              <div v-else-if="errorText" class="rounded-2xl border border-slate-200 bg-white p-5">
                <p class="type-body-strong text-ink">Couldn’t open this item</p>
                <p class="mt-2 type-body text-slate-token/75">
                  {{ errorText }}
                </p>
                <div class="mt-4 flex gap-2">
                  <Button variant="solid" @click="reload">Retry</Button>
                  <Button variant="ghost" @click="requestClose">Close</Button>
                </div>
              </div>

              <!-- Routed content -->
              <div v-else>
                <!-- ============================================================
                     Student Log follow-up (Phase 1)
                     - Mount the content-only action component.
                     - It owns its own fetching/actions and tells us when to close.
                   ============================================================ -->
                <StudentLogFollowUpAction
                  v-if="isStudentLogFollowUp"
                  :focus-item-id="props.focusItemId ?? null"
                  :student-log="studentLogName"
                  :mode="studentLogMode"
                  @close="requestClose"
                  @done="noop"
                />

                <!-- Not implemented -->
                <div v-else class="rounded-2xl border border-slate-200 bg-white p-5">
                  <p class="type-body-strong text-ink">Not supported yet</p>
                  <p class="mt-2 type-body text-slate-token/75">
                    This focus action type isn’t wired yet:
                    <span class="type-meta">{{ actionType }}</span>
                  </p>
                  <div class="mt-4">
                    <Button variant="ghost" @click="requestClose">Close</Button>
                  </div>
                </div>
              </div>
            </section>

            <!-- ============================================================
                 FOOTER
                 - Calm reminder: Focus is a router only.
               ============================================================ -->
            <footer class="if-overlay__footer">
              <p class="type-caption text-slate-token/60">
                Focus is a router. Completion happens inside the workflow.
              </p>
            </footer>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { Button, FeatherIcon, createResource } from 'frappe-ui'

import StudentLogFollowUpAction from '@/components/focus/StudentLogFollowUpAction.vue'

type Mode = 'assignee' | 'author'

const props = defineProps<{
  open: boolean
  zIndex?: number
  focusItemId?: string | null
  referenceDoctype?: string | null
  referenceName?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'after-leave'): void
}>()

function noop() {}

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }))

const loading = ref(false)
const errorText = ref<string | null>(null)

// resolved context (from server)
const actionType = ref<string | null>(null)
const referenceDoctype = ref<string | null>(null)
const referenceName = ref<string | null>(null)
const studentLogMode = ref<Mode>('assignee')

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

const studentLogName = computed(() =>
  referenceDoctype.value === 'Student Log' ? referenceName.value ?? null : null
)

/* API: focus.get_context -------------------------------------- */
const ctxResource = createResource({
  url: 'ifitwala_ed.api.focus.get_context',
  method: 'POST',
  auto: false,
  onSuccess(data: any) {
    const payload = data && typeof data === 'object' && 'message' in data ? data.message : data
    loading.value = false
    errorText.value = null

    actionType.value = payload?.action_type ?? null
    referenceDoctype.value = payload?.reference_doctype ?? null
    referenceName.value = payload?.reference_name ?? null

    const mode = (payload?.mode ?? null) as Mode | null
    if (mode === 'assignee' || mode === 'author') {
      studentLogMode.value = mode
    }
  },
  onError(err: any) {
    loading.value = false
    const msg =
      err?.messages?.[0] ||
      err?.message ||
      'The server refused this request or the item no longer exists.'
    errorText.value = String(msg)
  },
})

function reload() {
  errorText.value = null
  loading.value = true

  // v1: prefer focus_item_id if present (deterministic ID)
  // fallback: allow direct doctype/name open for debug
  ctxResource.submit({
    focus_item_id: props.focusItemId ?? null,
    reference_doctype: props.referenceDoctype ?? null,
    reference_name: props.referenceName ?? null,
  })
}

function requestClose() {
  emit('close')
}

function emitAfterLeave() {
  emit('after-leave')
}

function onDialogClose() {
  // OverlayHost controls closeOnBackdrop/closeOnEsc policy.
  // We always comply with Dialog close events by emitting close.
  requestClose()
}

/* LIFECYCLE ---------------------------------------------------- */
onMounted(() => {
  if (props.open) reload()
})

watch(
  () => props.open,
  (next) => {
    if (next) reload()
  }
)
</script>
