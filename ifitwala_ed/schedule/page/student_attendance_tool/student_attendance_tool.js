// Copyright (c) 2025, François de Ryckel
// Student Attendance – Desk Page (Bootstrap 5 cards)

/* Student Attendance – Desk Page (Bootstrap 5) */
/* globals frappe */

/* 1 Shared CSS bundle */
frappe.require('/assets/ifitwala_ed/dist/student_group_cards.bundle.css');

/* 2 Helper functions ------------------------------------------- */
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

/* One-time cache of attendance codes shown in the tool */
let ATT_CODES = null;
async function get_attendance_codes() {
	if (!ATT_CODES) {
		ATT_CODES = await frappe.db.get_list('Student Attendance Code', {
			filters: { show_in_attendance_tool: 1 },
			fields: ['attendance_code'],
			order_by: 'display_order asc'
		});
	}
	return ATT_CODES;
}

/* 3 ▪ Card renderer ---------------------------------------------- */
async function renderAttendanceCard(student, selected_code) {
	const codes = await get_attendance_codes();

	const student_name   = frappe.utils.escape_html(student.student_name);
	const preferred_name = frappe.utils.escape_html(student.preferred_name || '');
	const student_id     = frappe.utils.escape_html(student.student);
	const thumb_src      = get_student_image(student.student_image);
	const fallback_src   = student.student_image || '/assets/ifitwala_ed/images/default_student_image.png';

	let birthday_icon = '', health_icon = '';

	if (student.birth_date) {
		try {
			const bdate    = frappe.datetime.str_to_obj(student.birth_date);
			const today    = frappe.datetime.str_to_obj(frappe.datetime.now_date());
			const thisYear = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
			const diffDays = Math.floor((thisYear - today) / 86400000);
			if (Math.abs(diffDays) <= 5) {
				const formatted = moment(bdate).format('dddd, MMMM D');
				birthday_icon = `
					<span class="ms-1 text-warning" role="button"
					      onclick="frappe.msgprint('${__('Birthday:')} ${formatted}')"
					      title="${__('Birthday on {0}', [formatted])}">🎂</span>`;
			}
		} catch {}
	}

	if (student.medical_info) {
		const note = frappe.utils.escape_html(student.medical_info);
		health_icon = `
			<span class="ms-1 text-danger fw-bold" role="button"
			      onclick='frappe.msgprint({title:"${__('Health Note for {0}', [student_name])}",
			                                message:\`${note}\`,indicator:"red"})'
			      title="${__('Health Note Available')}">&#x2716;</span>`;
	}

	const options_html = codes.map(c =>
		`<option value="${c.attendance_code}" ${c.attendance_code === selected_code ? 'selected' : ''}>${c.attendance_code}</option>`
	).join('');

	async function renderAttendanceCard(student, selected_code) {
		const codes = await get_attendance_codes();
		/* … all existing code to build `options_html`, icons, etc. … */

		const html = `
			<div class="col-6 col-sm-4 col-md-3 col-lg-2">
				<div class="student-card bg-white shadow-sm p-3 text-center h-100 w-100 d-flex flex-column"
						data-student="${student_id}">
					<a href="/app/student/${student_id}" target="_blank" rel="noopener">
						<img src="${thumb_src}"
								onerror="this.onerror=null;this.src='${fallback_src}'"
								class="student-card-img img-fluid"
								alt="Photo of ${student_name}" loading="lazy">
					</a>
					<div class="student-name mt-2">
						<a href="/app/student/${student_id}" target="_blank" rel="noopener">
							${student_name}
						</a>
						${health_icon}${birthday_icon}
					</div>
					${preferred_name ? `<div class="preferred-name mb-1">${preferred_name}</div>` : ''}
					<select class="form-select mt-auto w-100" data-field="code" aria-label="Attendance code">
						${options_html}
					</select>
				</div>
			</div>`;
		return $(html);		// ← jQuery element, not plain string
	}
}

/* 4 Desk-page controller ------------------------------------- */
frappe.pages['student_attendance_tool'].on_page_load = async function (wrapper) {

	/* Page shell */
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Student Attendance'),
		single_column: true
	});

	/* Grid reference cached once */
	const $row = $('<div class="container-fluid mt-3">' +
	               '<div id="card-row" class="row row-cols-2 row-cols-md-3 row-cols-xl-4 g-3"></div>' +
	               '</div>').appendTo(wrapper).find('#card-row');

	/* ── Bulk-toggle helper ─────────────────────────────────── */
	function toggle_bulk(enabled) {
		page.actions_menu.find('a:contains("Mark All")')
			.toggleClass('disabled', !enabled);
	}

	/* Filters */
	const sg_field = page.add_field({
		fieldname: 'student_group',
		label: __('Student Group'),
		fieldtype: 'Link',
		options: 'Student Group',
		reqd: 1,
		change: refresh_dates
	});

	const date_field = page.add_field({
		fieldname: 'attendance_date',
		label: __('Date'),
		fieldtype: 'Select',
		reqd: 1,
		change: build_roster
	});

	const default_field = page.add_field({
		fieldname: 'default_code',
		label: __('Default Code'),
		fieldtype: 'Link',
		options: 'Student Attendance Code',
		default: 'Present',
		change: () => $row.find('select[data-field="code"]').val(default_field.get_value())
	});

	/* Bulk buttons */
	page.add_action_item(__('Mark All Present'), () => $row.find('select[data-field="code"]').val('Present'));
	page.add_action_item(__('Mark All Absent'),  () => $row.find('select[data-field="code"]').val('Absent'));
	page.set_primary_action(__('Submit'), async () => {
		page.toggle_primary_action(false);
		await submit_roster();
		page.toggle_primary_action(true);
	}, 'save');
	toggle_bulk(false);					// disabled until roster exists

	/* ── Date refresh ───────────────────────────────────────── */
	async function refresh_dates() {
		const group = sg_field.get_value();
		if (!group) return;

		const { message: dates } = await frappe.call(
			'ifitwala_ed.schedule.attendance_utils.get_meeting_dates',
			{ student_group: group }
		);

		if (!dates.length) {
			frappe.msgprint(__('No scheduled dates found for this group.'));
			date_field.df.options = [];
			date_field.refresh();
			$row.empty();
			toggle_bulk(false);
			return;
		}

		date_field.df.options = dates.map(d =>
			({ label: d === frappe.datetime.get_today() ? __('Today') : d, value: d }));
		date_field.refresh();
		date_field.set_value(dates[0]);
		build_roster();
	}

	/* ── Roster build ───────────────────────────────────────── */
	async function build_roster() {
		const group = sg_field.get_value();
		const date  = date_field.get_value();
		if (!group || !date) return;

		$row.empty();
		toggle_bulk(false);

		const [{ message: roster }, { message: prev }] = await Promise.all([
			frappe.call('ifitwala_ed.schedule.attendance_utils.fetch_students', {
				student_group: group, start: 0, page_length: 500
			}),
			frappe.call('ifitwala_ed.schedule.attendance_utils.previous_status_map', {
				student_group: group, attendance_date: date
			})
		]);

		if (!roster.students.length) return;

		const default_code = default_field.get_value() || 'Present';
		for (const student of roster.students) {
			$row.append(await renderAttendanceCard(
				student,
				prev[student.student] || default_code
			));
		}
		toggle_bulk(true);
	}

	/* ── Submit handler ─────────────────────────────────────── */
	async function submit_roster() {
		const group = sg_field.get_value();
		const date  = date_field.get_value();
		const payload = [];

		$row.find('.student-card').each(function () {
			payload.push({
				student:          $(this).data('student'),
				student_group:    group,
				attendance_date:  date,
				attendance_code:  $(this).find('select').val()
			});
		});

		const r = await frappe.call(
			'ifitwala_ed.schedule.attendance_utils.bulk_upsert_attendance',
			{ payload }
		);

		frappe.msgprint(
			__("{0} created | {1} updated", [r.message.created, r.message.updated])
		);
	}

	/* Auto-prefill default group */
	if (frappe.defaults.get_default('student_group')) {
		sg_field.set_value(frappe.defaults.get_default('student_group'));
	}
	if (sg_field.get_value()) await refresh_dates();
};