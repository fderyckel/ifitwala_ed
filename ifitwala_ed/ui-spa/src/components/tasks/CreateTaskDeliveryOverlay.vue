<!-- ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue -->
<template>
	<TransitionRoot
		as="template"
		:show="open"
		@after-leave="emitAfterLeave"
	>
    <Dialog as="div" class="if-overlay" :style="{ zIndex }" :initialFocus="initialFocus" @close="handleClose">
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
            <button
              ref="initialFocus"
              type="button"
              class="sr-only"
              aria-hidden="true"
              tabindex="0"
              @click="handleClose"
            >
              Close
            </button>
            <!-- Header -->
            <div class="flex items-start justify-between gap-3 px-5 pt-5">
              <div>
                <p class="type-overline">Task</p>
                <DialogTitle class="type-h3 text-ink mt-1">Create task</DialogTitle>
              </div>

              <button
                type="button"
                class="if-overlay__icon-button"
                aria-label="Close"
                @click="handleClose"
              >
                <FeatherIcon name="x" class="h-5 w-5" />
              </button>
            </div>

            <!-- Body -->
            <div class="if-overlay__body">
              <div class="space-y-6">
                <!-- Step 1 -->
                <section class="card-panel space-y-4 p-5">
                  <div class="flex items-center gap-3">
                    <span class="chip">Step 1</span>
                    <h3 class="type-h3 text-ink">What are you giving students?</h3>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <div class="space-y-1">
                      <label class="type-label">Title</label>
                      <FormControl v-model="form.title" type="text" placeholder="Assignment title" />
                    </div>
                    <div class="space-y-1">
                      <label class="type-label">Type</label>
                      <FormControl
                        v-model="form.task_type"
                        type="select"
                        :options="taskTypeOptions"
                        option-label="label"
                        option-value="value"
                        placeholder="Select type (optional)"
                      />
                    </div>
                  </div>

                  <div class="space-y-1">
                    <label class="type-label">Instructions</label>
                    <FormControl
                      v-model="form.instructions"
                      type="textarea"
                      :rows="4"
                      placeholder="Share directions, resources, or expectations..."
                    />
                  </div>
                </section>

                <!-- Step 2 -->
                <section class="card-panel space-y-4 p-5">
                  <div class="flex items-center gap-3">
                    <span class="chip">Step 2</span>
                    <h3 class="type-h3 text-ink">Which class?</h3>
                  </div>

                  <div class="space-y-1">
                    <label class="type-label">Class</label>

                    <div
                      v-if="isGroupLocked"
                      class="rounded-xl border border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/80"
                    >
                      {{ selectedGroupLabel || props.prefillStudentGroup || 'Class selected' }}
                    </div>

                    <FormControl
                      v-else
                      v-model="form.student_group"
                      type="select"
                      :options="groupOptions"
                      option-label="label"
                      option-value="value"
                      :disabled="groupsLoading"
                      placeholder="Select a class"
                    />

                    <p v-if="!groupsLoading && !groupOptions.length" class="type-caption text-slate-token/70">
                      No classes available for your role yet.
                    </p>
                  </div>
                </section>

                <!-- Step 3 -->
                <section class="card-panel space-y-4 p-5">
                  <div class="flex items-center gap-3">
                    <span class="chip">Step 3</span>
                    <h3 class="type-h3 text-ink">What will happen?</h3>
                  </div>

                  <div class="grid gap-3 md:grid-cols-3">
                    <button
                      v-for="option in deliveryOptions"
                      :key="option.value"
                      type="button"
                      class="rounded-2xl border px-4 py-4 text-left transition"
                      :class="form.delivery_mode === option.value
                        ? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
                        : 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'"
                      @click="form.delivery_mode = option.value"
                    >
                      <p class="text-sm font-semibold text-ink">{{ option.label }}</p>
                      <p class="mt-1 text-xs text-ink/60">{{ option.help }}</p>
                    </button>
                  </div>
                </section>

                <!-- Step 4 -->
                <section class="card-panel space-y-4 p-5">
                  <div class="flex items-center gap-3">
                    <span class="chip">Step 4</span>
                    <h3 class="type-h3 text-ink">Dates</h3>
                  </div>

                  <div class="grid gap-4 md:grid-cols-3">
                    <div class="space-y-1">
                      <label class="type-label">Available from</label>
                      <input
                        v-model="form.available_from"
                        type="datetime-local"
                        class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
                      />
                    </div>
                    <div class="space-y-1">
                      <label class="type-label">Due date</label>
                      <input
                        v-model="form.due_date"
                        type="datetime-local"
                        class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
                      />
                    </div>
                    <div class="space-y-1">
                      <label class="type-label">Lock date</label>
                      <input
                        v-model="form.lock_date"
                        type="datetime-local"
                        class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
                      />
                    </div>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
										<label v-if="showLateSubmission" class="flex items-center gap-2 text-sm text-ink/80">
											<input v-model="form.allow_late_submission" type="checkbox" class="rounded border-border/70 text-jacaranda" />
											Allow late submissions
										</label>
                    <label class="flex items-center gap-2 text-sm text-ink/80">
                      <input v-model="form.group_submission" type="checkbox" class="rounded border-border/70 text-jacaranda" />
                      Group submission
                    </label>
                  </div>
                </section>

                <!-- Step 5 -->
                <section class="card-panel space-y-4 p-5">
                  <div class="flex items-center gap-3">
                    <span class="chip">Step 5</span>
                    <h3 class="type-h3 text-ink">Grading (optional)</h3>
                  </div>

                  <div class="space-y-2">
                    <p class="type-label">Will you assess it?</p>
                    <div class="flex flex-wrap gap-2">
                      <button
                        type="button"
                        class="rounded-full border px-4 py-2 text-sm font-medium transition"
                        :class="gradingEnabled
                          ? 'border-leaf/60 bg-sky/20 text-ink'
                          : 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'"
                        @click="setGradingEnabled(true)"
                      >
                        Yes
                      </button>
                      <button
                        type="button"
                        class="rounded-full border px-4 py-2 text-sm font-medium transition"
                        :class="!gradingEnabled
                          ? 'border-leaf/60 bg-sky/20 text-ink'
                          : 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'"
                        @click="setGradingEnabled(false)"
                      >
                        No
                      </button>
                    </div>
                  </div>

                  <div v-if="gradingEnabled" class="space-y-4">
                    <div class="grid gap-3 md:grid-cols-3">
                      <button
                        v-for="option in gradingOptions"
                        :key="option.value"
                        type="button"
                        class="rounded-2xl border px-4 py-4 text-left transition"
                        :class="form.grading_mode === option.value
                          ? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
                          : 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'"
                        @click="form.grading_mode = option.value"
                      >
                        <p class="text-sm font-semibold text-ink">{{ option.label }}</p>
                        <p class="mt-1 text-xs text-ink/60">{{ option.help }}</p>
                      </button>
                    </div>

                    <div v-if="form.grading_mode === 'Points'" class="max-w-xs space-y-1">
                      <label class="type-label">Max points</label>
                      <FormControl
                        v-model="form.max_points"
                        type="number"
                        :min="0"
                        :step="0.5"
                        placeholder="Enter max points"
                      />
                    </div>
                  </div>

                  <p class="text-xs text-ink/60">Moderation happens after grading (peer check).</p>
                </section>

                <div v-if="errorMessage" class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame">
                  {{ errorMessage }}
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="if-overlay__footer">
              <Button appearance="secondary" @click="handleClose">Cancel</Button>
              <Button appearance="primary" :loading="submitting" :disabled="!canSubmit" @click="submit">
                Create
              </Button>
            </div>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { Button, FormControl, createResource, toast, FeatherIcon } from 'frappe-ui'
import type { CreateTaskDeliveryInput, CreateTaskDeliveryPayload } from '@/types/tasks'

const props = defineProps<{
  open: boolean
  zIndex?: number
  prefillStudentGroup?: string | null
  prefillDueDate?: string | null
  prefillAvailableFrom?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', payload: CreateTaskDeliveryPayload): void
  (e: 'after-leave'): void
}>()

console.log('[CreateTaskDeliveryOverlay] setup:start', {
  open: props.open,
  prefillStudentGroup: props.prefillStudentGroup,
})

const open = computed(() => props.open)
const zIndex = computed(() => props.zIndex ?? 60)

const submitting = ref(false)
const errorMessage = ref('')

const initialFocus = ref<HTMLElement | null>(null)

function handleClose() {
  emit('close')
}

function emitAfterLeave() {
  emit('after-leave')
}

const taskTypeOptions = [
  { label: 'Assignment', value: 'Assignment' },
  { label: 'Homework', value: 'Homework' },
  { label: 'Classwork', value: 'Classwork' },
  { label: 'Quiz', value: 'Quiz' },
  { label: 'Test', value: 'Test' },
  { label: 'Summative assessment', value: 'Summative assessment' },
  { label: 'Formative assessment', value: 'Formative assessment' },
  { label: 'Discussion', value: 'Discussion' },
  { label: 'Project', value: 'Project' },
  { label: 'Long Term Project', value: 'Long Term Project' },
  { label: 'Exam', value: 'Exam' },
  { label: 'Other', value: 'Other' },
]

const deliveryOptions = [
  { label: 'Just post it', value: 'Assign Only', help: 'Share the assignment without collecting work.' },
  { label: 'Collect work', value: 'Collect Work', help: 'Students submit evidence; grading is optional.' },
  { label: 'Collect and assess', value: 'Assess', help: 'Collect evidence and grade it.' },
]

const gradingOptions = [
  { label: 'Points', value: 'Points', help: 'Score work with a numeric total.' },
  { label: 'Complete / Not complete', value: 'Completion', help: 'Track completion only.' },
  { label: 'Yes / No', value: 'Binary', help: 'Simple yes or no grading.' },
]

const form = reactive({
  title: '',
  instructions: '',
  task_type: '',
  student_group: '',
  delivery_mode: 'Assign Only',
  available_from: '',
  due_date: '',
  lock_date: '',
  allow_late_submission: true,
  group_submission: false,
  grading_mode: '',
  max_points: '',
})

const gradingEnabled = ref(false)

function unwrapMessage<T>(res: any): T | undefined {
  if (res && typeof res === 'object' && 'message' in res) return (res as any).message
  return res as T
}

const isGroupLocked = computed(() => !!props.prefillStudentGroup)

const groups = ref<Array<{ name: string; student_group_name?: string }>>([])

const groupResource = createResource({
  url: 'ifitwala_ed.api.student_groups.fetch_groups',
  method: 'POST',
  auto: false,
  transform: unwrapMessage,
  onSuccess: (rows: any) => {
    groups.value = Array.isArray(rows) ? rows : []
  },
  onError: () => {
    groups.value = []
    toast({ appearance: 'danger', message: 'Unable to load classes right now.' })
  },
})

const groupsLoading = computed(() => groupResource.loading)

const groupOptions = computed(() =>
  groups.value.map((row) => ({
    label: row.student_group_name || row.name,
    value: row.name,
  }))
)

const selectedGroupLabel = computed(() => {
  const match = groupOptions.value.find((o) => o.value === form.student_group)
  return match?.label || ''
})

const showLateSubmission = computed(() => form.delivery_mode !== 'Assign Only')

watch(
	() => form.delivery_mode,
	(mode) => {
		if (mode === 'Assign Only') {
			form.allow_late_submission = false
		}
	}
)


const canSubmit = computed(() => {
  if (!form.title.trim()) return false
  if (!form.student_group) return false
  if (!form.delivery_mode) return false
  if (!gradingEnabled.value) return true
  if (!form.grading_mode) return false
  if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) return false
  return true
})

watch(
  () => props.open,
  (openNow) => {
    console.log('[CreateTaskDeliveryOverlay] watch:open', {
      openNow,
      locked: isGroupLocked.value,
      prefillStudentGroup: props.prefillStudentGroup,
    })

    if (!openNow) return

    initializeForm()

    // quick-link mode (no prefill) => load dropdown list
    if (!isGroupLocked.value) {
      groupResource.submit({})
    }
  },
  { immediate: true }
)

function initializeForm() {
  form.title = ''
  form.instructions = ''
  form.task_type = ''
  form.student_group = props.prefillStudentGroup || ''
  form.delivery_mode = 'Assign Only'
  form.available_from = toDateTimeInput(props.prefillAvailableFrom)
  form.due_date = toDateTimeInput(props.prefillDueDate)
  form.lock_date = ''
  form.allow_late_submission = true
  form.group_submission = false
  form.grading_mode = ''
  form.max_points = ''
  gradingEnabled.value = false
  errorMessage.value = ''
}

function setGradingEnabled(value: boolean) {
  gradingEnabled.value = value
  if (!value) {
    form.grading_mode = ''
    form.max_points = ''
  }
}

function toDateTimeInput(value?: string | null) {
  if (!value) return ''
  if (value.includes('T')) {
    const [date, timeRaw] = value.split('T')
    const [hour = '00', minute = '00'] = timeRaw.split(':')
    return `${date}T${hour}:${minute}`
  }
  if (value.includes(' ')) {
    const [date, timeRaw] = value.split(' ')
    const [hour = '00', minute = '00'] = timeRaw.split(':')
    return `${date}T${hour}:${minute}`
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return formatDateTimeInput(date)
}

function formatDateTimeInput(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

function toFrappeDatetime(value: string) {
  if (!value) return null
  if (value.includes('T')) {
    const [date, timeRaw] = value.split('T')
    const [hour = '00', minute = '00', second = '00'] = timeRaw.split(':')
    return `${date} ${hour}:${minute}:${second}`
  }
  return value
}

/**
 * ✅ Frappe-UI canonical mutation: use createResource + submit(payload)
 * - This matches your groupResource pattern.
 * - It also guarantees the request is sent as form_dict kwargs (payload key present),
 *   which matches your current server signature: create_task_and_delivery(payload)
 */
const createTaskResource = createResource({
  url: 'ifitwala_ed.assessment.task_creation_service.create_task_and_delivery',
  method: 'POST',
  auto: false,
  transform: unwrapMessage,
  onError: (err: any) => {
    console.error('[CreateTaskDeliveryOverlay] createTaskResource:error', err)
  },
})

async function submit() {
  console.log('[CreateTaskDeliveryOverlay] submit:clicked')

  if (!canSubmit.value) {
    const missing: string[] = []
    if (!form.title.trim()) missing.push('Title')
    if (!form.student_group) missing.push('Class')
    if (gradingEnabled.value) {
      if (!form.grading_mode) missing.push('Grading mode')
      if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) missing.push('Max points')
    }

    const msg = missing.length ? `Please complete: ${missing.join(', ')}.` : 'Please complete the required fields.'
    errorMessage.value = msg
    toast({ appearance: 'warning', message: msg })
    return
  }

  submitting.value = true
  errorMessage.value = ''

  const payload: CreateTaskDeliveryInput = {
    title: form.title.trim(),
    student_group: form.student_group,
    delivery_mode: form.delivery_mode,
    allow_late_submission: form.allow_late_submission ? 1 : 0,
    group_submission: form.group_submission ? 1 : 0,
  }

  if (form.instructions.trim()) payload.instructions = form.instructions.trim()
  if (form.task_type) payload.task_type = form.task_type
  if (form.available_from) payload.available_from = toFrappeDatetime(form.available_from) as any
  if (form.due_date) payload.due_date = toFrappeDatetime(form.due_date) as any
  if (form.lock_date) payload.lock_date = toFrappeDatetime(form.lock_date) as any

  if (gradingEnabled.value) {
    payload.grading_mode = form.grading_mode as any
    if (form.grading_mode === 'Points') payload.max_points = form.max_points as any
  } else {
    payload.grading_mode = 'None' as any
  }

  try {
    // ✅ server expects `payload` argument -> submit({ payload })
    const res = await createTaskResource.submit(payload)
    const out = res as CreateTaskDeliveryPayload | undefined

    console.log('[CreateTaskDeliveryOverlay] submit:response', out)

    if (!out?.task || !out?.task_delivery) throw new Error('Unexpected server response.')

    emit('created', out)
    emit('close')
  } catch (error) {
    console.error('[CreateTaskDeliveryOverlay] submit:error', error)
    const msg = error instanceof Error ? error.message : 'Unable to create the assignment right now.'
    errorMessage.value = msg
    toast({ appearance: 'danger', message: msg })
  } finally {
    submitting.value = false
  }
}
</script>
