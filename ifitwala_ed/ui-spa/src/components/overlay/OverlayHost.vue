<!-- ui-spa/src/components/overlay/OverlayHost.vue -->

<template>
  <Teleport v-if="teleportReady" to="#overlay-root">
    <div v-if="stack.length" class="overlay-host">
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

const { stack, close } = useOverlayStack()

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
    default:
      return CreateTaskDeliveryOverlay
  }
}

function handleClose(id: string) {
  close(id)
}
</script>

<style scoped>
.overlay-host {
  position: fixed;
  inset: 0;
  z-index: 99;
  pointer-events: auto;
}
</style>
