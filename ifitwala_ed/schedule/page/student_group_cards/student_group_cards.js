// Copyright (c) 2025, François de Ryckel
// Tailwind-compliant Desk Page (scoped, no global leakage)

// Load Tailwind-scoped styles
frappe.require("/assets/ifitwala_ed/dist/student_group_cards.min.css");

/* ── Helpers (now embedded directly) ───────────────────────────── */

function slugify(filename) {
	return filename
		.replace(/\.[^.]+$/, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '_')
		.replace(/^_+|_+$/g, '');
}

function get_student_image(original_url) {
	const fallback = '/assets/ifitwala_ed/images/default_student_image.png';
	if (!original_url) return fallback;

	if (original_url.startsWith('/files/gallery_resized/student/')) return original_url;
	if (!original_url.startsWith('/files/student/')) return fallback;

	const base = slugify(original_url.split('/').pop());
	return `/files/gallery_resized/student/thumb_${base}.webp`;
}

function renderStudentCard(student, { thumbSize = 80 } = {}) {
	const student_name   = frappe.utils.escape_html(student.student_name);
	const preferred_name = frappe.utils.escape_html(student.preferred_name || '');
	const student_id     = frappe.utils.escape_html(student.student);

	const thumb_src    = get_student_image(student.student_image);
	const fallback_src = student.student_image || '/assets/ifitwala_ed/images/default_student_image.png';

	// 🎂 Birthday icon
	let birthday_icon = '';
	if (student.birth_date) {
		try {
			const bdate    = frappe.datetime.str_to_obj(student.birth_date);
			const today    = frappe.datetime.str_to_obj(frappe.datetime.now_date());
			const thisYear = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
			const diffDays = Math.floor((thisYear - today) / 86400000);

			if (Math.abs(diffDays) <= 5) {
				const formatted = moment(bdate).format('dddd, MMMM D');
				birthday_icon = `
					<span class="ml-2 text-yellow-500 cursor-pointer"
						  onclick="frappe.msgprint('${__('Birthday:')} ${formatted}')"
						  title="${__('Birthday on {0}', [formatted])}">🎂</span>`;
			}
		} catch {
			// Ignore date parse errors
		}
	}

	// 🚑 Health icon
	let health_icon = '';
	if (student.medical_info) {
		const note = frappe.utils.escape_html(student.medical_info);
		health_icon = `
			<span class="ml-2 text-red-500 font-bold cursor-pointer"
				  onclick='frappe.msgprint({title:"${__('Health Note for {0}', [student_name])}",
										   message:\`${note}\`,indicator:"red"})'
				  title="${__('Health Note Available')}">&#x2716;</span>`;
	}

	return `
		<div class="student-card bg-white rounded-xl p-4 text-center shadow hover:-translate-y-1 transition duration-200">
			<a href="/app/student/${student_id}" target="_blank" rel="noopener">
				<img src="${thumb_src}"
					 onerror="this.onerror=null;this.src='${fallback_src}';"
					 class="student-card-img"
					 loading="lazy">
			</a>
			<div class="mt-3 text-lg font-semibold">
				<a href="/app/student/${student_id}" target="_blank" rel="noopener">${student_name}</a>
				${health_icon}${birthday_icon}
			</div>
			${preferred_name ? `<div class="text-sm text-gray-500 mt-1">${preferred_name}</div>` : ''}
		</div>`;
}

frappe.pages['student_group_cards'].on_page_load = function (wrapper) {

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
			<div class="desk-tw">
				<div class="tw-sticky-title">
					<div id="student-group-title" class="tw-text-center"></div>
				</div>
				<div id="student-cards" class="student-card-grid"></div>
				<div class="tw-flex tw-justify-center tw-mt-6">
					<button id="load-more" class="tw-load-more">
						${__("Load More")}
					</button>
				</div>
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
			$("#student-group-title").html(`
				<h2 class="tw-text-2xl tw-font-semibold tw-text-gray-800">${frappe.utils.escape_html(name)}</h2>
				${subtitle ? `<div class="tw-text-sm tw-text-gray-500 tw-mt-1">${frappe.utils.escape_html(subtitle)}</div>` : ""}
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
