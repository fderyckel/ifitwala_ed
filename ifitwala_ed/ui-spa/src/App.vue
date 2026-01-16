<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/App.vue -->

<template>
  <!-- ✅ One canonical overlay root for the whole SPA -->
  <div id="overlay-root"></div>

  <!-- Keep layout behavior identical -->
  <component :is="layoutComponent" :key="layoutKey">
    <RouterView />
  </component>

  <!-- ✅ One canonical overlay host for the whole SPA -->
  <OverlayHost />
</template>


<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import PortalLayout from './layouts/PortalLayout.vue'
import StaffPortalLayout from './layouts/StaffPortalLayout.vue'
import OverlayHost from './components/overlay/OverlayHost.vue'


const route = useRoute()

// Keep last known layout so we never flash to student during meta transitions.
const activeLayout = ref<'student' | 'staff'>('student')

watch(
  () => route.meta?.layout,
  (val) => {
    if (val === 'staff' || val === 'student') {
      activeLayout.value = val
    }
  },
  { immediate: true }
)

const layoutComponent = computed(() => {
  return activeLayout.value === 'staff' ? StaffPortalLayout : PortalLayout
})

// Force a clean remount if layout family changes (rare, but prevents DOM carryover).
const layoutKey = computed(() => activeLayout.value)
</script>
