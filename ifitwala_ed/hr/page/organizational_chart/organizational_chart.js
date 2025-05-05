frappe.pages["organizational-chart"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Organizational Chart"),
		single_column: true,
	});

	$(wrapper).bind("show", () => {
		frappe.require("hierarchy-chart.bundle.js", () => {
			let organizational_chart;
			// CHANGED: use get_children from ifitwala_ed instead of hrms
			let method = "ifitwala_ed.hr.page.organizational_chart.organizational_chart.get_children";

			if (frappe.is_mobile()) {
				// CHANGED: instantiate from ifitwala_ed namespace
				organizational_chart = new ifitwala_ed.HierarchyChartMobile("Employee", wrapper, method);
			} else {
				organizational_chart = new ifitwala_ed.HierarchyChart("Employee", wrapper, method);
			}

			frappe.breadcrumbs.add("HR");
			organizational_chart.show();
		});
	});
};