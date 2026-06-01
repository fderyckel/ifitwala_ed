<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue -->
<template>
	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<RouterLink :to="{ name: 'guardian-home' }" class="if-action">
				{{ __('Back to Home') }}
			</RouterLink>
		</div>
		<PortfolioFeedSurface
			actor="guardian"
			:title="__('Showcase Portfolio')"
			subtitle="View approved showcase evidence only for linked children, with no access to draft reflections."
		/>
	</div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { __ } from '@/lib/i18n';
import PortfolioFeedSurface from '@/components/portfolio/PortfolioFeedSurface.vue';
</script>
