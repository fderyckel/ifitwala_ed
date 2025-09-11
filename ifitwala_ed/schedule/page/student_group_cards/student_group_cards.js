// Copyright (c) 2025, François de Ryckel

frappe.require("/assets/ifitwala_ed/dist/student_group_cards.bundle.css");

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

function renderSSGInlineIcon(student) {
	if (!student.has_ssg) return '';

	const title = __("Support guidance available");
	return `
		<span class="ms-2 text-primary fw-bold ssg-inline"
		      title="${frappe.utils.escape_html(title)}"
		      aria-label="${frappe.utils.escape_html(title)}"
		      data-student="${frappe.utils.escape_html(student.student)}">
			<i class="bi bi-journal-medical"></i>
		</span>
	`;
}

function renderSupportBadge(student) {
	// Show badge only when viewer is authorized (server adds has_ssg accordingly)
	if (!student.has_ssg) return '';

	const title = __("Support guidance available");

	// Positioned/colored via CSS in Phase 1, step 3
	// We include data-student for future (Phase 2) modal click handling.
	return `
		<span class="support-badge cross"
		      title="${frappe.utils.escape_html(title)}"
		      aria-label="${frappe.utils.escape_html(title)}"
		      data-student="${frappe.utils.escape_html(student.student)}">
			<i class="bi bi-plus-lg"></i>
		</span>
	`;
}

async function openSSGModal(studentId, studentName) {
	const isTriager =
		frappe.user.has_role("Counselor") ||
		frappe.user.has_role("Academic Admin") ||
		frappe.user.has_role("System Manager");

	const d = new frappe.ui.Dialog({
		title: __("Support Guidance for {0}", [frappe.utils.escape_html(studentName || studentId)]),
		fields: [{ fieldname: "body", fieldtype: "HTML" }],
		size: "large",
		primary_action_label: __("Close"),
		primary_action: () => d.hide()
	});

	d.show();

	const $body = d.get_field("body").$wrapper;
	$body.html(`<div class="p-3 text-muted small">${__("Loading published guidance…")}</div>`);

	// helper: 09 September 2025
	const neatDate = (dt) => {
		try {
			const o = frappe.datetime.str_to_obj(dt);
			return o
				? o.toLocaleDateString(undefined, { day: "2-digit", month: "long", year: "numeric" })
				: "";
		} catch { return ""; }
	};

	try {
		const { message: rows } = await frappe.call({
			method: "ifitwala_ed.students.doctype.referral_case.referral_case.get_student_support_guidance",
			args: { student: studentId }
		});

		const items = Array.isArray(rows) ? rows : [];
		if (!items.length) {
			$body.html(`<div class="p-3 text-muted">${__("No published, active guidance found.")}</div>`);
			return;
		}

		const html = items.map((r) => {
			const when = r.entry_datetime ? neatDate(r.entry_datetime) : "";
			const status = (r.status || "Open").trim();
			const statusBadge =
				status === "In Progress"
					? `<span class="badge bg-success ms-2">${__("In Progress")}</span>`
					: ""; // keep Open implicit

			const assignee = r.assignee ? frappe.utils.escape_html(r.assignee) : __("All instructors");
			const ui = r.author ? (frappe.user_info(r.author) || {}) : {};
			const authorName = r.author ? frappe.utils.escape_html(ui.fullname || r.author) : "";
			const summary = r.summary || ""; // server supplies sanitized Text Editor HTML

			const viewBtn = isTriager && r.case_name
				? `<button class="btn btn-sm btn-outline-primary ms-2" data-case="${frappe.utils.escape_html(r.case_name)}">
						${__("View Case")}
				   </button>`
				: "";

			return `
				<div class="card mb-3 shadow-sm" style="border-left: .35rem solid var(--bs-info);">
					<div class="card-body">
						<div class="d-flex justify-content-between align-items-center">
							<div class="small text-muted d-inline-flex align-items-center gap-1">
								<i class="bi bi-calendar-event"></i>
								<strong>${when}</strong>
								${statusBadge}
							</div>
							${viewBtn}
						</div>

						<div class="mt-2 small text-muted d-inline-flex align-items-center gap-2 flex-wrap">
							<i class="bi bi-person"></i>
							<span>${__("Assignee")}: <strong>${assignee}</strong></span>
							${authorName ? `<span class="d-inline-flex align-items-center gap-1"><i class="bi bi-pencil-square"></i>${__("Author")}: <strong>${authorName}</strong></span>` : ""}
						</div>

						<div class="mt-3 d-inline-flex align-items-start gap-2">
							<i class="bi bi-journal-text text-info"></i>
							<span>${summary}</span>
						</div>
					</div>
				</div>
			`;
		}).join("");

		$body.html(`<div>${html}</div>`);

		// Route to case (triage roles only)
		if (isTriager) {
			$body.on("click", "button[data-case]", (e) => {
				const cn = e.currentTarget.getAttribute("data-case");
				if (cn) {
					d.hide();
					frappe.set_route("Form", "Referral Case", cn);
				}
			});
		}
	} catch (err) {
		$body.html(`<div class="p-3 text-danger small">${__("Failed to load guidance or permission denied.")}</div>`);
		// eslint-disable-next-line no-console
		console.error(err);
	}
}


function renderStudentCard(student) {
	const student_name   = frappe.utils.escape_html(student.student_name);
	const preferred_name = frappe.utils.escape_html(student.preferred_name || '');
	const student_id     = frappe.utils.escape_html(student.student);
	const thumb_src      = get_student_image(student.student_image);
	const fallback_src   = student.student_image || '/assets/ifitwala_ed/images/default_student_image.png';

	let birthday_icon = '', health_icon = '';

	const ssg_icon = renderSSGInlineIcon(student);

	if (student.birth_date) {
		try {
			const bdate    = frappe.datetime.str_to_obj(student.birth_date);
			const today    = frappe.datetime.str_to_obj(frappe.datetime.now_date());
			const thisYear = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
			const diffDays = Math.floor((thisYear - today) / 86400000);

			if (Math.abs(diffDays) <= 5) {
				const formatted = moment(bdate).format('dddd, MMMM D');
				birthday_icon = `
					<span class="ms-2 text-warning" role="button"
						onclick="frappe.msgprint('${__('Birthday:')} ${formatted}')"
						title="${__('Birthday on {0}', [formatted])}">🎂</span>`;
			}
		} catch {}
	}

	if (student.medical_info) {
		const note = frappe.utils.escape_html(student.medical_info);
		health_icon = `
			<span class="ms-2 text-danger fw-bold" role="button"
				onclick='frappe.msgprint({title:"${__('Health Note for {0}', [student_name])}",
										 message:\`${note}\`,indicator:"red"})'
				title="${__('Health Note Available')}">&#x2716;</span>`;
	}

	return `
		<div class="col-6 col-sm-4 col-md-3 col-lg-2">
			<div class="student-card bg-white shadow-sm p-3 text-center h-100 w-100 d-flex flex-column">
				<div class="img-wrap position-relative">
					<a href="/app/student/${student_id}" target="_blank" rel="noopener">
						<img src="${thumb_src}"
							 onerror="this.onerror=null;this.src='${fallback_src}'"
							 class="student-card-img img-fluid"
							 alt="Photo of ${student_name}"
							 loading="lazy">
					</a>
				</div>
				<div class="student-name mt-3">
					<a href="/app/student/${student_id}" target="_blank" rel="noopener">
						${student_name}
					</a>
					${ssg_icon}${health_icon}${birthday_icon}
				</div>
				${preferred_name ? `<div class="preferred-name">${preferred_name}</div>` : ''}
			</div>
		</div>
	`;
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

		if (frappe.route_options?.student_group) {
			const group = frappe.route_options.student_group;
			delete frappe.route_options.student_group; 
			
			// Clear other filters so we don't restrict the query
			program_field.set_value(''); 
			course_field.set_value(''); 
			cohort_field.set_value(''); 
			
			// Ensure the Link field is filled, then trigger fetch 
			student_group_field.set_value(group).then(() => { 
				fetch_students(true); 
			});
		}		

		function clear_and_refresh_group() {
			student_group_field.set_value('');
			student_group_field.refresh();
		}

		/* ── Layout container ─────────────────────────────────────────── */
		$(wrapper).append(`
			<div class="student-group-wrapper container mt-3">
				<div id="student-group-title" class="student-group-title"></div>
				<div id="student-cards" class="row gx-2 gy-3"></div>
				<div class="load-more-wrapper">
					<button id="load-more" class="btn btn-primary">
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
				<h2 class="fs-4 fw-semibold text-dark">${frappe.utils.escape_html(name)}</h2>
				${subtitle ? `<div class="small text-muted mt-1">${frappe.utils.escape_html(subtitle)}</div>` : ""}
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

		// open modal when user clicks the inline SSG icon
		$("#student-cards").on("click", ".ssg-inline", function (e) {
			const studentId = e.currentTarget.getAttribute("data-student");
			// try to read the visible name text in the same card
			const nameEl = e.currentTarget.closest(".student-card")?.querySelector(".student-name a");
			const studentName = nameEl ? nameEl.textContent.trim() : studentId;
			if (studentId) openSSGModal(studentId, studentName);
		});


		/* ── “Load More” handler ──────────────────────────────────────── */
		$('#load-more').on('click', () => fetch_students());
};
