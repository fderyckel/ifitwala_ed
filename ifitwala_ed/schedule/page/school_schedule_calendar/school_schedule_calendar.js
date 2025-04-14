// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages['school_schedule_calendar'].on_page_load = function(wrapper) {

  const script = document.createElement("script");
  script.src = "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js";
  script.onload = () => {
    render_school_schedule_page(wrapper);
  };
  document.head.appendChild(script);
};

function render_school_schedule_page(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'School Schedule Calendar',
    single_column: true
  });

  // Add filter container
  const filterContainer = $(`
    <div class="mb-4">
      <label for="school-filter"><strong>School:</strong></label>
      <select id="school-filter" class="form-control" style="max-width: 300px;">
        <option value="">All Schools</option>
      </select>
    </div>
  `).appendTo(page.body);

  // Fetch schools and populate dropdown
  frappe.db.get_list("School", {
    fields: ["name"]
  }).then(schools => {
    schools.forEach(s => {
      $('#school-filter').append(`<option value="${s.name}">${s.name}</option>`);
    });
  });

  // Calendar DOM container
  const calendarEl = $('<div id="schedule-calendar" class="mt-4"></div>').appendTo(page.body)[0];

  // Load events for initial (all schools)
  load_calendar_events(calendarEl, "");

  // Watch for filter change
  $('#school-filter').on("change", function() {
    const selectedSchool = $(this).val();
    load_calendar_events(calendarEl, selectedSchool);
  });
}

let calendar = null;

function load_calendar_events(calendarEl, school = "") {
  console.log(`[School Schedule Calendar] Loading events for school: ${school || "All"}`);

  frappe.call({
    method: "ifitwala_ed.schedule.page.school_schedule_calendar.school_schedule_calendar.get_schedule_events",
    args: { school },
    callback: function (r) {
      if (!r.message) return;

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

