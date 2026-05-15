import { describe, expect, it } from 'vitest';

import {
	buildScheduleCalendarListMeta,
	extractScheduleCalendarLocation,
	formatScheduleCalendarTimeLabel,
} from '@/components/calendar/scheduleCalendarListMeta';

describe('scheduleCalendarListMeta', () => {
	it('formats timed events with time and location for list rows', () => {
		const event = {
			start: new Date('2026-04-28T09:00:00Z'),
			end: new Date('2026-04-28T10:30:00Z'),
			allDay: false,
			extendedProps: {
				meta: {
					location: 'Science Lab',
				},
			},
		};

		expect(
			buildScheduleCalendarListMeta(event, {
				locale: 'en-US',
				timeZone: 'UTC',
			})
		).toBe('9:00 AM - 10:30 AM | Science Lab');
	});

	it('formats all-day events without losing the location hint', () => {
		const event = {
			start: new Date('2026-05-01T00:00:00Z'),
			end: new Date('2026-05-02T00:00:00Z'),
			allDay: true,
			extendedProps: {
				meta: {
					location: 'Main Hall',
				},
			},
		};

		expect(
			formatScheduleCalendarTimeLabel(event, {
				locale: 'en-US',
				timeZone: 'UTC',
			})
		).toBe('All day');
		expect(extractScheduleCalendarLocation(event)).toBe('Main Hall');
		expect(buildScheduleCalendarListMeta(event)).toBe('All day | Main Hall');
	});

	it('omits the separator when no location is available', () => {
		const event = {
			start: new Date('2026-04-28T13:00:00Z'),
			end: new Date('2026-04-28T14:00:00Z'),
			allDay: false,
			extendedProps: {},
		};

		expect(
			buildScheduleCalendarListMeta(event, {
				locale: 'en-US',
				timeZone: 'UTC',
			})
		).toBe('1:00 PM - 2:00 PM');
	});
});
