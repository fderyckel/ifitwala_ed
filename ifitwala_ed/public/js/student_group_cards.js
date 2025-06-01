// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Shared helpers for student-card rendering
// Exposed globally as  frappe.renderStudentCard()

function slugify(filename) {
	return filename
		.replace(/\.[^.]+$/, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '_')
		.replace(/^_+|_+$/g, '');
}

export function get_student_image(original_url) {
	const fallback = '/assets/ifitwala_ed/images/default_student_image.png';
	if (!original_url) return fallback;

	if (original_url.startsWith('/files/gallery_resized/student/')) return original_url;
	if (!original_url.startsWith('/files/student/')) return fallback;

	const base = slugify(original_url.split('/').pop());
	return `/files/gallery_resized/student/thumb_${base}.webp`;
}

/**
 * Render a Tailwind card for a student.
 * @param {Object} student – row returned by the Python controller
 * @param {Object} options – { thumbSize: 80 }  (pixels, square)
 */
export function renderStudentCard(student, options = {}) {
	const {
		thumbSize = 80 // default 80 px – matches Desk page
	} = options;

	const student_name   = frappe.utils.escape_html(student.student_name);
	const preferred_name = frappe.utils.escape_html(student.preferred_name || '');
	const student_id     = frappe.utils.escape_html(student.student);
	const thumb_src      = get_student_image(student.student_image);
	const original_src   = student.student_image || '/assets/ifitwala_ed/images/default_student_image.png';

	/* ── Birthday tooltip ───────────────────────────────────────── */
	let birthday_icon = '';
	if (student.birth_date) {
		try {
			const bdate = frappe.datetime.str_to_obj(student.birth_date);
			const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());
			const b_this_year = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
			const diff_days = Math.floor((b_this_year - today) / (1000 * 60 * 60 * 24));
			if (Math.abs(diff_days) <= 5) {
				const formatted = dayjs(bdate).format('dddd, MMMM D');
				birthday_icon = `
					<span class="ml-2 text-yellow-500 group relative cursor-pointer"
						onclick="frappe.msgprint('${__('Birthday:')} ${formatted}')">
						🎂
						<span class="absolute left-1/2 -translate-x-1/2 mt-1 w-max px-2 py-1 text-xs text-white bg-black rounded opacity-0 group-hover:opacity-100 transition z-10 whitespace-nowrap">
							${__('Birthday on {0}', [formatted])}
						</span>
					</span>`;
			}
		} catch (e) {
			console.warn('Invalid birth_date', student.student, e);
		}
	}

	/* ── Health tooltip ─────────────────────────────────────────── */
	let health_icon = '';
	if (student.medical_info) {
		const note = frappe.utils.escape_html(student.medical_info);
		health_icon = `
			<span class="ml-2 text-red-500 font-bold group relative cursor-pointer"
				onclick='frappe.msgprint({title: "${__('Health Note for {0}', [student_name])}",
					message: \`${note}\`, indicator: "red"})'>
				&#x2716;
				<span class="absolute left-1/2 -translate-x-1/2 mt-1 w-max px-2 py-1 text-xs text-white bg-red-600 rounded opacity-0 group-hover:opacity-100 transition z-10 whitespace-nowrap">
					${__('Health Note Available')}
				</span>
			</span>`;
	}

	/* ── Final markup ───────────────────────────────────────────── */
	return `
		<div class="bg-white rounded-xl p-4 text-center shadow hover:-translate-y-1 transition-transform duration-200">
			<a href="/app/student/${student_id}" target="_blank" rel="noopener">
				<img src="${thumb_src}" onerror="this.onerror=null;this.src='${original_src}';"
					 class="w-[${thumbSize}px] h-[${thumbSize}px] rounded-full object-cover mx-auto bg-gray-100" loading="lazy">
			</a>
			<div class="mt-3 text-lg font-semibold">
				<a href="/app/student/${student_id}" target="_blank" rel="noopener">${student_name}</a>
				${health_icon}${birthday_icon}
			</div>
			${preferred_name ? `<div class="text-sm text-gray-500 mt-1">${preferred_name}</div>` : ''}
		</div>`;
}

frappe.renderStudentCard = renderStudentCard;
