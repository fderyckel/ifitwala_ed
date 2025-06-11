// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages["school_schedule_calendar"].on_page_load = function (wrapper) {
	// defer page render until the Rollup bundle is in place 
	loadFullCalendarAssets(() => render_school_schedule_page(wrapper)); 
};

function loadFullCalendarAssets(done) { 
	const css = "/assets/ifitwala_ed/dist/fullcalendar.bundle.css"; 
	if (!document.querySelector(`link[href="${css}"]`)) { 
		document.head.append( 
			Object.assign(document.createElement("link"), { rel: "stylesheet", href: css }) 
		); 
	} 
	
	if (window.fullcalendarBundleLoaded) return done(); 
	frappe.require(js, () => { 
		window.fullcalendarBundleLoaded = true; 
		done(); 
	}); 
}

function render_school_schedule_page(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'School Schedule Calendar',
    single_column: true
  });

	/* ── Filters ───────────────────────────────────────────── */ 
	page.add_field({ 
		label: __("School"), 
		fieldtype: "Link", 
		options: "School", 
		fieldname: "school", 
		default: frappe.defaults.get_default("school"), 
		change: refresh_timeline, 
	});

	page.add_field({
		label: __("Academic Year"),
		fieldtype: "Link",
		options: "Academic Year",
		fieldname: "academic_year",
		default: frappe.defaults.get_default("academic_year"),
		change: refresh_timeline,  
	});	

  // Add legend for event colors
  const legend = $(`
		<div class="d-flex flex-wrap align-items-center mb-4" style="gap: 1.5rem;">
			<div class="d-flex align-items-center me-4 mb-2">
				<div style="width:16px; height:16px; background-color: #CAE9FF; border:1px solid #ccc; margin-right:6px;"></div>
				<span>Weekend</span>
			</div>
			<div class="d-flex align-items-center me-4 mb-2">
				<div style="width:16px; height:16px; background-color: #87BCDE; border:1px solid #ccc; margin-right:6px;"></div>
				<span>Holiday</span>
			</div>
			<div class="d-flex align-items-center me-4 mb-2">
				<div style="width:16px; height:16px; background-color: #4caf50; border:1px solid #ccc; margin-right:6px;"></div>
				<span>Course</span>
			</div>
			<div class="d-flex align-items-center me-4 mb-2">
				<div style="width:16px; height:16px; background-color: #2196f3; border:1px solid #ccc; margin-right:6px;"></div>
				<span>Activity</span>
			</div>
			<div class="d-flex align-items-center me-4 mb-2">
				<div style="width:16px; height:16px; background-color: #ff9800; border:1px solid #ccc; margin-right:6px;"></div>
				<span>Recess</span>
			</div>
			<div class="d-flex align-items-center mb-2">
				<div style="width:16px; height:16px; background-color: #9c27b0; border:1px solid #ccc; margin-right:6px;"></div>
				<span>Assembly</span>
			</div>
		</div>
	`).appendTo(page.body);
  
	function refresh_timeline() { 
		const school        = page.fields_dict.school.get_value(); 
		const academic_year = page.fields_dict.academic_year.get_value(); 
		frappe.call({
			method: "ifitwala_ed.school_settings.page.school_schedule_calendar.school_schedule_calendar.get_schedule_events", 
			args: { school, academic_year }, 
			callback: ({ message }) => build_calendar(message), 
		});
	} 
	
	// Calendar DOM container 
	$('<div id="schedule-calendar" class="mt-4"></div>').appendTo(page.body);
	
	// initial load 
	refresh_timeline();

}

let calendar = null;

function build_calendar(events) { 
	if (!events) return; 
	// destroy previous instance (avoids stacking) 
	if (calendar) { 
		calendar.destroy(); 
		calendar = null; 
	}

	calendar = new FullCalendar.Calendar( 
		document.getElementById("schedule-calendar"),
		{ 
			initialView: "dayGridMonth", 
			height: "auto", 
			events, 
			headerToolbar: { 
				left: "prev,next today", 
				center: "title", 
				right: "dayGridMonth,timeGridWeek", 
			}, 
		} 
	); 
	
	calendar.render();
}

