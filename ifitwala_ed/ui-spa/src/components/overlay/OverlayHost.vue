<!-- ui-spa/src/components/overlay/OverlayHost.vue -->
<template>
  <Teleport v-if="teleportReady" to="#overlay-root">
    <div v-if="rendered.length" class="if-overlay-host" :style="{ zIndex: baseZ }">
      <div
        v-for="(entry, idx) in rendered"
        :key="entry.id"
        class="if-overlay-host__layer"
        :class="{ 'if-overlay-host__layer--inactive': idx !== rendered.length - 1 }"
        :aria-hidden="idx !== rendered.length - 1 ? 'true' : 'false'"
        :inert="idx !== rendered.length - 1 ? '' : null"
      >
        <component
          :is="resolveComponent(entry.type)"
          v-bind="entry.props"
          :open="entry.open"
          :z-index="baseZ + idx * zStep"
          :overlay-id="entry.id"
          @close="requestClose(entry.id, 'backdrop')"
          @after-leave="finalizeClose(entry.id)"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useOverlayStack, type OverlayEntry, type OverlayType } from '@/composables/useOverlayStack'

import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue'
import MeetingEventModal from '@/components/calendar/MeetingEventModal.vue'
import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue'
import ClassEventModal from '@/components/calendar/ClassEventModal.vue'
import OrgCommunicationQuickCreateOverlay from '@/components/communication/OrgCommunicationQuickCreateModal.vue'
import StudentLogCreateOverlay from '@/components/student/StudentLogCreateOverlay.vue'
import StudentLogFollowUpOverlay from '@/components/student/StudentLogFollowUpOverlay.vue'
import FocusRouterOverlay from '@/components/focus/FocusRouterOverlay.vue'
import StudentLogAnalyticsExpandOverlay from '@/components/analytics/StudentLogAnalyticsExpandOverlay.vue'
import StudentContextOverlay from '@/components/overlays/class-hub/StudentContextOverlay.vue'
import QuickEvidenceOverlay from '@/components/overlays/class-hub/QuickEvidenceOverlay.vue'
import QuickCFUOverlay from '@/components/overlays/class-hub/QuickCFUOverlay.vue'
import TaskReviewOverlay from '@/components/overlays/class-hub/TaskReviewOverlay.vue'

type RenderedEntry = OverlayEntry & {
	open: boolean
	_closing?: boolean
	_closeTimer?: number | null
}

const overlay = useOverlayStack()

const teleportReady = ref(false)
onMounted(() => {
	// Defensive: guarantee teleport target exists
	let root = document.getElementById('overlay-root')
	if (!root) {
		root = document.createElement('div')
		root.id = 'overlay-root'
		document.body.appendChild(root)
	}
	teleportReady.value = true
})

// z-index policy: explicit + stable
const baseZ = 60
const zStep = 10

// Local rendered stack (includes closing entries until transitions finish)
const rendered = ref<RenderedEntry[]>([])

watch(
	() => overlay.state.stack,
	(nextRaw) => {
		const next = Array.isArray(nextRaw) ? nextRaw : []
		const nextIds = new Set(next.map((e) => e.id))

		// Add / update entries from store stack
		for (const entry of next) {
			const existing = rendered.value.find((r) => r.id === entry.id)
			if (!existing) {
				rendered.value.push({ ...entry, open: true, _closing: false, _closeTimer: null })
			} else {
				existing.type = entry.type
				existing.props = entry.props
				existing.closeOnBackdrop = entry.closeOnBackdrop
				existing.closeOnEsc = entry.closeOnEsc

				// Re-open if it was closing
				if (existing._closing) {
					existing._closing = false
					existing.open = true
					if (existing._closeTimer) {
						window.clearTimeout(existing._closeTimer)
						existing._closeTimer = null
					}
				}
			}
		}

		// Mark removed entries as closing (don’t drop instantly)
		for (const r of rendered.value) {
			if (!nextIds.has(r.id) && !r._closing) {
				r._closing = true
				r.open = false

				// Fallback cleanup if an overlay forgets to emit after-leave
				r._closeTimer = window.setTimeout(() => {
					const still = rendered.value.find((x) => x.id === r.id)
					if (still?._closing) finalizeClose(r.id)
				}, 350)
			}
		}

		// Ordering: store stack order first, then closing leftovers
		const ordered: RenderedEntry[] = []
		for (const entry of next) {
			const match = rendered.value.find((r) => r.id === entry.id)
			if (match) ordered.push(match)
		}
		for (const r of rendered.value) {
			if (!nextIds.has(r.id)) ordered.push(r)
		}
		rendered.value = ordered
	},
	{ immediate: true, deep: true }
)

function resolveComponent(type: OverlayType) {
	switch (type) {
		case 'create-task':
			return CreateTaskDeliveryOverlay
		case 'meeting-event':
			return MeetingEventModal
		case 'school-event':
			return SchoolEventModal
		case 'class-event':
			return ClassEventModal
		case 'org-communication-quick-create':
			return OrgCommunicationQuickCreateOverlay
		case 'student-log-create':
			return StudentLogCreateOverlay
		case 'student-log-follow-up':
			return StudentLogFollowUpOverlay
		case 'student-log-analytics-expand':
			return StudentLogAnalyticsExpandOverlay
		case 'focus-router':
			return FocusRouterOverlay
		case 'class-hub-student-context':
			return StudentContextOverlay
		case 'class-hub-quick-evidence':
			return QuickEvidenceOverlay
		case 'class-hub-quick-cfu':
			return QuickCFUOverlay
		case 'class-hub-task-review':
			return TaskReviewOverlay
		default:
			return CreateTaskDeliveryOverlay
	}
}

type CloseReason = 'backdrop' | 'esc' | 'programmatic'

function requestClose(id: string, reason: CloseReason = 'programmatic') {
	// Only the top overlay may be interactively closed
	const top = rendered.value[rendered.value.length - 1]
	if (!top || top.id !== id) return

	// Enforce close flags centrally (A+)
	if (reason === 'backdrop' && top.closeOnBackdrop === false) return
	if (reason === 'esc' && top.closeOnEsc === false) return

	// Use overlay stack API only (no direct state mutation)
	const anyOverlay = overlay as any
	if (typeof anyOverlay.close === 'function') {
		anyOverlay.close(id)
		return
	}

	// Emergency escape hatch: still must live in the composable
	if (typeof anyOverlay.forceRemove === 'function') {
		// eslint-disable-next-line no-console
		console.error('[OverlayHost] overlay.close missing; using overlay.forceRemove (defect)', { id, reason })
		anyOverlay.forceRemove(id)
		return
	}

	// If neither exists, we do nothing (better than mutating state and drifting invariants)
	// eslint-disable-next-line no-console
	console.error('[OverlayHost] Cannot close overlay: missing overlay.close and overlay.forceRemove', { id, reason })
}

function finalizeClose(id: string) {
	const idx = rendered.value.findIndex((r) => r.id === id)
	if (idx < 0) return
	const entry = rendered.value[idx]
	if (!entry._closing) return

	if (entry._closeTimer) {
		window.clearTimeout(entry._closeTimer)
		entry._closeTimer = null
	}
	rendered.value.splice(idx, 1)
}

/**
 * Central ESC handling (A+):
 * - OverlayHost owns ESC policy consistently across overlays
 * - Respects closeOnEsc flag on the top overlay
 */
function onKeydown(e: KeyboardEvent) {
	if (e.key !== 'Escape') return
	const top = rendered.value[rendered.value.length - 1]
	if (!top) return
	if (top.closeOnEsc === false) return
	e.preventDefault()
	requestClose(top.id, 'esc')
}

onMounted(() => {
	document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown)
})
</script>


<style scoped>
.if-overlay-host__layer--inactive {
  pointer-events: none;
}
</style>
