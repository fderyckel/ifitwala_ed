<template>
	<Dialog v-model="open" :options="{ title: dialogTitle, size: 'md' }">
		<div class="space-y-3">
			<div class="text-sm text-slate-600">
				{{ helperText }}
			</div>
			<textarea
				ref="textareaRef"
				v-model="localValue"
				class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-inner focus:border-blue-400 focus:outline-none focus:ring focus:ring-blue-100"
				rows="4"
				maxlength="255"
			/>
			<p class="text-right text-xs text-slate-400">
				{{ localValue.length }}/255
			</p>
		</div>

		<template #footer>
			<div class="flex items-center justify-end gap-2">
				<Button appearance="minimal" @click="cancel">
					{{ __('Cancel') }}
				</Button>
				<Button appearance="primary" @click="save">
					{{ __('Save Remark') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'
import { Dialog, Button } from 'frappe-ui'
import type { StudentRosterEntry, BlockKey } from '../types'

const props = defineProps<{
	modelValue: boolean
	student: StudentRosterEntry | null
	block: BlockKey | null
	value: string
}>()

const emit = defineEmits<{
	(event: 'update:modelValue', value: boolean): void
	(event: 'save', value: string): void
}>()

const open = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
})

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const localValue = ref(props.value)

watch(
	() => props.value,
	(value) => {
		localValue.value = value ?? ''
		if (props.modelValue) {
			nextTick(() => textareaRef.value?.focus())
		}
	},
	{ immediate: true }
)

watch(
	() => props.modelValue,
	(value) => {
		if (value) {
			nextTick(() => textareaRef.value?.focus())
		}
	}
)

const dialogTitle = computed(() => {
	if (!props.student) {
		return __('Remark')
	}
	const name = props.student.preferred_name || props.student.student_name || props.student.student
	return __('Remark for {0}', [name])
})

const helperText = computed(() => {
	if (!props.block || props.block === -1) {
		return __('Add an optional remark for this student on the selected day.')
	}
	return __('Add an optional remark for block {0}.', [props.block])
})

function save() {
	const trimmed = (localValue.value || '').trim().slice(0, 255)
	emit('save', trimmed)
	emit('update:modelValue', false)
}

function cancel() {
	emit('update:modelValue', false)
	localValue.value = props.value ?? ''
}
</script>
