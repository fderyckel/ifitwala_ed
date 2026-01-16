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
                  <p class="type-overline text-slate-token/70">Student Context</p>
                  <h2 class="type-h2 text-ink">{{ student_name }}</h2>
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
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="tab in tabs"
                  :key="tab"
                  type="button"
                  class="rounded-full border px-4 py-1 type-button-label"
                  :class="activeTab === tab ? 'border-jacaranda bg-jacaranda/10 text-jacaranda' : 'border-slate-200 bg-white text-slate-token/70'"
                  @click="activeTab = tab"
                >
                  {{ tab }}
                </button>
              </div>

              <section v-if="activeTab === 'Snapshot'" class="space-y-4">
                <div class="space-y-2">
                  <p class="type-caption text-slate-token/70">Signal</p>
                  <div class="flex flex-wrap gap-2">
                    <button
                      v-for="option in signalOptions"
                      :key="option"
                      type="button"
                      class="rounded-full border px-4 py-1 type-button-label"
                      :class="signal === option ? 'border-canopy bg-canopy/10 text-canopy' : 'border-slate-200 bg-white text-slate-token/70'"
                      @click="signal = option"
                    >
                      {{ option }}
                    </button>
                  </div>
                </div>

                <div class="space-y-2">
                  <label class="type-caption text-slate-token/70" for="snapshot-note">Quick note</label>
                  <textarea
                    id="snapshot-note"
                    v-model="snapshotNote"
                    rows="3"
                    class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 type-body text-ink"
                    placeholder="Add a quick note..."
                  ></textarea>
                </div>

                <p v-if="errorMessage" class="type-caption text-flame">
                  {{ errorMessage }}
                </p>

                <button
                  type="button"
                  class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
                  @click="saveSnapshot"
                >
                  Save snapshot
                </button>
              </section>

              <section v-else-if="activeTab === 'Evidence'" class="space-y-4">
                <div class="rounded-xl border border-slate-200 bg-white/90 px-4 py-4">
                  <p class="type-body text-slate-token/70">No evidence recorded yet for this session.</p>
                </div>
                <button
                  type="button"
                  class="rounded-full border border-slate-200 bg-white px-5 py-2 type-button-label text-ink shadow-sm hover:border-jacaranda/60"
                  @click="openQuickEvidence"
                >
                  Add evidence
                </button>
              </section>

              <section v-else class="space-y-4">
                <div class="space-y-2">
                  <label class="type-caption text-slate-token/70" for="teacher-note">Teacher note</label>
                  <textarea
                    id="teacher-note"
                    v-model="teacherNote"
                    rows="4"
                    class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 type-body text-ink"
                    placeholder="Capture a quick note for later."
                  ></textarea>
                </div>
                <p v-if="noteMessage" class="type-caption text-flame">
                  {{ noteMessage }}
                </p>
                <button
                  type="button"
                  class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
                  @click="saveNote"
                >
                  Save note
                </button>
              </section>
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
import { useOverlayStack } from '@/composables/useOverlayStack'
import { createClassHubService } from '@/lib/classHubService'
import type { ClassHubSignal } from '@/types/classHub'

const props = defineProps<{
  open: boolean
  zIndex?: number
  overlayId?: string | null
  student: string
  student_name: string
  student_group: string
  lesson_instance?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'after-leave'): void
}>()

const overlay = useOverlayStack()
const service = createClassHubService()

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }))

const tabs = ['Snapshot', 'Evidence', 'Notes'] as const
const activeTab = ref<(typeof tabs)[number]>('Snapshot')

const signalOptions: ClassHubSignal['signal'][] = ['Not Yet', 'Almost', 'Got It', 'Exceeded']
const signal = ref<ClassHubSignal['signal'] | ''>('')
const snapshotNote = ref('')
const teacherNote = ref('')
const errorMessage = ref('')
const noteMessage = ref('')

function emitClose() {
  emit('close')
}

async function saveSnapshot() {
  errorMessage.value = ''
  if (!props.lesson_instance) {
    errorMessage.value = 'Start a session before saving snapshots.'
    return
  }
  if (!signal.value) {
    errorMessage.value = 'Choose a signal before saving.'
    return
  }

  const payload: ClassHubSignal[] = [
    {
      student: props.student,
      signal: signal.value,
      note: snapshotNote.value.trim() || null,
    },
  ]

  try {
    await service.saveSignals(props.lesson_instance, payload)
    emitClose()
  } catch (err) {
    errorMessage.value = 'Unable to save right now.'
    console.error('[StudentContextOverlay] saveSnapshot failed', err)
  }
}

function openQuickEvidence() {
  overlay.replaceTop('class-hub-quick-evidence', {
    student_group: props.student_group,
    lesson_instance: props.lesson_instance ?? null,
    preselected_students: [
      {
        student: props.student,
        student_name: props.student_name,
      },
    ],
  })
}

async function saveNote() {
  noteMessage.value = ''
  if (!teacherNote.value.trim()) {
    noteMessage.value = 'Add a note before saving.'
    return
  }

  try {
    await service.quickEvidence({
      student_group: props.student_group,
      lesson_instance: props.lesson_instance ?? null,
      students: [props.student],
      evidence_type: 'text',
      text: teacherNote.value.trim(),
    })
    emitClose()
  } catch (err) {
    noteMessage.value = 'Unable to save right now.'
    console.error('[StudentContextOverlay] saveNote failed', err)
  }
}
</script>
