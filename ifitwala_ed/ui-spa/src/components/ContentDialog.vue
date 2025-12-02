<template>
	<Dialog v-model="isOpen" :options="{ size: 'xl', title: null }">
		<template #body-content>
			<div class="p-6 space-y-4 bg-white rounded-b-xl">
				<div class="flex items-center gap-4 border-b border-gray-100 pb-4">
					<div v-if="image || imageFallback" class="h-16 w-16 rounded-xl bg-slate-100 overflow-hidden flex-shrink-0">
						<img v-if="image" :src="image" class="h-full w-full object-cover">
						<div v-else class="h-full w-full flex items-center justify-center text-xl font-bold text-slate-400">
							{{ imageFallback }}
						</div>
					</div>
					<div>
						<h2 class="text-xl font-bold text-ink" v-if="!titleInHeader">{{ title }}</h2>
						<div class="flex gap-2 mt-1 items-center flex-wrap">
							<span v-if="badge" class="inline-chip bg-slate-100 text-slate-600">{{ badge }}</span>
							<span v-if="subtitle" class="text-sm text-slate-500">{{ subtitle }}</span>
						</div>
					</div>
				</div>

				<div class="prose prose-sm max-w-none text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-100">
					<div v-html="content"></div>
				</div>

				<div class="flex justify-end pt-2">
					<button class="fui-btn-primary px-4 py-2 rounded-lg" @click="isOpen = false">Close</button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed } from 'vue'
import { Dialog } from 'frappe-ui'

const props = defineProps({
	modelValue: {
		type: Boolean,
		required: true
	},
	title: {
		type: String,
		default: ''
	},
	subtitle: {
		type: String,
		default: ''
	},
	content: {
		type: String,
		default: ''
	},
	image: {
		type: String,
		default: ''
	},
	imageFallback: {
		type: String,
		default: ''
	},
	badge: {
		type: String,
		default: ''
	},
	titleInHeader: {
		type: Boolean,
		default: false
	}
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
})
</script>
