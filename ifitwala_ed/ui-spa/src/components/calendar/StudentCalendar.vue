<template>
<!--
  StudentCalendar.vue
  FullCalendar wrapper specialized for the Student portal view, showing classes and school events.
  Handles filtering by source (Classes, Meetings, School Events) and interacting with event modals.

  Used by:
  - PortalLayout.vue (or StudentHome.vue)
-->
<!--
  StudentCalendar.vue
  FullCalendar wrapper specialized for the Student portal view, showing classes and school events.

  Used by:
  - PortalLayout.vue (or StudentHome.vue)
-->
  <div class="relative">
    <section class="paper-card schedule-card p-6">
      <header
        class="flex flex-col gap-4 border-b border-[rgb(var(--border-rgb)/0.9)] pb-4 md:flex-row md:items-center md:justify-between"
      >
        <div>
          <h2 class="text-xl font-semibold text-canopy">My Calendar</h2>
          <p class="text-sm text-[rgb(var(--slate-rgb)/0.75)]">
            {{ subtitle }}
          </p>
        </div>

        <div class="flex items-center gap-3 text-xs text-[rgb(var(--slate-rgb)/0.7)]">
          <button
            class="inline-flex items-center gap-2 rounded-full border border-[rgb(var(--border-rgb)/0.95)]
                   bg-white px-3 py-1.5 text-xs font-medium text-[rgb(var(--slate-rgb)/0.9)]
                   shadow-soft transition hover:border-[rgb(var(--leaf-rgb)/0.9)] hover:text-[rgb(var(--leaf-rgb))]"
            @click="calendarResource.fetch"
          >
            <FeatherIcon name="refresh-cw" class="h-4 w-4" :class="{ 'animate-spin': calendarResource.loading }" />
            Refresh
          </button>
        </div>
      </header>

      <!-- Chips row -->
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <!-- Weekend / Full-day toggles -->
        <div class="mr-auto flex items-center gap-3 text-xs">
          <button
            class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-medium transition"
            :class="
              showWeekends
                ? 'border-[rgb(var(--border-rgb)/0.9)] bg-white text-[rgb(var(--slate-rgb)/0.9)]'
                : 'border-[rgb(var(--leaf-rgb)/0.9)] bg-[rgb(var(--leaf-rgb)/0.08)] text-[rgb(var(--canopy-rgb))]'
            "
            @click="showWeekends = !showWeekends"
          >
            <FeatherIcon name="calendar" class="h-4 w-4" />
            {{ showWeekends ? 'Show all days' : 'Hide weekends' }}
          </button>
        </div>

        <!-- Source chips -->
        <button
          v-for="chip in sourceChips"
          :key="chip.id"
          type="button"
          class="group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition"
          :class="
            chip.active
              ? chip.activeClass
              : 'border-[rgb(var(--border-rgb)/0.9)] bg-white/80 text-[rgb(var(--slate-rgb)/0.7)] hover:border-[rgb(var(--border-rgb)/1)]'
          "
          @click="toggleChip(chip.id)"
        >
          <span
            class="mr-1 inline-flex h-2.5 w-2.5 rounded-full"
            :class="chip.dotClass"
          ></span>
          {{ chip.label }}
          <span
             v-if="counts[chip.id]"
            class="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-semibold text-[rgb(var(--slate-rgb)/0.7)]"
          >
            {{ counts[chip.id] }}
          </span>
        </button>
      </div>

      <!-- Calendar shell -->
      <div
        class="mt-6 overflow-hidden rounded-2xl border border-[rgb(var(--border-rgb)/0.95)]
               bg-white shadow-soft p-3 sm:p-4"
      >
        <FullCalendar
          ref="calendarRef"
          :options="calendarOptions"
          class="calendar-shell"
        />

        <!-- Loading veil -->
        <div
          v-if="calendarResource.loading"
          class="absolute inset-0 z-10 flex items-center justify-center rounded-3xl bg-white/70 backdrop-blur"
        >
          <div class="flex items-center gap-2 text-sm font-medium text-[rgb(var(--slate-rgb)/0.8)]">
            <FeatherIcon name="loader" class="h-4 w-4 animate-spin" />
            Loading calendar…
          </div>
        </div>
      </div>
    </section>

    <!-- Modals -->
    <MeetingEventModal
      :open="meetingModal.open"
      :loading="meetingModal.loading"
      :error="meetingModal.error"
      :meeting="meetingModal.data"
      @close="closeMeetingModal"
    />
    <SchoolEventModal
      :open="schoolEventModal.open"
      :loading="schoolEventModal.loading"
      :error="schoolEventModal.error"
      :event="schoolEventModal.data"
      @close="closeSchoolEventModal"
    />
    <ClassEventModal
        :open="classEventModal.open"
        :loading="classEventModal.loading"
        :error="classEventModal.error"
        :event="classEventModal.data"
        @close="closeClassEventModal"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, reactive } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import { DatesSetArg, EventClickArg } from '@fullcalendar/core';
import { FeatherIcon, createResource } from 'frappe-ui';
import { api } from '@/lib/client';

// Reuse existing modals
import MeetingEventModal from '@/components/calendar/MeetingEventModal.vue';
import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue';
import ClassEventModal from '@/components/calendar/ClassEventModal.vue';

// Types
import type { MeetingDetails } from '@/components/calendar/meetingTypes';
import type { SchoolEventDetails } from '@/components/calendar/schoolEventTypes';
import type { ClassEventDetails } from '@/components/calendar/classEventTypes';

// Styles
import '@/styles/fullcalendar/core.css';
import '@/styles/fullcalendar/daygrid.css';
import '@/styles/fullcalendar/timegrid.css';
import '@/styles/fullcalendar/list.css';

const props = defineProps<{
  autoRefreshInterval?: number;
}>();

// --- State ---
const showWeekends = ref(false);
// Default visible sources
const activeSources = ref(new Set(['student_group', 'school_event', 'meeting']));
const currentRange = ref<{ start: string; end: string } | null>(null);

// --- Resource ---
const calendarResource = createResource({
  url: 'ifitwala_ed.api.student_calendar.get_student_calendar',
  makeParams() {
    return {
      from_datetime: currentRange.value?.start,
      to_datetime: currentRange.value?.end,
    };
  },
  auto: false,
});

// --- Derived API Data ---
const allEvents = computed(() => calendarResource.data?.events || []);

const filteredEvents = computed(() => {
  return allEvents.value.filter((evt: any) => activeSources.value.has(evt.source));
});

const counts = computed(() => {
  const c: Record<string, number> = {};
  for (const evt of allEvents.value) {
    c[evt.source] = (c[evt.source] || 0) + 1;
  }
  return c;
});

const subtitle = computed(() => {
  const total = filteredEvents.value.length;
  return total ? `${total} event${total === 1 ? '' : 's'} in view` : 'Nothing scheduled';
});

// --- Chip Config ---
const sourcePalette = {
  student_group: {
    label: 'Classes',
    dot: 'bg-blue-500',
    active: 'border-blue-200 bg-blue-50 text-blue-700',
  },
  meeting: {
    label: 'Meetings',
    dot: 'bg-violet-500',
    active: 'border-violet-200 bg-violet-50 text-violet-700',
  },
  school_event: {
    label: 'School Events',
    dot: 'bg-emerald-500',
    active: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  },
} as const;

const sourceChips = computed(() =>
  Object.entries(sourcePalette).map(([id, palette]) => ({
    id,
    label: palette.label,
    active: activeSources.value.has(id),
    dotClass: activeSources.value.has(id) ? palette.dot : 'bg-slate-300',
    activeClass: palette.active,
  }))
);

function toggleChip(id: string) {
  if (activeSources.value.has(id)) {
    activeSources.value.delete(id);
  } else {
    activeSources.value.add(id);
  }
  // Force re-eval of filteredEvents (Vue Set reactivity workaround if needed, usually auto)
  activeSources.value = new Set(activeSources.value);
}

// --- Calendar Options ---
const calendarRef = ref<InstanceType<typeof FullCalendar> | null>(null);
const systemTimezone = ref('local'); 

const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin],
  initialView: 'timeGridWeek',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,listWeek',
  },
  slotMinTime: '07:00:00',
  slotMaxTime: '18:00:00',
  allDaySlot: true,
  height: 'auto',
  displayEventTime: false,
  events: filteredEvents, // reactive
  hiddenDays: [0, 6], // default hide weekends
  eventClick: handleEventClick,
  datesSet: handleDatesSet,
  nowIndicator: true,
});

// Watchers
watch(filteredEvents, (val) => {
  calendarOptions.value.events = val;
});

watch(showWeekends, (val) => {
  calendarOptions.value.hiddenDays = val ? [] : [0, 6];
});

// --- Event Handlers ---
function handleDatesSet(arg: DatesSetArg) {
  currentRange.value = {
    start: arg.startStr,
    end: arg.endStr,
  };
  calendarResource.fetch();
}

function handleEventClick(info: EventClickArg) {
  info.jsEvent.preventDefault();
  const evt = info.event;
  const rawId = evt.id;
  
  if (rawId.startsWith('sg::')) {
     openClassEventModal(rawId);
  } else if (rawId.startsWith('meeting::')) {
     const name = rawId.split('::')[1];
     openMeetingModal(name);
  } else if (rawId.startsWith('school_event::')) {
     const name = rawId.split('::')[1];
     openSchoolEventModal(name);
  }
}


// --- Modals Logic (Reused from ScheduleCalendar) ---
// 1. Class Modal
const classEventModal = reactive<{
    open: boolean;
    loading: boolean;
    error: string | null;
    data: ClassEventDetails | null;
}>({ open: false, loading: false, error: null, data: null });

async function openClassEventModal(eventId: string) {
    classEventModal.open = true;
    classEventModal.loading = true;
    try {
        const payload = await api('ifitwala_ed.api.calendar.get_student_group_event_details', {
            event_id: eventId
        }) as ClassEventDetails;
        classEventModal.data = payload;
    } catch (e: any) {
        classEventModal.error = e.message || 'Error loading class details';
    } finally {
        classEventModal.loading = false;
    }
}
function closeClassEventModal() { classEventModal.open = false; }


// 2. Meeting Modal
const meetingModal = reactive<{
    open: boolean;
    loading: boolean;
    error: string | null;
    data: MeetingDetails | null;
}>({ open: false, loading: false, error: null, data: null });

async function openMeetingModal(meetingName: string) {
    meetingModal.open = true;
    meetingModal.loading = true;
    try {
        const payload = await api('ifitwala_ed.api.calendar.get_meeting_details', {
            meeting: meetingName
        }) as MeetingDetails;
        meetingModal.data = payload;
    } catch (e: any) {
        meetingModal.error = e.message;
    } finally {
        meetingModal.loading = false;
    }
}
function closeMeetingModal() { meetingModal.open = false; }


// 3. School Event Modal
const schoolEventModal = reactive<{
    open: boolean;
    loading: boolean;
    error: string | null;
    data: SchoolEventDetails | null;
}>({ open: false, loading: false, error: null, data: null });

async function openSchoolEventModal(eventName: string) {
    schoolEventModal.open = true;
    schoolEventModal.loading = true;
    try {
         const payload = await api('ifitwala_ed.api.calendar.get_school_event_details', {
            event: eventName
        }) as SchoolEventDetails;
        schoolEventModal.data = payload;
    } catch(e: any) {
        schoolEventModal.error = e.message;
    } finally {
        schoolEventModal.loading = false;
    }
}
function closeSchoolEventModal()  { schoolEventModal.open = false; }

</script>
