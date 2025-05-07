/*
 * Student Log Dashboard – Ifitwala_Ed
 * Updated: 2025‑05‑07
 * Frappe v15 compatible
 */

// ───────────────────────────────────────────────────────────────
frappe.pages["student-log-dashboard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Student Log Dashboard",
    single_column: true,
  });

  /* ─── Filter fields (cascading logic) ───────────────────────── */
  const school_field = page.add_field({
    fieldname: "school",
    label: __("School"),
    fieldtype: "Link",
    options: "School",
    change: () => {
      program_field.set_value("");
      student_field.set_value("");
      fetch_dashboard_data(page);
    },
  });

  const program_field = page.add_field({
    fieldname: "program",
    label: __("Program"),
    fieldtype: "Link",
    options: "Program",
    get_query: () => ({
      filters: {
        ...(school_field.get_value() && { school: school_field.get_value() }),
      },
    }),
    change: () => {
      student_field.set_value("");
      fetch_dashboard_data(page);
    },
  });

  const academic_year_field = page.add_field({
    fieldname: "academic_year",
    label: __("Academic Year"),
    fieldtype: "Link",
    options: "Academic Year",
    change: () => fetch_dashboard_data(page),
  });

  const author_field = page.add_field({
    fieldname: "author",
    label: __("Author"),
    fieldtype: "Link",
    options: "Employee",
    change: () => fetch_dashboard_data(page),
  });

  /* ─── CSS STYLES ───────────────────────────────── */
	// Inject custom CSS
	const style = document.createElement('style');
	style.innerHTML = `
		.dashboard-card {
			background: #fff;
			border-radius: 8px;
			box-shadow: 0 2px 5px rgba(0,0,0,0.1);
			margin: 10px;
			padding: 20px;
			transition: transform 0.3s ease, box-shadow 0.3s ease;
			cursor: pointer;
			flex: 1 1 calc(50% - 40px); 
			max-width: calc(50% - 40px); 
		}
		.dashboard-card:hover {
			transform: scale(1.02);
			box-shadow: 0 4px 10px rgba(0,0,0,0.15);
		}
		.dashboard-card.zoomed {
			position: fixed;
			top: 50%;
			left: 50%;
			transform: translate(-50%, -50%);
			z-index: 1000;
			width: 90vw;
			height: 90vh;
			overflow: auto;
			max-width: 1200px;  
			max-height: 800px; 
		}
		.dashboard-card.zoomed .frappe-chart {
			width: 100% !important;
			height: 100% !important;
		}	
		.dashboard-card.zoomed .card-body {
			width: 100%;
			height: 100%;
			padding: 0;
			display: flex;
			justify-content: center;
			align-items: center;			
		}
		.dashboard-overlay {
			position: fixed;
			top: 0;
			left: 0;
			width: 100%;
			height: 100%;
			background: rgba(0,0,0,0.5);
			z-index: 999;
			display: none;
		}
		.dashboard-overlay.active {
			display: block;
		}
		.dashboard-content.container {
			display: flex;
			flex-wrap: wrap;
			gap: 20px;
			justify-content: space-between;
			margin-bottom: 20px;
		}
		.student-log-filter {
				margin-bottom: 10px;
		}
		.student-log-table-wrapper {
				max-height: 400px;
				overflow-y: auto;
				border: 1px solid #ddd;
				border-radius: 8px;
		}
		.student-log-table th, .student-log-table td {
				padding: 8px 12px;
				border-bottom: 1px solid #f0f0f0;
		}
		.student-log-table th {
				background-color: #f7f7f7;
				position: sticky;
				top: 0;
				z-index: 1;
		}
		.student-dropdown {
				position: absolute;
				background: #fff;
				border: 1px solid #ddd;
				border-radius: 4px;
				width: 100%;
				max-height: 200px;
				overflow-y: auto;
				z-index: 1000;
				margin-top: 5px;
		}
		.student-suggestion {
				padding: 8px 12px;
				cursor: pointer;
		}
		.student-suggestion:hover {
				background-color: #f0f0f0;
		}

		.full-size {
			width: 100%;
			height: 100%;
		}

		@media (max-width: 768px) {
			.dashboard-card {
				flex: 1 1 100%;
				max-width: 100%;
			}
		}
	`;
	document.head.appendChild(style);

  /* ─── Main content containers ───────────────────────────────── */
  $(wrapper).append(`
		<div class="dashboard-overlay" id="dashboard-overlay"></div>
		<div class="dashboard-content container">
				<div class="dashboard-card" id="student-log-detail">
						<div class="student-log-filter">
								<label for="student-select">Student</label>
								<input type="text" id="student-select" placeholder="Select Student" autocomplete="off">
						</div>
						<div class="student-log-table-wrapper">
								<table class="student-log-table">
										<thead>
												<tr>
														<th>Date</th>
														<th>Log Type</th>
														<th>Log Content</th>
														<th>Author</th>
												</tr>
										</thead>
										<tbody id="student-log-table-body"></tbody>
								</table>
						</div>
				</div>
				<div class="dashboard-card" id="log-type-count"></div>
				<div class="dashboard-card" id="logs-by-cohort"></div>
				<div class="dashboard-card" id="logs-by-program"></div>
				<div class="dashboard-card" id="logs-by-author"></div>
				<div class="dashboard-card" id="next-step-types"></div>
				<div class="dashboard-card" id="incidents-over-time"></div>
				<div class="dashboard-card" id="open-follow-ups"></div>
		</div>
	`);

	// Student filter logic
	const studentInput = document.getElementById("student-select");
	studentInput.addEventListener("input", () => {
			const query = studentInput.value.trim();
			if (query.length > 2) {
					frappe.call({
							method: "frappe.desk.search.search_link",
							args: {
									doctype: "Student",
									txt: query,
									filters: {
											school: page.fields_dict.school.get_value(),
											program: page.fields_dict.program.get_value(),
											academic_year: page.fields_dict.academic_year.get_value(),
									},
									limit: 10,
							},
							callback: (r) => {
									if (r.message) {
											const suggestions = r.message.map(s => `
													<div class="student-suggestion" data-name="${s.value}">
															${s.value} - ${s.description}
													</div>
											`).join("");
											showStudentSuggestions(suggestions);
									}
							},
					});
			}
	});

	function showStudentSuggestions(suggestions) {
			const dropdown = document.createElement("div");
			dropdown.classList.add("student-dropdown");
			dropdown.innerHTML = suggestions;
			document.getElementById("student-log-detail").appendChild(dropdown);

			// Handle suggestion click
			dropdown.addEventListener("click", (e) => {
					const selectedStudent = e.target.getAttribute("data-name");
					if (selectedStudent) {
							studentInput.value = selectedStudent;
							fetch_student_logs(selectedStudent);
							dropdown.remove();
					}
			});

			// Close on outside click
			document.addEventListener("click", (e) => {
				if (!dropdown.contains(e.target) && e.target !== studentInput) {
					dropdown.remove();
				}
			}, { once: true });
	}

	function fetch_student_logs(student_id) {
    frappe.call({
        method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_student_logs",
        args: { student_id },
        callback: (r) => {
            if (r.message) {
                const logs = r.message;
                const rows = logs.map(log => `
                    <tr>
                        <td>${log.date}</td>
                        <td>${log.log_type}</td>
                        <td>${log.content}</td>
                        <td>${log.author}</td>
                    </tr>
                `).join("");
                document.getElementById("student-log-table-body").innerHTML = rows;
            }
        },
    });
	}

	// Keep this inside on_page_load
	function toggleZoom(card) {
		if (card.classList.contains('zoomed')) {
			card.classList.remove('zoomed');
			document.getElementById('dashboard-overlay').classList.remove('active');
		} else {
			// Remove zoom from any other card
			document.querySelectorAll('.dashboard-card.zoomed').forEach(c => {
				if (c !== card) c.classList.remove('zoomed');
			});
			card.classList.add('zoomed');
			document.getElementById('dashboard-overlay').classList.add('active');
		}
	}

	// Add event listeners to cards
	document.querySelectorAll('.dashboard-card').forEach(card => {
		card.addEventListener('click', () => toggleZoom(card));
	});

	// Close zoom when overlay is clicked
	const overlay = document.getElementById('dashboard-overlay');
	overlay.addEventListener('click', () => {
		document.querySelectorAll('.dashboard-card.zoomed').forEach(c => c.classList.remove('zoomed'));
		overlay.classList.remove('active');
	});		

  // initial load
  fetch_dashboard_data(page);
};

// ───────────────────────────────────────────────────────────────
// helpers
const safe = (arr) => (Array.isArray(arr) ? arr : []);

// ───────────────────────────────────────────────────────────────
function fetch_dashboard_data(page) {
  const filters = {
    school: page.fields_dict.school.get_value(),
    academic_year: page.fields_dict.academic_year.get_value(),
    program: page.fields_dict.program.get_value(),
    student: page.fields_dict.student ? page.fields_dict.student.get_value() : null,
    author: page.fields_dict.author.get_value(),
  };

  frappe.call({
    method:
      "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_dashboard_data",
    args: { filters },
    callback: (r) => {
      if (r.message) {
        console.log("Dashboard data loaded:", r.message);
        update_charts(r.message);
      }
    },
  });
}

// ───────────────────────────────────────────────────────────────
function update_charts(data) {
  new frappe.Chart("#log-type-count", {
    data: {
      labels: safe(data.logTypeCount).map((i) => i.label),
      datasets: [{ values: safe(data.logTypeCount).map((i) => i.value) }],
    },
    type: "bar",
    height: 300,
    colors: ["#007bff"],
    title: "Log Type Count",
  });

  new frappe.Chart("#logs-by-cohort", {
    data: {
      labels: safe(data.logsByCohort).map((i) => i.label),
      datasets: [{ values: safe(data.logsByCohort).map((i) => i.value) }],
    },
    type: "bar",
    height: 300,
    colors: ["#17a2b8"],
    title: "Logs by Cohort",
  });

  new frappe.Chart("#logs-by-program", {
    data: {
      labels: safe(data.logsByProgram).map((i) => i.label),
      datasets: [{ values: safe(data.logsByProgram).map((i) => i.value) }],
    },
    type: "bar",
    height: 300,
    colors: ["#28a745"],
    title: "Logs by Program",
  });

  new frappe.Chart("#logs-by-author", {
    data: {
      labels: safe(data.logsByAuthor).map((i) => i.label),
      datasets: [{ values: safe(data.logsByAuthor).map((i) => i.value) }],
    },
    type: "bar",
    height: 300,
    colors: ["#ffc107"],
    title: "Logs by Author",
  });

  new frappe.Chart("#next-step-types", {
    data: {
      labels: safe(data.nextStepTypes).map((i) => i.label),
      datasets: [{ values: safe(data.nextStepTypes).map((i) => i.value) }],
    },
    type: "bar",
    height: 300,
    colors: ["#fd7e14"],
    title: "Next Step Types",
  });

  new frappe.Chart("#incidents-over-time", {
    data: {
      labels: safe(data.incidentsOverTime).map((i) => i.label),
      datasets: [
        { values: safe(data.incidentsOverTime).map((i) => i.value) },
      ],
    },
    type: "line",
    height: 300,
    colors: ["#dc3545"],
    title: "Incidents Over Time",
  });

  $("#open-follow-ups").html(`
		<div class="card full-size">
			<div class="card-body text-center">
				<h2>${data.openFollowUps}</h2>
				<p class="text-muted">Open Follow‑Ups</p>
			</div>
		</div>
	`);
}

