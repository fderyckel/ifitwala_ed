// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Enrollment Report"] = {
	"filters": [
			{
					"fieldname": "report_type",
					"label": "Report Type",
					"fieldtype": "Select",
					"options": "\nProgram\nCourse",
					"default": "Program"
			},
			{
					"fieldname": "school",
					"label": "School",
					"fieldtype": "Link",
					"options": "School"
			},
			{
					"fieldname": "program",
					"label": "Program",
					"fieldtype": "Link",
					"options": "Program"
			},
			{
					"fieldname": "academic_year",
					"label": "Academic Year",
					"fieldtype": "Link",
					"options": "Academic Year",
					"depends_on": "eval:doc.report_type=='Course' || doc.report_type=='Program'", 
					"get_query": function (doc) {
						let school = frappe.query_report.get_filter_value("school");
						if (school) {
								return {
										query: "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.get_academic_years_for_school",
										filters: { school: school }
								};
						}
					}
			}
	],
	"chart_type": "bar",
	"default_columns": 2,
	
	onload: function(report) {
		frappe.after_ajax(() => {
			console.log("RAW CHART DATA:", report.chart);  // Add this line
				const setupChart = () => {
						const chart = report.chartObj?.chart;
						if (!chart) return;

						// Clear existing legend first
						const existingLegend = chart.wrapper.parentElement.querySelector('.custom-legend');
						if (existingLegend) existingLegend.remove();

						// Get chart data
						const breakdown = report.chart?.custom_options?.tooltip_breakdown || {};
						const legend_labels = report.chart?.custom_options?.legend_labels || [];
						const legend_colors = report.chart?.custom_options?.legend_colors || [];

						// 1. Update tooltips
						chart.options.tooltipOptions = {
								formatTooltipX: label => label,
								formatTooltipY: (value, name, opts, index) => {
										const label = chart.data.labels[index];
										console.log("TOOLTIP DATA FOR:", label, "BREAKDOWN:", breakdown[label]); 
										const items = breakdown[label] || [];
										return items.length > 0 
												? `<strong>${label}</strong><br>${items.join("<br>")}`
												: `${value}`;
								}
						};

						// 2. Create legend if needed
						if (legend_labels.length > 0) {
								const legend = document.createElement("div");
								legend.style.position = "absolute";
								legend.style.bottom = "-40px";
								legend.style.left = "20px";
								legend.style.display = "flex";
								legend.style.gap = "12px";
								legend.style.padding = "8px";
								legend.style.background = "white";
								legend.style.border = "1px solid #ddd";
								legend.style.borderRadius = "4px";
								

								legend_labels.forEach((label, i) => {
										const item = document.createElement("div");
										item.style.display = "flex";
										item.style.alignItems = "center";
										item.innerHTML = `
												<div style="width:16px; height:16px; 
														background:${legend_colors[i] || '#999'};
														border-radius:4px; margin-right:8px;">
												</div>
												<span style="font-size:12px">${label}</span>
										`;
										legend.appendChild(item);
								});

								// Insert after chart
								chart.wrapper.parentElement.appendChild(legend);
						}

						chart.update();
				};

				// Wait for chart to render
				let tries = 0;
				const interval = setInterval(() => {
						if (report.chartObj || tries > 20) {
								clearInterval(interval);
								setupChart();
						}
						tries++;
				}, 100);
		});
	}
};
