frappe.pages["organizational-chart"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Organizational Chart"),
		single_column: true,
	});

	$(wrapper).bind("show", () => {
		frappe.require("hierarchy-chart.bundle.js", () => {
			let organizational_chart;
			let method = "ifitwala_ed.hr.page.organizational_chart.organizational_chart.get_children";

			console.log("Fetching organization chart data...");

      // Fetch and log the data
      frappe.call({
        method: method,
        args: { organization: "IO BKK Campus" },
        callback: function (response) {
          console.log("Organization chart data:", response.message);

          if (!response.message || response.message.length === 0) {
            console.warn("No data received for the organization chart.");
            return;
          }

          if (frappe.is_mobile()) {
            organizational_chart = new ifitwala_ed.HierarchyChartMobile("Employee", wrapper, method);
          } else {
            organizational_chart = new ifitwala_ed.HierarchyChart("Employee", wrapper, method);
          }

          frappe.breadcrumbs.add("HR");

          // Slight delay to ensure DOM is ready before rendering
          setTimeout(() => {
            organizational_chart.show();
          }, 500);
        },
        error: function (err) {
          console.error("Error fetching organization chart data:", err);
        },
      });
    });
  });			
};