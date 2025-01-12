frappe.provide("ifitwala_ed.student-portal");

ifitwala_ed.student_portal = {
    init: function() {
        // Handle Navigation Clicks
        $(".ifitwala-student-portal .sidebar ul li a").on("click", function(e) {
            e.preventDefault();
            let section = $(this).data("section");
            ifitwala_ed.student_portal.load_section(section);
        });

        // Load initial section
        ifitwala_ed.student_portal.load_section("about-me");
    },

    load_section: function(section) {
        let content_area = $(".ifitwala-student-portal .content-area");
        content_area.empty();

        if (section === "student-log") {
            ifitwala_ed.student_portal.load_student_log(content_area);
        } else if (section === "about-me") {
            ifitwala_ed.student_portal.load_about_me(content_area);
        }
    },

    load_student_log: function(content_area) {
        frappe.call({
            method: "ifitwala_ed.utilities.student_portal_utils.get_student_logs",
            callback: function(r) {
                if (r.message) {
                    // Render the student_log.html template with the logs data
                    r.message.logs = r.message;
                    frappe.render_template("student_log", r.message).then(html => {
                        content_area.html(html);
                    });
                } else {
                    content_area.html("<p>No Student Logs found.</p>");
                }
            }
        });
    },

    load_about_me: function(content_area) {
        frappe.call({
            method: "ifitwala_ed.utilities.student_portal_utils.get_context",
            callback: function(r) {
                if (r.message) {
                    // Display Personal Info (using a simple div for now)
                    frappe.render_template("about_me", r.message).then(html => {
                        content_area.html(html);
                    });
                } else {
                    content_area.html("<p>Could not retrieve student information.</p>");
                }
            }
        });
    }
};

frappe.ready(function() {
    if (frappe.get_route()[0] === "student-portal") {
        ifitwala_ed.student_portal.init();
    }
});