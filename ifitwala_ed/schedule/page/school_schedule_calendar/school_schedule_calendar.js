// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages['school_schedule_calendar'].on_page_load = function(wrapper) {
  const script = document.createElement("script");
  script.src = "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js";
  script.onload = () => load_schedule_calendar(wrapper); // load once script finishes
  document.head.appendChild(script);
};

function load_schedule_calendar(wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'School Schedule Calendar',
    single_column: true
  });

  frappe.call({
    method: "ifitwala_ed.schedule.page.school_schedule_calendar.school_schedule_calendar.get_schedule_events",
    callback: function (r) {
      const calendarEl = $('<div id="schedule-calendar" class="mt-4"></div>').appendTo(page.body)[0];

      const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: "dayGridMonth",
        height: "auto",
        events: r.message,
        headerToolbar: {
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek"
        }
      });

      calendar.render();
    }
  });
}
