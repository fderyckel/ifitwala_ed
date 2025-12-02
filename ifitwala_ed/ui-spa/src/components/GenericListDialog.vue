<template>
	<Dialog v-model="show" :options="{ size: 'xl', title: null }">
		<template #body-content>
			<div class="flex flex-col h-[80vh]">
				<!-- Header -->
				<div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between shrink-0">
					<div>
						<h3 class="text-xl font-bold text-ink">{{ title }}</h3>
						<p v-if="subtitle" class="text-sm text-slate-500 mt-1">{{ subtitle }}</p>
					</div>
					<button @click="show = false"
						class="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-400 hover:text-ink">
						<FeatherIcon name="x" class="h-5 w-5" />
					</button>
				</div>

				<!-- Content -->
				<div class="flex-1 overflow-y-auto p-0 custom-scrollbar bg-slate-50/50">
					<div v-if="loading" class="p-10 flex justify-center">
						<FeatherIcon name="loader" class="h-8 w-8 animate-spin text-slate-300" />
					</div>

					<div v-else-if="items && items.length > 0" class="divide-y divide-slate-100">
						<div v-for="(item, index) in items" :key="index" class="bg-white hover:bg-slate-50 transition-colors">
							<slot name="item" :item="item" :index="index">
								<!-- Default Item Render if no slot provided -->
								<div class="p-4">
									{{ item }}
								</div>
							</slot>
						</div>
					</div>

					<div v-else class="p-10 text-center text-slate-400">
						<FeatherIcon name="inbox" class="h-10 w-10 mx-auto mb-3 opacity-50" />
						<p>No items found</p>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Dialog, FeatherIcon } from 'frappe-ui'

const props = defineProps<{
	modelValue: boolean
	title: string
	subtitle?: string
	items: any[]
	loading?: boolean
}>()

const emit = defineEmits(['update:modelValue'])

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
	width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
	background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
	background-color: #cbd5e1;
	border-radius: 20px;
	border: 2px solid transparent;
	background-clip: content-box;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
	background-color: #94a3b8;
}
</style>
