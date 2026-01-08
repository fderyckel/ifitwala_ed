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
          @close="requestClose(entry.id)"
          @after-leave="finalizeClose(entry.id)"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useOverlayStack, type OverlayEntry, type OverlayType } from '@/composables/useOverlayStack'

import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue'
import MeetingEventModal from '@/components/calendar/MeetingEventModal.vue'
import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue'
import ClassEventModal from '@/components/calendar/ClassEventModal.vue'

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
    default:
      return CreateTaskDeliveryOverlay
  }
}

function requestClose(id: string) {
  overlay.close(id)
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
