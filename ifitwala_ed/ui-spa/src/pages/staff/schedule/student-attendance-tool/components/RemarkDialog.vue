<template>
	<Dialog v-model="open" :options="{ title: dialogTitle, size: 'md' }">
		<div class="space-y-4">
			<!-- Context chips -->
			<div v-if="props.student" class="flex flex-wrap items-center gap-2 text-xs">
				<span
					class="inline-flex items-center gap-1 rounded-full
					       bg-[rgb(var(--sky-rgb)/0.9)] px-2.5 py-1
					       font-medium text-ink/80"
				>
					<span class="inline-block h-1.5 w-1.5 rounded-full bg-[rgb(var(--leaf-rgb))]" />
					{{ studentName }}
				</span>
				<span
					v-if="blockLabel"
					class="inline-flex items-center gap-1 rounded-full
					       bg-[rgb(var(--sand-rgb)/0.9)] px-2.5 py-1
					       font-medium text-ink/70"
				>
					{{ blockLabel }}
				</span>
			</div>

			<!-- Card surface with textarea -->
			<div
				class="rounded-2xl border border-[var(--border-light)]
				       bg-[rgb(var(--surface-rgb)/0.98)] p-3
				       shadow-soft"
			>
				<p class="mb-2 text-xs text-slate-token/80">
					{{ helperText }}
				</p>

				<textarea
					ref="textareaRef"
					v-model="localValue"
					rows="4"
					maxlength="255"
					class="w-full rounded-xl border border-[var(--border-light)]
					       bg-[rgb(var(--surface-strong-rgb))]
					       px-3 py-2 text-sm text-ink shadow-inner
					       focus-visible:outline-none
					       focus-visible:ring-2
					       focus-visible:ring-[rgb(var(--leaf-rgb)/0.55)]"
					:placeholder="__('Add a short, specific note (optional)…')"
				/>

				<div class="mt-1 flex items-center justify-between text-[0.7rem] text-slate-token/60">
					<p>
						{{ __('Keep remarks factual, short, and focused on today’s context.') }}
					</p>
					<p>
						{{ localValue.length }}/255
					</p>
				</div>
			</div>
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
import { __ } from '@/lib/i18n'
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

// v-model bridge: Frappe-UI pattern
const open = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
})

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const localValue = ref(props.value ?? '')

/**
 * Keep local state in sync with incoming props and focus on open.
 * - When the dialog opens, copy the latest remark and focus the textarea.
 * - If the parent updates the remark while closed, refresh localValue so it
 *   shows up the next time we open.
 */
watch(
	() => [props.modelValue, props.value],
	async ([isOpen, nextValue], [wasOpen, prevValue]) => {
		const opened = isOpen && !wasOpen
		const valueChangedWhileClosed = !isOpen && nextValue !== prevValue

		if (opened || valueChangedWhileClosed) {
			localValue.value = nextValue ?? ''
		}

		if (opened) {
			await nextTick()
			textareaRef.value?.focus()
			textareaRef.value?.setSelectionRange(localValue.value.length, localValue.value.length)
		}
	},
	{ immediate: true },
)

const studentName = computed(() => {
	if (!props.student) return ''
	return (
		props.student.preferred_name ||
		props.student.student_name ||
		props.student.student
	)
})

const dialogTitle = computed(() => {
	if (!studentName.value) {
		return __('Remark')
	}
	return __('Remark for {0}', [studentName.value])
})

const blockLabel = computed(() => {
	if (!props.block || props.block === -1) return ''
	return __('Block {0}', [props.block])
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
