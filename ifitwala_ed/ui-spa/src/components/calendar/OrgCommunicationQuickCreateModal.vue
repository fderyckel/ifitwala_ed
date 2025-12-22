<!-- ifitwala_ed/ui-spa/src/components/calendar/OrgCommunicationQuickCreateModal.vue -->
<template>
	<Dialog v-model="isOpen" :options="{ size: 'xl', title: null }">
		<template #body-content>
			<div class="flex h-[80vh] flex-col gap-4 text-ink">
				<header class="flex flex-wrap items-start justify-between gap-3 border-b border-border/70 pb-3">
					<div class="min-w-0">
						<p class="type-overline text-slate-token/70">Class announcement</p>
						<h2 class="type-h2 text-ink">Create announcement</h2>
						<p class="type-meta text-slate-token/70">
							Student group: {{ groupLabel }}
						</p>
					</div>

					<Button appearance="minimal" icon="x" @click="isOpen = false" />
				</header>

				<div class="grid flex-1 grid-cols-1 gap-4 overflow-y-auto pr-1 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.9fr)]">
					<section class="space-y-4">
						<div class="space-y-1">
							<label class="type-label">Title</label>
							<FormControl
								v-model="form.title"
								type="text"
								placeholder="Student group - Date"
							/>
							<p class="type-caption text-slate-token/70">
								If left blank, we will use "{{ fallbackTitle }}".
							</p>
						</div>

						<div class="space-y-1">
							<label class="type-label">Message</label>
							<FormControl
								v-model="form.message"
								type="textarea"
								:rows="8"
								placeholder="Write the announcement for this class..."
							/>
						</div>
					</section>

					<aside class="space-y-4 rounded-xl border border-border/80 bg-surface-soft p-4 shadow-sm">
						<div>
							<p class="type-label">Audience</p>
							<div class="mt-2 flex flex-wrap gap-2">
								<span class="chip">Students</span>
								<span class="chip">{{ groupLabel }}</span>
								<span class="chip">{{ schoolLabel }}</span>
							</div>
						</div>

						<div>
							<p class="type-label">Delivery</p>
							<div class="mt-2 flex flex-wrap gap-2">
								<span class="chip">Published</span>
								<span class="chip">Everywhere</span>
							</div>
						</div>

						<div class="space-y-3">
							<div class="space-y-1">
								<label class="type-label">Publish from</label>
								<input
									v-model="form.publish_from"
									type="datetime-local"
									class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
								/>
							</div>

							<div class="space-y-1">
								<label class="type-label">Publish until</label>
								<input
									v-model="form.publish_to"
									type="datetime-local"
									class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
								/>
							</div>

							<div class="space-y-1">
								<label class="type-label">Brief start date</label>
								<input
									v-model="form.brief_start_date"
									type="date"
									class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
								/>
							</div>

							<div class="space-y-1">
								<label class="type-label">Brief end date</label>
								<input
									v-model="form.brief_end_date"
									type="date"
									class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
								/>
							</div>
						</div>

						<div class="rounded-lg border border-dashed border-border/80 bg-white/70 px-3 py-2 text-xs text-slate-token/70">
							Course: <span class="font-semibold text-ink">{{ courseLabel }}</span>
							<span v-if="sessionDateLabel"> · Date: {{ sessionDateLabel }}</span>
						</div>
					</aside>
				</div>

				<footer class="flex flex-wrap items-center justify-end gap-2 border-t border-border/70 pt-3">
					<Button appearance="secondary" @click="isOpen = false">Cancel</Button>
					<Button
						appearance="primary"
						:loading="submitting"
						:disabled="!canSubmit"
						@click="submit"
					>
						Create announcement
					</Button>
				</footer>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { Button, Dialog, FormControl, toast } from 'frappe-ui';

import { api } from '@/types/client';
import type { ClassEventDetails } from './classEventTypes';

const props = defineProps<{
	modelValue: boolean;
	event: ClassEventDetails | null;
}>();

const emit = defineEmits<{
	(e: 'update:modelValue', value: boolean): void;
	(e: 'created', doc: any): void;
}>();

const isOpen = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
});

const submitting = ref(false);

const form = reactive({
	title: '',
	message: '',
	publish_from: '',
	publish_to: '',
	brief_start_date: '',
	brief_end_date: '',
});

const groupLabel = computed(
	() => props.event?.title || props.event?.student_group || 'Student group'
);
const schoolLabel = computed(() => props.event?.school || 'School');
const courseLabel = computed(
	() => props.event?.course_name || props.event?.course || 'Course'
);
const sessionDateLabel = computed(() => formatDateLabel(props.event?.session_date));

const fallbackTitle = computed(() => {
	const date = props.event?.session_date || formatDateInput(new Date());
	return `${groupLabel.value} - ${date}`;
});

const canSubmit = computed(
	() =>
		!!props.event?.student_group &&
		!!props.event?.school &&
		!submitting.value
);

watch(
	() => [isOpen.value, props.event?.id],
	([open]) => {
		if (!open) return;
		initializeForm();
	},
);

function initializeForm() {
	const now = new Date();
	form.title = '';
	form.message = '';
	form.publish_from = formatDateTimeInput(now);
	form.publish_to = '';
	form.brief_start_date = formatDateInput(now);
	form.brief_end_date = '';
}

function formatDateInput(date: Date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function formatDateTimeInput(date: Date) {
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${formatDateInput(date)}T${hours}:${minutes}`;
}

function formatDateLabel(value?: string | null) {
	if (!value) return '';
	if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
		return value;
	}
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleDateString('en-GB', {
		day: '2-digit',
		month: 'short',
		year: 'numeric',
	});
}

function toFrappeDatetime(value: string | null) {
	if (!value) return null;
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00', second = '00'] = timeRaw.split(':');
		return `${date} ${hour}:${minute}:${second}`;
	}
	return value;
}

async function submit() {
	if (!props.event?.student_group || !props.event?.school) {
		toast({
			appearance: 'danger',
			message: 'Missing student group or school for this class.',
		});
		return;
	}

	submitting.value = true;

	const payload: Record<string, any> = {
		doctype: 'Org Communication',
		title: form.title.trim() || fallbackTitle.value,
		communication_type: 'Class Announcement',
		status: 'Published',
		priority: 'Normal',
		portal_surface: 'Everywhere',
		publish_from: toFrappeDatetime(form.publish_from) || undefined,
		publish_to: toFrappeDatetime(form.publish_to) || undefined,
		brief_start_date: form.brief_start_date || formatDateInput(new Date()),
		brief_end_date: form.brief_end_date || undefined,
		message: form.message.trim(),
		school: props.event.school,
		audiences: [
			{
				target_group: 'Students',
				student_group: props.event.student_group,
				school: props.event.school,
			},
		],
	};

	try {
		const doc = await api('frappe.client.insert', { doc: payload });
		toast({
			appearance: 'success',
			message: 'Announcement created.',
		});
		emit('created', doc);
		isOpen.value = false;
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to create announcement.';
		toast({
			appearance: 'danger',
			message,
		});
	} finally {
		submitting.value = false;
	}
}
</script>
