export type StaffTimetableExportPreset = 'this_week' | 'next_2_weeks' | 'next_month';

const STAFF_TIMETABLE_EXPORT_METHOD = 'ifitwala_ed.api.calendar.export_staff_timetable_pdf';

export const STAFF_TIMETABLE_EXPORT_PRESETS: Array<{
	id: StaffTimetableExportPreset;
	label: string;
	copy: string;
}> = [
	{
		id: 'this_week',
		label: 'This week',
		copy: 'Current Monday to Sunday planning spread.',
	},
	{
		id: 'next_2_weeks',
		label: 'Next 2 weeks',
		copy: 'Two consecutive weekly spreads from this week.',
	},
	{
		id: 'next_month',
		label: 'Next month',
		copy: 'Next calendar month, arranged as weekly pages.',
	},
];

export function buildStaffTimetableExportUrl(preset: StaffTimetableExportPreset): string {
	const params = new URLSearchParams({ preset });
	return `/api/method/${STAFF_TIMETABLE_EXPORT_METHOD}?${params.toString()}`;
}
