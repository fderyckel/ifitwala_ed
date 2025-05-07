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


  /* ─── Main content containers ───────────────────────────────── */
  $(wrapper).append(`
		<div class="dashboard-overlay" id="dashboard-overlay"></div>
		<div class="dashboard-content container">
				<div class="dashboard-card" id="student-log-detail">
						<div class="student-log-filter">
							<label for="student-select">Student</label>
							<input type="text" id="student-select" placeholder="Select Student" autocomplete="off">
							<div id="student-dropdown" class="student-dropdown"></div>
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
			if (query.length > 0) {
					const filters = {
							school: page.fields_dict.school.get_value(),
							program: page.fields_dict.program.get_value(),
							academic_year: page.fields_dict.academic_year.get_value(),
					};

					frappe.call({
							method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_distinct_students",
							args: { filters: JSON.stringify(filters) },
							callback: (r) => {
									if (r.message && !r.message.error) {
											const suggestions = r.message.map(s => `
													<div class="student-suggestion" data-name="${s.student}">
															${s.student} - ${s.student_name}
													</div>
											`).join("");
											showStudentSuggestions(suggestions);
									}
							},
					});
			} else {
					hideStudentSuggestions();  // Clear suggestions when input is empty
			}
	});

	function showStudentSuggestions(suggestions) {
			const dropdown = document.getElementById("student-dropdown");
			dropdown.innerHTML = suggestions;
			dropdown.style.display = "block";

			// Handle suggestion click
			dropdown.addEventListener("click", (e) => {
					const selectedStudent = e.target.getAttribute("data-name");
					if (selectedStudent) {
							studentInput.value = selectedStudent;
							fetch_student_logs(selectedStudent);
							hideStudentSuggestions();
					}
			});
	}

	function hideStudentSuggestions() {
			const dropdown = document.getElementById("student-dropdown");
			dropdown.innerHTML = "";
			dropdown.style.display = "none";
	}

	// Close dropdown on outside click
	document.addEventListener("click", (e) => {
			const dropdown = document.getElementById("student-dropdown");
			if (e.target !== studentInput && !dropdown.contains(e.target)) {
					hideStudentSuggestions();
			}
	});



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

