import { readFileSync } from 'node:fs';

import { describe, expect, it } from 'vitest';

const attendanceAnalyticsSource = readFileSync(
	new URL('../analytics/AttendanceAnalytics.vue', import.meta.url),
	'utf8'
);

describe('AttendanceAnalytics shell contract', () => {
	it('mounts in the canonical analytics shell', () => {
		expect(attendanceAnalyticsSource).toContain('class="analytics-shell attendance-analytics-shell"');
	});

	it('does not override the shared analytics shell width', () => {
		expect(attendanceAnalyticsSource).not.toMatch(/max-width:\s*none\s*;/);
	});

	it('requests programs from the selected school scope instead of globally', () => {
		expect(attendanceAnalyticsSource).toMatch(/fetchPrograms\(\{\s*school:\s*filters\.school,?\s*\}\)/s);
		expect(attendanceAnalyticsSource).not.toContain('programs.value = await attendanceService.fetchPrograms();');
	});

	it('keeps window presets in the page header actions instead of the filter grid', () => {
		expect(attendanceAnalyticsSource).toMatch(
			/page-header__actions">[\s\S]*<DateRangePills[\s\S]*:model-value="preset"[\s\S]*<\/div>/s
		);
		expect(attendanceAnalyticsSource).not.toMatch(/<label class="type-label">Window<\/label>/);
	});
});
