/**********************************************************************
 * Instructor Schedule Calendar – simple CDN loader version
 * (use v6.1.8 “index.global” build just like your school calendar)
 *********************************************************************/

frappe.pages["schedule_calendar"].on_page_load = function (wrapper) {
	// ---- FullCalendar CSS --------------------------------------------------
	const fc_css = document.createElement("link");
	fc_css.rel  = "stylesheet";
	fc_css.href = "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css";
	document.head.appendChild(fc_css);

	// ---- FullCalendar JS ---------------------------------------------------
	const script = document.createElement("script");
	script.src   = "https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js";
	script.onload = () => render_schedule_calendar_page(wrapper);
	document.head.appendChild(script);
};

// ────────────────────────────────────────────────────────────────────────────
function render_schedule_calendar_page(wrapper) {
	// -----------------------------------------------------------------------
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Instructor Schedule Calendar"),
		single_column: true
	});
	page.set_primary_action(__("Refresh"), () => cal.refetchEvents(), "refresh");

	const roles          = frappe.user_roles || [];
	const is_acad_admin  = roles.includes("Academic Admin");
	const is_plain_instr = roles.includes("Instructor") && !is_acad_admin;

	// -----------------------------------------------------------------------
	// build filters
	let fld_instructor, fld_year, cal;

	frappe.call("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_default_instructor")
		.then(r => build_filters(r.message));

	frappe.call("ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_default_instructor")
		.then(r => {
			const default_instructor = r.message;
			return frappe.call(
				"ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_default_academic_year"
			).then(yr => {
				const default_year = yr.message;
				build_filters(default_instructor, default_year);
			});
		});


	function build_filters(default_instr, default_year) {
		// Instructor selector
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

		// Academic Year selector
		fld_year = page.add_field({
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			default: default_year,
			change() { if (cal) cal.refetchEvents(); }
		});

		if (is_plain_instr) fld_instructor.$wrapper.hide();   // keep value, just hide

		build_calendar();
	}

	// -----------------------------------------------------------------------
	function build_calendar() {
		const $container = $('<div id="instructor-cal">').appendTo(page.body);

		cal = new FullCalendar.Calendar($container[0], {
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
			eventSources: [{
				events: fetch_events
			}],
			eventDidMount(info) {
				const p = info.event.extendedProps || {};
				if (p.block_type || p.location) {
					const tip = [
						p.block_type ? __("Type") + ": " + p.block_type : "",
						p.location   ? __("Room") + ": " + p.location   : ""
					].filter(Boolean).join("<br>");
					$(info.el).tooltip({ title: tip, html: true, container: "body" });
				}
			}
		});

		cal.render();
	}

	// -----------------------------------------------------------------------
	function fetch_events(fetchInfo, success, failure) {
		const filters = {
			instructor: fld_instructor ? fld_instructor.get_value() : null,
			academic_year: fld_year ? fld_year.get_value() : null
		};

		frappe.call({
			method: "ifitwala_ed.schedule.page.schedule_calendar.schedule_calendar.get_instructor_events",
			args: {
				start: fetchInfo.startStr,
				end:   fetchInfo.endStr,
				filters
			},
			callback(r) {
				success(r.message || []);
			},
			error: () => {
				console.error(__("Failed to load calendar data"));
				failure();
			}
		});
	}
}
