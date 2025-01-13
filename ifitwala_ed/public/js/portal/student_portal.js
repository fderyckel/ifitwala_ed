frappe.provide("ifitwala_ed.student_portal");

ifitwala_ed.student_portal = {
    contextData: null, // Store the context data fetched once

    init: function() {
        // Fetch context data on initialization
        frappe.call({
            method: "ifitwala_ed.www.student_portal.student_portal.get_context",
            callback: function(r) {
                if (r.message) {
                    ifitwala_ed.student_portal.contextData = r.message;
                    ifitwala_ed.student_portal.load_section("about-me"); // Load initial section
                } else {
                    // Handle case where context data could not be fetched
                    $(".ifitwala-student-portal .content-area").html("<p>Could not load portal data.</p>");
                }
            }
        });

        // Handle Navigation Clicks
        $(".ifitwala-student-portal .sidebar ul li a").on("click", function(e) {
            e.preventDefault();
            let section = $(this).data("section");
            ifitwala_ed.student_portal.load_section(section);
        });
    },

    load_section: function(section) {
      let content_area = $(".ifitwala-student-portal .content-area");
        // Use stored context data
        if (!ifitwala_ed.student_portal.contextData) {
            content_area.html("<p>Loading...</p>"); // Or handle error appropriately
            return;
        }

        let template_path = `student_portal/${section}`;

        frappe.render_template(template_path, ifitwala_ed.student_portal.contextData)
          .then(html => {
            content_area.html(html);
        });
    }
};

frappe.ready(function() {
    if (frappe.get_route()[0] === "student_portal") {
        ifitwala_ed.student_portal.init();
    }
});