<!-- ui-spa/src/components/overlay/OverlayHost.vue -->
<template>
  <Teleport v-if="teleportReady" to="#overlay-root">
    <div v-if="stack.length" class="if-overlay-host">
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
import { onMounted, ref } from 'vue'
import { useOverlayStack, type OverlayType } from '@/composables/useOverlayStack'

import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue'
import MeetingEventModal from '@/components/calendar/MeetingEventModal.vue'
import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue'
import ClassEventModal from '@/components/calendar/ClassEventModal.vue'

const { stack, close } = useOverlayStack()

// Keep z-index explicit in the stack.
// (Base here is higher than page content; panel z-index is set inline on each overlay root.)
const baseZ = 60
const zStep = 10

const teleportReady = ref(false)
onMounted(() => {
  teleportReady.value = !!document.getElementById('overlay-root')
})

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

function handleClose(id: string) {
  close(id)
}
</script>
