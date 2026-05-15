<template>
	<div class="space-y-5">
		<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="space-y-1">
					<p class="type-overline text-ink/55">Class event</p>
					<div class="flex flex-wrap items-center gap-2">
						<h3 class="type-h3 text-ink">Locked context</h3>
						<span class="rounded-full bg-sky/25 px-3 py-1 type-caption text-canopy">
							Auto applied
						</span>
					</div>
					<p class="type-caption text-ink/65">
						The selected class event keeps scope, history, and archive context in sync
						automatically.
					</p>
				</div>
			</div>

			<div class="if-class-event-context-card mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
				<div
					v-for="(item, index) in classEventContextCards"
					:key="item.label"
					class="if-class-event-context-pill"
					:class="`if-class-event-context-pill--${index}`"
				>
					<span class="if-class-event-context-pill__label">
						{{ item.label }}
					</span>
					<p class="min-w-0 type-body-strong text-ink">
						{{ item.value }}
					</p>
				</div>
			</div>
		</section>

		<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
			<div class="space-y-1">
				<p class="type-overline text-ink/55">Message</p>
				<h3 class="type-h3 text-ink">Announcement</h3>
				<p class="type-caption text-ink/65">
					Write the announcement once. Class context, issuing scope, and thread rules are applied
					automatically.
				</p>
			</div>

			<div class="mt-4 space-y-1">
				<label class="type-label">Title</label>
				<FormControl
					v-model="form.title"
					type="text"
					placeholder="Class announcement"
					:disabled="submitting"
				/>
			</div>

			<div class="mt-4 space-y-1">
				<label class="type-label">Message</label>
				<div
					class="if-org-communication-message-editor overflow-hidden rounded-2xl border border-border/80 bg-white shadow-sm"
				>
					<TextEditor
						:content="form.message"
						placeholder="Share the update, reminder, or call to action."
						:editable="!submitting"
						:fixed-menu="messageEditorButtons"
						editor-class="prose prose-sm max-w-none min-h-[14rem] bg-white px-4 py-3 text-sm text-ink focus:outline-none"
						@change="emit('update-message', $event)"
					/>
				</div>
			</div>
		</section>

		<OrgCommunicationQuickCreateAttachmentSection
			v-bind="attachmentSection"
			@trigger-file-picker="emit('trigger-file-picker')"
			@toggle-link-composer="emit('toggle-link-composer')"
			@reset-link-draft="emit('reset-link-draft')"
			@submit-link="emit('submit-link')"
			@delete-attachment="emit('delete-attachment', $event)"
		/>

		<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
			<div class="space-y-1">
				<p class="type-overline text-ink/55">Delivery</p>
				<h3 class="type-h3 text-ink">Send options</h3>
				<p class="type-caption text-ink/65">
					Pick whether to save this draft, schedule it, or publish it now. Students in the selected
					class are always included.
				</p>
			</div>

			<div class="mt-4 flex flex-wrap gap-2">
				<button
					v-for="statusOption in statusOptions"
					:key="statusOption"
					type="button"
					class="rounded-full px-3 py-1.5 type-button-label transition"
					:class="
						form.status === statusOption
							? 'bg-jacaranda text-white'
							: 'bg-slate-100 text-slate-token hover:bg-slate-200'
					"
					:disabled="submitting"
					@click="form.status = statusOption"
				>
					{{ statusOption }}
				</button>
			</div>

			<div v-if="form.status === 'Scheduled'" class="mt-4 space-y-1">
				<label class="type-label">Publish from</label>
				<input
					v-model="form.publish_from"
					type="datetime-local"
					class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
					:disabled="submitting"
				/>
				<p class="type-caption text-ink/55">
					Schedule when this announcement should become visible.
				</p>
			</div>

			<div class="mt-4 rounded-[24px] border border-border/70 bg-surface-soft/70 p-4">
				<div class="space-y-1">
					<p class="type-overline text-ink/55">Recipients</p>
					<h4 class="type-h4 text-ink">Audience</h4>
				</div>

				<div
					class="if-class-event-audience-grid mt-4 grid grid-cols-1 gap-3 min-[480px]:grid-cols-2"
				>
					<div
						class="flex h-full items-start gap-3 rounded-2xl border border-border/70 bg-white px-4 py-3 type-caption text-ink/75"
					>
						<input
							checked
							type="checkbox"
							class="mt-0.5 rounded border-slate-300 text-jacaranda"
							disabled
						/>
						<div>
							<p class="type-body-strong text-ink">Students</p>
							<p class="mt-1 type-caption text-ink/65">
								The selected student group is always included.
							</p>
						</div>
					</div>

					<label
						v-if="classEventAudienceRow"
						class="flex h-full cursor-pointer items-start gap-3 rounded-2xl border border-border/70 bg-white px-4 py-3 type-caption text-ink/75"
					>
						<input
							v-model="classEventAudienceRow.to_guardians"
							type="checkbox"
							class="mt-0.5 rounded border-slate-300 text-jacaranda"
							:disabled="submitting"
						/>
						<div>
							<p class="type-body-strong text-ink">Visible to guardians</p>
							<p class="mt-1 type-caption text-ink/65">
								Turn this on only when guardians should also receive the class announcement.
							</p>
						</div>
					</label>
				</div>
			</div>
		</section>

		<details class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
			<summary class="cursor-pointer list-none">
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
					<div class="space-y-1">
						<p class="type-overline text-ink/55">Staff note</p>
						<h3 class="type-h3 text-ink">Internal note</h3>
						<p class="type-caption text-ink/65">
							Optional context for staff managing this communication later.
						</p>
					</div>
					<span
						class="rounded-full border border-border/80 bg-surface px-3 py-1.5 type-caption text-ink/65"
					>
						Optional
					</span>
				</div>
			</summary>

			<div class="mt-4 space-y-1">
				<label class="type-label">Internal note</label>
				<FormControl
					v-model="form.internal_note"
					type="textarea"
					:rows="3"
					placeholder="Optional staff note for managing this communication."
					:disabled="submitting"
				/>
			</div>
		</details>
	</div>
</template>

<script setup lang="ts">
import { FormControl, TextEditor } from 'frappe-ui';

import OrgCommunicationQuickCreateAttachmentSection from './OrgCommunicationQuickCreateAttachmentSection.vue';
import type {
	AttachmentSectionState,
	AudienceRowState,
	ClassEventContextCard,
	MessageEditorButton,
} from './orgCommunicationQuickCreateTypes';
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';

defineProps<{
	classEventContextCards: ClassEventContextCard[];
	form: {
		title: string;
		message: string;
		status: string;
		publish_from: string;
		internal_note: string;
	};
	submitting: boolean;
	statusOptions: string[];
	messageEditorButtons: MessageEditorButton[];
	classEventAudienceRow: AudienceRowState | null;
	attachmentSection: AttachmentSectionState;
}>();

const emit = defineEmits<{
	(e: 'update-message', content: string): void;
	(e: 'trigger-file-picker'): void;
	(e: 'toggle-link-composer'): void;
	(e: 'reset-link-draft'): void;
	(e: 'submit-link'): void;
	(e: 'delete-attachment', attachment: OrgCommunicationAttachmentRow): void;
}>();
</script>

<style scoped>
.if-class-event-context-pill {
	display: flex;
	min-width: 0;
	flex-wrap: wrap;
	align-items: center;
	gap: 0.625rem;
	border-radius: 1.25rem;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background: rgb(var(--surface-rgb) / 0.66);
	padding: 0.75rem 0.875rem;
}

.if-class-event-context-pill__label {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 9999px;
	padding: 0.25rem 0.625rem;
	font-size: 0.6875rem;
	font-weight: 700;
	letter-spacing: 0.16em;
	line-height: 1;
	text-transform: uppercase;
}

.if-class-event-context-pill--0 .if-class-event-context-pill__label {
	background: rgb(var(--jacaranda-rgb) / 0.14);
	color: rgb(var(--jacaranda-rgb) / 1);
}

.if-class-event-context-pill--1 .if-class-event-context-pill__label {
	background: rgb(var(--leaf-rgb) / 0.14);
	color: rgb(var(--canopy-rgb) / 1);
}

.if-class-event-context-pill--2 .if-class-event-context-pill__label {
	background: rgb(var(--sky-rgb) / 0.24);
	color: rgb(var(--canopy-rgb) / 1);
}

.if-class-event-context-pill--3 .if-class-event-context-pill__label {
	background: rgb(var(--slate-rgb) / 0.14);
	color: rgb(var(--slate-rgb) / 0.9);
}
</style>
