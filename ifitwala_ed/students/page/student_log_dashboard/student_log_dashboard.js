frappe.pages['student-log-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
			parent: wrapper,
			title: 'Student Log Dashboard',
			single_column: true
	});

	// Create a container for the dashboard content
	let $container = $(wrapper).find('.layout-main-section');
	$container.empty();

	// Add filter section
	$container.append(`
			<div class="filters mb-4">
					<select id="filter-school" class="form-control mb-2"></select>
					<select id="filter-academic-year" class="form-control mb-2"></select>
					<select id="filter-program" class="form-control mb-2"></select>
					<select id="filter-student" class="form-control mb-2"></select>
					<select id="filter-author" class="form-control mb-2"></select>
					<button id="apply-filters" class="btn btn-primary">Apply Filters</button>
			</div>
	`);

	// Add charts section
	$container.append(`
			<div class="charts row">
					<div class="col-md-6"><div id="logTypeCountChart" class="mb-4"></div></div>
					<div class="col-md-6"><div id="logsByCohortChart" class="mb-4"></div></div>
					<div class="col-md-6"><div id="logsByProgramChart" class="mb-4"></div></div>
					<div class="col-md-6"><div id="logsByAuthorChart" class="mb-4"></div></div>
					<div class="col-md-6"><div id="nextStepTypesChart" class="mb-4"></div></div>
					<div class="col-md-6"><div id="incidentsOverTimeChart" class="mb-4"></div></div>
			</div>
	`);

	// Add open follow-ups card
	$container.append(`
			<div class="mt-4">
					<div class="card">
							<div class="card-body">
									<h5 class="card-title">Open Follow-Ups</h5>
									<p id="open-follow-ups" class="card-text">Loading...</p>
							</div>
					</div>
			</div>
	`);

	// Fetch filter data on page load
	frappe.call({
			method: 'ifitwala_ed.students.page.student_log_dashboard.get_filter_data',
			callback: function(response) {
					const { schools, academic_years, programs, students, authors } = response.message;
					populateFilter('filter-school', schools);
					populateFilter('filter-academic-year', academic_years);
					populateFilter('filter-program', programs);
					populateFilter('filter-student', students);
					populateFilter('filter-author', authors);
			}
	});

	// Populate filter dropdowns
	function populateFilter(elementId, data) {
			const select = document.getElementById(elementId);
			select.innerHTML = `<option value="">Select ${elementId.replace('filter-', '').replace('-', ' ').toUpperCase()}</option>`;
			data.forEach(item => {
					select.innerHTML += `<option value="${item.name}">${item.name}</option>`;
			});
	}

	// Apply filters button click
	document.getElementById('apply-filters').addEventListener('click', () => {
			// TODO: Fetch and render charts
			console.log('Filters applied');
	});
};
