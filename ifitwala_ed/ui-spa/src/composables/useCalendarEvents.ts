// ifitwala_ed/ui-spa/src/composables/useCalendarEvents.ts
import { call } from 'frappe-ui';
import { Ref, computed, ref } from 'vue';

export type CalendarSource = 'student_group' | 'meeting' | 'school_event' | 'frappe_event';

export interface PortalCalendarEvent {
	id: string;
	title: string;
	start: string;
	end: string;
	allDay: boolean;
	source: CalendarSource;
	color: string;
	meta: Record<string, unknown>;
}

export interface CalendarPayload {
	timezone: string;
	window: { from: string; to: string };
	generated_at: string;
	sources: CalendarSource[];
	counts: Record<string, number>;
	events: PortalCalendarEvent[];
}

const DEFAULT_SOURCES: CalendarSource[] = ['student_group', 'meeting', 'school_event', 'frappe_event'];
const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes
const STORAGE_PREFIX = 'ifw:calendar:';

interface CacheEntry {
	timestamp: number;
	data: CalendarPayload;
}

interface FetchOptions {
	reason?: 'manual' | 'range-change' | 'visibility' | 'interval';
	force?: boolean;
}

export interface CalendarComposableOptions {
	role?: 'staff' | 'student' | 'guardian';
	sources?: CalendarSource[];
}

const memoryCache = new Map<string, CacheEntry>();

function makeRangeKey(range: { start: string; end: string }) {
	return `${range.start}__${range.end}`;
}

function makeSourceKey(sources: Iterable<CalendarSource>) {
	return Array.from(new Set(sources)).sort().join(',');
}

function makeCacheKey(role: string, rangeKey: string, sources: Iterable<CalendarSource>) {
	return `${role}:${makeSourceKey(sources)}:${rangeKey}`;
}

function getSessionStorage(): Storage | null {
	if (typeof window === 'undefined' || typeof window.sessionStorage === 'undefined') {
		return null;
	}
	return window.sessionStorage;
}

function readCache(cacheKey: string): CacheEntry | null {
	const entry = memoryCache.get(cacheKey);
	if (entry && Date.now() - entry.timestamp < CACHE_TTL_MS) {
		return entry;
	}

	try {
		const storage = getSessionStorage();
		if (!storage) return null;
		const stored = storage.getItem(STORAGE_PREFIX + cacheKey);
		if (!stored) return null;
		const parsed = JSON.parse(stored) as CacheEntry;
		if (Date.now() - parsed.timestamp < CACHE_TTL_MS) {
			memoryCache.set(cacheKey, parsed);
			return parsed;
		}
		storage.removeItem(STORAGE_PREFIX + cacheKey);
	} catch (err) {
		console.warn('[calendar] Failed to read cache', err);
	}

	return null;
}

function writeCache(cacheKey: string, payload: CalendarPayload) {
	const entry: CacheEntry = { timestamp: Date.now(), data: payload };
	memoryCache.set(cacheKey, entry);
	try {
		const storage = getSessionStorage();
		if (storage) {
			storage.setItem(STORAGE_PREFIX + cacheKey, JSON.stringify(entry));
		}
	} catch (err) {
		// best effort only
	}
}

function clearCache(cacheKey: string) {
	memoryCache.delete(cacheKey);
	try {
		const storage = getSessionStorage();
		if (storage) {
			storage.removeItem(STORAGE_PREFIX + cacheKey);
		}
	} catch (err) {
		// best effort
	}
}

function unwrapResponse(response: unknown) {
	if (response && typeof response === 'object' && 'message' in response) {
		return (response as Record<string, unknown>).message;
	}
	return response;
}

export function useCalendarEvents(options: CalendarComposableOptions = {}) {
	const role = options.role ?? 'staff';

	const events: Ref<PortalCalendarEvent[]> = ref([]);
	const counts: Ref<Record<string, number>> = ref({});
	const timezone = ref('UTC');
	const loading = ref(false);
	const error = ref<string | null>(null);
	const lastUpdated = ref<number | null>(null);

	const activeSources = ref<Set<CalendarSource>>(new Set(options.sources ?? DEFAULT_SOURCES));
	const currentRange = ref<{ start: string; end: string } | null>(null);

	async function fetchRange(range: { start: string; end: string }, opts: FetchOptions = {}) {
		if (!range.start || !range.end) return;
		currentRange.value = range;
		const rangeKey = makeRangeKey(range);
		const cacheKey = makeCacheKey(role, rangeKey, activeSources.value);

		if (opts.force) {
			clearCache(cacheKey);
		}

		if (!opts.force) {
			const cached = readCache(cacheKey);
			if (cached) {
				applyPayload(cached.data, false);
				// No need to re-fetch if cache is still fresh
				return;
			}
		}

		loading.value = true;
		error.value = null;

		try {
			const payload = unwrapResponse(
				await call('ifitwala_ed.api.calendar.get_staff_calendar', {
					from_datetime: range.start,
					to_datetime: range.end,
					sources: Array.from(activeSources.value),
					force_refresh: Boolean(opts.force),
				})
			) as CalendarPayload;

			if (payload) {
				writeCache(cacheKey, payload);
				applyPayload(payload, true);
			}
		} catch (err) {
			console.error('[calendar] fetch failed', err);
			error.value = 'Unable to load events right now.';
		} finally {
			loading.value = false;
		}
	}

	function applyPayload(payload: CalendarPayload, updateTimestamp: boolean) {
		events.value = payload.events ?? [];
		counts.value = payload.counts ?? {};
		timezone.value = payload.timezone ?? 'UTC';
		if (updateTimestamp) {
			lastUpdated.value = Date.now();
		}
	}

	function setRange(start: string, end: string, opts?: FetchOptions) {
		return fetchRange({ start, end }, { reason: 'range-change', ...opts });
	}

	function refresh(opts: FetchOptions = {}) {
		if (!currentRange.value) return;
		return fetchRange(currentRange.value, { reason: opts.reason ?? 'manual', force: opts.force });
	}

	function setSources(list: CalendarSource[]) {
		activeSources.value = new Set(list.length ? list : DEFAULT_SOURCES);
		if (currentRange.value) {
			fetchRange(currentRange.value, { reason: 'manual', force: true });
		}
	}

	function toggleSource(source: CalendarSource) {
		const next = new Set(activeSources.value);
		if (next.has(source)) {
			if (next.size === 1) {
				return;
			}
			next.delete(source);
		} else {
			next.add(source);
		}
		setSources(Array.from(next));
	}

	const isEmpty = computed(() => !loading.value && events.value.length === 0);

	return {
		events,
		counts,
		timezone,
		loading,
		error,
		lastUpdated,
		activeSources,
		isEmpty,
		setRange,
		refresh,
		setSources,
		toggleSource,
	};
}
