// ifitwala_ed/ui-spa/src/lib/analyticsOverlay.ts
import type { useOverlayStack } from '@/composables/useOverlayStack';

type AnalyticsOverlayStack = ReturnType<typeof useOverlayStack>;
type ChartOption = Record<string, unknown>;

export function openAnalyticsChartOverlay(
	overlay: AnalyticsOverlayStack,
	title: string,
	chartOption: ChartOption,
	subtitle?: string | null
) {
	overlay.open('analytics-expand', {
		title,
		chartOption,
		kind: 'chart',
		subtitle: subtitle ?? null,
	});
}

export function openAnalyticsTableOverlay<T extends Record<string, unknown>>(
	overlay: AnalyticsOverlayStack,
	title: string,
	rows: T[],
	subtitle?: string | null
) {
	overlay.open('analytics-expand', {
		title,
		chartOption: {},
		kind: 'table',
		rows,
		subtitle: subtitle ?? null,
	});
}
