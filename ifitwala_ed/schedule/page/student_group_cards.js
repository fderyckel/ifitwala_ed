frappe.pages['student_group_cards'].on_page_load = function(wrapper) {
  // Parse the route; e.g. route = ["student_group_cards", "<group_id>"]
  const route = frappe.get_route();
  const group_id = route[1];

  // Track pagination
  let start = 0;
  const page_length = 25;

  // Create a container for the student cards and a "Load More" button
  $(wrapper).html(`
      <div class="student-group-cards">
          <div class="row student-cards-container" style="margin: 0 10px;"></div>
          <div class="text-center" style="margin-top: 16px;">
              <button class="btn btn-primary btn-load-more">Load More</button>
          </div>
      </div>
  `);

  const $container = $(wrapper).find('.student-cards-container');
  const $loadMoreBtn = $(wrapper).find('.btn-load-more');

  // Function to fetch a batch of students from the server
  function load_students() {
      frappe.call({
          method: "ifitwala_ed.schedule.page.student_group_cards.student_group_cards.get_students",
          args: {
              group_id: group_id,
              start: start,
              page_length: page_length
          },
          callback: function(r) {
              if (r.message) {
                  const students = r.message;
                  // If no students returned, disable the button
                  if (!students.length) {
                      $loadMoreBtn.text("No More Students").prop("disabled", true);
                      return;
                  }

                  // Render each student as a card in the browser
                  students.forEach(student => {
                      render_student_card(student);
                  });

                  // Increase start pointer for next "Load More" call
                  start += page_length;
              }
          }
      });
  }

  // A helper to build & append a single student's card HTML
  function render_student_card(student) {
      const img_url = student.student_image || "/assets/frappe/images/default-placeholder.png";
      const dob = student.student_date_of_birth || "N/A";
      
      // Concatenate first/middle/last name
      const full_name = [
          student.student_full_name,
          student.student_preferred_name,
      ].filter(Boolean).join(" ");

      // We'll use Bootstrap (from Frappe) classes for a 4-column layout on md screens
      const card_html = `
          <div class="student-card col-md-3" style="padding: 8px;">
              <div class="card" style="border: 1px solid #eaeaea; border-radius: 4px; padding: 12px;">
                  <div class="text-center" style="margin-bottom: 8px;">
                      <img src="${img_url}" class="img-fluid"
                           style="border-radius: 50%; max-width: 100px; height: auto;" />
                  </div>
                  <div class="student-info text-center">
                      <h5 style="margin-bottom: 4px;">${full_name}</h5>
                      <div class="text-muted">DOB: ${dob}</div>
                  </div>
              </div>
          </div>
      `;
      $container.append(card_html);
  }

  // Initial load on page open
  load_students();

  // "Load More" button to fetch next set of 25
  $loadMoreBtn.on("click", function() {
      load_students();
  });
};
