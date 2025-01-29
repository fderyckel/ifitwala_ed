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

			if (frappe.is_mobile()) {
				organizational_chart = new ifitwala_ed.HierarchyChartMobile("Employee", wrapper, method);
			} else {
				organizational_chart = new ifitwala_ed.HierarchyChart("Employee", wrapper, method);
			}

			frappe.breadcrumbs.add("HR");
			organizational_chart.show();
		});
	});
};