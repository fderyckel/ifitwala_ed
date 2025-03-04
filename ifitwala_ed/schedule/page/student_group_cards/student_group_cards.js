// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages["student_group_cards"].on_page_load = function (wrapper) { 
  frappe.require("/assets/ifitwala_ed/css/student_group.css");
  
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Student Group Cards"),
    single_column: true,
  });

  // Load the template from public/templates/
  frappe.call({
    method: "frappe.client.get",
    args: {
      doctype: "File",
      name: "student_group_cards.html",
    },
    callback: function (r) {
      if (r.message) {
        page.main.html(r.message.content);
      }
    },
  });

  // Create filters container
  let filters_container = $('<div id="filters-container"></div>').prependTo(page.main);

  // Add filters
  let program_field = page.add_field({
    parent: filters_container,
    fieldname: "program",
    label: __("Program"),
    fieldtype: "Link",
    options: "Program",
    change: () => clear_student_group(),
  });

  let course_field = page.add_field({
    parent: filters_container,
    fieldname: "course",
    label: __("Course"),
    fieldtype: "Link",
    options: "Course",
    change: () => clear_student_group(),
  });

  let instructor_field = page.add_field({
    parent: filters_container,
    fieldname: "instructor",
    label: __("Instructor"),
    fieldtype: "Link",
    options: "Instructor",
    change: () => clear_student_group(),
  });

  let student_group_field = page.add_field({
    parent: filters_container,
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
      let card_html = frappe.render_template("student_card", {
        student_image: image_url,
        student_full_name: stu.student_full_name || "",
        student_preferred_name: stu.student_preferred_name || "",
      });
      container.append(card_html);
    });
  }
};
