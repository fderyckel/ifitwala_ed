<!-- ifitwala_ed/ui-spa/src/components/org-chart/OrgChartNodeCard.vue -->
<!--
  OrgChartNodeCard.vue
  Represents a single node (person) in the Organization Chart visualization.

  Used by:
  - OrgChart.vue (pages/staff)
-->
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
				<img v-if="node.image" :src="node.image" :alt="node.name" loading="lazy" />
				<span v-else class="org-chart-avatar__fallback type-caption">
					{{ initials }}
				</span>
			</div>

			<div class="org-chart-node__titles">
				<p class="type-body-strong text-ink">
					{{ node.name }}
				</p>
				<p class="type-caption text-slate-500">
					Preferred name: {{ node.preferred_name || node.first_name || '-' }}
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
				{{ node.school_abbr || node.school || '-' }} ·
				{{ node.organization_abbr || node.organization || '-' }}
			</p>
			<p class="type-caption text-slate-500 break-all">
				Email: {{ node.professional_email || '-' }}
			</p>
			<p class="type-caption text-slate-500">Ext: {{ node.phone_ext || '-' }}</p>
			<p class="type-caption text-slate-500">Joined: {{ node.date_of_joining_label || '-' }}</p>
		</div>

		<div v-if="loading" class="org-chart-node__loading type-caption">Loading reports...</div>
	</button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
	node: {
		id: string;
		name: string;
		first_name: string | null;
		preferred_name: string | null;
		title: string | null;
		school: string | null;
		school_abbr: string | null;
		organization: string | null;
		organization_abbr: string | null;
		image: string | null;
		professional_email: string | null;
		phone_ext: string | null;
		date_of_joining: string | null;
		date_of_joining_label: string | null;
		connections: number;
		expandable: boolean;
		parent_id: string | null;
	};
	tone?: 'default' | 'active' | 'path';
	disabled?: boolean;
	loading?: boolean;
}>();

const emit = defineEmits<{
	(e: 'select', node: typeof props.node): void;
}>();

const initials = computed(() => {
	const source = (props.node.first_name || props.node.name || '').trim();
	if (!source) return '-';
	const parts = source.split(/\s+/).slice(0, 2);
	return parts.map(part => part[0]?.toUpperCase() || '').join('') || '-';
});

const toneClass = computed(() => ({
	'org-chart-node--active': props.tone === 'active',
	'org-chart-node--path': props.tone === 'path',
}));
</script>
