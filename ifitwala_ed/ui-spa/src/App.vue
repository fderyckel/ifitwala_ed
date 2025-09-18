<template>
  <PortalLayout>
    <RouterView />
  </PortalLayout>
</template>

<script setup>
import { RouterView } from 'vue-router';
import PortalLayout from './layouts/PortalLayout.vue';
</script>
