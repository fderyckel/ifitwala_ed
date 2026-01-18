<!-- ui-spa/src/overlays/attendance/AttendanceRemarkOverlay.vue -->
<template>
  <TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
    <Dialog
      as="div"
      class="if-overlay if-overlay--attendance-remark"
      :style="overlayStyle"
      :initialFocus="closeBtnEl"
      @close="onDialogClose"
    >
      <TransitionChild
        as="template"
        enter="if-overlay__fade-enter"
        enter-from="if-overlay__fade-from"
        enter-to="if-overlay__fade-to"
        leave="if-overlay__fade-leave"
        leave-from="if-overlay__fade-to"
        leave-to="if-overlay__fade-from"
      >
        <div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
      </TransitionChild>

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
          <DialogPanel class="if-overlay__panel if-overlay__panel--compact">
            <div class="px-6 pt-6">
              <div class="flex items-center justify-between gap-3">
                <DialogTitle class="type-h2 text-ink">
                  {{ __('Remark') }}
                </DialogTitle>
                <button
                  ref="closeBtnEl"
                  type="button"
                  class="if-overlay__icon-button"
                  @click="emitClose('programmatic')"
                  aria-label="Close"
                >
                  <FeatherIcon name="x" class="h-4 w-4" />
                </button>
              </div>

              <p class="mt-2 type-caption text-ink/60">
                {{ helperText }}
              </p>
            </div>

            <div class="if-overlay__body px-6 pb-2">
              <div v-if="contextMissing" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
                <p class="type-body-strong text-rose-900">
                  {{ __('Missing context') }}
                </p>
                <p class="mt-1 type-caption text-rose-900/80">
                  {{ __('Select a student and block before adding a remark.') }}
                </p>
              </div>

              <div v-else class="space-y-3">
                <div class="flex flex-wrap items-center gap-2 text-xs">
                  <span
                    class="inline-flex items-center gap-1 rounded-full bg-[rgb(var(--sky-rgb)/0.9)] px-2.5 py-1 font-medium text-ink/80"
                  >
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-[rgb(var(--leaf-rgb))]" />
                    {{ studentLabel }}
                  </span>
                  <span
                    v-if="studentSecondaryLabel"
                    class="inline-flex items-center gap-1 rounded-full bg-[rgb(var(--sand-rgb)/0.9)] px-2.5 py-1 font-medium text-ink/70"
                  >
                    {{ studentSecondaryLabel }}
                  </span>
                  <span
                    v-if="blockLabel"
                    class="inline-flex items-center gap-1 rounded-full bg-[rgb(var(--sand-rgb)/0.9)] px-2.5 py-1 font-medium text-ink/70"
                  >
                    {{ blockLabel }}
                  </span>
                </div>

                <div
                  class="rounded-2xl border border-[var(--border-light)] bg-[rgb(var(--surface-rgb)/0.98)] p-3 shadow-soft"
                >
                  <textarea
                    ref="textareaRef"
                    v-model="localValue"
                    rows="4"
                    :maxlength="maxLength"
                    class="w-full rounded-xl border border-[var(--border-light)]
                      bg-[rgb(var(--surface-strong-rgb))]
                      px-3 py-2 text-sm text-ink shadow-inner
                      focus-visible:outline-none
                      focus-visible:ring-2
                      focus-visible:ring-[rgb(var(--leaf-rgb)/0.55)]"
                    :placeholder="__('Add a short, specific note (optional)...')"
                  />

                  <div class="mt-2 flex items-center justify-between text-[0.7rem] text-slate-token/60">
                    <p>{{ __("Keep remarks factual, short, and focused on today's context.") }}</p>
                    <p>{{ localValue.length }}/{{ maxLength }}</p>
                  </div>
                </div>
              </div>
            </div>

            <footer class="if-overlay__footer">
              <Button appearance="minimal" @click="emitClose('programmatic')">
                {{ __('Cancel') }}
              </Button>
              <Button appearance="primary" :disabled="contextMissing" @click="save">
                {{ __('Save Remark') }}
              </Button>
            </footer>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { Button, FeatherIcon } from 'frappe-ui'

import { __ } from '@/lib/i18n'
import { useOverlayStack } from '@/composables/useOverlayStack'

type CloseReason = 'backdrop' | 'esc' | 'programmatic'

const props = defineProps<{
  open: boolean
  zIndex?: number
  overlayId?: string
  studentId?: string | null
  studentLabel?: string | null
  studentSecondaryLabel?: string | null
  blockNumber?: number | null
  value?: string | null
  maxLength?: number
  helperText?: string | null
  onSave?: (value: string) => void
}>()

const emit = defineEmits<{
  (e: 'close', reason: CloseReason): void
  (e: 'after-leave'): void
  (e: 'done', payload?: { value: string }): void
}>()

const overlay = useOverlayStack()

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }))
const closeBtnEl = ref<HTMLButtonElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const localValue = ref(props.value ?? '')

const maxLength = computed(() => props.maxLength ?? 255)

const studentLabel = computed(() => props.studentLabel || props.studentId || '')
const studentSecondaryLabel = computed(() => props.studentSecondaryLabel || '')

const contextMissing = computed(() => {
  return !props.studentId || props.blockNumber === null || props.blockNumber === undefined
})

const blockLabel = computed(() => {
  if (props.blockNumber === null || props.blockNumber === undefined) return ''
  if (props.blockNumber === -1) return __('All day')
  return __('Block {0}', [props.blockNumber])
})

const helperText = computed(() => {
  if (props.helperText) return props.helperText
  if (props.blockNumber === -1) return __('Add an optional remark for this student on the selected day.')
  if (props.blockNumber === null || props.blockNumber === undefined) return __('Add a remark once a block is selected.')
  return __('Add an optional remark for block {0}.', [props.blockNumber])
})

function emitClose(reason: CloseReason) {
  const overlayId = props.overlayId || null
  if (overlayId) {
    try {
      overlay.close(overlayId)
      return
    } catch (err) {
      // fall through to emit fallback
    }
  }

  emit('close', reason)
}

function emitAfterLeave() {
  localValue.value = props.value ?? ''
  emit('after-leave')
}

function onDialogClose(_payload: unknown) {
  // no-op by design
}

function save() {
  if (contextMissing.value) return
  const trimmed = (localValue.value || '').trim().slice(0, maxLength.value)
  if (props.onSave) {
    props.onSave(trimmed)
  }
  emit('done', { value: trimmed })
  emitClose('programmatic')
}

function onKeydown(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') emitClose('esc')
}

watch(
  () => [props.open, props.value],
  async ([isOpen, nextValue], [wasOpen]) => {
    if (isOpen && !wasOpen) {
      localValue.value = nextValue ?? ''
      await nextTick()
      textareaRef.value?.focus()
      textareaRef.value?.setSelectionRange(localValue.value.length, localValue.value.length)
    }
    if (!isOpen && wasOpen) {
      localValue.value = nextValue ?? ''
    }
  },
  { immediate: true },
)

onMounted(() => {
  document.addEventListener('keydown', onKeydown, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown, true)
})
</script>
