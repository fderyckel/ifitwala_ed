// ifitwala_ed/ui-spa/src/lib/datetime.ts

type DateInput = string | Date | null | undefined;
type DayStyle = 'numeric' | '2-digit';
type MonthStyle = 'short' | 'long' | 'numeric' | '2-digit';

type FormatOptions = {
	fallback?: string;
	includeWeekday?: boolean;
	includeYear?: boolean;
	day?: DayStyle;
	month?: MonthStyle;
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
