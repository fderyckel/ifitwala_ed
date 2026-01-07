<!-- ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryModal.vue -->
<template>
	<Dialog v-model="isOpen" :options="{ title: 'Create task', size: '3xl' }">
		<div class="space-y-6">
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

			<section class="card-panel space-y-4 p-5">
				<div class="flex items-center gap-3">
					<span class="chip">Step 2</span>
					<h3 class="type-h3 text-ink">Which class?</h3>
				</div>

				<div class="space-y-1">
					<label class="type-label">Class</label>
					<div v-if="isGroupLocked" class="rounded-xl border border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/80">
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
					<label class="flex items-center gap-2 text-sm text-ink/80">
						<input v-model="form.allow_late_submission" type="checkbox" class="rounded border-border/70 text-jacaranda" />
						Allow late submissions
					</label>
					<label class="flex items-center gap-2 text-sm text-ink/80">
						<input v-model="form.group_submission" type="checkbox" class="rounded border-border/70 text-jacaranda" />
						Group submission
					</label>
				</div>
			</section>

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

			<div class="flex flex-wrap items-center justify-end gap-2 border-t border-border/60 pt-4">
				<Button appearance="secondary" @click="handleClose">Cancel</Button>
				<Button appearance="primary" :loading="submitting" :disabled="!canSubmit" @click="submit">
					Create
				</Button>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { Button, Dialog, FormControl, createResource, toast } from 'frappe-ui';

import { api } from '@/lib/client';
import type { CreateTaskDeliveryInput, CreateTaskDeliveryPayload } from '@/types/tasks';

const props = defineProps<{
	modelValue: boolean;
	prefillStudentGroup?: string | null;
	prefillDueDate?: string | null;
	prefillAvailableFrom?: string | null;
}>();

const emit = defineEmits<{
	(e: 'update:modelValue', value: boolean): void;
	(e: 'created', payload: CreateTaskDeliveryPayload): void;
}>();

const isOpen = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
});

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
];

const deliveryOptions = [
	{
		label: 'Just post it',
		value: 'Assign Only',
		help: 'Share the assignment without collecting work.',
	},
	{
		label: 'Collect work',
		value: 'Collect Work',
		help: 'Students submit evidence; grading is optional.',
	},
	{
		label: 'Collect and assess',
		value: 'Assess',
		help: 'Collect evidence and grade it.',
	},
];

const gradingOptions = [
	{
		label: 'Points',
		value: 'Points',
		help: 'Score work with a numeric total.',
	},
	{
		label: 'Complete / Not complete',
		value: 'Completion',
		help: 'Track completion only.',
	},
	{
		label: 'Yes / No',
		value: 'Binary',
		help: 'Simple yes or no grading.',
	},
];

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
});

const gradingEnabled = ref(false);
const submitting = ref(false);
const errorMessage = ref('');

function unwrapMessage<T>(res: any): T | undefined {
	if (res && typeof res === 'object' && 'message' in res) {
		return (res as any).message;
	}
	return res as T;
}

const groups = ref<Array<{ name: string; student_group_name?: string }>>([]);

const groupResource = createResource({
	url: 'ifitwala_ed.api.student_groups.fetch_groups',
	method: 'POST',
	auto: true,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		groups.value = Array.isArray(rows) ? rows : [];
	},
	onError: () => {
		groups.value = [];
		toast({
			appearance: 'danger',
			message: 'Unable to load classes right now.',
		});
	},
});

const groupsLoading = computed(() => groupResource.loading);
const groupOptions = computed(() =>
	groups.value.map((row) => ({
		label: row.student_group_name || row.name,
		value: row.name,
	}))
);

const selectedGroupLabel = computed(() => {
	const match = groupOptions.value.find((option) => option.value === form.student_group);
	return match?.label || '';
});

const isGroupLocked = computed(() => !!props.prefillStudentGroup);

const canSubmit = computed(() => {
	if (!form.title.trim()) return false;
	if (!form.student_group) return false;
	if (!form.delivery_mode) return false;
	if (!gradingEnabled.value) return true;
	if (!form.grading_mode) return false;
	if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) return false;
	return true;
});

watch(
	() => isOpen.value,
	(open) => {
		if (open) {
			initializeForm();
		}
	}
);

function initializeForm() {
	form.title = '';
	form.instructions = '';
	form.task_type = '';
	form.student_group = props.prefillStudentGroup || '';
	form.delivery_mode = 'Assign Only';
	form.available_from = toDateTimeInput(props.prefillAvailableFrom);
	form.due_date = toDateTimeInput(props.prefillDueDate);
	form.lock_date = '';
	form.allow_late_submission = true;
	form.group_submission = false;
	form.grading_mode = '';
	form.max_points = '';
	gradingEnabled.value = false;
	errorMessage.value = '';
}

function setGradingEnabled(value: boolean) {
	gradingEnabled.value = value;
	if (!value) {
		form.grading_mode = '';
		form.max_points = '';
	}
}

function toDateTimeInput(value?: string | null) {
	if (!value) return '';
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00'] = timeRaw.split(':');
		return `${date}T${hour}:${minute}`;
	}
	if (value.includes(' ')) {
		const [date, timeRaw] = value.split(' ');
		const [hour = '00', minute = '00'] = timeRaw.split(':');
		return `${date}T${hour}:${minute}`;
	}
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '';
	return formatDateTimeInput(date);
}

function formatDateTimeInput(date: Date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function toFrappeDatetime(value: string) {
	if (!value) return null;
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00', second = '00'] = timeRaw.split(':');
		return `${date} ${hour}:${minute}:${second}`;
	}
	return value;
}

function handleClose() {
	isOpen.value = false;
}

async function submit() {
	if (!canSubmit.value) return;
	submitting.value = true;
	errorMessage.value = '';

	const payload: CreateTaskDeliveryInput = {
		title: form.title.trim(),
		student_group: form.student_group,
		delivery_mode: form.delivery_mode,
		allow_late_submission: form.allow_late_submission ? 1 : 0,
		group_submission: form.group_submission ? 1 : 0,
	};

	if (form.instructions.trim()) {
		payload.instructions = form.instructions.trim();
	}
	if (form.task_type) {
		payload.task_type = form.task_type;
	}
	if (form.available_from) {
		payload.available_from = toFrappeDatetime(form.available_from);
	}
	if (form.due_date) {
		payload.due_date = toFrappeDatetime(form.due_date);
	}
	if (form.lock_date) {
		payload.lock_date = toFrappeDatetime(form.lock_date);
	}

	if (gradingEnabled.value) {
		payload.grading_mode = form.grading_mode;
		if (form.grading_mode === 'Points') {
			payload.max_points = form.max_points;
		}
	} else {
		payload.grading_mode = 'None';
	}

	try {
		const res = await api('ifitwala_ed.assessment.task_creation_service.create_task_and_delivery', {
			payload,
		});
		const out = unwrapMessage<CreateTaskDeliveryPayload>(res);
		if (!out?.task || !out?.task_delivery) {
			throw new Error('Unexpected server response.');
		}
		emit('created', out);
		isOpen.value = false;
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to create the assignment right now.';
		errorMessage.value = message;
	} finally {
		submitting.value = false;
	}
}
</script>

<style scoped>
:deep(.fui-dialog-panel) {
	background:
		radial-gradient(circle at 0% 0%, rgb(var(--sky-rgb) / 0.9), transparent 65%),
		radial-gradient(circle at 100% 0%, rgb(var(--sand-rgb) / 0.9), transparent 65%),
		#ffffff;
	border: 1px solid rgb(var(--border-rgb) / 0.9);
	box-shadow: 0 18px 45px rgba(7, 16, 25, 0.18);
}
</style>
