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

/* ------------------------------------------------------------------ *
 *  Render one student card                                            *
 * ------------------------------------------------------------------ */
export function renderStudentCard(student, { thumbSize = 80 } = {}) {

  const student_name   = frappe.utils.escape_html(student.student_name);
  const preferred_name = frappe.utils.escape_html(student.preferred_name || '');
  const student_id     = frappe.utils.escape_html(student.student);

  const thumb_src      = get_student_image(student.student_image);
  const fallback_src   = student.student_image || '/assets/ifitwala_ed/images/default_student_image.png';

  /* 🎂 Birthday icon ------------------------------------------------ */
  let birthday_icon = '';
  if (student.birth_date) {
    try {
      const bdate    = frappe.datetime.str_to_obj(student.birth_date);
      const today    = frappe.datetime.str_to_obj(frappe.datetime.now_date());
      const thisYear = new Date(today.getFullYear(), bdate.getMonth(), bdate.getDate());
      const diffDays = Math.floor((thisYear - today) / 86_400_000);

      if (Math.abs(diffDays) <= 5) {
        const formatted = moment(bdate).format('dddd, MMMM D');
        birthday_icon = `
          <span class="ml-2 text-yellow-500 cursor-pointer"
                onclick="frappe.msgprint('${__('Birthday:')} ${formatted}')"
                title="${__('Birthday on {0}', [formatted])}">🎂</span>`;
      }
    } catch { /* ignore parse errors */ }
  }

  /* 🚑 Health icon -------------------------------------------------- */
  let health_icon = '';
  if (student.medical_info) {
    const note = frappe.utils.escape_html(student.medical_info);
    health_icon = `
      <span class="ml-2 text-red-500 font-bold cursor-pointer"
            onclick='frappe.msgprint({title:"${__('Health Note for {0}', [student_name])}",
                                     message:\`${note}\`,indicator:"red"})'
            title="${__('Health Note Available')}">&#x2716;</span>`;
  }

  /* 🖼 Final markup -------------------------------------------------- */
  return `
    <div class="bg-white rounded-xl p-4 text-center shadow hover:-translate-y-1 transition duration-200">
      <a href="/app/student/${student_id}" target="_blank" rel="noopener">
        <img src="${thumb_src}"
             onerror="this.onerror=null;this.src='${fallback_src}';"
             class="w-[${thumbSize}px] h-[${thumbSize}px] rounded-full object-cover mx-auto bg-neutral-100"
             loading="lazy">
      </a>
      <div class="mt-3 text-lg font-semibold">
        <a href="/app/student/${student_id}" target="_blank" rel="noopener">${student_name}</a>
        ${health_icon}${birthday_icon}
      </div>
      ${preferred_name ? `<div class="text-sm text-gray-500 mt-1">${preferred_name}</div>` : ''}
    </div>`;
}