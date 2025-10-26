<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/App.vue -->

<template>
  <component :is="layoutComponent">
    <RouterView />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import PortalLayout from './layouts/PortalLayout.vue'
import StaffPortalLayout from './layouts/StaffPortalLayout.vue'

const route = useRoute()

const layoutComponent = computed(() => {
  const layout = route.meta?.layout
  if (layout === 'staff') {
    return StaffPortalLayout
  }
  return PortalLayout
})
</script>
