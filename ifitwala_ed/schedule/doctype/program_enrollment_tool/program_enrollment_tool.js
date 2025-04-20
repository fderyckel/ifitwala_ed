// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Enrollment Tool", {
  // --------------------
  refresh(frm) {
    frm.disable_save();

    // Dynamic toggle of filter fields on every refresh
    toggle_filter_fields(frm);

    // Add helper buttons after render
    add_table_toolbar(frm);

    // Live progress updates
    frappe.realtime.on("program_enrollment_tool", data => {
      frappe.hide_msgprint(true);
      frappe.show_progress(__('Enrolling students'), data.progress[0], data.progress[1]);
    });

    frappe.realtime.on("program_enrollment_tool_done", summary => {
      const msg = `Created: ${summary.created}, Skipped: ${summary.skipped}, Failed: ${summary.failed}`;
      if (summary.fail_link) {
        frappe.msgprint({
          title: __('Batch Finished'),
          message: msg + `<br><a href="/files/${summary.fail_link}" target="_blank">Download failures CSV</a>`,
          indicator: 'green'
        });
      } else {
        frappe.msgprint(msg);
      }
      frm.set_value('students', []);
    });
  },

  // --------------------
  onload(frm) {
    frm.set_query('academic_year', () => ({
      query: 'ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years'
    }));
  },

  // --------------------
  get_students_from(frm) {
    toggle_filter_fields(frm);
  },

  program(frm) {
    frm.set_value('academic_year', null);
    frm.set_query('academic_year', () => ({
      query: 'ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years'
    }));
  },

  new_program(frm) {
    frm.set_value('new_academic_year', null);
    frm.set_query('new_academic_year', () => ({
      query: 'ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years'
    }));
  },

  // --------------------
  get_students(frm) {
    frm.set_value('students', []);
    frappe.call({
      doc: frm.doc,
      method: 'get_students',
      callback(r) {
        if (r.message) {
          frm.set_value('students', r.message);
          highlight_duplicates(frm);
        }
      }
    });
  },

  enroll_students(frm) {
    frappe.call({
      doc: frm.doc,
      method: 'enroll_students',
      freeze: true,
      callback() {
        // wait for realtime summary
      }
    });
  }
});

// -------------------------
// Helper Functions
// -------------------------
function add_table_toolbar(frm) {
  const grid = frm.get_field('students').grid;

  // Select All
  grid.add_custom_button(__('Select All'), () => {
    grid.grid_rows.forEach(r => r.doc.__checked = 1);
    grid.refresh();
  });

  // Clear
  grid.add_custom_button(__('Clear Table'), () => {
    frm.set_value('students', []);
  });

  // Add Student manually
  grid.add_custom_button(__('Add Student…'), () => {
    frappe.prompt([
      { fieldtype: 'Link', label: 'Student', fieldname: 'student', options: 'Student', reqd: 1 }
    ], values => {
      frappe.db.get_value('Student', values.student, ['student_full_name','cohort']).then(({ message }) => {
        grid.add_new_row({
          student: values.student,
          student_name: message.student_full_name,
          student_cohort: message.cohort
        });
        grid.refresh();
      });
    });
  });
}

function highlight_duplicates(frm) {
  const grid = frm.get_field('students').grid;
  grid.grid_rows.forEach(row => {
    if (row.doc.already_enrolled) {
      row.wrapper.css({ background: '#ffebe9' });
    }
  });
}

function toggle_filter_fields(frm) {
  const source = frm.doc.get_students_from;

  frm.toggle_display('program', false);
  frm.toggle_display('academic_year', false);
  frm.toggle_display('student_cohort', false);

  if (source === 'Program Enrollment') {
    frm.toggle_display('program', true);
    frm.toggle_display('academic_year', true);
    frm.toggle_display('student_cohort', true); // optional cohort filter
  } else if (source === 'Cohort') {
    frm.toggle_display('student_cohort', true);
  }
}

