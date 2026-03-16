<!-- ifitwala_ed/ui-spa/src/apps/admissions/AdmissionsApp.vue -->

<template>
	<div id="overlay-root"></div>

	<AdmissionsLayout>
		<RouterView v-slot="{ Component, route }">
			<component :is="Component" :key="route.fullPath" />
		</RouterView>
	</AdmissionsLayout>

	<OverlayHost />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router';
import AdmissionsLayout from '@/layouts/AdmissionsLayout.vue';
import OverlayHost from '@/overlays/OverlayHost.vue';
</script>
