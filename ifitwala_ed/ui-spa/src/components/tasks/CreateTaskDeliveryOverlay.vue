<!-- ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue -->
<template>
  <TransitionRoot as="template" :show="open">
    <Dialog as="div" class="if-overlay" :style="{ zIndex: zIndex }" @close="handleClose">
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
            <div class="flex items-start justify-between gap-3 px-5 pt-5">
              <div>
                <p class="text-xs font-semibold tracking-wider text-[rgb(var(--slate-rgb)/0.75)] uppercase">
                  Task
                </p>
                <DialogTitle class="type-h3 text-ink mt-1">
                  Create task
                </DialogTitle>
              </div>
              <button
                type="button"
                class="meeting-modal__icon-button"
                aria-label="Close"
                @click="handleClose"
              >
                <FeatherIcon name="x" class="h-5 w-5" />
              </button>
            </div>

            <!-- Body: reuse your existing content -->
            <div class="if-overlay__body">
              <!-- Paste your exact Step1..Step5 markup here (from your modal template),
                   BUT remove the outer <Dialog> and keep only the inner content. -->
              <div class="space-y-6">
                <!-- (same sections as your current CreateTaskDeliveryModal.vue) -->
                <!-- ... -->
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
import { api } from '@/lib/client'
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
}>()

const zIndex = computed(() => props.zIndex ?? 60)

// --- Keep your existing logic below with minimal change ---
// IMPORTANT: remove any "open ref + v-model bridging" watchers.
// In overlay system, "open" is controlled externally; close via emit('close').

const submitting = ref(false)
const errorMessage = ref('')

// options arrays: taskTypeOptions, deliveryOptions, gradingOptions
// form reactive, gradingEnabled, groups createResource, canSubmit computed
// initializeForm, toDateTimeInput, submit()

function handleClose() {
  emit('close')
}

// 🔑 When the overlay becomes open, initialize defaults
watch(
  () => props.open,
  (v) => {
    if (v) initializeForm()
  },
  { immediate: true }
)

// ---------- Copy/paste your current CreateTaskDeliveryModal logic here ----------
// BUT: remove open ref + emit update:modelValue code and remove any watch(isOpen...)
// Keep everything else identical.
// ------------------------------------------------------------------------------

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

const groups = ref<Array<{ name: string; student_group_name?: string }>>([])

const groupResource = createResource({
  url: 'ifitwala_ed.api.student_groups.fetch_groups',
  method: 'POST',
  auto: true,
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

const isGroupLocked = computed(() => !!props.prefillStudentGroup)

const canSubmit = computed(() => {
  if (!form.title.trim()) return false
  if (!form.student_group) return false
  if (!form.delivery_mode) return false
  if (!gradingEnabled.value) return true
  if (!form.grading_mode) return false
  if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) return false
  return true
})

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

async function submit() {
  if (!canSubmit.value) return
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
  if (form.available_from) payload.available_from = toFrappeDatetime(form.available_from)
  if (form.due_date) payload.due_date = toFrappeDatetime(form.due_date)
  if (form.lock_date) payload.lock_date = toFrappeDatetime(form.lock_date)

  if (gradingEnabled.value) {
    payload.grading_mode = form.grading_mode
    if (form.grading_mode === 'Points') payload.max_points = form.max_points
  } else {
    payload.grading_mode = 'None'
  }

  try {
    const res = await api('ifitwala_ed.assessment.task_creation_service.create_task_and_delivery', { payload })
    const out = unwrapMessage<CreateTaskDeliveryPayload>(res)
    if (!out?.task || !out?.task_delivery) throw new Error('Unexpected server response.')
    emit('created', out)
    emit('close')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unable to create the assignment right now.'
  } finally {
    submitting.value = false
  }
}
</script>
