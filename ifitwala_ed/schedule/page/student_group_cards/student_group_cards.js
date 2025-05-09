// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages['student_group_cards'].on_page_load = function(wrapper) {

    // 🔗 Set up breadcrumb based on workspace
    const urlParams = new URLSearchParams(window.location.search);
    const workspace = urlParams.get("workspace") || "Academics";  
    frappe.breadcrumbs.add({
      label: workspace,
      route: `/app/${workspace.replace(/\s+/g, "-").toLowerCase()}`
    });

    // 🗂️ Create the main page structure
    let page = frappe.ui.make_app_page({
      parent: wrapper,
      title: 'Student Group Cards',
      single_column: true
    });

    // 📋 Add filters for Program, Course, Cohort, and Student Group
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

    // 📝 Create main content area
    $(wrapper).append(`
      <div class="filters-and-title">
        <div id="student-group-title" class="student-group-title"></div>
      </div>
      <div id="student-cards" class="student-grid container"></div>
      <button id="load-more" class="btn btn-primary">Load More</button>
    `);

    // 📊 Pagination State
    let start = 0;
    const page_length = 25;
    let total_students = 0;
    let group_info = {};

    // 📅 Update the title based on group info
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

    // 📸 Helper function to get optimized student image
    function get_student_image(image_url) {
      // Fallback to default if no image is provided
      if (!image_url || !image_url.startsWith("/files/student/")) {
          return "/assets/ifitwala_ed/images/default_student_image.png";
      }

      // Attempt to use the thumb_ version
      const filename = image_url.split("/").pop().replace(/\s+/g, "_").replace(/[-]/g, "_").toLowerCase();
      const thumb_url = `/files/gallery_resized/student/thumb_${filename}.webp`;

      // Synchronous existence check using HEAD request
      let thumb_exists = false;
      const xhr = new XMLHttpRequest();
      xhr.open("HEAD", thumb_url, false);
      xhr.onload = function() {
          if (xhr.status === 200) {
              thumb_exists = true;
          }
      };
      xhr.send();

      // Use the thumb if it exists, otherwise the original
      return thumb_exists ? thumb_url : image_url;
    }


    // 📝 Render a single student card
    function renderStudentCard(student) {
      const student_name = frappe.utils.escape_html(student.student_name);
      const preferred_name = frappe.utils.escape_html(student.preferred_name || "");
      const student_id = frappe.utils.escape_html(student.student);
      const img_src = get_student_image(student.student_image);

      // 🎂 Birthday Icon Logic
      let birthday_icon = '';
      if (student.birth_date) {
        try {
          const birth_date = frappe.datetime.str_to_obj(student.birth_date);
          const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());
          const birth_this_year = new Date(today.getFullYear(), birth_date.getMonth(), birth_date.getDate());
          const diff_days = Math.floor((birth_this_year - today) / (1000 * 60 * 60 * 24));

          if (Math.abs(diff_days) <= 5) {
            const formatted_date = moment(birth_date).format("dddd, MMMM Do");
            birthday_icon = `
              <span class="birthday-icon" title="${__("Birthday on {0}", [formatted_date])}">🎂</span>
            `;
          }
        } catch (e) {
          console.warn("Invalid birth_date for student", student.student, e);
        }
      }

      // 🚨 Medical Alert Logic
      let health_icon = '';
      if (student.medical_info) {
        health_icon = `
          <span class="medical-alert" title="${__("Medical Note Available")}" 
            onclick='frappe.msgprint({
              title: "Health Note for ${student_name}",
              message: \`${student.medical_info}\`,
              indicator: "red"
            })'>
            &#x2716;
          </span>
        `;
      }

      // 📦 Return the full card HTML
      return `
        <div class="student-card">
          <a href="/app/student/${student_id}" target="_blank" rel="noopener">
            <img src="${img_src}" class="student-image" loading="lazy">
          </a>
          <div class="student-name">
            <a href="/app/student/${student_id}" target="_blank" rel="noopener">
              ${student_name}
            </a>
            ${health_icon}
            ${birthday_icon}
          </div>
          ${preferred_name ? `<div class="student-preferred-name">${preferred_name}</div>` : ""}
        </div>
      `;
    }

    // 🗂️ Fetch and render student cards
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
          group_info = data.message.group_info || {};
          data.message.students.forEach(student => {
            const card_html = renderStudentCard(student);
            $('#student-cards').append(card_html);
          });
          $('#load-more').toggle(start < total_students);
          update_title();
        }
      });
    }

    // 🖱️ Load more button
    $('#load-more').click(() => fetch_students());
};
