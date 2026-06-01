<template>
	<div class="admissions-assignee-search">
		<label class="action-field">
			<span>{{ label }}</span>
			<input
				:value="modelValue"
				:data-testid="inputTestId"
				type="text"
				:placeholder="placeholder"
				@input="handleInput"
			/>
		</label>
		<p v-if="loading" class="action-drawer__note">
			{{ __('Searching staff...') }}
		</p>
		<div v-if="candidates.length" :data-testid="candidatesTestId" class="assignee-picker">
			<button
				v-for="candidate in candidates"
				:key="candidate.value"
				type="button"
				:data-testid="candidateTestId"
				class="assignee-picker__option"
				@click="$emit('select', candidate)"
			>
				<span>{{ candidate.label || candidate.value }}</span>
				<small v-if="candidateMeta(candidate)">
					{{ candidateMeta(candidate) }}
				</small>
			</button>
		</div>
		<p v-else-if="noMatches" class="action-drawer__note">
			{{ noMatchesMessage }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { __ } from '@/lib/i18n';
import type { AdmissionsInboxAssigneeOption } from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

withDefaults(
	defineProps<{
		modelValue: string;
		label: string;
		placeholder: string;
		loading: boolean;
		candidates: AdmissionsInboxAssigneeOption[];
		noMatches: boolean;
		noMatchesMessage: string;
		inputTestId: string;
		candidatesTestId: string;
		candidateTestId: string;
	}>(),
	{
		modelValue: '',
		placeholder: '',
		noMatchesMessage: '',
	}
);

const emit = defineEmits<{
	(e: 'update:modelValue', value: string): void;
	(e: 'input', value: string): void;
	(e: 'select', candidate: AdmissionsInboxAssigneeOption): void;
}>();

function handleInput(event: Event) {
	const value = (event.target as HTMLInputElement | null)?.value || '';
	emit('update:modelValue', value);
	emit('input', value);
}

function candidateMeta(candidate: AdmissionsInboxAssigneeOption) {
	const parts = [
		candidate.meta || '',
		candidate.lane ? __('{0} lane', [candidate.lane]) : '',
	].filter(part => String(part || '').trim());
	return parts.join(' - ');
}
</script>

<style scoped>
.admissions-assignee-search {
	display: contents;
}

.action-field {
	display: grid;
	gap: 0.35rem;
}

.action-field span {
	color: rgb(var(--slate-rgb) / 0.76);
	font-size: 0.72rem;
	font-weight: 750;
	letter-spacing: 0;
	text-transform: uppercase;
}

.action-field input {
	min-width: 0;
	width: 100%;
	border: 1px solid rgb(203 213 225);
	border-radius: 0.5rem;
	background: white;
	color: rgb(var(--ink-rgb));
	font-size: 0.9rem;
	line-height: 1.4;
	padding: 0.6rem 0.7rem;
}

.action-drawer__note,
.assignee-picker {
	grid-column: 1 / -1;
}

.action-drawer__note {
	border-radius: 0.5rem;
	background: rgb(248 250 252);
	color: rgb(var(--slate-rgb));
	font-size: 0.84rem;
	line-height: 1.45;
	padding: 0.75rem;
}

.assignee-picker {
	display: grid;
	overflow: hidden;
	border: 1px solid rgb(226 232 240);
	border-radius: 0.5rem;
	background: white;
}

.assignee-picker__option {
	display: grid;
	gap: 0.2rem;
	border: 0;
	border-bottom: 1px solid rgb(226 232 240);
	background: white;
	padding: 0.65rem 0.75rem;
	text-align: left;
}

.assignee-picker__option:last-child {
	border-bottom: 0;
}

.assignee-picker__option:hover {
	background: rgb(var(--sky-rgb) / 0.14);
}

.assignee-picker__option span {
	color: rgb(var(--ink-rgb));
	font-size: 0.9rem;
	font-weight: 720;
	overflow-wrap: anywhere;
}

.assignee-picker__option small {
	color: rgb(var(--slate-rgb) / 0.72);
	font-size: 0.78rem;
	line-height: 1.35;
	overflow-wrap: anywhere;
}
</style>
