<template>
	<div
		v-if="editable"
		class="planning-richtext-field overflow-hidden rounded-2xl border border-line-soft bg-white shadow-sm"
	>
		<TextEditor
			:content="normalizedContent"
			:editable="editable"
			:fixed-menu="editorButtons"
			:extensions="editorExtensions"
			:placeholder="placeholder"
			:editor-class="editorClass"
			@change="handleChange"
		/>
	</div>
	<div
		v-else-if="hasContent"
		class="planning-richtext-display prose prose-sm max-w-none text-ink"
		:class="displayClass"
		v-html="trustedHtml(normalizedContent)"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TextEditor } from 'frappe-ui';
import PlanningUnderline from '@/components/planning/extensions/underline';

const props = withDefaults(
	defineProps<{
		modelValue?: string | null;
		placeholder?: string;
		editable?: boolean;
		minHeightClass?: string;
		displayClass?: string;
	}>(),
	{
		modelValue: '',
		placeholder: '',
		editable: true,
		minHeightClass: 'min-h-[8rem]',
		displayClass: '',
	}
);

const emit = defineEmits<{
	(e: 'update:modelValue', value: string): void;
}>();

const editorButtons = [
	'Paragraph',
	['Heading 2', 'Heading 3'],
	'Separator',
	'Bold',
	'Italic',
	'Underline',
	'Separator',
	'Bullet List',
	'Numbered List',
	'Separator',
	'Link',
	'Blockquote',
];
const editorExtensions = [PlanningUnderline];

const normalizedContent = computed(() => String(props.modelValue || ''));
const editorClass = computed(
	() =>
		`prose prose-sm max-w-none bg-white px-4 py-3 text-sm text-ink focus:outline-none ${props.minHeightClass}`
);
const hasContent = computed(() => hasRichTextContent(normalizedContent.value));

function handleChange(content: string) {
	emit('update:modelValue', content);
}

function trustedHtml(html: string): string {
	return String(html || '');
}

function hasRichTextContent(value: string): boolean {
	return Boolean(
		String(value || '')
			.replace(/<style[\s\S]*?<\/style>/gi, ' ')
			.replace(/<script[\s\S]*?<\/script>/gi, ' ')
			.replace(/<[^>]*>/g, ' ')
			.replace(/&nbsp;|&#160;/gi, ' ')
			.trim()
	);
}
</script>

<style>
.planning-richtext-field .ProseMirror ul:not([data-type='taskList']),
.planning-richtext-display ul {
	list-style-type: disc;
	padding-inline-start: 1.5rem;
}

.planning-richtext-field .ProseMirror ol,
.planning-richtext-display ol {
	list-style-type: decimal;
	padding-inline-start: 1.5rem;
}

.planning-richtext-field .ProseMirror ul[data-type='taskList'] {
	padding-inline-start: 0;
}

.planning-richtext-field .ProseMirror li,
.planning-richtext-display li {
	margin: 0.25rem 0;
}

.planning-richtext-field .ProseMirror a,
.planning-richtext-display a {
	color: rgb(var(--jacaranda-rgb) / 1);
	text-decoration: underline;
	text-underline-offset: 0.14em;
}

.planning-richtext-field .ProseMirror u,
.planning-richtext-display u {
	text-decoration: underline;
	text-underline-offset: 0.14em;
}

.planning-richtext-field .ProseMirror h2,
.planning-richtext-display h2 {
	font-size: 1.25rem;
	font-weight: 600;
	line-height: 1.35;
}

.planning-richtext-field .ProseMirror h3,
.planning-richtext-display h3 {
	font-size: 1.125rem;
	font-weight: 600;
	line-height: 1.4;
}
</style>
