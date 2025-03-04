// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages["student_group_cards"].on_page_load = function (wrapper) {
    // Create the page
    let page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Student Group Cards"),
      single_column: true
    });
  
    // We'll store our custom controls here
    let controls = {};
  
    // 1) Setup the filters/controls inside the page
    create_filters();
  
    // 2) Attach event handlers to fetch matching groups and then fetch students
  
    /**
     * Creates the filter controls and renders them on the page.
     */
    function create_filters() {
      // Container where we'll place the filters
      const $filters_container = page.main.find("#filters-container");
  
      // We'll create four controls:
      // program, course, instructor (all Autocomplete)
      // student_group (Autocomplete) - only populated once the first three filters have a result.
  
      // Program Filter
      controls.program = new frappe.ui.form.ControlAutocomplete({
        parent: $filters_container[0],
        label: __("Program"),
        placeholder: __("Select Program"),
        reqd: 0,
        // fetch possible programs on user input:
        get_data: function(txt) {
          return frappe.db.get_link_options("Program", txt);
        }
      });
      controls.program.make();
  
      // Course Filter
      controls.course = new frappe.ui.form.ControlAutocomplete({
        parent: $filters_container[0],
        label: __("Course"),
        placeholder: __("Select Course"),
        reqd: 0,
        get_data: function(txt) {
          return frappe.db.get_link_options("Course", txt);
        }
      });
      controls.course.make();
  
      // Instructor Filter
      controls.instructor = new frappe.ui.form.ControlAutocomplete({
        parent: $filters_container[0],
        label: __("Instructor"),
        placeholder: __("Select Instructor"),
        reqd: 0,
        get_data: function(txt) {
          return frappe.db.get_link_options("Instructor", txt);
        }
      });
      controls.instructor.make();
  
      // Student Group Filter (populated dynamically based on the three filters above)
      controls.student_group = new frappe.ui.form.ControlAutocomplete({
        parent: $filters_container[0],
        label: __("Student Group"),
        placeholder: __("Select Student Group"),
        reqd: 0,
        get_data: async function(txt) {
          // Fire a backend call to get matching Student Groups
          let groups = [];
          let program_val = controls.program.get_value();
          let course_val = controls.course.get_value();
          let instructor_val = controls.instructor.get_value();
  
          let r = await frappe.call({
            method: "ifitwala_ed.schedule.page.student_group_cards.student_group_cards.get_student_groups",
            args: {
              program: program_val,
              course: course_val,
              instructor: instructor_val,
              text: txt
            }
          });
          if (r && r.message) {
            groups = r.message;
          }
          // Return in the format that ControlAutocomplete expects:
          return groups.map(g => ({value: g.name, label: g.student_group_name || g.name}));
        }
      });
      controls.student_group.make();
  
      // On change of Student Group, load the students
      controls.student_group.$input.on("change", function() {
        let group_value = controls.student_group.get_value();
        if (group_value) {
          load_students(group_value);
        } else {
          render_cards([]);
        }
      });
    }
  
    /**
     * Retrieves the students in a given Student Group, then renders them.
     */
    function load_students(student_group) {
      frappe.call({
        method: "ifitwala_ed.schedule.page.student_group_cards.student_group_cards.get_students_in_group",
        args: {
          student_group: student_group
        },
        callback: function(r) {
          if (r && r.message) {
            render_cards(r.message);
          } else {
            render_cards([]);
          }
        }
      });
    }
  
    /**
     * Renders the student cards in the #cards-container area.
     * Expects an array of:
     *  {
     *    student_image: str,
     *    student_full_name: str,
     *    student_preferred_name: str
     *  }
     */
    function render_cards(students) {
      let container = page.main.find("#cards-container");
      container.empty();
  
      if (!students || !students.length) {
        container.html(`<div class="no-students-found text-muted">${__("No students found")}</div>`);
        return;
      }
  
      // Build HTML for each student
      students.forEach(stu => {
        let card_html = `
          <div class="student-card">
            <div class="student-img">
              <img src="${stu.student_image || '/assets/frappe/images/no-image.jpg'}" alt="Student Image" />
            </div>
            <div class="student-info">
              <div class="student-full-name">${__(stu.student_full_name || "")}</div>
              <div class="student-preferred-name">${__(stu.student_preferred_name || "")}</div>
            </div>
          </div>
        `;
        container.append(card_html);
      });
    }
  };
  