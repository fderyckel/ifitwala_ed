<!-- ifitwala_ed/ui-spa/src/pages/staff/organization_chart/OrganizationChart.vue -->
<template>
	<div class="staff-shell org-chart-shell">
		<header class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="type-h2 text-canopy">Organization Chart</h1>
				<p class="type-body text-slate-500 mt-1">
					Explore reporting lines across your organization in a focused, calm view.
				</p>
			</div>

			<div class="flex flex-wrap items-center gap-2">
				<Button
					appearance="secondary"
					class="org-chart-action type-button-label"
					:disabled="!canExport"
					@click="exportChart"
				>
					<FeatherIcon name="download" class="h-4 w-4" />
					<span>{{ exporting ? 'Exporting...' : 'Export PNG' }}</span>
				</Button>
			</div>
		</header>

		<section class="org-chart-panel card-surface">
			<div class="org-chart-toolbar">
				<div class="org-chart-toolbar__filters">
					<FormControl
						type="select"
						size="md"
						:options="orgOptions"
						option-label="organization_name"
						option-value="name"
						:model-value="selectedOrganization"
						:disabled="loadingRoots || !orgOptions.length"
						placeholder="All Organizations"
						@update:modelValue="onOrganizationSelected"
					/>
				</div>

				<div class="org-chart-toolbar__actions">
					<Button
						appearance="primary"
						class="org-chart-action type-button-label"
						:disabled="!canExpandAll"
						@click="expandAll"
					>
						<FeatherIcon name="maximize-2" class="h-4 w-4" />
						<span>Expand all</span>
					</Button>
					<Button
						appearance="secondary"
						class="org-chart-action type-button-label"
						:disabled="!expandedView"
						@click="collapseAll"
					>
						<FeatherIcon name="minimize-2" class="h-4 w-4" />
						<span>Collapse</span>
					</Button>
				</div>
			</div>

			<p v-if="limitHint" class="type-caption text-slate-500 org-chart-hint">
				{{ limitHint }}
			</p>
			<p v-if="expandedMeta" class="type-caption text-slate-500 org-chart-hint">
				{{ expandedMeta }}
			</p>
			<p v-if="actionMessage" class="type-caption org-chart-message">
				{{ actionMessage }}
			</p>

			<div v-if="loadingRoots" class="org-chart-empty">
				<div class="org-chart-empty__spinner"></div>
				<p class="type-body">Loading organization chart...</p>
			</div>
			<div v-else-if="errorMessage" class="org-chart-empty">
				<p class="type-body">{{ errorMessage }}</p>
			</div>
			<div v-else-if="!hasNodes" class="org-chart-empty">
				<p class="type-body">No staff members found for this organization.</p>
				<p class="type-caption text-slate-500 mt-1">Try adjusting the organization filter.</p>
			</div>
			<div v-else ref="chartStageRef" class="org-chart-stage">
				<div ref="chartSurfaceRef" class="org-chart-surface">
					<svg
						ref="connectorSvgRef"
						class="org-chart-connectors"
						:width="connectorSize.width"
						:height="connectorSize.height"
						aria-hidden="true"
					>
						<defs>
							<marker
								id="org-chart-arrow-active"
								viewBox="0 0 10 10"
								refX="6"
								refY="5"
								markerWidth="6"
								markerHeight="6"
								orient="auto"
								fill="currentColor"
							>
								<path d="M 0 0 L 10 5 L 0 10 z"></path>
							</marker>
							<marker
								id="org-chart-arrow-path"
								viewBox="0 0 10 10"
								refX="6"
								refY="5"
								markerWidth="6"
								markerHeight="6"
								orient="auto"
								fill="currentColor"
							>
								<path d="M 0 0 L 10 5 L 0 10 z"></path>
							</marker>
						</defs>

						<path
							v-for="(connector, index) in connectorPaths"
							:key="`${connector.state}-${index}`"
							:d="connector.d"
							:class="connectorClass(connector.state)"
							fill="none"
							stroke-linecap="round"
							stroke-linejoin="round"
							:marker-end="markerEnd(connector.state)"
						/>
					</svg>

					<div class="org-chart-levels">
						<div
							v-for="(level, levelIndex) in visibleLevels"
							:key="`level-${levelIndex}`"
							class="org-chart-level"
						>
							<OrgChartNodeCard
								v-for="node in level"
								:key="node.id"
								:node="node"
								:disabled="expandedView"
								:tone="nodeTone(node.id)"
								:loading="loadingChildrenId === node.id"
								@select="selectNode(node, levelIndex)"
							/>
						</div>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Button, FeatherIcon, FormControl } from 'frappe-ui'

import OrgChartNodeCard from '@/components/org-chart/OrgChartNodeCard.vue'
import {
	getOrganizationChartChildren,
	getOrganizationChartContext,
	getOrganizationChartTree,
} from '@/lib/services/organizationChart/organizationChartService'

import type { Response as OrgChartChildrenResponse } from '@/types/contracts/organization_chart/get_org_chart_children'
import type { Response as OrgChartContextResponse } from '@/types/contracts/organization_chart/get_org_chart_context'

type OrgChartNode = OrgChartChildrenResponse[number]

type Edge = {
	parentId: string
	childId: string
	state: 'active' | 'path' | 'expanded'
}

type ConnectorPath = {
	d: string
	state: Edge['state']
}

type FocusSnapshot = {
	levels: OrgChartNode[][]
	selectedNodeId: string | null
}

const STACKED_BREAKPOINT = 1024

const context = ref<OrgChartContextResponse | null>(null)
const contextReady = ref(false)
const selectedOrganization = ref('')
const loadingRoots = ref(false)
const loadingChildrenId = ref<string | null>(null)
const actionMessage = ref<string | null>(null)
const errorMessage = ref<string | null>(null)
const exporting = ref(false)

const levels = ref<OrgChartNode[][]>([])
const selectedNodeId = ref<string | null>(null)
const expandedView = ref(false)
const fullTree = ref<OrgChartNode[]>([])
const fullRoots = ref<string[]>([])
const fullDepth = ref(0)
const focusSnapshot = ref<FocusSnapshot | null>(null)

const chartStageRef = ref<HTMLDivElement | null>(null)
const chartSurfaceRef = ref<HTMLDivElement | null>(null)
const connectorSvgRef = ref<SVGSVGElement | null>(null)
const connectorPaths = ref<ConnectorPath[]>([])
const connectorSize = ref({ width: 0, height: 0 })

const isStacked = ref(false)
const childrenCache = new Map<string, OrgChartNode[]>()

const organizationFilter = computed(() => selectedOrganization.value || null)
const organizations = computed(() => context.value?.organizations ?? [])
const expandLimits = computed(() => context.value?.expand_limits ?? null)

const orgOptions = computed(() => {
	if (!organizations.value.length) return []
	return [
		{ name: '', organization_name: 'All Organizations' },
		...organizations.value,
	]
})

const visibleLevels = computed(() => (expandedView.value ? buildLevels() : levels.value))
const hasNodes = computed(() => visibleLevels.value.some((level) => level.length))

const limitHint = computed(() => {
	if (!expandLimits.value) return ''
	return `Expand all shows up to ${expandLimits.value.max_nodes} people or ${expandLimits.value.max_depth} levels.`
})

const expandedMeta = computed(() => {
	if (!expandedView.value || !fullTree.value.length) return ''
	return `Expanded view: ${fullTree.value.length} people across ${fullDepth.value} levels.`
})

const nodeLookup = computed(() => {
	const map = new Map<string, OrgChartNode>()
	for (const level of levels.value) {
		for (const node of level) {
			map.set(node.id, node)
		}
	}
	return map
})

const activePath = computed(() => {
	const path: string[] = []
	const lookup = nodeLookup.value
	let current = selectedNodeId.value
	while (current) {
		path.unshift(current)
		const parent = lookup.get(current)?.parent_id || null
		current = parent
	}
	return path
})

const activePathSet = computed(() => new Set(activePath.value))

const selectedLevelIndex = computed(() => {
	if (!selectedNodeId.value) return null
	for (let i = 0; i < levels.value.length; i += 1) {
		if (levels.value[i].some((node) => node.id === selectedNodeId.value)) {
			return i
		}
	}
	return null
})

const edges = computed<Edge[]>(() => {
	if (expandedView.value) {
		return fullTree.value
			.filter((node) => node.parent_id)
			.map((node) => ({
				parentId: node.parent_id as string,
				childId: node.id,
				state: 'expanded',
			}))
	}

	const result: Edge[] = []
	const path = activePath.value
	for (let i = 1; i < path.length; i += 1) {
		result.push({ parentId: path[i - 1], childId: path[i], state: 'path' })
	}

	const index = selectedLevelIndex.value
	if (index !== null && selectedNodeId.value) {
		const children = levels.value[index + 1] || []
		for (const child of children) {
			result.push({ parentId: selectedNodeId.value, childId: child.id, state: 'active' })
		}
	}

	return result
})

const canExpandAll = computed(() => {
	return !expandedView.value && !loadingRoots.value && hasNodes.value && !exporting.value
})

const canExport = computed(() => {
	return hasNodes.value && !loadingRoots.value && !exporting.value
})

let connectorFrame: number | null = null

function onOrganizationSelected(value: string | null) {
	const nextValue = value || ''
	if (nextValue === selectedOrganization.value) return

	selectedOrganization.value = nextValue
	if (!contextReady.value) return

	childrenCache.clear()
	expandedView.value = false
	fullTree.value = []
	fullRoots.value = []
	fullDepth.value = 0
	focusSnapshot.value = null
	loadRoots()
}

function nodeTone(nodeId: string) {
	if (expandedView.value) return 'default'
	if (nodeId === selectedNodeId.value) return 'active'
	if (activePathSet.value.has(nodeId)) return 'path'
	return 'default'
}

function connectorClass(state: Edge['state']) {
	return {
		'org-chart-connector--active': state === 'active',
		'org-chart-connector--path': state === 'path',
		'org-chart-connector--expanded': state === 'expanded',
	}
}

function markerEnd(state: Edge['state']) {
	if (state === 'active') return 'url(#org-chart-arrow-active)'
	if (state === 'path') return 'url(#org-chart-arrow-path)'
	return undefined
}

function scheduleConnectors() {
	if (connectorFrame) {
		window.cancelAnimationFrame(connectorFrame)
	}
	connectorFrame = window.requestAnimationFrame(() => {
		connectorFrame = null
		buildConnectors()
	})
}

async function buildConnectors() {
	await nextTick()
	const surface = chartSurfaceRef.value
	if (!surface) return

	const surfaceRect = surface.getBoundingClientRect()
	const positions = new Map<string, { x: number; y: number; width: number; height: number }>()

	const nodeElements = surface.querySelectorAll<HTMLElement>('[data-node-id]')
	for (const element of nodeElements) {
		const id = element.dataset.nodeId
		if (!id) continue
		const rect = element.getBoundingClientRect()
		positions.set(id, {
			x: rect.left - surfaceRect.left,
			y: rect.top - surfaceRect.top,
			width: rect.width,
			height: rect.height,
		})
	}

	connectorSize.value = {
		width: Math.max(surface.scrollWidth, surface.clientWidth),
		height: Math.max(surface.scrollHeight, surface.clientHeight),
	}

	const paths: ConnectorPath[] = []
	for (const edge of edges.value) {
		const parent = positions.get(edge.parentId)
		const child = positions.get(edge.childId)
		if (!parent || !child) continue

		const path = isStacked.value
			? buildVerticalPath(parent, child)
			: buildHorizontalPath(parent, child)

		paths.push({ d: path, state: edge.state })
	}

	connectorPaths.value = paths
}

function buildHorizontalPath(
	parent: { x: number; y: number; width: number; height: number },
	child: { x: number; y: number; width: number; height: number }
) {
	const startX = parent.x + parent.width
	const startY = parent.y + parent.height / 2
	const endX = child.x
	const endY = child.y + child.height / 2
	const midX = (startX + endX) / 2

	return `M ${startX} ${startY} L ${midX} ${startY} L ${midX} ${endY} L ${endX} ${endY}`
}

function buildVerticalPath(
	parent: { x: number; y: number; width: number; height: number },
	child: { x: number; y: number; width: number; height: number }
) {
	const startX = parent.x + parent.width / 2
	const startY = parent.y + parent.height
	const endX = child.x + child.width / 2
	const endY = child.y
	const midY = (startY + endY) / 2

	return `M ${startX} ${startY} L ${startX} ${midY} L ${endX} ${midY} L ${endX} ${endY}`
}

function buildLevels() {
	const byId = new Map<string, OrgChartNode>()
	for (const node of fullTree.value) {
		byId.set(node.id, node)
	}

	const childrenByParent = new Map<string, string[]>()
	for (const node of fullTree.value) {
		if (node.parent_id && byId.has(node.parent_id)) {
			const bucket = childrenByParent.get(node.parent_id) || []
			bucket.push(node.id)
			childrenByParent.set(node.parent_id, bucket)
		}
	}

	const levelsLocal: OrgChartNode[][] = []
	let current = fullRoots.value.filter((id) => byId.has(id))
	while (current.length) {
		levelsLocal.push(current.map((id) => byId.get(id)!).filter(Boolean))
		const next: string[] = []
		for (const id of current) {
			const children = childrenByParent.get(id)
			if (children) next.push(...children)
		}
		current = next
	}

	return levelsLocal
}

async function loadContext() {
	try {
		context.value = await getOrganizationChartContext()
		selectedOrganization.value = context.value.default_organization || ''
		contextReady.value = true
		await loadRoots()
	} catch (error) {
		errorMessage.value = 'Unable to load organization chart context.'
	}
}

async function loadRoots() {
	loadingRoots.value = true
	errorMessage.value = null
	actionMessage.value = null

	const orgSnapshot = organizationFilter.value

	try {
		const roots = await getOrganizationChartChildren({
			parent: null,
			organization: orgSnapshot,
		})

		if (orgSnapshot !== organizationFilter.value) return

		levels.value = roots.length ? [roots] : []
		selectedNodeId.value = null

		const first = roots.find((node) => node.expandable) || roots[0]
		if (first) {
			await selectNode(first, 0)
		}
	} catch (error) {
		errorMessage.value = 'Unable to load staff members for this organization.'
		levels.value = []
	} finally {
		loadingRoots.value = false
		scheduleConnectors()
	}
}

async function selectNode(node: OrgChartNode, levelIndex: number) {
	if (expandedView.value) return

	selectedNodeId.value = node.id
	actionMessage.value = null

	const trimmedLevels = levels.value.slice(0, levelIndex + 1)
	levels.value = trimmedLevels

	if (!node.expandable) {
		scheduleConnectors()
		return
	}

	const cached = childrenCache.get(node.id)
	if (cached) {
		levels.value = cached.length ? [...trimmedLevels, cached] : trimmedLevels
		scheduleConnectors()
		return
	}

	loadingChildrenId.value = node.id
	const orgSnapshot = organizationFilter.value

	try {
		const children = await getOrganizationChartChildren({
			parent: node.id,
			organization: orgSnapshot,
		})
		if (orgSnapshot !== organizationFilter.value) return

		childrenCache.set(node.id, children)
		levels.value = children.length ? [...trimmedLevels, children] : trimmedLevels
	} catch (error) {
		actionMessage.value = 'Unable to load direct reports for this role.'
	} finally {
		loadingChildrenId.value = null
		scheduleConnectors()
	}
}

async function expandAll() {
	if (!canExpandAll.value) return

	actionMessage.value = null
	const orgSnapshot = organizationFilter.value

	try {
		const response = await getOrganizationChartTree({ organization: orgSnapshot })
		if (orgSnapshot !== organizationFilter.value) return

		if (response.status === 'blocked') {
			actionMessage.value = response.message
			return
		}

		focusSnapshot.value = {
			levels: levels.value,
			selectedNodeId: selectedNodeId.value,
		}

		expandedView.value = true
		fullTree.value = response.nodes
		fullRoots.value = response.roots
		fullDepth.value = response.max_depth
	} catch (error) {
		actionMessage.value = 'Unable to expand the organization chart right now.'
	} finally {
		scheduleConnectors()
	}
}

function collapseAll() {
	if (!expandedView.value) return

	expandedView.value = false
	fullTree.value = []
	fullRoots.value = []
	fullDepth.value = 0
	actionMessage.value = null

	if (focusSnapshot.value) {
		levels.value = focusSnapshot.value.levels
		selectedNodeId.value = focusSnapshot.value.selectedNodeId
	} else {
		loadRoots()
	}

	scheduleConnectors()
}

async function exportChart() {
	if (!chartSurfaceRef.value) {
		actionMessage.value = 'Nothing to export yet.'
		return
	}

	exporting.value = true
	actionMessage.value = null

	try {
		const html2canvas = (await import('html2canvas')).default
		const surface = chartSurfaceRef.value

		const canvas = await html2canvas(surface, {
			backgroundColor: '#f9f8f4',
			scale: 2,
			width: surface.scrollWidth,
			height: surface.scrollHeight,
		})

		const dataUrl = canvas.toDataURL('image/png')
		const link = document.createElement('a')
		link.href = dataUrl
		link.download = 'organization_chart.png'
		link.click()
	} catch (error) {
		actionMessage.value = 'Export failed. Please try again.'
	} finally {
		exporting.value = false
	}
}

function updateLayout() {
	isStacked.value = window.innerWidth < STACKED_BREAKPOINT
	scheduleConnectors()
}

watch(edges, () => {
	scheduleConnectors()
})

onMounted(() => {
	updateLayout()
	window.addEventListener('resize', updateLayout)
	loadContext()
})

onBeforeUnmount(() => {
	window.removeEventListener('resize', updateLayout)
	if (connectorFrame) {
		window.cancelAnimationFrame(connectorFrame)
	}
})
</script>
