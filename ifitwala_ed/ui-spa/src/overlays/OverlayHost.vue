<!-- ui-spa/src/overlays/OverlayHost.vue -->
<template>
  <Teleport v-if="teleportReady" to="#overlay-root">
    <!--
      Critical: PortalGroup forces ANY headlessui portals created by overlay descendants
      (Listbox/Popover/Combobox etc.) to render inside #overlay-root.
      Without this, portals go to #headlessui-portal-root (a sibling) and Dialog will aria-hide it,
      causing “clicks don’t work” + aria-hidden focus warnings.
    -->
    <PortalGroup target="#overlay-root">
      <div v-if="rendered.length" class="if-overlay-host" :style="{ zIndex: baseZ }">
        <div
          v-for="(entry, idx) in rendered"
          :key="entry.id"
          class="if-overlay-host__layer"
          :class="{ 'if-overlay-host__layer--inactive': idx !== activeIdx }"
          :aria-hidden="idx !== activeIdx ? 'true' : 'false'"
          :inert="idx !== activeIdx ? '' : null"
        >
          <component
            :is="resolveComponent(entry.type)"
            v-bind="entry.props"
            :open="entry.open"
            :z-index="baseZ + idx * zStep"
            :overlay-id="entry.id"
            @close="onChildClose(entry.id, $event)"
            @after-leave="finalizeClose(entry.id)"
          />
        </div>
      </div>
    </PortalGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { PortalGroup } from '@headlessui/vue'
import { useOverlayStack, type OverlayEntry, type OverlayType } from '@/composables/useOverlayStack'

import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue'
import MeetingEventModal from '@/components/calendar/MeetingEventModal.vue'
import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue'
import ClassEventModal from '@/components/calendar/ClassEventModal.vue'
import OrgCommunicationQuickCreateOverlay from '@/components/communication/OrgCommunicationQuickCreateModal.vue'
import StudentLogCreateOverlay from '@/overlays/student/StudentLogCreateOverlay.vue'
import StudentLogFollowUpOverlay from '@/overlays/student/StudentLogFollowUpOverlay.vue'
import FocusRouterOverlay from '@/overlays/focus/FocusRouterOverlay.vue'
import StudentLogAnalyticsExpandOverlay from '@/overlays/analytics/StudentLogAnalyticsExpandOverlay.vue'
import StudentContextOverlay from '@/components/overlays/class-hub/StudentContextOverlay.vue'
import QuickEvidenceOverlay from '@/components/overlays/class-hub/QuickEvidenceOverlay.vue'
import QuickCFUOverlay from '@/components/overlays/class-hub/QuickCFUOverlay.vue'
import TaskReviewOverlay from '@/components/overlays/class-hub/TaskReviewOverlay.vue'

type CloseReason = 'backdrop' | 'esc' | 'programmatic'

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

/**
 * Active layer index:
 * - The topmost entry that is NOT closing.
 * - Closing leftovers must never become the “active” interactive layer,
 *   otherwise they can inert/disable the real top overlay beneath (dead clicks).
 */
const activeIdx = computed(() => {
  for (let i = rendered.value.length - 1; i >= 0; i--) {
    const entry = rendered.value[i]
    if (!entry?._closing) return i
  }
  return -1
})

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

function getTopInteractive(): RenderedEntry | null {
  const idx = activeIdx.value
  if (idx < 0) return null
  const entry = rendered.value[idx]
  if (!entry || entry._closing) return null
  return entry
}

/**
 * Normalize the close payload coming from child overlays.
 *
 * IMPORTANT:
 * - HeadlessUI Dialog emits boolean `false` on @close by default.
 * - Some overlays may emit undefined or other values.
 * - Under A+ rules, unknown payloads MUST NOT trigger a close.
 */
function normalizeCloseReason(payload: unknown): CloseReason | null {
  if (payload === 'backdrop' || payload === 'esc' || payload === 'programmatic') return payload
  return null
}

function onChildClose(id: string, payload: unknown) {
  const reason = normalizeCloseReason(payload)

  // If the child didn’t provide a valid reason, ignore.
  // This prevents HeadlessUI’s default boolean `false` from closing overlays.
  if (!reason) {
    // eslint-disable-next-line no-console
    console.warn('[OverlayHost] Ignoring invalid close payload from overlay', { id, payload })
    return
  }

  requestClose(id, reason)
}

/**
 * A+ central close enforcement:
 * - Only the top overlay can be interactively closed
 * - closeOnBackdrop / closeOnEsc enforced here (not per-overlay ad hoc)
 * - OverlayHost NEVER mutates overlay.state.stack directly
 * - Emergency hatch is overlay.forceRemove(id) (implemented in useOverlayStack)
 */
function requestClose(id: string, reason: CloseReason = 'programmatic') {
  const top = getTopInteractive()
  if (!top || top.id !== id) return

  if (reason === 'backdrop' && top.closeOnBackdrop === false) return
  if (reason === 'esc' && top.closeOnEsc === false) return

  // Primary: public API
  try {
    overlay.close(id)
    return
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('[OverlayHost] overlay.close failed; using forceRemove', { id, reason, err })
  }

  // Emergency: API-based removal (still no direct state mutation here)
  if (typeof (overlay as any).forceRemove === 'function') {
    ;(overlay as any).forceRemove(id)
    return
  }

  // eslint-disable-next-line no-console
  console.error('[OverlayHost] forceRemove is missing; overlay may remain stuck', { id, reason })
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
</script>

<style scoped>
.if-overlay-host__layer--inactive {
  pointer-events: none;
}
</style>
