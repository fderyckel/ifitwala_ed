<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffPortfolioFeed.vue -->
<template>
	<div class="staff-shell space-y-4">
		<div class="flex items-center justify-between">
			<RouterLink :to="{ name: 'staff-home' }" class="if-action">
				{{ __('Back to Staff Home') }}
			</RouterLink>
		</div>
		<PortfolioFeedSurface
			actor="staff"
			:title="__('Student Portfolio Review')"
			subtitle="Review curated evidence and reflections by student, program enrollment, year, date, and tag."
		/>
	</div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { __ } from '@/lib/i18n';
import PortfolioFeedSurface from '@/components/portfolio/PortfolioFeedSurface.vue';
</script>
