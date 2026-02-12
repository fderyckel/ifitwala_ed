<!-- ifitwala_ed/ui-spa/src/pages/student/StudentPortfolioFeed.vue -->
<template>
	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<RouterLink :to="{ name: 'student-home' }" class="if-action">Back to Home</RouterLink>
		</div>
		<PortfolioFeedSurface
			actor="student"
			title="My Portfolio + Reflections"
			subtitle="Curate annual evidence, journal continuously, and share approved showcase items with family."
		/>
	</div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import PortfolioFeedSurface from '@/components/portfolio/PortfolioFeedSurface.vue'
</script>
