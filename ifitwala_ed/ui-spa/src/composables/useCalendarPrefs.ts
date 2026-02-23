// ifitwala_ed/ui-spa/src/composables/useCalendarPrefs.ts
import { call } from 'frappe-ui';
import { ref } from 'vue';

type Prefs = {
  timezone: string;
  weekendDays: number[]; // FullCalendar day indices 0..6
  defaultSlotMin: string; // HH:MM:SS
  defaultSlotMax: string; // HH:MM:SS
};

const CACHE_TTL_MS = 60 * 60 * 1000; // 1h
const KEY = 'ifw:cal:prefs';

const mem = { ts: 0, data: null as Prefs | null };

function readStore(): Prefs | null {
  if (mem.data && Date.now() - mem.ts < CACHE_TTL_MS) return mem.data;
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { ts: number; data: Prefs };
    if (Date.now() - parsed.ts < CACHE_TTL_MS) {
      mem.ts = parsed.ts;
      mem.data = parsed.data;
      return parsed.data;
    }
    sessionStorage.removeItem(KEY);
  } catch {}
  return null;
}

function writeStore(p: Prefs) {
  mem.ts = Date.now();
  mem.data = p;
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ ts: mem.ts, data: p }));
  } catch {}
}

export function useCalendarPrefs() {
  const prefs = ref<Prefs | null>(readStore());
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetch() {
    if (prefs.value) return prefs.value;
    loading.value = true;
    error.value = null;
    try {
      const res = await call('ifitwala_ed.api.calendar.get_portal_calendar_prefs');
      const data = (res && typeof res === 'object' && 'message' in res) ? (res as any).message : res;
      if (data) {
        prefs.value = data as Prefs;
        writeStore(prefs.value);
      }
      return prefs.value;
    } catch (e) {
      console.error('[calendar] prefs fetch failed', e);
      error.value = 'Unable to load calendar preferences.';
      return null;
    } finally {
      loading.value = false;
    }
  }

  return { prefs, loading, error, fetch };
}
