export function formatPct(value: number | null | undefined, digits = 0) {
	if (value == null || Number.isNaN(value)) return '0%';
	return `${Math.round(Number(value) * 100 * 10 ** digits) / 10 ** digits}%`;
}

export function formatCount(value: number | null | undefined) {
	if (value == null) return '0';
	return new Intl.NumberFormat().format(value);
}

export function formatDate(value?: string | null) {
	if (!value) return '';
	return value.slice(0, 10);
}
