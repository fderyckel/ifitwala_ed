// Copyright (c) 2025, François de Ryckel
// Tailwind-compliant version – no external CSS required

const { renderStudentCard } = frappe.ifitwala_ed.helpers;

frappe.pages['student_group_cards'].on_page_load = function (wrapper) {
	/* ── Breadcrumb ────────────────────────────────────────────────── */
	const urlParams = new URLSearchParams(window.location.search);
	const workspace = urlParams.get('workspace') || 'Academics';
	frappe.breadcrumbs.add({
		label: workspace,
		route: `/app/${workspace.replace(/\s+/g, '-').toLowerCase()}`
	});

	/* ── Page skeleton ─────────────────────────────────────────────── */
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Student Group Cards'),
		single_column: true
	});

	/* ── Filter controls ───────────────────────────────────────────── */
	const program_field = page.add_field({
		fieldname: 'program',
		label: __('Program'),
		fieldtype: 'Link',
		options: 'Program',
		change: clear_and_refresh_group
	});

	const course_field = page.add_field({
		fieldname: 'course',
		label: __('Course'),
		fieldtype: 'Link',
		options: 'Course',
		change: clear_and_refresh_group
	});

	const cohort_field = page.add_field({
		fieldname: 'cohort',
		label: __('Cohort'),
		fieldtype: 'Link',
		options: 'Student Cohort',
		change: clear_and_refresh_group
	});

	const student_group_field = page.add_field({
		fieldname: 'student_group',
		label: __('Student Group'),
		fieldtype: 'Link',
		options: 'Student Group',
		get_query() {
			return {
				filters: {
					...(program_field.get_value() && { program: program_field.get_value() }),
					...(course_field.get_value() && { course: course_field.get_value() }),
					...(cohort_field.get_value() && { cohort: cohort_field.get_value() })
				}
			};
		},
		change() { fetch_students(true); }
	});

	function clear_and_refresh_group() {
		student_group_field.set_value('');
		student_group_field.refresh();
	}

	/* ── Layout container ─────────────────────────────────────────── */
	$(wrapper).append(`
		<div class="sticky top-[65px] bg-white py-3 shadow-sm z-10">
			<div id="student-group-title" class="text-center"></div>
		</div>

		<div id="student-cards" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-6 mt-4 px-4"></div>

		<div class="flex justify-center mt-6">
			<button id="load-more" class="bg-blue-600 text-white px-5 py-2 rounded transition">
				${__('Load More')}
			</button>
		</div>
	`);

	/* ── Pagination state ─────────────────────────────────────────── */
	let start = 0;
	const page_length = 25;
	let total_students = 0;
	let group_info = {};

	/* ── Title helper ─────────────────────────────────────────────── */
	function update_title() {
		const { name, program, course, cohort } = group_info;
		if (!name) return $('#student-group-title').empty();

		const subtitle = [program, course, cohort].filter(Boolean).join(' – ');
		$('#student-group-title').html(`
			<h2 class="text-2xl font-semibold text-gray-800">${frappe.utils.escape_html(name)}</h2>
			${subtitle ? `<div class="text-sm text-gray-500 mt-1">${frappe.utils.escape_html(subtitle)}</div>` : ''}
		`);
	}

	/* ── Fetch + render ───────────────────────────────────────────── */
	function fetch_students(reset = false) {
		const student_group = student_group_field.get_value();
		if (!student_group) return;

		if (reset) {
			start = 0;
			$('#student-cards').empty();
		}

		// loading guard
		$('#load-more').prop('disabled', true).text(__('Loading …'));

		frappe.call({
			method: 'ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_students',
			args: { student_group, start, page_length },
			callback({ message }) {
				start = message.start;
				total_students = message.total;
				group_info = message.group_info || {};

				message.students.forEach(student => {
					$('#student-cards').append(renderStudentCard(student));
				});

				update_title();
			},
			always() {
				const show_more = start < total_students;
				$('#load-more')
					.toggle(show_more)
					.prop('disabled', false)
					.text(__('Load More'));
			}
		});
	}

	/* ── “Load More” handler ──────────────────────────────────────── */
	$('#load-more').on('click', () => fetch_students());
};
