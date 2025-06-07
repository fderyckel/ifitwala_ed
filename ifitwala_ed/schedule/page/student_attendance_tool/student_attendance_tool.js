// Copyright (c) 2025, François de Ryckel
// Student Attendance – Desk Page (Bootstrap 6 cards)

/* ------------------------------------------------------------------ */
/* Shared CSS bundle                                                  */
/* ------------------------------------------------------------------ */

frappe.require("/assets/ifitwala_ed/dist/student_group_cards.bundle.css");
console.log("🟡 JS Loaded: student_attendance_tool.js");
/* ------------------------------------------------------------------ */
/* Helper utilities (unchanged)                                       */
/* ------------------------------------------------------------------ */
function slugify(filename) {
	return filename
		.replace(/\.[^.]+$/, "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "_")
		.replace(/^_+|_+$/g, "");
}
function get_student_image(original_url) {
	const fallback = "/assets/ifitwala_ed/images/default_student_image.png";
	if (!original_url) return fallback;
	if (original_url.startsWith("/files/gallery_resized/student/")) return original_url;
	if (!original_url.startsWith("/files/student/")) return fallback;
	const base = slugify(original_url.split("/").pop());
	return `/files/gallery_resized/student/thumb_${base}.webp`;
}

/* ── one-time cache for codes ─────────────────────────────────────── */
let ATT_CODES = null;
async function get_attendance_codes() {
	if (!ATT_CODES) {
		ATT_CODES = await frappe.db.get_list("Student Attendance Code", {
			filters: { show_in_attendance_tool: 1 },
			fields: ["name", "attendance_code_name"],
			order_by: "display_order asc",
		});
	}
	return ATT_CODES;
}

/* ------------------------------------------------------------------ */
/* Card renderer                                                      */
/* ------------------------------------------------------------------ */
async function renderAttendanceCard(student, selected_code) {
	const codes = await get_attendance_codes();

	const student_name   = frappe.utils.escape_html(student.student_name);
	const preferred_name = frappe.utils.escape_html(student.preferred_name || "");
	const student_id     = frappe.utils.escape_html(student.student);
	const thumb_src      = get_student_image(student.student_image);
	const fallback_src   = student.student_image || "/assets/ifitwala_ed/images/default_student_image.png";

	/* birthday + medical icons (same logic as before) ---------------- */
	let birthday_icon = "", health_icon = "";
	if (student.birth_date) {
		try {
			const bdate    = frappe.datetime.str_to_obj(student.birth_date);
			const today    = frappe.datetime.str_to_obj(frappe.datetime.now_date());
			const thisYear = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
			const diff     = Math.floor((thisYear - today) / 86400000);
			if (Math.abs(diff) <= 5) {
				const formatted = moment(bdate).format("dddd, MMMM D");
				birthday_icon = `
					<span class="ms-1 text-warning" role="button"
						onclick="frappe.msgprint('${__("Birthday:")} ${formatted}')"
						title="${__("Birthday on {0}", [formatted])}">🎂</span>`;
			}
		} catch {}
	}
	if (student.medical_info) {
		const note = frappe.utils.escape_html(student.medical_info);
		health_icon = `
			<span class="ms-1 text-danger fw-bold" role="button"
				onclick='frappe.msgprint({title:"${__("Health Note for {0}", [student_name])}",
				                         message:\`${note}\`,indicator:"red"})'
				title="${__("Health Note Available")}">&#x2716;</span>`;
	}

	/* attendance-code <select> -------------------------------------- */
	const options = codes.map(c =>
		`<option value="${c.name}" ${
			c.name === selected_code ? "selected" : "" 
		}>${frappe.utils.escape_html(c.attendance_code_name)}</option>`
	).join('');

	return `
		<div class="col-6 col-sm-4 col-md-3 col-lg-2" data-student="${student_id}">
			<div class="student-card bg-white shadow-sm p-3 text-center h-100 w-100 d-flex flex-column">
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

				${preferred_name ? `<div class="preferred-name mb-1">${preferred_name}</div>` : ""}

				<select class="form-select mt-auto w-100" data-field="code" aria-label="Attendance code">
					${options}
				</select>
			</div>
		</div>`;
}

/* ------------------------------------------------------------------ */
/* Desk-page controller                                               */
/* ------------------------------------------------------------------ */
frappe.pages["student_attendance_tool"].on_page_load = async function (wrapper) {
	/* 1 ▸ base page */
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Student Attendance"),
		single_column: true,
	});

	/* 2 ▸ filters */
	const student_group_field = page.add_field({
		fieldname: "student_group",
		label: __("Student Group"),
		fieldtype: "Link",
		options: "Student Group",
		reqd: 1,
		change: refresh_dates,
	});
	const date_field = page.add_field({
		fieldname: "attendance_date",
		label: __("Date"),
		fieldtype: "Select",
		reqd: 1,
		change: build_roster,
	});
	const default_field = page.add_field({
		fieldname: "default_code",
		label: __("Default Code"),
		fieldtype: "Link",
		options: "Student Attendance Code",
		default: "Present",
		change: () => $("#attendance-cards select[data-field='code']").val(default_field.get_value()),
	});

	const $toolbarRight = $(`
		<div class="d-flex align-items-center ms-auto" id="bulk-action-buttons">
			<button id="mark-all-present" class="btn btn-outline-success me-2 d-none">
				${__("Mark All Present")}
			</button>
			<button id="mark-all-absent" class="btn btn-outline-danger d-none">
				${__("Mark All Absent")}
			</button>
		</div>
	`);

	page.inner_toolbar.find(".page-form").append($toolbarRight);	

	/* 3 ▸ bulk actions */
		console.log("🔹 Page loaded – setting up page");

		setTimeout(() => {
			console.log("🔹 Setting primary action");
			page.set_primary_action(
				__("Submit"),
				async () => {
					console.log("🔹 Submit clicked");
					page.toggle_primary_action(false);
					await submit_roster();
					page.toggle_primary_action(true);
				},
				"save"
			);
		}, 150);

		page.add_action_item("🚀 Quick Submit", async () => {
			console.log("✔ Quick Submit clicked");
			await submit_roster();
		});

	/* 4 ▸ layout wrapper (same pattern as student_group_cards) */
	$(wrapper).append(`
		<div class="student-group-wrapper container mt-3">
			<div id="attendance-title"   class="student-group-title"></div>
			<div id="attendance-cards"  class="row gx-2 gy-3"></div>
		</div>
	`);

	/* cached DOM refs */
	const $cards = $("#attendance-cards");
	const $title = $("#attendance-title");
	const $btnPresent = $("#mark-all-present");
	const $btnAbsent  = $("#mark-all-absent");

	/* 5 ▸ helper toggles */
	function toggle_bulk(enabled) {
		$btnPresent.toggleClass("d-none", !enabled);
		$btnAbsent .toggleClass("d-none", !enabled);
	}

	/* 6 ▸ data flows ------------------------------------------------- */
	async function refresh_dates() {
		const group = student_group_field.get_value();
		if (!group) return;

		const { message: dates } = await frappe.call(
			"ifitwala_ed.schedule.attendance_utils.get_meeting_dates",
			{ student_group: group }
		);

		if (!dates.length) {
			frappe.msgprint(__("No scheduled dates found for this group."));
			date_field.df.options = [];
			date_field.refresh();
			$cards.empty();
			toggle_bulk(false);
			return;
		}

		date_field.df.options = dates.map((d) =>
			({ label: d === frappe.datetime.get_today() ? __("Today") : d, value: d })
		);
		date_field.refresh();
		date_field.set_value(dates[0]);
		await build_roster();
	}

	async function build_roster() {
		const group = student_group_field.get_value();
		const date  = date_field.get_value();
		if (!group || !date) return;

		$cards.empty();
		toggle_bulk(false);

		const [{ message: roster }, { message: prev }] = await Promise.all([
			frappe.call("ifitwala_ed.schedule.attendance_utils.fetch_students", {
				student_group: group, start: 0, page_length: 500,
			}),
			frappe.call("ifitwala_ed.schedule.attendance_utils.previous_status_map", {
				student_group: group, attendance_date: date,
			}),
		]);

		if (!roster.students.length) return;

		/* update title */
		const { name, program, course, cohort } = roster.group_info || {};
		const subtitle = [program, course, cohort].filter(Boolean).join(" - ");
		$title.html(`
			<h2 class="fs-4 fw-semibold text-dark">${frappe.utils.escape_html(name || group)}</h2>
			${subtitle ? `<div class="small text-muted mt-1">${frappe.utils.escape_html(subtitle)}</div>` : ""}
		`);

		const default_code = default_field.get_value() || "Present";
		for (const stu of roster.students) {
			$cards.append(
				await renderAttendanceCard(stu, prev[stu.student] || default_code)
			);
		}
		toggle_bulk(true);
	}

	async function submit_roster() {
		const group = student_group_field.get_value();
		const date  = date_field.get_value();
		const payload = [];

		$cards.find("> div[data-student]").each(function () {
			payload.push({
				student:         $(this).data("student"),
				student_group:   group,
				attendance_date: date,
				attendance_code: $(this).find("select").val(),
			});
		});

		console.log("🟢 Payload going to server:", payload);

		try {
			const r = await frappe.call({
				method: "ifitwala_ed.schedule.attendance_utils.bulk_upsert_attendance",
				args: { payload: payload },
		});
			frappe.msgprint(__("{0} created | {1} updated", [r.message.created, r.message.updated]));
		} catch (e) {
			console.error(e);
			frappe.msgprint({
				title: __("Error Submitting Attendance"),
				message: e.message || e,
				indicator: "red",
			});
		}
	}

	/* 7 ▸ wire buttons ---------------------------------------------- */
	$btnPresent.on("click", () => $cards.find("select[data-field='code']").val("Present"));
	$btnAbsent .on("click", () => $cards.find("select[data-field='code']").val("Absent"));

	/* 8 ▸ auto-prefill default group (optional) ---------------------- */
	const default_group = frappe.defaults.get_default("student_group");
	if (default_group) student_group_field.set_value(default_group);
	if (student_group_field.get_value()) await refresh_dates();
};
