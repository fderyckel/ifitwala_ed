<!-- ui-spa/src/components/overlay/OverlayHost.vue -->

<template>
  <Teleport to="#overlay-root">
    <!-- Host exists only when at least one overlay is open -->
    <div v-if="stack.length" class="overlay-host">
      <!-- Render overlays in stack order -->
      <component
        v-for="(entry, idx) in stack"
        :key="entry.id"
        :is="resolveComponent(entry.type)"
        v-bind="entry.props"
        :open="true"
        :z-index="baseZ + idx * zStep"
        @close="handleClose(entry.id)"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOverlayStack, type OverlayType } from '@/composables/useOverlayStack'

// Phase 0: only one overlay wired
import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue'

const { stack, close } = useOverlayStack()

/**
 * z-index strategy
 * - baseZ must be higher than any legacy modal
 * - step spacing allows future nested overlays
 */
const baseZ = 60
const zStep = 10

function resolveComponent(type: OverlayType) {
  switch (type) {
    case 'create-task':
      return CreateTaskDeliveryOverlay

    // future overlays go here
    // case 'meeting':
    //   return MeetingOverlay

    default:
      // Fail safe: never crash render tree
      return CreateTaskDeliveryOverlay
  }
}

function handleClose(id: string) {
  close(id)
}
</script>

<style scoped>
/**
 * Overlay host must:
 * - sit above app content
 * - allow pointer events
 * - not impose styling decisions
 */
.overlay-host {
  position: fixed;
  inset: 0;
  z-index: 99;
  pointer-events: auto;
}
</style>
