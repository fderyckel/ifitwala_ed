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
});
