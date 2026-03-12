// ifitwala_ed/ui-spa/src/lib/datetime.ts

type DateInput = string | Date | null | undefined;
type DayStyle = 'numeric' | '2-digit';
type MonthStyle = 'short' | 'long' | 'numeric' | '2-digit';
type WeekdayStyle = 'short' | 'long';

type FormatOptions = {
	fallback?: string;
	includeWeekday?: boolean;
	includeYear?: boolean;
	day?: DayStyle;
	month?: MonthStyle;
};

type HumanDateFieldOptions = {
	fallback?: string;
	includeWeekday?: boolean;
	includeYear?: boolean;
	includeOrdinalDay?: boolean;
	weekday?: WeekdayStyle;
	month?: Extract<MonthStyle, 'short' | 'long'>;
};

function resolveAppLocale(): string | undefined {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const bootLang = String(globalAny.frappe?.boot?.lang || '').trim();
	if (bootLang) return bootLang.replace('_', '-');
	const htmlLang = document.documentElement.lang?.trim();
	if (htmlLang) return htmlLang.replace('_', '-');
	return navigator.languages?.[0] || navigator.language || undefined;
}

function resolveSiteTimeZone(): string | undefined {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const siteTz = String(globalAny.frappe?.boot?.sysdefaults?.time_zone || '').trim();
	return siteTz || undefined;
}

export function parseDateInput(value: DateInput): Date | null {
	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? null : value;
	}

	const raw = String(value || '').trim();
	if (!raw) return null;

	const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
	const parsed = new Date(normalized);
	if (!Number.isNaN(parsed.getTime())) return parsed;

	const fallback = new Date(raw);
	return Number.isNaN(fallback.getTime()) ? null : fallback;
}

function buildPartLookup(parts: Intl.DateTimeFormatPart[]): Record<string, string> {
	const lookup: Record<string, string> = {};
	for (const part of parts) {
		if (part.type === 'literal') continue;
		if (!lookup[part.type]) lookup[part.type] = part.value;
	}
	return lookup;
}

function normalizeOptions(options?: FormatOptions) {
	return {
		fallback: options?.fallback ?? '',
		hasFallback: Boolean(options && Object.prototype.hasOwnProperty.call(options, 'fallback')),
		includeWeekday: Boolean(options?.includeWeekday),
		includeYear: Boolean(options?.includeYear),
		day: options?.day ?? 'numeric',
		month: options?.month ?? 'short',
	};
}

function withEnglishOrdinalDay(dayText: string, locale?: string): string {
	const dayNumber = Number.parseInt(dayText, 10);
	if (!Number.isFinite(dayNumber)) return dayText;
	if (!String(locale || '').toLowerCase().startsWith('en')) return String(dayNumber);
	if (dayNumber % 100 >= 11 && dayNumber % 100 <= 13) return `${dayNumber}th`;
	switch (dayNumber % 10) {
		case 1:
			return `${dayNumber}st`;
		case 2:
			return `${dayNumber}nd`;
		case 3:
			return `${dayNumber}rd`;
		default:
			return `${dayNumber}th`;
	}
}

function extractTimeFieldLabel(value?: string | null): string {
	const raw = String(value || '').trim();
	if (!raw) return '';
	const match = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?$/);
	if (!match) return '';
	const hours = match[1]?.padStart(2, '0') || '';
	const minutes = match[2] || '';
	return hours && minutes ? `${hours}:${minutes}` : '';
}

export function formatHumanDateTimeFields(
	dateValue: DateInput,
	timeValue?: string | null,
	options?: HumanDateFieldOptions
): string {
	const fallback = options?.fallback ?? '';
	const rawDate = String(dateValue || '').trim();
	if (!rawDate) return fallback;

	const locale = resolveAppLocale();
	const includeWeekday = options?.includeWeekday ?? true;
	const includeYear = options?.includeYear ?? false;
	const includeOrdinalDay = options?.includeOrdinalDay ?? true;
	const weekday = options?.weekday ?? 'long';
	const month = options?.month ?? 'long';
	const timeLabel = extractTimeFieldLabel(timeValue);
	const dateOnlyMatch = rawDate.match(/^(\d{4})-(\d{2})-(\d{2})$/);

	if (dateOnlyMatch) {
		const yearNumber = Number.parseInt(dateOnlyMatch[1] || '', 10);
		const monthNumber = Number.parseInt(dateOnlyMatch[2] || '', 10);
		const dayNumber = Number.parseInt(dateOnlyMatch[3] || '', 10);
		if (
			Number.isFinite(yearNumber) &&
			Number.isFinite(monthNumber) &&
			Number.isFinite(dayNumber) &&
			monthNumber >= 1 &&
			monthNumber <= 12 &&
			dayNumber >= 1 &&
			dayNumber <= 31
		) {
			try {
				// Use UTC noon so weekday/month/day stay stable for date-only values.
				const stableDate = new Date(Date.UTC(yearNumber, monthNumber - 1, dayNumber, 12, 0, 0));
				const formatter = new Intl.DateTimeFormat(locale, {
					weekday: includeWeekday ? weekday : undefined,
					day: 'numeric',
					month,
					year: includeYear ? 'numeric' : undefined,
					timeZone: 'UTC',
				});
				const parts = buildPartLookup(formatter.formatToParts(stableDate));
				const dayLabel =
					includeOrdinalDay && parts.day ? withEnglishOrdinalDay(parts.day, locale) : parts.day;
				const dateBits: string[] = [];

				if (includeWeekday && parts.weekday) dateBits.push(parts.weekday);
				if (dayLabel) dateBits.push(dayLabel);
				if (parts.month) dateBits.push(parts.month);
				if (includeYear && parts.year) dateBits.push(parts.year);

				const dateLabel = dateBits.join(' ').trim() || formatter.format(stableDate);
				if (dateLabel && timeLabel) return `${dateLabel}, ${timeLabel}`;
				return dateLabel || timeLabel || fallback;
			} catch {
				return fallback || rawDate;
			}
		}
	}

	const parsed = parseDateInput(rawDate);
	if (!parsed) return fallback || rawDate;

	try {
		const formatter = new Intl.DateTimeFormat(locale, {
			weekday: includeWeekday ? weekday : undefined,
			day: 'numeric',
			month,
			year: includeYear ? 'numeric' : undefined,
			hour: timeLabel ? '2-digit' : undefined,
			minute: timeLabel ? '2-digit' : undefined,
			hour12: false,
			timeZone: resolveSiteTimeZone(),
		});
		const parts = buildPartLookup(formatter.formatToParts(parsed));
		const dayLabel =
			includeOrdinalDay && parts.day ? withEnglishOrdinalDay(parts.day, locale) : parts.day;
		const dateBits: string[] = [];

		if (includeWeekday && parts.weekday) dateBits.push(parts.weekday);
		if (dayLabel) dateBits.push(dayLabel);
		if (parts.month) dateBits.push(parts.month);
		if (includeYear && parts.year) dateBits.push(parts.year);

		const resolvedTimeLabel =
			timeLabel || (parts.hour && parts.minute ? `${parts.hour}:${parts.minute}` : '');
		const dateLabel = dateBits.join(' ').trim() || formatter.format(parsed);
		if (dateLabel && resolvedTimeLabel) return `${dateLabel}, ${resolvedTimeLabel}`;
		return dateLabel || resolvedTimeLabel || fallback || rawDate;
	} catch {
		return fallback || rawDate;
	}
}

export function formatLocalizedDate(value: DateInput, options?: FormatOptions): string {
	const normalized = normalizeOptions(options);
	const parsed = parseDateInput(value);
	if (!parsed) return normalized.hasFallback ? normalized.fallback : String(value || '');

	try {
		const formatter = new Intl.DateTimeFormat(resolveAppLocale(), {
			weekday: normalized.includeWeekday ? 'short' : undefined,
			day: normalized.day,
			month: normalized.month,
			year: normalized.includeYear ? 'numeric' : undefined,
			timeZone: resolveSiteTimeZone(),
		});
		const parts = buildPartLookup(formatter.formatToParts(parsed));
		const dateBits: string[] = [];

		if (normalized.includeWeekday && parts.weekday) dateBits.push(parts.weekday);
		if (parts.day) dateBits.push(parts.day);
		if (parts.month) dateBits.push(parts.month);
		if (normalized.includeYear && parts.year) dateBits.push(parts.year);

		if (dateBits.length) return dateBits.join(' ');
		return formatter.format(parsed);
	} catch {
		return normalized.hasFallback ? normalized.fallback : String(value || '');
	}
}

export function formatLocalizedDateTime(value: DateInput, options?: FormatOptions): string {
	const normalized = normalizeOptions(options);
	const parsed = parseDateInput(value);
	if (!parsed) return normalized.hasFallback ? normalized.fallback : String(value || '');

	try {
		const formatter = new Intl.DateTimeFormat(resolveAppLocale(), {
			weekday: normalized.includeWeekday ? 'short' : undefined,
			day: normalized.day,
			month: normalized.month,
			year: normalized.includeYear ? 'numeric' : undefined,
			hour: '2-digit',
			minute: '2-digit',
			hour12: false,
			timeZone: resolveSiteTimeZone(),
		});
		const parts = buildPartLookup(formatter.formatToParts(parsed));
		const dateBits: string[] = [];

		if (normalized.includeWeekday && parts.weekday) dateBits.push(parts.weekday);
		if (parts.day) dateBits.push(parts.day);
		if (parts.month) dateBits.push(parts.month);
		if (normalized.includeYear && parts.year) dateBits.push(parts.year);

		if (parts.hour && parts.minute) {
			const dateLabel = dateBits.join(' ');
			return dateLabel ? `${dateLabel} ${parts.hour}:${parts.minute}` : `${parts.hour}:${parts.minute}`;
		}
		return formatter.format(parsed);
	} catch {
		return normalized.hasFallback ? normalized.fallback : String(value || '');
	}
}
