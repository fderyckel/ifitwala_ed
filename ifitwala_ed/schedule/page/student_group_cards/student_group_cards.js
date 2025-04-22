// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.require("/assets/ifitwala_ed/css/student_group.css");

frappe.pages['student_group_cards'].on_page_load = function(wrapper) {
  let page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Student Group Cards',
    single_column: true
  });

  // Add filters
  let program_field = page.add_field({
    fieldname: "program",
    label: __("Program"),
    fieldtype: "Link",
    options: "Program",
    change: () => student_group_field.refresh()
  });

  let course_field = page.add_field({
    fieldname: "course",
    label: __("Course"),
    fieldtype: "Link",
    options: "Course",
    change: () => student_group_field.refresh()
  });

  let cohort_field = page.add_field({
    fieldname: "cohort",
    label: __("Cohort"),
    fieldtype: "Link",
    options: "Student Cohort",
    change: () => student_group_field.refresh()
  });

  let student_group_field = page.add_field({
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

  // Main content and button
  $(wrapper).append(`
    <div class="filters-and-title">
      <div id="student-group-title" class="student-group-title"></div>
    </div>
    <div id="student-cards" class="student-grid container"></div>
    <button id="load-more" class="btn btn-primary">Load More</button>
  `);

  let start = 0;
  const page_length = 25;
  let total_students = 0;
  
  function update_title() {
    const group = group_info.name;
    const program = group_info.program;
    const course = group_info.course;
    const cohort = group_info.cohort;
  
    if (!group) {
      $('#student-group-title').html('');
      return;
    }
  
    let title_html = `<h2>${group}</h2>`;
    let subtitle_parts = [];
  
    if (program) subtitle_parts.push(program);
    if (course) subtitle_parts.push(course);
    if (cohort) subtitle_parts.push(cohort);
  
    let subtitle_html = subtitle_parts.length ? `<div class="subtitle">${subtitle_parts.join(' – ')}</div>` : '';
  
    $('#student-group-title').html(`${title_html}${subtitle_html}`);
  }

  
  function fetch_students(reset = false) {

    let group_info = {};

    const student_group = student_group_field.get_value();
    if (!student_group) return;
    if (reset) start = 0; 

    frappe.call({
      method: 'ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_students',
      args: { student_group, start, page_length },
      callback: function(data) {
        if (reset) $('#student-cards').html('');
        start = data.message.start;
        total_students = data.message.total;
        group_info = data.message.group_info || {}; 
        render_students(data.message.students);
        $('#load-more').toggle(start < total_students);
        update_title();
      }
    });

    
  }

  // Function to render the students' cards
  function render_students(students) {
    students.forEach(student => {
      const student_name = frappe.utils.escape_html(student.student_name);
      const preferred_name = frappe.utils.escape_html(student.preferred_name);
      const student_id = frappe.utils.escape_html(student.student);
      const img_src = student.student_image && student.student_image.startsWith('/files/')
        ? student.student_image
        : '/files/default-profile.png';
  
      // Red cross icon for medical info
      let health_icon = '';
      if (student.medical_info) {
        health_icon = `
          <span class="medical-alert" data-tooltip="Click to view health info"
            onclick='frappe.msgprint({
              title: "Health Note for ${student_name}",
              message: \`${student.medical_info}\`,
              indicator: "red"
            })'>
            &#x2716;
          </span>
        `;
      }

      let birthday_icon = '';
      if (student.birth_date) {
        const birth = frappe.datetime.str_to_obj(student.birth_date);
        const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());

        // normalize to current year
        const birth_this_year = new Date(today.getFullYear(), birth.getMonth(), birth.getDate());
        const diff_days = Math.floor((birth_this_year - today) / (1000 * 60 * 60 * 24));

        if (Math.abs(diff_days) <= 5) {
          const formatted = frappe.format_date(birth, "d MMMM");
          birthday_icon = `
            <span class="birthday-icon" title="Birthday on ${formatted}">🎂</span>
          `;
        }
      }
  
      $('#student-cards').append(`
        <div class="student-card">
          <a href="/app/student/${student_id}" target="_blank" rel="noopener">
            <img src="${img_src}" class="student-image">
          </a>
        <div class="student-name">
          <a href="/app/student/${student_id}" target="_blank" rel="noopener">
            ${student_name}
          </a>
          ${health_icon}
          ${birthday_icon}
        </div>
          <div class="student-preferred-name">${preferred_name}</div>
        </div>
      `);
    });
  }
  
  
  $('#load-more').click(() => fetch_students());
};

// Route-based filter setting
frappe.pages['student_group_cards'].on_page_show = function(wrapper) {
  frappe.after_ajax(() => {
    const route_options = frappe.route_options;
    if (route_options && route_options.student_group) {
      const page = wrapper.page;
      const student_group_field = page.fields_dict.student_group;

      student_group_field.set_value(route_options.student_group).then(() => {
        frappe.route_options = null;
        if (typeof student_group_field.df.change === 'function') {
          student_group_field.df.change();
        }
      });
    }
  });
};
