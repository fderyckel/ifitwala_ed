// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.require("/assets/ifitwala_ed/css/student_group.css");

frappe.pages['student_group_cards'].on_page_load = function(wrapper) {
  let page = frappe.ui.make_app_page({
      parent: wrapper,
      title: 'Student Group Cards',
      single_column: true
  });
  
  // Add standard Frappe filters
  let program_field = page.add_field({
      fieldname: "program",
      label: __("Program"),
      fieldtype: "Link",
      options: "Program",
      change: () => fetch_student_groups()
  });
  
  let course_field = page.add_field({
      fieldname: "course",
      label: __("Course"),
      fieldtype: "Link",
      options: "Course",
      change: () => fetch_student_groups()
  });
  
  let cohort_field = page.add_field({
      fieldname: "cohort",
      label: __("Cohort"),
      fieldtype: "Link",
      options: "Student Cohort",
      change: () => fetch_student_groups()
  });
  
  let student_group_field = page.add_field({
      fieldname: "student_group",
      label: __("Student Group"),
      fieldtype: "Link",
      options: "Student Group",
      change: () => fetch_students(true)
  });
  
  $(wrapper).append(`
      <div id="student-cards" class="student-grid"></div>
      <button id="load-more" class="btn btn-primary">Load More</button>
  `);
  
  let start = 0;
  const page_length = 25;
  let total_students = 0;
  
  function fetch_student_groups() {
      frappe.call({
          method: 'ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_student_groups',
          args: {
              program: program_field.get_value(),
              course: course_field.get_value(),
              cohort: cohort_field.get_value()
          },
          callback: function(data) {
              student_group_field.df.options = data.message.map(group => group.name);
              student_group_field.refresh();
          }
      });
  }
  
  function fetch_students(reset=false) {
      let student_group = student_group_field.get_value();
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
  
  function render_students(students) {
      students.forEach(student => {
          let img_src = student.student_image && student.student_image.startsWith('/files/') ? student.student_image : '/files/default-profile.png';
          $('#student-cards').append(`
              <div class="student-card">
                  <img src="${img_src}" class="student-image">
                  <div class="student-name">${student.student_name}</div>
                  <div class="student-preferred-name">${student.preferred_name}</div>
              </div>
          `);
      });
  }

  $('#load-more').click(function() {
      fetch_students();
  });
};
