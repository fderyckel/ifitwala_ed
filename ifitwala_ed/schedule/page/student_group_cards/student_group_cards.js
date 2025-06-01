// Copyright (c) 2025, François de Ryckel
// Tailwind-compliant version – no external CSS required

frappe.pages['student_group_cards'].on_page_load = function(wrapper) {

  /* ── Fallback Helpers ───────────────────────────── */
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

  // 🔗 Breadcrumb
  const urlParams = new URLSearchParams(window.location.search);
  const workspace = urlParams.get("workspace") || "Academics";
  frappe.breadcrumbs.add({
    label: workspace,
    route: `/app/${workspace.replace(/\s+/g, "-").toLowerCase()}`
  });

  // 📄 Page
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Student Group Cards',
    single_column: true
  });

  // 🔍 Filters
  const program_field = page.add_field({
    fieldname: "program",
    label: __("Program"),
    fieldtype: "Link",
    options: "Program",
    change: () => student_group_field.refresh()
  });

  const course_field = page.add_field({
    fieldname: "course",
    label: __("Course"),
    fieldtype: "Link",
    options: "Course",
    change: () => student_group_field.refresh()
  });

  const cohort_field = page.add_field({
    fieldname: "cohort",
    label: __("Cohort"),
    fieldtype: "Link",
    options: "Student Cohort",
    change: () => student_group_field.refresh()
  });

  const student_group_field = page.add_field({
    fieldname: "student_group",
    label: __("Student Group"),
    fieldtype: "Link",
    options: "Student Group",
    get_query: () => ({
      filters: {
        ...(program_field.get_value() && { program: program_field.get_value() }),
        ...(course_field.get_value() && { course: course_field.get_value() }),
        ...(cohort_field.get_value() && { cohort: cohort_field.get_value() })
      }
    }),
    change: () => fetch_students(true)
  });

  // 🧱 Layout container
  $(wrapper).append(`
    <div class="sticky top-[65px] bg-white py-3 shadow-sm z-0">
      <div id="student-group-title" class="text-center"></div>
    </div>
		<div id="student-cards" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-6 mt-4 px-4"></div>
    <div class="flex justify-center mt-6">
      <button id="load-more" class="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700 transition">
        Load More
      </button>
    </div>
  `);

  // 📊 Pagination
  let start = 0;
  const page_length = 25;
  let total_students = 0;
  let group_info = {};

  // 🏷️ Title updater
  function update_title() {
    const group = group_info.name;
    const program = group_info.program;
    const course = group_info.course;
    const cohort = group_info.cohort;

    if (!group) return $('#student-group-title').empty();

    const subtitle_parts = [program, course, cohort].filter(Boolean).join(' – ');

    $('#student-group-title').html(`
      <h2 class="text-2xl font-semibold text-gray-800">${group}</h2>
      ${subtitle_parts ? `<div class="text-sm text-gray-500 mt-1">${subtitle_parts}</div>` : ''}
    `);
  }

  // 🧍 Render Student Card
  function renderStudentCard(student) {
    const student_name = frappe.utils.escape_html(student.student_name);
    const preferred_name = frappe.utils.escape_html(student.preferred_name || "");
    const student_id = frappe.utils.escape_html(student.student);
    const thumb_src = get_student_image(student.student_image);
    const original_src = student.student_image || "/assets/ifitwala_ed/images/default_student_image.png";

    // 🎂 Birthday logic
    let birthday_icon = '';
    if (student.birth_date) {
      try {
        const birth_date = frappe.datetime.str_to_obj(student.birth_date);
        const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());
        const birth_this_year = new Date(today.getFullYear(), birth_date.getMonth(), birth_date.getDate());
        const diff_days = Math.floor((birth_this_year - today) / (1000 * 60 * 60 * 24));
        if (Math.abs(diff_days) <= 5) {
          const formatted = moment(birth_date).format("dddd, MMMM Do");
          birthday_icon = `<span class="ml-2 text-yellow-500" title="${__("Birthday on {0}", [formatted])}">🎂</span>`;
        }
      } catch (e) {
        console.warn("Invalid birth_date", student.student, e);
      }
    }

		// 🚨 Health icon
		let health_icon = '';
		if (student.medical_info) {
			const escaped_note = frappe.utils.escape_html(student.medical_info);
			health_icon = `
				<span class="ml-2 text-red-500 font-bold group relative cursor-pointer"
							onclick='frappe.msgprint({
								title: "Health Note for ${student_name}",
								message: \`${escaped_note}\`,
								indicator: "red"
							})'>
					&#x2716;
					<span class="absolute left-1/2 -translate-x-1/2 mt-1 w-max px-2 py-1 text-xs text-white bg-red-600 rounded opacity-0 group-hover:opacity-100 transition z-10 whitespace-nowrap">
						${__("Health Note Available")}
					</span>
				</span>
			`;
		}

    return `
      <div class="bg-white rounded-xl p-4 text-center shadow hover:-translate-y-1 transition-transform duration-200">
        <a href="/app/student/${student_id}" target="_blank" rel="noopener">
          <img src="${thumb_src}" onerror="this.onerror=null;this.src='${original_src}';"
            class="w-20 h-20 rounded-full object-cover mx-auto bg-gray-100" loading="lazy">
        </a>
        <div class="mt-3 text-lg font-semibold">
          <a href="/app/student/${student_id}" target="_blank" rel="noopener">${student_name}</a>
          ${health_icon}${birthday_icon}
        </div>
        ${preferred_name ? `<div class="text-sm text-gray-500 mt-1">${preferred_name}</div>` : ""}
      </div>
    `;
  }

  // 📦 Fetch students
  function fetch_students(reset = false) {
    const student_group = student_group_field.get_value();
    if (!student_group) return;
    if (reset) start = 0;

    frappe.call({
      method: 'ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_students',
      args: { student_group, start, page_length },
      callback: function(data) {
        if (reset) $('#student-cards').empty();
        start = data.message.start;
        total_students = data.message.total;
        group_info = data.message.group_info || {};
        data.message.students.forEach(student => {
          $('#student-cards').append(renderStudentCard(student));
        });
        $('#load-more').toggle(start < total_students);
        update_title();
      }
    });
  }

  // ➕ Load more handler
  $('#load-more').click(() => fetch_students());
};
