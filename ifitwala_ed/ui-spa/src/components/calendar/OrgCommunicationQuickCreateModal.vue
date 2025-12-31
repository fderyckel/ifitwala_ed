<template>
	<TransitionRoot as="template" :show="isOpen">
		<Dialog as="div" class="meeting-modal meeting-modal--class z-[100]" @close="handleClose">
			<TransitionChild
				as="template"
				enter="meeting-modal__fade-enter"
				enter-from="meeting-modal__fade-from"
				enter-to="meeting-modal__fade-to"
				leave="meeting-modal__fade-leave"
				leave-from="meeting-modal__fade-to"
				leave-to="meeting-modal__fade-from"
			>
				<div class="meeting-modal__backdrop" />
			</TransitionChild>

			<div class="meeting-modal__wrapper">
				<TransitionChild
					as="template"
					enter="meeting-modal__panel-enter"
					enter-from="meeting-modal__panel-from"
					enter-to="meeting-modal__panel-to"
					leave="meeting-modal__panel-leave"
					leave-from="meeting-modal__panel-to"
					leave-to="meeting-modal__panel-from"
				>
					<DialogPanel class="meeting-modal__panel bg-white">
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline">
								<p class="meeting-modal__eyebrow">Class announcement</p>
								<DialogTitle as="h3">Create announcement</DialogTitle>
								<p class="meeting-modal__time">
									Student group: {{ groupLabel }}
								</p>
							</div>

							<button
								class="meeting-modal__icon-button"
								aria-label="Close modal"
								@click="handleClose"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="meeting-modal__body">
							<div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.9fr)]">
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
							<div class="flex items-center justify-between">
								<p class="type-label">Audience</p>
								<label class="flex cursor-pointer items-center gap-2 text-sm text-ink/80 hover:text-ink">
									<input
										v-model="form.to_guardians"
										type="checkbox"
										class="rounded border-gray-300 text-jacaranda focus:ring-jacaranda"
									/>
									Include guardians
								</label>
							</div>
							<div class="mt-2 flex flex-wrap gap-2">
								<span class="chip">Students</span>
								<span v-if="form.to_guardians" class="chip">Guardians</span>
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
			</div>

				<footer class="flex flex-wrap items-center justify-end gap-2 border-t border-border/70 pt-3">
					<Button appearance="secondary" @click="handleClose">Cancel</Button>
					<Button
						appearance="primary"
						:loading="submitting"
						:disabled="!canSubmit"
						@click="submit"
					>
						Create announcement
					</Button>
				</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { Button, FeatherIcon, FormControl, toast } from 'frappe-ui';

import { api } from '@/lib/client';
import type {
	CommunicationType,
	OrgCommunicationAudienceRow,
	OrgCommunicationCreateDoc,
} from '@/types/orgCommunication';
import type { ClassEventDetails } from './classEventTypes';

const props = defineProps<{
	modelValue: boolean;
	event: ClassEventDetails | null;
}>();

const emit = defineEmits<{
	(e: 'update:modelValue', value: boolean): void;
	(e: 'created', doc: Record<string, unknown>): void;
}>();

const isOpen = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
});

function handleClose() {
	isOpen.value = false;
}

const submitting = ref(false);

type OrgCommunicationQuickForm = {
	title: string;
	message: string;
	publish_from: string;
	publish_to: string;
	brief_start_date: string;
	brief_end_date: string;
	to_guardians: boolean;
};

const form = reactive<OrgCommunicationQuickForm>({
	title: '',
	message: '',
	publish_from: '',
	publish_to: '',
	brief_start_date: '',
	brief_end_date: '',
	to_guardians: false,
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
	// Use the event's session date if available, otherwise default to today
	const eventDate = props.event?.session_date || formatDateInput(now);
	form.brief_start_date = eventDate;
	form.brief_end_date = eventDate;
	form.to_guardians = false;
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

function toFrappeDatetime(value: string) {
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

	const audience: OrgCommunicationAudienceRow = {
		target_mode: 'Student Group',
		student_group: props.event.student_group,
		school: props.event.school,
		include_descendants: 0,
		to_students: 1,
		to_guardians: form.to_guardians ? 1 : 0,
		to_staff: 0,
		to_community: 0,
	};

	const payload: OrgCommunicationCreateDoc = {
		doctype: 'Org Communication',
		title: form.title.trim() || fallbackTitle.value,
		communication_type: 'Class Announcement' satisfies CommunicationType,
		status: 'Published',
		priority: 'Normal',
		portal_surface: 'Everywhere',
		publish_from: toFrappeDatetime(form.publish_from) || undefined,
		publish_to: toFrappeDatetime(form.publish_to) || undefined,
		brief_start_date: form.brief_start_date || formatDateInput(new Date()),
		brief_end_date: form.brief_end_date || undefined,
		message: form.message.trim(),
		school: props.event.school,
		audiences: [audience],
	};

	try {
		const doc = (await api('frappe.client.insert', { doc: payload })) as Record<
			string,
			unknown
		>;
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
