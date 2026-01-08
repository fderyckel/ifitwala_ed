<!-- ui-spa/src/components/overlay/OverlayHost.vue -->
<template>
  <Teleport v-if="teleportReady" to="#overlay-root">
    <div v-if="rendered.length" class="if-overlay-host">
      <div
        v-for="(entry, idx) in rendered"
        :key="entry.id"
        class="if-overlay-host__layer"
        :class="{
          'if-overlay-host__layer--inactive': idx !== rendered.length - 1,
        }"
        :aria-hidden="idx !== rendered.length - 1 ? 'true' : 'false'"
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

const { stack, close } = useOverlayStack()

/**
 * Overlay host responsibilities:
 *  1) Render stack entries
 *  2) Guarantee only the top layer is interactive (pointer + focus safety)
 *  3) Support transition-safe closing (keep closing overlays mounted until leave finishes)
 */

type RenderedEntry = OverlayEntry & { open: boolean; _closing?: boolean }

const teleportReady = ref(false)
onMounted(() => {
  teleportReady.value = !!document.getElementById('overlay-root')
})

// z-index policy: explicit and stable
const baseZ = 60
const zStep = 10

// Local rendered stack (can include "closing" entries not present in store stack anymore)
const rendered = ref<RenderedEntry[]>([])

// Keep rendered list in sync with store stack.
// - New entries => add as open=true
// - Removed entries => if we still have them rendered and open, mark them closing (open=false)
//   so their own leave transition can run, then remove on after-leave.
watch(
  stack,
  (next) => {
    const nextIds = new Set(next.value.map((e) => e.id))

    // Add / update entries from store stack
    for (const entry of next.value) {
      const existing = rendered.value.find((r) => r.id === entry.id)
      if (!existing) {
        rendered.value.push({ ...entry, open: true })
      } else {
        // Keep props fresh in case caller updates them
        existing.type = entry.type
        existing.props = entry.props
        existing.closeOnBackdrop = entry.closeOnBackdrop
        existing.closeOnEsc = entry.closeOnEsc
        // If it was closing but re-opened, flip back open
        if (existing._closing) {
          existing._closing = false
          existing.open = true
        }
      }
    }

    // Mark removed entries as closing (don’t instantly drop from DOM)
    for (const r of rendered.value) {
      if (!nextIds.has(r.id) && !r._closing) {
        r._closing = true
        r.open = false
        // Fallback: if overlay doesn't emit after-leave, remove after a grace delay.
        // This avoids stuck layers without forcing RAF hacks.
        window.setTimeout(() => {
          // If still closing, finalize.
          const still = rendered.value.find((x) => x.id === r.id)
          if (still?._closing) finalizeClose(r.id)
        }, 350) // should be >= your leave duration
      }
    }

    // Ensure ordering matches store stack order, with closing entries staying behind.
    // Strategy: keep store entries in order, then append any closing leftovers (already in DOM).
    const ordered: RenderedEntry[] = []
    for (const entry of next.value) {
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

/**
 * Close request from overlay UI.
 * We close via the central store, then our watcher will mark it closing (open=false)
 * and keep it rendered until after-leave.
 */
function requestClose(id: string) {
  close(id)
}

/**
 * Overlays that support transition completion should emit `after-leave`
 * when their leave TransitionRoot finishes. Host will then remove the layer.
 */
function finalizeClose(id: string) {
  const idx = rendered.value.findIndex((r) => r.id === id)
  if (idx >= 0) {
    rendered.value.splice(idx, 1)
  }
}
</script>

<style scoped>
/* Host guarantees that only the top overlay layer is interactive */
.if-overlay-host__layer--inactive {
  pointer-events: none;
}
</style>
