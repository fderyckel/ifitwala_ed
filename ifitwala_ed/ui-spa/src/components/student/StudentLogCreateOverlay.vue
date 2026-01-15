<!-- ui-spa/src/components/student/StudentLogCreateOverlay.vue -->
<template>
  <TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
    <Dialog as="div" class="if-overlay if-overlay--student-log" :style="overlayStyle" @close="emitClose">
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
            <!-- Header -->
            <div class="if-overlay__header px-6 pt-6">
              <div class="min-w-0">
                <DialogTitle class="type-h2 text-ink">
                  {{ step === 'review' ? __('Review student note') : __('New student note') }}
                </DialogTitle>
                <p class="mt-1 type-caption text-ink/60">
                  {{
                    step === 'review'
                      ? __('Once submitted, this note cannot be edited.')
                      : (mode === 'group' ? __('Fast entry for this class.') : __('Search across your school.'))
                  }}
                </p>
              </div>

              <button type="button" class="if-overlay__close" @click="emitClose" aria-label="Close">
                <FeatherIcon name="x" class="h-5 w-5" />
              </button>
            </div>

            <!-- Body -->
            <div class="if-overlay__body px-6 pb-6 space-y-5">
              <!-- EDIT STEP -->
              <template v-if="step !== 'review'">
                <!-- Student -->
                <section class="space-y-2">
                  <p class="type-caption text-ink/70">{{ __('Student') }}</p>

                  <!-- Group mode: roster select -->
                  <div v-if="mode === 'group'" class="space-y-2">
                    <FormControl
                      type="select"
                      size="md"
                      :options="groupStudentOptions"
                      option-label="label"
                      option-value="value"
                      :model-value="form.student"
                      :disabled="!groupStudentOptions.length || submitting"
                      placeholder="Select student"
                      @update:modelValue="onStudentSelected"
                    />
                  </div>

                  <!-- School mode: search OR selected card -->
                  <div v-else class="space-y-2">
                    <!-- Search UI: only when no student selected -->
                    <div v-if="!form.student" class="space-y-2">
                      <FormControl
                        type="text"
                        size="md"
                        :model-value="studentQuery"
                        :disabled="submitting"
                        placeholder="Search student name…"
                        @update:modelValue="onStudentQuery"
                      />

                      <div v-if="studentSearch.loading" class="flex items-center gap-2 text-ink/60">
                        <Spinner class="h-4 w-4" />
                        <span class="type-caption">{{ __('Searching…') }}</span>
                      </div>

                      <div
                        v-if="studentCandidates.length"
                        class="rounded-2xl border border-border/70 bg-white shadow-soft overflow-hidden"
                      >
                        <button
                          v-for="c in studentCandidates"
                          :key="c.value"
                          type="button"
                          class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-sky/30 transition"
                          @click="onStudentSelected(c.value)"
                        >
                          <img
                            v-if="c.image"
                            :src="c.image"
                            alt=""
                            class="h-9 w-9 rounded-full object-cover ring-1 ring-black/5"
                            loading="lazy"
                            decoding="async"
                          />
                          <div class="min-w-0 flex-1">
                            <p class="type-body-strong text-ink truncate">{{ c.label }}</p>
                            <p class="type-caption text-ink/55 truncate">{{ c.meta }}</p>
                          </div>
                          <FeatherIcon name="chevron-right" class="h-4 w-4 text-ink/40" />
                        </button>
                      </div>
                    </div>

                    <!-- Selected student card: replaces search UI -->
                    <div
                      v-else
                      class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft flex items-center justify-between gap-3"
                    >
                      <div class="flex items-center gap-3 min-w-0">
                        <img
                          v-if="selectedStudentImage"
                          :src="selectedStudentImage"
                          alt=""
                          class="h-10 w-10 rounded-full object-cover ring-1 ring-black/5"
                          loading="lazy"
                          decoding="async"
                        />
                        <div class="min-w-0">
                          <p class="type-body-strong text-ink truncate">{{ selectedStudentLabel }}</p>
                          <p v-if="selectedStudentMeta" class="type-caption text-ink/55 truncate">
                            {{ selectedStudentMeta }}
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        class="type-caption text-ink/70 hover:text-ink underline underline-offset-4"
                        :disabled="submitting"
                        @click="changeStudent()"
                      >
                        {{ __('Change') }}
                      </button>
                    </div>
                  </div>
                </section>

                <!-- Type -->
                <section class="space-y-2">
                  <div class="flex items-center justify-between">
                    <p class="type-caption text-ink/70">{{ __('Type') }}</p>
                    <span v-if="options.loading" class="type-caption text-ink/55 flex items-center gap-2">
                      <Spinner class="h-4 w-4" /> {{ __('Loading…') }}
                    </span>
                  </div>

                  <FormControl
                    type="select"
                    size="md"
                    :options="logTypeOptions"
                    option-label="label"
                    option-value="value"
                    :model-value="form.log_type"
                    :disabled="!form.student || options.loading || submitting"
                    placeholder="Select type"
                    @update:modelValue="(v) => (form.log_type = v)"
                  />
                </section>

                <!-- Note -->
                <section class="space-y-2">
                  <p class="type-caption text-ink/70">{{ __('Note') }}</p>
                  <textarea
                    v-model="form.log"
                    class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
                    rows="6"
                    :placeholder="__('Write what you observed…')"
                    :disabled="submitting"
                  />
                </section>

                <!-- Visibility (defaults OFF in SPA) -->
                <section class="space-y-2">
                  <p class="type-caption text-ink/70">{{ __('Visibility') }}</p>

                  <div class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <label class="flex gap-3 rounded-xl border border-border/60 bg-white px-3 py-3 hover:bg-sky/20 transition">
                        <input
                          v-model="form.visible_to_student"
                          type="checkbox"
                          class="mt-1 h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
                          :disabled="submitting"
                        />
                        <div class="min-w-0">
                          <p class="type-body-strong text-ink">{{ __('Visible to student') }}</p>
                          <p class="type-caption text-ink/55">{{ __('Show this note in the student portal.') }}</p>
                        </div>
                      </label>

                      <label class="flex gap-3 rounded-xl border border-border/60 bg-white px-3 py-3 hover:bg-sky/20 transition">
                        <input
                          v-model="form.visible_to_guardians"
                          type="checkbox"
                          class="mt-1 h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
                          :disabled="submitting"
                        />
                        <div class="min-w-0">
                          <p class="type-body-strong text-ink">{{ __('Visible to parents') }}</p>
                          <p class="type-caption text-ink/55">{{ __('Show this note in the guardian portal.') }}</p>
                        </div>
                      </label>
                    </div>
                  </div>
                </section>

                <!-- Follow-up -->
                <section class="space-y-2">
                  <p class="type-caption text-ink/70">{{ __('Follow-up') }}</p>

                  <div class="rounded-2xl border border-border/70 bg-white px-4 py-3 shadow-soft space-y-3">
                    <label class="flex items-start gap-3">
                      <input
                        v-model="form.requires_follow_up"
                        type="checkbox"
                        class="mt-1 h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
                        :disabled="submitting || !form.student"
                      />
                      <div class="min-w-0">
                        <p class="type-body-strong text-ink">{{ __('Needs follow-up') }}</p>
                        <p class="type-caption text-ink/55">{{ __('Assign this note to someone else, with a clear next step.') }}</p>
                      </div>
                    </label>

                    <div v-if="form.requires_follow_up" class="space-y-3 pt-1">
                      <FormControl
                        type="select"
                        size="md"
                        :options="nextStepOptions"
                        option-label="label"
                        option-value="value"
                        :model-value="form.next_step"
                        :disabled="submitting || options.loading"
                        placeholder="Select next step"
                        @update:modelValue="onNextStepSelected"
                      />

                      <div v-if="followUpRoleHint" class="type-caption text-ink/55">
                        {{ followUpRoleHint }}
                      </div>

                      <FormControl
                        type="text"
                        size="md"
                        :model-value="assigneeQuery"
                        :disabled="submitting || !form.next_step"
                        placeholder="Search staff to assign…"
                        @update:modelValue="onAssigneeQuery"
                      />

                      <div v-if="assigneeSearch.loading" class="flex items-center gap-2 text-ink/60">
                        <Spinner class="h-4 w-4" />
                        <span class="type-caption">{{ __('Searching…') }}</span>
                      </div>

                      <div
                        v-if="assigneeCandidates.length"
                        class="rounded-2xl border border-border/70 bg-[rgb(var(--surface-strong-rgb))] overflow-hidden"
                      >
                        <button
                          v-for="u in assigneeCandidates"
                          :key="u.value"
                          type="button"
                          class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-sky/30 transition"
                          @click="selectAssignee(u.value, u.label)"
                        >
                          <div class="min-w-0">
                            <p class="type-body-strong text-ink truncate">{{ u.label }}</p>
                            <p class="type-caption text-ink/55 truncate">{{ u.meta }}</p>
                          </div>
                          <FeatherIcon name="check" class="h-4 w-4 text-leaf" v-if="form.follow_up_person === u.value" />
                        </button>
                      </div>

                      <div v-if="selectedAssigneeLabel" class="type-caption text-ink/60">
                        {{ __('Assigned to:') }} <span class="text-ink">{{ selectedAssigneeLabel }}</span>
                      </div>
                    </div>
                  </div>
                </section>
              </template>

              <!-- REVIEW STEP -->
              <template v-else>
                <section class="space-y-3">
                  <div class="rounded-2xl border border-border/70 bg-white px-5 py-4 shadow-soft space-y-4">
                    <!-- Student + Type -->
                    <div class="flex items-start justify-between gap-4">
                      <div class="min-w-0">
                        <p class="type-caption text-ink/55">{{ __('Student') }}</p>
                        <div class="mt-1 flex items-center gap-3 min-w-0">
                          <img
                            v-if="selectedStudentImage"
                            :src="selectedStudentImage"
                            alt=""
                            class="h-10 w-10 rounded-full object-cover ring-1 ring-black/5"
                            loading="lazy"
                            decoding="async"
                          />
                          <div class="min-w-0">
                            <p class="type-body-strong text-ink truncate">{{ selectedStudentLabel || form.student }}</p>
                            <p v-if="selectedStudentMeta" class="type-caption text-ink/55 truncate">{{ selectedStudentMeta }}</p>
                          </div>
                        </div>
                      </div>

                      <div class="text-right shrink-0">
                        <p class="type-caption text-ink/55">{{ __('Type') }}</p>
                        <p class="mt-1 type-body-strong text-ink">
                          {{ selectedLogTypeLabel || form.log_type || '—' }}
                        </p>
                      </div>
                    </div>

                    <!-- Note preview -->
                    <div class="space-y-1">
                      <p class="type-caption text-ink/55">{{ __('Note') }}</p>
                      <div class="rounded-xl border border-border/60 bg-[rgb(var(--surface-strong-rgb))] px-4 py-3">
                        <p class="text-sm text-ink/90 whitespace-pre-wrap">
                          {{ reviewNotePreview || '—' }}
                        </p>
                      </div>
                      <p v-if="isNoteTruncated" class="type-caption text-ink/55">
                        {{ __('Preview truncated. Go back to edit to review full text.') }}
                      </p>
                    </div>

                    <!-- Visibility + Follow-up summary -->
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div class="rounded-xl border border-border/60 bg-white px-4 py-3">
                        <p class="type-caption text-ink/55">{{ __('Visibility') }}</p>
                        <ul class="mt-2 space-y-1 text-sm text-ink/85">
                          <li class="flex items-center justify-between gap-3">
                            <span class="text-ink/70">{{ __('Student') }}</span>
                            <span class="type-body-strong text-ink">{{ form.visible_to_student ? __('Yes') : __('No') }}</span>
                          </li>
                          <li class="flex items-center justify-between gap-3">
                            <span class="text-ink/70">{{ __('Parents') }}</span>
                            <span class="type-body-strong text-ink">{{ form.visible_to_guardians ? __('Yes') : __('No') }}</span>
                          </li>
                        </ul>
                      </div>

                      <div class="rounded-xl border border-border/60 bg-white px-4 py-3">
                        <p class="type-caption text-ink/55">{{ __('Follow-up') }}</p>
                        <div class="mt-2 text-sm text-ink/85 space-y-1">
                          <p>
                            <span class="text-ink/70">{{ __('Needs follow-up') }}:</span>
                            <span class="type-body-strong text-ink ml-1">{{ form.requires_follow_up ? __('Yes') : __('No') }}</span>
                          </p>
                          <p v-if="form.requires_follow_up">
                            <span class="text-ink/70">{{ __('Next step') }}:</span>
                            <span class="type-body-strong text-ink ml-1">{{ selectedNextStepLabel || form.next_step || '—' }}</span>
                          </p>
                          <p v-if="form.requires_follow_up">
                            <span class="text-ink/70">{{ __('Assigned to') }}:</span>
                            <span class="type-body-strong text-ink ml-1">{{ selectedAssigneeLabel || form.follow_up_person || '—' }}</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </template>
            </div>

						<!-- Footer -->
						<div class="if-overlay__footer">
							<!-- EDIT FOOTER -->
							<div v-if="step !== 'review'" class="w-full flex flex-col items-stretch gap-2">
								<Button
									variant="solid"
									class="w-full"
									:loading="submitting"
									:disabled="!canSubmit || submitting"
									@click="goReview"
								>
									<template #prefix><FeatherIcon name="eye" class="h-4 w-4" /></template>
									{{ __('Review & submit') }}
								</Button>

								<p class="type-caption text-ink/50 whitespace-normal leading-snug">
									{{ footerHint }}
								</p>
							</div>

							<!-- REVIEW FOOTER -->
							<div v-else class="w-full flex flex-col gap-3">
								<div class="flex items-center gap-3">
									<Button variant="outline" class="flex-1" :disabled="submitting" @click="goEdit">
										<template #prefix><FeatherIcon name="edit-2" class="h-4 w-4" /></template>
										{{ __('Go back and edit') }}
									</Button>

									<Button
										variant="solid"
										class="flex-1"
										:loading="submitting"
										:disabled="!canSubmit || submitting"
										@click="submit"
									>
										<template #prefix><FeatherIcon name="send" class="h-4 w-4" /></template>
										{{ __('Confirm & submit') }}
									</Button>
								</div>

								<p class="type-caption text-ink/50 whitespace-normal leading-snug">
									{{ __('Submitting will create a new student log entry. You won’t be able to edit it afterwards.') }}
								</p>
							</div>
						</div>


          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { Button, FormControl, FeatherIcon, Spinner, toast, createResource } from 'frappe-ui'
import { __ } from '@/lib/i18n'
import { useOverlayStack } from '@/composables/useOverlayStack'

type Mode = 'group' | 'school'

type GroupStudent = {
  student: string
  student_name?: string | null
  preferred_name?: string | null
  student_image?: string | null
}

type PickerItem = {
  value: string
  label: string
  image?: string | null
  meta?: string | null
}

const props = defineProps<{
  open: boolean
  zIndex?: number
  mode: Mode
  // in 'group' mode:
  studentGroup?: string | null
  students?: GroupStudent[] | null
  overlayId?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'after-leave'): void
}>()

const overlay = useOverlayStack()

type ToastPayload = Parameters<typeof toast>[0]

function showToast(payload: ToastPayload) {
  if (typeof toast !== 'function') {
    console.warn('[StudentLogCreateOverlay] toast is unavailable', payload)
    return
  }
  try {
    toast(payload)
  } catch (err) {
    console.error('[StudentLogCreateOverlay] toast failed', err, payload)
  }
}

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }))

// Review step state
const step = ref<'edit' | 'review'>('edit')

const NOTE_PREVIEW_LEN = 220

const reviewNotePreview = computed(() => {
	const txt = (form.log || '').trim()
	if (!txt) return ''
	return txt.length > NOTE_PREVIEW_LEN ? txt.slice(0, NOTE_PREVIEW_LEN).trim() + '…' : txt
})

const isNoteTruncated = computed(() => {
	const txt = (form.log || '').trim()
	return !!txt && txt.length > NOTE_PREVIEW_LEN
})

const selectedLogTypeLabel = computed(() => {
	if (!form.log_type) return ''
	const row = logTypeOptions.value.find((x) => x.value === form.log_type)
	return row?.label || ''
})

const selectedNextStepLabel = computed(() => {
	if (!form.next_step) return ''
	const row = nextStepOptions.value.find((x) => x.value === form.next_step)
	return row?.label || ''
})


function emitClose() {
	const overlayId = props.overlayId || null
	if (overlayId) {
		try {
			if (typeof overlay.close === 'function') {
				overlay.close(overlayId)
				return
			}
		} catch (err) {
			// fall through to stack mutation/emit fallback
		}

		if (overlay?.state?.stack) {
			overlay.state.stack = overlay.state.stack.filter((e) => e.id !== overlayId)
			return
		}
	}

	emit('close')
}

function emitAfterLeave() {
	step.value = 'edit'
	emit('after-leave')
}

function goReview() {
	if (!canSubmit.value) return
	step.value = 'review'
}

function goEdit() {
	step.value = 'edit'
}


const mode = computed(() => props.mode)

const submitting = ref(false)

const form = reactive({
  student: '' as string,
  log_type: '' as string,
  log: '' as string,
  requires_follow_up: false,
  next_step: '' as string,
  follow_up_person: '' as string,
  // ✅ SPA safety defaults (override DocType defaults)
  visible_to_student: false,
  visible_to_guardians: false,
})

const selectedStudentLabel = ref('')
const selectedStudentImage = ref<string | null>(null)
const selectedStudentMeta = ref<string | null>(null)

const footerHint = computed(() => {
  if (!form.student) return __('Select a student first.')
  if (!form.log_type) return __('Choose a note type.')
  if (!form.log.trim()) return __('Write a short note.')
  if (form.requires_follow_up && !form.next_step) return __('Choose a next step.')
  if (form.requires_follow_up && !form.follow_up_person) return __('Assign the follow-up to someone.')
  return __('Saved immediately. For changes, add a clarification note later.')
})

const canSubmit = computed(() => {
  if (!form.student || !form.log_type || !form.log.trim()) return false
  if (form.requires_follow_up) {
    if (!form.next_step) return false
    if (!form.follow_up_person) return false
  }
  return true
})

/* Group student options */
const groupStudentOptions = computed(() => {
  const list = props.students || []
  return list.map((s) => {
    const name = (s.preferred_name || s.student_name || '').trim()
    return { value: s.student, label: name || s.student }
  })
})

function _getGroupStudentMeta(id: string) {
  const s = (props.students || []).find((x) => x.student === id)
  if (!s) return { label: id, image: null as string | null, meta: null as string | null }
  const display = (s.preferred_name || s.student_name || id).trim()
  const meta = s.preferred_name && s.student_name ? s.student_name : null
  return { label: display, image: s.student_image || null, meta }
}

/* Student search (school-scoped server-side using current user's Employee.school) */
const studentQuery = ref('')
const studentCandidates = ref<PickerItem[]>([])

const studentSearch = createResource({
  url: 'ifitwala_ed.api.student_log.search_students',
  auto: false,
  onSuccess(data: any) {
    studentCandidates.value = (data || []).map((x: any) => ({
      value: x.student,
      label: x.label,
      image: x.image || null,
      meta: x.meta || null,
    }))
  },
  onError(err: any) {
    showToast({ title: __('Could not search students'), text: err?.message || String(err), icon: 'x' })
  },
})

function onStudentQuery(v: string) {
  studentQuery.value = v
  if (!v || v.trim().length < 2) {
    studentCandidates.value = []
    return
  }
  studentSearch.submit({ query: v.trim(), limit: 10 })
}

/* Form options (log types + next steps, derived from selected student) */
const options = createResource({
  url: 'ifitwala_ed.api.student_log.get_form_options',
  auto: false,
  onError(err: any) {
    showToast({ title: __('Could not load options'), text: err?.message || String(err), icon: 'x' })
  },
})

const logTypeOptions = computed(() => (options.data?.log_types || []) as { value: string; label: string }[])
const nextStepOptions = computed(() => (options.data?.next_steps || []) as { value: string; label: string; role?: string | null }[])

const followUpRoleHint = computed(() => {
  if (!form.next_step) return ''
  const row = nextStepOptions.value.find((x) => x.value === form.next_step)
  const role = row?.role
  if (!role) return __('Assignee will be filtered by role.')
  return `${__('Assignee role:')} ${role}`
})

/* Assignee search */
const assigneeQuery = ref('')
const assigneeCandidates = ref<{ value: string; label: string; meta?: string | null }[]>([])
const selectedAssigneeLabel = ref('')

const assigneeSearch = createResource({
  url: 'ifitwala_ed.api.student_log.search_follow_up_users',
  auto: false,
  onSuccess(data: any) {
    assigneeCandidates.value = (data || []).map((x: any) => ({
      value: x.value,
      label: x.label,
      meta: x.meta || null,
    }))
  },
  onError(err: any) {
    showToast({ title: __('Could not search staff'), text: err?.message || String(err), icon: 'x' })
  },
})

function onAssigneeQuery(v: string) {
  assigneeQuery.value = v
  if (!form.next_step) return

  // ✅ updated API supports dropdown mode when query is empty:
  // - empty/short query => keep current list (already loaded)
  // - 2+ chars => filtered search
  if (!v || v.trim().length < 2) {
    return
  }

  assigneeSearch.submit({
    next_step: form.next_step,
    student: form.student,
    query: v.trim(),
    limit: 50,
  })
}

function selectAssignee(user: string, label: string) {
  form.follow_up_person = user
  selectedAssigneeLabel.value = label
  assigneeCandidates.value = []
  assigneeQuery.value = label
}

/* Student selection */
function onStudentSelected(studentId: string) {
	// capture selection meta BEFORE we clear candidates (school mode)
	const picked =
		mode.value === 'school'
			? studentCandidates.value.find((x) => x.value === studentId)
			: null

	form.student = studentId

	// reset dependent fields
	form.log_type = ''
	form.next_step = ''
	form.follow_up_person = ''
	selectedAssigneeLabel.value = ''
	assigneeQuery.value = ''
	assigneeCandidates.value = []

	// clear student search UI
	studentCandidates.value = []
	studentQuery.value = ''

	// fill UI meta
	if (mode.value === 'group') {
		const m = _getGroupStudentMeta(studentId)
		selectedStudentLabel.value = m.label
		selectedStudentImage.value = m.image
		selectedStudentMeta.value = m.meta
	} else {
		selectedStudentLabel.value = picked?.label || studentId
		selectedStudentImage.value = picked?.image || null
		selectedStudentMeta.value = picked?.meta || null
	}

	// load dependent options (types + next steps)
	options.submit({ student: studentId })
}

function changeStudent() {
	step.value = 'edit'

	// Clear student selection + anything that depends on student/options
	form.student = ''

	form.log_type = ''
	form.requires_follow_up = false
	form.next_step = ''
	form.follow_up_person = ''

	// Assignee UI state
	selectedAssigneeLabel.value = ''
	assigneeQuery.value = ''
	assigneeCandidates.value = []

	// Student search UI state
	studentQuery.value = ''
	studentCandidates.value = []

	// Selected student UI meta
	selectedStudentLabel.value = ''
	selectedStudentImage.value = null
	selectedStudentMeta.value = null

	// Clear options payload so selects don't show stale options
	options.data = null as any
}


function onNextStepSelected(v: string) {
  form.next_step = v
  form.follow_up_person = ''
  selectedAssigneeLabel.value = ''
  assigneeQuery.value = ''
  assigneeCandidates.value = []

  // ✅ NEW: preload dropdown list (no typing required) using updated API behavior
  if (form.next_step && form.student) {
    assigneeSearch.submit({
      next_step: form.next_step,
      student: form.student,
      query: '',
      limit: 50,
    })
  }
}

/* Submit (Option A: toast + close) */
const submitResource = createResource({
  url: 'ifitwala_ed.api.student_log.submit_student_log',
  auto: false,
	onSuccess() {
		emitClose()
		showToast({ title: __('Saved'), text: __('Student note submitted.'), icon: 'check' })
	},
  onError(err: any) {
    console.error('[StudentLogCreateOverlay] submit:error', err)
    showToast({ title: __('Could not submit'), text: err?.message || String(err), icon: 'x' })
  },
})

async function submit() {
	if (!canSubmit.value) return

	// Only allow actual server submit from the review step.
	// If user triggers submit while editing (e.g. Enter), push them to review instead.
	if (step.value !== 'review') {
		step.value = 'review'
		return
	}

	submitting.value = true
	try {
		await submitResource.submit({
			student: form.student,
			log_type: form.log_type,
			log: form.log,
			requires_follow_up: form.requires_follow_up ? 1 : 0,
			next_step: form.requires_follow_up ? form.next_step : null,
			follow_up_person: form.requires_follow_up ? form.follow_up_person : null,
			visible_to_student: form.visible_to_student ? 1 : 0,
			visible_to_guardians: form.visible_to_guardians ? 1 : 0,
		})
	} finally {
		submitting.value = false
	}
}

</script>
