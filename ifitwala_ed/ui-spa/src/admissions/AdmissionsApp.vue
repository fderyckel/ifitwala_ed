<!-- ifitwala_ed/ui-spa/src/admissions/AdmissionsApp.vue -->

<template>
	<div id="overlay-root"></div>

	<AdmissionsLayout>
		<RouterView />
	</AdmissionsLayout>

	<OverlayHost />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router';
import AdmissionsLayout from '@/layouts/AdmissionsLayout.vue';
import OverlayHost from '@/overlays/OverlayHost.vue';
</script>
