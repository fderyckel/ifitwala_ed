// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages['student-group-cards'].on_page_load = function(wrapper) {
  let page = frappe.ui.make_app_page({
      parent: wrapper,
      title: 'Student Group Cards',
      single_column: true
  });
  
  $(wrapper).append(`
      <div class="filters">
          <select id="program-filter" class="form-control">
              <option value="">Select Program</option>
          </select>
          <select id="course-filter" class="form-control">
              <option value="">Select Course</option>
          </select>
          <select id="cohort-filter" class="form-control">
              <option value="">Select Cohort</option>
          </select>
          <select id="student-group-filter" class="form-control">
              <option value="">Select Student Group</option>
          </select>
      </div>
      <div id="student-cards" class="student-grid"></div>
      <button id="load-more" class="btn btn-primary">Load More</button>
  `);

  let start = 0;
  let student_group = "";
  const page_length = 25;
  let total_students = 0;
  
  function fetchFilters() {
      frappe.call({
          method: 'ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_student_groups',
          callback: function(data) {
              let options = '<option value="">Select Student Group</option>';
              data.message.forEach(group => {
                  options += `<option value="${group.name}">${group.student_group_name}</option>`;
              });
              $('#student-group-filter').html(options);
          }
      });
  }
  
  function fetchStudents(reset=false) {
      if (!student_group) return;
      if (reset) start = 0;

      frappe.call({
          method: 'ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_students',
          args: { student_group, start, page_length },
          callback: function(data) {
              if (reset) $('#student-cards').html('');
              start = data.message.start;
              total_students = data.message.total;
              renderStudents(data.message.students);
              $('#load-more').toggle(start < total_students);
          }
      });
  }
  
  function renderStudents(students) {
      students.forEach(student => {
          let img_src = student.image || 'path/to/placeholder.png';
          $('#student-cards').append(`
              <div class="student-card">
                  <img src="${img_src}" class="student-image">
                  <div class="student-name">${student.student_name}</div>
                  <div class="student-preferred-name">${student.preferred_name}</div>
              </div>
          `);
      });
  }

  $('#student-group-filter').change(function() {
      student_group = $(this).val();
      fetchStudents(true);
  });

  $('#load-more').click(function() {
      fetchStudents();
  });

  fetchFilters();
};
