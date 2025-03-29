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
    <div id="student-cards" class="student-grid"></div>
    <button id="load-more" class="btn btn-primary">Load More</button>
  `);

  let start = 0;
  const page_length = 25;
  let total_students = 0;

  function fetch_students(reset = false) {
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
        render_students(data.message.students);
        $('#load-more').toggle(start < total_students);
      }
    });
  }

  // Function to render the students' cards
  function render_students(students) {
    students.forEach(student => {
      const img_src = student.student_image && student.student_image.startsWith('/files/')
        ? student.student_image
        : '/files/default-profile.png';
  
      // Add red cross icon if medical_info exists
      let health_icon = '';
      if (student.medical_info) {
        health_icon = `
          <span class="medical-alert" title="Click to view health info"
            onclick='frappe.msgprint({
              title: "Health Note for ${frappe.utils.escape_html(student.student_name)}",
              message: \`${student.medical_info}\`,
              indicator: "red"
            })'>
            &#x2716;
          </span>
        `;
      }
  
      $('#student-cards').append(`
        <div class="student-card">
          <img src="${img_src}" class="student-image">
          <div class="student-name">
            ${frappe.utils.escape_html(student.student_name)} ${health_icon}
          </div>
          <div class="student-preferred-name">${frappe.utils.escape_html(student.preferred_name)}</div>
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
