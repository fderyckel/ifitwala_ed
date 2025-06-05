/**********************************************************************
 * Instructor Schedule Calendar 
 * *
 *********************************************************************/

frappe.require('/assets/ifitwala_ed/dist/ifitwala_ed.bundle.css');

frappe.pages["schedule_calendar"].on_page_load = function (wrapper) { 
	render_schedule_calendar_page(wrapper);   
};

// ───────────────────────────────────────────────────────────────────────────
function render_schedule_calendar_page(wrapper) {

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Instructor Schedule Calendar"),
		single_column: true
	});

	/* ------------------------------------------------------------------ *
	 * Declared FIRST, so it’s initialised (undefined) before any handler *
	 * ------------------------------------------------------------------ */
	let cal            = null;
	let fld_instructor = null;
	let fld_year       = null;
	let fld_calendar   = null;

	page.set_primary_action(__("Refresh"), () => {
		if (cal) cal.refetchEvents();
	}, "refresh");

	const roles          = frappe.user_roles || [];
	const is_acad_admin  = roles.includes("Academic Admin");
	const is_plain_instr = roles.includes("Instructor") && !is_acad_admin;
	const is_sysmgr      = roles.includes("System Manager");

	// ---------------------------------------------------------------------
	// Fetch defaults, then build the filter bar
	// ---------------------------------------------------------------------
	frappe.call("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_default_instructor")
		.then(instrResp => {
			const default_instr = instrResp.message;

			return frappe.call(
				"ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_default_academic_year"
			).then(yrResp => {
				const default_year = yrResp.message || "";

				/* If System Manager has no default year, offer Calendar list
				   otherwise we don’t need the extra dropdown                */
				if (is_sysmgr && !default_year) {
					return frappe.call({
						method: "frappe.client.get_list",
						args:  { doctype: "School Calendar", fields: ["name"], limit_page_length: 0 }
					}).then(calResp => {
						const calendars = calResp.message.map(r => r.name);
						build_filters(default_instr, default_year, calendars);
					});
				}

				build_filters(default_instr, default_year, []);
			});
		});

	// ---------------------------------------------------------------------
	function build_filters(default_instr, default_year, calendars) {

		// — Instructor —
		fld_instructor = page.add_field({
			fieldname: "instructor",
			label: __("Instructor"),
			fieldtype: "Link",
			options: "Instructor",
			reqd: 1,
			default: default_instr,
			get_query: () => ({
				query: "ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.fetch_instructor_options"
			}),
			change() { if (cal) cal.refetchEvents(); }
		});

		// — Academic Year —
		fld_year = page.add_field({
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			default: default_year,      // may be ""
			change() { if (cal) cal.refetchEvents(); }
		});

		// — School Calendar (SysMgr, only if calendars supplied) —
		if (calendars.length) {
			fld_calendar = page.add_field({
				fieldname: "school_calendar",
				label: __("School Calendar"),
				fieldtype: "Link",
				options: "School Calendar",
				change() { if (cal) cal.refetchEvents(); }
			});
			// limit dropdown choices
			fld_calendar.df.get_query = () => ({ filters: { name: ["in", calendars] } });
		}

		if (is_plain_instr) fld_instructor.$wrapper.hide();

		build_calendar();   // create & render FullCalendar
	}

	// ---------------------------------------------------------------------
	function build_calendar() {
		const $div = $('<div id="instructor-cal">').appendTo(page.body);

		cal = new FullCalendar.Calendar($div[0], {
			plugins: [ 
				FullCalendar.timeGridPlugin, 
				FullCalendar.dayGridPlugin, 
				FullCalendar.listPlugin 
			],
			initialView: "timeGridWeek",
			headerToolbar: {
				left:   "prev,next today",
				center: "title",
				right:  "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
			},
			slotMinTime: "06:00:00",
			slotMaxTime: "20:00:00",
			editable: false,
			height: "auto",
			eventSources: [{ events: fetch_events }],
			eventDidMount(info) {
				const p = info.event.extendedProps || {};
				if (p.block_type || p.location) {
					const tip = [
						p.block_type ? __("Type") + ": " + p.block_type : "",
						p.location   ? __("Room") + ": " + p.location   : ""
					].filter(Boolean).join("<br>");
					$(info.el).tooltip({ title: tip, html: true, container: "body" });
				}
			}, 

			eventClick(info) {
				info.jsEvent.preventDefault();   // stop native link behaviour

				// 1️⃣ Quick route to Student Group (keeps teachers productive)
				if (info.event.extendedProps.student_group) {
					frappe.set_route(
						"Form",
						"Student Group",
						info.event.extendedProps.student_group
					);
					return;
				}
			}, 
		});
		cal.render();
	}

	// ---------------------------------------------------------------------
	function fetch_events(fetchInfo, success, failure) {

		const filters = {
			instructor:      fld_instructor ? fld_instructor.get_value() : null,
			academic_year:   fld_year       ? fld_year.get_value()       : null,
			school_calendar: fld_calendar   ? fld_calendar.get_value()   : null
		};

		frappe.call({
			method: "ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_instructor_events",
			args:   { start: fetchInfo.startStr, end: fetchInfo.endStr, filters },
			callback(r) { success(Array.isArray(r.message) ? r.message : []); },
			error()  { console.warn("Calendar data load failed"); failure(); }
		});
	}
}
