// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages["student_group_cards"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __("Student Group Cards"),
      single_column: true,
    });
  
    // Render our HTML template (which contains the div for cards) into the main page area
    page.main.html(frappe.render_template("student_group_cards"));
  
    // Create filters using page.add_field
    let program_field = page.add_field({
      fieldname: "program",
      label: __("Program"),
      fieldtype: "Link",
      options: "Program",
      change: () => clear_student_group(),
    });
  
    let course_field = page.add_field({
      fieldname: "course",
      label: __("Course"),
      fieldtype: "Link",
      options: "Course",
      change: () => clear_student_group(),
    });
  
    let instructor_field = page.add_field({
      fieldname: "instructor",
      label: __("Instructor"),
      fieldtype: "Link",
      options: "Instructor",
      change: () => clear_student_group(),
    });
  
    // Student Group filter with custom query
    let student_group_field = page.add_field({
      fieldname: "student_group",
      label: __("Student Group"),
      fieldtype: "Link",
      options: "Student Group",
      get_query: function () {
        return {
          query: "ifitwala_ed.schedule.page.student_group_cards.student_group_cards.get_student_groups_query",
          filters: {
            program: program_field.get_value(),
            course: course_field.get_value(),
            instructor: instructor_field.get_value(),
          },
        };
      },
      change: function () {
        let group_val = student_group_field.get_value();
        if (group_val) {
          load_students(group_val);
        } else {
          render_cards([]);
        }
      },
    });
  
    function clear_student_group() {
      student_group_field.set_value("");
      render_cards([]);
    }
  
    function load_students(student_group_name) {
      frappe.call({
        method: "ifitwala_ed.schedule.page.student_group_cards.student_group_cards.get_students_in_group",
        args: { student_group: student_group_name },
        callback: (r) => {
          if (r && r.message) {
            render_cards(r.message);
          } else {
            render_cards([]);
          }
        },
      });
    }
  
    function render_cards(students) {
      let container = $("#student-group-cards-container");
      container.empty();
  
      if (!students || !students.length) {
        container.html(`<div class="text-muted">${__("No students found")}</div>`);
        return;
      }
  
      students.forEach((stu) => {
        let image_url = stu.student_image || "/assets/frappe/images/no-image.jpg";
        let card_html = `
          <div class="student-card">
            <div class="student-img">
              <img src="${image_url}" alt="Student Image" />
            </div>
            <div class="student-info">
              <div class="student-full-name">${frappe.utils.escape_html(stu.student_full_name || "")}</div>
              <div class="student-preferred-name">${frappe.utils.escape_html(stu.student_preferred_name || "")}</div>
            </div>
          </div>
        `;
        container.append(card_html);
      });
    }
  };
  
  