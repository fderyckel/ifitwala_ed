<!-- ifitwala_ed/ui-spa/src/components/overlays/class-hub/QuickCFUOverlay.vue -->
<!--
  QuickCFUOverlay.vue
  A specialized overlay for "Check For Understanding" (CFU) entries during a class session.
  Allows capturing signals (Thumbs, etc.) for multiple selected students.

  Used by:
  - ClassHub.vue (via OverlayHost)
-->
<template>
  <TransitionRoot :show="open" as="template" @after-leave="$emit('after-leave')">
    <Dialog as="div" class="if-overlay if-overlay--class-hub" :style="overlayStyle" @close="emitClose">
      <TransitionChild
        as="template"
        enter="if-overlay__fade-enter"
        enter-from="if-overlay__fade-from"
        enter-to="if-overlay__fade-to"
        leave="if-overlay__fade-leave"
        leave-from="if-overlay__fade-to"
        leave-to="if-overlay__fade-from"
      >
        <div class="if-overlay__backdrop" />
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
          <DialogPanel class="if-overlay__panel">
            <div class="if-overlay__header px-6 pt-6">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="type-overline text-slate-token/70">Quick CFU</p>
                  <h2 class="type-h2 text-ink">Check for understanding</h2>
                </div>
                <button
                  type="button"
                  class="if-overlay__icon-button"
                  aria-label="Close"
                  @click="emitClose"
                >
                  <span aria-hidden="true">x</span>
                </button>
              </div>
            </div>

            <div class="if-overlay__body space-y-5">
              <section class="space-y-2">
                <p class="type-caption text-slate-token/70">CFU type</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="option in cfuOptions"
                    :key="option"
                    type="button"
                    class="rounded-full border px-4 py-1 type-button-label"
                    :class="cfuType === option ? 'border-canopy bg-canopy/10 text-canopy' : 'border-slate-200 bg-white text-slate-token/70'"
                    @click="cfuType = option"
                  >
                    {{ option }}
                  </button>
                </div>
              </section>

              <section class="space-y-2">
                <label class="type-caption text-slate-token/70" for="cfu-note">Class note</label>
                <textarea
                  id="cfu-note"
                  v-model="classNote"
                  rows="3"
                  class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 type-body text-ink"
                  placeholder="Capture a quick class note..."
                ></textarea>
              </section>

              <section class="space-y-2">
                <p class="type-caption text-slate-token/70">Apply signal</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="option in signalOptions"
                    :key="option"
                    type="button"
                    class="rounded-full border px-4 py-1 type-button-label"
                    :class="signal === option ? 'border-jacaranda bg-jacaranda/10 text-jacaranda' : 'border-slate-200 bg-white text-slate-token/70'"
                    @click="signal = option"
                  >
                    {{ option }}
                  </button>
                </div>
              </section>

              <section class="space-y-2">
                <p class="type-caption text-slate-token/70">Students</p>
                <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <label
                    v-for="student in students"
                    :key="student.student"
                    class="flex items-center gap-2 rounded-xl border border-slate-200 bg-white/90 px-3 py-2"
                  >
                    <input
                      type="checkbox"
                      class="h-4 w-4"
                      :value="student.student"
                      v-model="selectedStudents"
                    />
                    <span class="type-body text-ink">{{ student.student_name }}</span>
                  </label>
                </div>
              </section>

              <p v-if="errorMessage" class="type-caption text-flame">
                {{ errorMessage }}
              </p>
            </div>

            <div class="if-overlay__footer">
              <button
                type="button"
                class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink"
                @click="emitClose"
              >
                Cancel
              </button>
              <button
                type="button"
                class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
                @click="submit"
              >
                Save CFU
              </button>
            </div>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { createClassHubService } from '@/lib/classHubService'
import type { ClassHubSignal } from '@/types/classHub'

type StudentOption = { student: string; student_name: string }

const props = defineProps<{
  open: boolean
  zIndex?: number
  overlayId?: string | null
  student_group: string
  lesson_instance?: string | null
  students?: StudentOption[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'after-leave'): void
}>()

const service = createClassHubService()

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }))

const cfuOptions = ['Thumbs', 'Mini-whiteboard', 'Exit ticket'] as const
const signalOptions: ClassHubSignal['signal'][] = ['Not Yet', 'Almost', 'Got It', 'Exceeded']

const cfuType = ref<(typeof cfuOptions)[number]>('Thumbs')
const signal = ref<ClassHubSignal['signal'] | ''>('')
const classNote = ref('')
const errorMessage = ref('')

const students = computed(() => props.students || [])
const selectedStudents = ref<string[]>([])

function emitClose() {
  emit('close')
}

async function submit() {
  errorMessage.value = ''

  if (!props.lesson_instance) {
    errorMessage.value = 'Start a session before saving CFU signals.'
    return
  }

  if (!signal.value) {
    errorMessage.value = 'Choose a signal to apply.'
    return
  }

  if (!selectedStudents.value.length) {
    errorMessage.value = 'Select at least one student.'
    return
  }

  const payload: ClassHubSignal[] = selectedStudents.value.map((student) => ({
    student,
    signal: signal.value,
    note: classNote.value.trim() || `CFU: ${cfuType.value}`,
  }))

  try {
    await service.saveSignals(props.lesson_instance, payload)
    emitClose()
  } catch (err) {
    errorMessage.value = 'Unable to save right now.'
    console.error('[QuickCFUOverlay] submit failed', err)
  }
}
</script>
