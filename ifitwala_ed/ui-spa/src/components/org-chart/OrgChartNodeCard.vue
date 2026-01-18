<!-- ifitwala_ed/ui-spa/src/components/org-chart/OrgChartNodeCard.vue -->
<template>
	<button
		type="button"
		class="org-chart-node"
		:class="toneClass"
		:data-node-id="node.id"
		:data-parent-id="node.parent_id || ''"
		:disabled="disabled"
		@click="emit('select', node)"
	>
		<div class="org-chart-node__header">
			<div class="org-chart-avatar">
				<img
					v-if="node.image"
					:src="node.image"
					:alt="node.name"
					loading="lazy"
				/>
				<span v-else class="org-chart-avatar__fallback type-caption">
					{{ initials }}
				</span>
			</div>

			<div class="org-chart-node__titles">
				<p class="type-body-strong text-ink">
					{{ node.name }}
				</p>
				<p class="type-caption text-slate-500">
					First name: {{ node.first_name || '-' }}
				</p>
			</div>

			<div v-if="node.connections" class="org-chart-node__count type-caption">
				{{ node.connections }} connections
			</div>
		</div>

		<div class="org-chart-node__meta">
			<p class="type-caption text-slate-500">
				{{ node.title || '-' }}
			</p>
			<p class="type-caption text-slate-500">
				{{ node.school || '-' }} · {{ node.organization || '-' }}
			</p>
		</div>

		<div v-if="loading" class="org-chart-node__loading type-caption">
			Loading reports...
		</div>
	</button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
	node: {
		id: string
		name: string
		first_name: string | null
		title: string | null
		school: string | null
		organization: string | null
		image: string | null
		connections: number
		expandable: boolean
		parent_id: string | null
	}
	tone?: 'default' | 'active' | 'path'
	disabled?: boolean
	loading?: boolean
}>()

const emit = defineEmits<{
	(e: 'select', node: typeof props.node): void
}>()

const initials = computed(() => {
	const source = (props.node.first_name || props.node.name || '').trim()
	if (!source) return '-'
	const parts = source.split(/\s+/).slice(0, 2)
	return parts.map((part) => part[0]?.toUpperCase() || '').join('') || '-'
})

const toneClass = computed(() => ({
	'org-chart-node--active': props.tone === 'active',
	'org-chart-node--path': props.tone === 'path',
}))
</script>
