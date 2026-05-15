export type ScheduleCalendarListMetaEvent = {
	start: Date | null;
	end: Date | null;
	allDay: boolean;
	extendedProps?: Record<string, unknown>;
};

type ScheduleCalendarListMetaOptions = {
	locale?: string;
	timeZone?: string;
};

function asRecord(value: unknown): Record<string, unknown> {
	return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function asText(value: unknown): string {
	if (value === null || value === undefined) return '';
	return String(value).trim();
}

function formatTimeValue(
	value: Date,
	{ locale, timeZone }: ScheduleCalendarListMetaOptions = {}
): string {
	return new Intl.DateTimeFormat(locale, {
		hour: 'numeric',
		minute: '2-digit',
		timeZone,
	}).format(value);
}

export function extractScheduleCalendarLocation(event: ScheduleCalendarListMetaEvent): string {
	const extendedProps = asRecord(event.extendedProps);
	const meta = asRecord(extendedProps.meta);
	return asText(meta.location ?? extendedProps.location);
}

export function formatScheduleCalendarTimeLabel(
	event: ScheduleCalendarListMetaEvent,
	options: ScheduleCalendarListMetaOptions = {}
): string {
	if (event.allDay) return 'All day';
	if (!(event.start instanceof Date) || Number.isNaN(event.start.getTime())) return '';

	const startLabel = formatTimeValue(event.start, options);
	if (!(event.end instanceof Date) || Number.isNaN(event.end.getTime())) {
		return startLabel;
	}

	if (event.end.getTime() <= event.start.getTime()) {
		return startLabel;
	}

	const endLabel = formatTimeValue(event.end, options);
	if (!endLabel || endLabel === startLabel) {
		return startLabel;
	}

	return `${startLabel} - ${endLabel}`;
}

export function buildScheduleCalendarListMeta(
	event: ScheduleCalendarListMetaEvent,
	options: ScheduleCalendarListMetaOptions = {}
): string {
	const timeLabel = formatScheduleCalendarTimeLabel(event, options);
	const locationLabel = extractScheduleCalendarLocation(event);
	return [timeLabel, locationLabel].filter(Boolean).join(' | ');
}
