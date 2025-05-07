frappe.pages['student-log-dashboard'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
			parent: wrapper,
			title: 'Student Log Dashboard',
			single_column: true
	});

	// Add Filters
	let school_field = page.add_field({
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
			change: () => fetch_dashboard_data(page)
	});

	let academic_year_field = page.add_field({
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			change: () => fetch_dashboard_data(page)
	});

	let program_field = page.add_field({
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
			change: () => fetch_dashboard_data(page)
	});

	let student_field = page.add_field({
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
			get_query: () => ({
					filters: {
							...(academic_year_field.get_value() && { academic_year: academic_year_field.get_value() }),
							...(program_field.get_value() && { program: program_field.get_value() })
					}
			}),
			change: () => fetch_dashboard_data(page)
	});

	let author_field = page.add_field({
			fieldname: "author",
			label: __("Author"),
			fieldtype: "Link",
			options: "Employee",
			change: () => fetch_dashboard_data(page)
	});

	// Main Content Area
	$(wrapper).append(`
			<div class="dashboard-content container">
					<div id="log-type-count" class="chart-container"></div>
					<div id="logs-by-cohort" class="chart-container"></div>
					<div id="logs-by-program" class="chart-container"></div>
					<div id="logs-by-author" class="chart-container"></div>
					<div id="next-step-types" class="chart-container"></div>
					<div id="incidents-over-time" class="chart-container"></div>
					<div id="open-follow-ups" class="open-follow-ups-card"></div>
			</div>
	`);

	// Initial Data Load
	fetch_dashboard_data(page);
};

function fetch_dashboard_data(page) {
	let filters = {
			school: page.fields_dict.school.get_value(),
			academic_year: page.fields_dict.academic_year.get_value(),
			program: page.fields_dict.program.get_value(),
			student: page.fields_dict.student.get_value(),
			author: page.fields_dict.author.get_value()
	};

	frappe.call({
			method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_dashboard_data",
			args: { filters },
			callback: function(response) {
					if (response.message) {
							console.log("Dashboard data loaded:", response.message);
							update_charts(response.message);
					}
			}
	});
}

function update_charts(data) {
	// Log Type Count
	new frappe.Chart("#log-type-count", {
		data: {
			labels: safe(data.logTypeCount).map(item => item.label),
			datasets: [{ values: safe(data.logTypeCount).map(item => item.value) }]
		},
		type: 'bar',
    height: 300, 
		colors: ['#007bff'],
    title: 'Log Type Count'
  });

	// Logs by Cohort
	new frappe.Chart("#logs-by-cohort", {
			data: {
				labels: safe(data.logsByCohort).map(item => item.label),
				datasets: [{ values: safe(data.logsByCohort).map(item => item.value) }]
			},
			type: 'bar',
			height: 300,
			colors: ['#17a2b8'],
			title: 'Logs by Cohort'
	});

	// Logs by Program
	new frappe.Chart("#logs-by-program", {
			data: {
					labels: data.logsByProgram.map(item => item.program),
					datasets: [{ values: data.logsByProgram.map(item => item.count) }]
			},
			type: 'bar',
			height: 300,
			colors: ['#28a745'],
			title: 'Logs by Program'
	});

	// Logs by Author
	new frappe.Chart("#logs-by-author", {
			data: {
					labels: data.logsByAuthor.map(item => item.author_name),
					datasets: [{ values: data.logsByAuthor.map(item => item.count) }]
			},
			type: 'bar',
			height: 300,
			colors: ['#ffc107'],
			title: 'Logs by Author'
	});

	// Next Step Types
	new frappe.Chart("#next-step-types", {
			data: {
					labels: data.nextStepTypes.map(item => item.next_step),
					datasets: [{ values: data.nextStepTypes.map(item => item.count) }]
			},
			type: 'bar',
			height: 300,
			colors: ['#fd7e14'],
			title: 'Next Step Types'
	});

	// Incidents Over Time
	new frappe.Chart("#incidents-over-time", {
			data: {
					labels: data.incidentsOverTime.map(item => item.day),
					datasets: [{ values: data.incidentsOverTime.map(item => item.count) }]
			},
			type: 'line',
			height: 300,
			colors: ['#dc3545'],
			title: 'Incidents Over Time'
	});

	// Open Follow-Ups
	$("#open-follow-ups").html(`
			<div class="card">
					<div class="card-body">
							<h2>${data.openFollowUps}</h2>
							<p>Open Follow-Ups</p>
					</div>
			</div>
	`);
}
